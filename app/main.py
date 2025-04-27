# app/main.py

import asyncio
import logging
from typing import AsyncGenerator, List, Dict, Any, Callable # Added more specific types

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from contextlib import asynccontextmanager

# Central configuration and settings getter
from app.config import Settings, get_settings

# Models
from app.models import MessageClass, BoggleClass

# Game logic
import app.games.boggle as bg

# Saying logic
import app.sayings.sayings as say

# Import the async connector and its exceptions
from app.connectors.vestaboard import (
    VestaboardConnector,
    VestaboardError,
    VestaboardAuthError,
    VestaboardInvalidCharsError
)

# Setup basic logging
log = logging.getLogger(__name__)
# Ensure logging is configured (e.g., in your app startup or main script)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# --- Lifespan Management for Shared Resources ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup
    log.info("Application startup: Initializing Vestaboard connector...")
    settings = get_settings() # Get settings
    connector = None
    try:
        connector = VestaboardConnector(settings)
        app.state.vestaboard_connector = connector # Store connector in app state
        log.info("Vestaboard connector initialized and stored in app state.")
        yield # Application runs here
    finally:
        # Runs on shutdown
        log.info("Application shutdown: Closing Vestaboard connector...")
        if hasattr(app.state, 'vestaboard_connector') and app.state.vestaboard_connector:
             await app.state.vestaboard_connector.close()
             log.info("Vestaboard connector closed.")
        else:
             log.warning("Vestaboard connector not found in app state during shutdown.")


# --- Dependency for Vestaboard Connector ---

async def get_vestaboard_connector(request: Request) -> VestaboardConnector:
    """
    FastAPI dependency that retrieves the shared VestaboardConnector
    instance created during application startup (via lifespan).
    """
    connector = getattr(request.app.state, "vestaboard_connector", None)
    if connector is None:
        log.error("Vestaboard connector not found in application state. Lifespan did not run correctly.")
        # Raise an internal server error if the connector isn't available
        raise HTTPException(status_code=500, detail="Internal Server Error: Vestaboard connector not initialized")
    return connector


# --- FastAPI Application ---
app = FastAPI(
    title="Home Automation Helper API",
    description="API for controlling Vestaboard, playing games, and getting sayings.",
    lifespan=lifespan
)


# --- Helper Functions ---

async def _get_and_send_quote(
    quote_func: Callable[[Settings], str | None], # More specific callable signature
    success_message: str,
    error_message: str,
    settings: Settings,
    connector: VestaboardConnector
) -> Dict[str, str]:
    """Async helper function to get a quote and send it via VestaboardConnector."""
    try:
        # Run synchronous DB/quote logic in a thread pool to avoid blocking event loop
        data = await asyncio.to_thread(quote_func, settings=settings)

        if data is None:
             log.warning(f"{error_message}: Quote function returned None (DB disabled or no quote found).")
             raise HTTPException(status_code=404, detail=f"{error_message}: Quote not found or DB disabled")

        # Send the message using the async connector
        await connector.send_message(data)

        log.info(f"Successfully sent quote to board: {success_message}")
        return {"message": success_message} # Return dict on success

    except (VestaboardInvalidCharsError, VestaboardAuthError, VestaboardError) as vex:
         # Catch specific Vestaboard errors
         log.error(f"Vestaboard error sending quote: {vex}", exc_info=True)
         if isinstance(vex, VestaboardInvalidCharsError):
             raise HTTPException(status_code=422, detail=f"{error_message}: Invalid characters in quote.")
         elif isinstance(vex, VestaboardAuthError):
            raise HTTPException(status_code=503, detail=f"{error_message}: Vestaboard authentication error.")
         else: # General VestaboardError
            raise HTTPException(status_code=502, detail=f"{error_message}: Error communicating with Vestaboard.")
    except HTTPException as http_exc:
         raise http_exc
    except ConnectionError as conn_err: # Catch DB connection errors specifically
        log.error(f"Database connection error getting quote: {conn_err}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"{error_message}: Database unavailable")
    except Exception as e:
        # Catch any other unexpected errors during the process
        log.exception(f"Unexpected error in quote process: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{error_message}: An unexpected internal error occurred")


# --- API Endpoints ---

@app.post("/games/boggle", status_code=202) # 202 Accepted for background task
async def start_boggle_game(
    item: BoggleClass,
    background_tasks: BackgroundTasks,
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
):
    """
    Starts a 4x4 or 5x5 Boggle game. Sends start grid, schedules end grid. (Async)
    """
    if item.size not in (4, 5):
        raise HTTPException(status_code=400, detail="Invalid Boggle size. Must be 4 or 5.")

    try:
        # Assuming grid generation is CPU-bound or fast
        start_grid, end_grid = bg.generate_boggle_grids(item.size)
        if not start_grid or not end_grid:
             raise ValueError("Failed to generate Boggle grids.")

    except Exception as e:
        log.exception(f"Error generating Boggle grids: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating game grids")

    # Define the background task *inside* the endpoint to capture 'connector' and 'end_grid'
    async def schedule_end_boggle_display(grid_to_send: List[List[int]], conn: VestaboardConnector):
        """Background task to wait and send the final Boggle grid."""
        await asyncio.sleep(200) # Game duration
        log.info("Boggle timer finished. Sending end grid.")
        try:
            await conn.send_array(grid_to_send)
            log.info("Successfully sent Boggle end grid.")
        except Exception as bg_task_err:
            # Log errors from background task - can't easily return HTTP errors here
            log.error(f"Error sending Boggle end grid in background task: {bg_task_err}", exc_info=True)

    try:
        # Send the initial grid using the injected connector
        await connector.send_array(start_grid)
        log.info(f"Boggle {item.size}x{item.size} start grid sent.")

        # Schedule the background task
        background_tasks.add_task(schedule_end_boggle_display, end_grid, connector)
        return {"message": f"Boggle {item.size}x{item.size} game queued."}

    except (VestaboardAuthError, VestaboardError) as vex:
        log.error(f"Vestaboard error sending start grid: {vex}", exc_info=True)
        status_code = 503 if isinstance(vex, VestaboardAuthError) else 502
        raise HTTPException(status_code=status_code, detail=f"Vestaboard error initiating game: {vex}")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        log.exception(f"Unexpected error sending Boggle start grid: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error initiating game on board")


# --- Quote Endpoints (Async) ---

@app.get("/sfw_quote")
async def get_sfw_quote(
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    """Gets a random SFW saying and sends it to the board. (Async)"""
    return await _get_and_send_quote(
        quote_func=say.GetSingleRandSfwS,
        success_message="Random SFW quote queued",
        error_message="Error getting SFW quote",
        settings=settings,
        connector=connector
    )

@app.get("/nsfw_quote")
async def get_nsfw_quote(
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    """Gets a random NSFW saying and sends it to the board. (Async)"""
    # Call the helper function directly and return its result
    return await _get_and_send_quote(
        quote_func=say.GetSingleRandNsfwS,
        success_message="Random NSFW quote queued",
        error_message="Error getting NSFW quote",
        settings=settings,
        connector=connector
    )


# --- Message Endpoint (Async) ---

@app.post("/message", status_code=200)
async def post_message(
    item: MessageClass,
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    """Posts a message directly to the Vestaboard. (Async)"""
    if not item.message:
        raise HTTPException(status_code=400, detail="No message content provided.")

    try:
        # Use the async connector method
        await connector.send_message(item.message)
        return {"message": "Message sent successfully"}

    except VestaboardInvalidCharsError as vic_err:
        log.warning(f"Invalid characters in message post: {vic_err}")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid characters in message. See Vestaboard docs. Error: {vic_err}"
        )
    except (VestaboardAuthError, VestaboardError) as vex:
        log.error(f"Vestaboard error posting message: {vex}", exc_info=True)
        status_code = 503 if isinstance(vex, VestaboardAuthError) else 502
        raise HTTPException(status_code=status_code, detail=f"Vestaboard error sending message: {vex}")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        log.exception(f"Unexpected error posting message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while sending the message")


# --- Home Endpoint ---

@app.get("/")
async def home() -> Dict[str, str]:
    """Basic health check / home endpoint."""
    return {"message": "Hello, World! I am the home automation helper"}