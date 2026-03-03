# app/main.py

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Dict, Callable, Awaitable, TypeVar, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from contextlib import asynccontextmanager

from app.config import Settings, get_settings
from app.models import MessageClass, BoggleClass
import app.games.boggle as bg
import app.sayings.sayings as say
from app.connectors.vestaboard import (
    VestaboardConnector,
    VestaboardError,
    VestaboardAuthError,
    VestaboardInvalidCharsError
)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

T = TypeVar('T')

@dataclass
class ActionConfig:
    success_message: str
    error_message: str
    source: str = 'rw'

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Application startup: Initializing Vestaboard connector...")
    settings = get_settings()
    try:
        connector = VestaboardConnector(settings)
        app.state.vestaboard_connector = connector
        log.info("Vestaboard connector initialized.")

        log.info("Application startup: Initializing database connection pool...")
        say.init_db_pool(settings)

        yield
    finally:
        log.info("Application shutdown: Closing database connection pool...")
        say.close_db_pool()

        log.info("Application shutdown: Closing Vestaboard connector...")
        if hasattr(app.state, 'vestaboard_connector') and app.state.vestaboard_connector:
            await app.state.vestaboard_connector.close()
            log.info("Vestaboard connector closed.")
        else:
            log.warning("Vestaboard connector not found during shutdown.")

async def get_vestaboard_connector(request: Request) -> VestaboardConnector:
    connector = getattr(request.app.state, "vestaboard_connector", None)
    if connector is None:
        log.error("Vestaboard connector not found in application state.")
        raise HTTPException(status_code=500, detail="Internal Server Error: Vestaboard connector not initialized")
    return connector

app = FastAPI(
    title="Home Automation Helper API",
    description="API for controlling Vestaboard, playing games, and getting sayings.",
    lifespan=lifespan
)

async def handle_vestaboard_action(
    action: Callable[[], Awaitable[T]],
    error_prefix: str
) -> T:
    try:
        return await action()
    except VestaboardInvalidCharsError as e:
        log.warning(f"{error_prefix}: Invalid characters. {e}")
        raise HTTPException(status_code=422, detail=f"{error_prefix}: Invalid characters. {e}")
    except VestaboardAuthError as e:
        log.error(f"{error_prefix}: Authentication error. {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"{error_prefix}: Vestaboard authentication error.")
    except VestaboardError as e:
        log.error(f"{error_prefix}: Vestaboard API error. {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"{error_prefix}: Error communicating with Vestaboard.")
    except Exception as e:
        log.exception(f"Unexpected error during Vestaboard action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{error_prefix}: An unexpected internal error occurred.")


async def get_and_send_quote(
    quote_func: Callable[[Settings], str | None],
    config: ActionConfig,
    settings: Settings,
    connector: VestaboardConnector,
    **kwargs
) -> Dict[str, str]:
    try:
        data = await asyncio.to_thread(quote_func, settings=settings)
        if data is None:
            log.warning(f"{config.error_message}: Quote function returned None (DB disabled or no quote found).")
            raise HTTPException(status_code=404, detail=f"{config.error_message}: Quote not found or DB disabled")

        await handle_vestaboard_action(
            lambda: connector.send_message(data, source=config.source, **kwargs),
            config.error_message
        )
        log.info(f"Successfully sent quote to board: {config.success_message}")
        return {"message": config.success_message}
    except HTTPException:
        raise
    except ConnectionError as e:
        log.error(f"Database connection error getting quote: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"{config.error_message}: Database unavailable")
    except Exception as e:
        log.exception(f"Unexpected error in quote process: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{config.error_message}: An unexpected internal error occurred")

async def get_and_send_art(
    art_func: Callable[[Settings], List[List[int]] | tuple[List[List[int]], str] | None],
    config: ActionConfig,
    settings: Settings,
    connector: VestaboardConnector,
    **kwargs
) -> Dict[str, str]:
    try:
        result = await asyncio.to_thread(art_func, settings=settings)
        if result is None:
            log.warning(f"{config.error_message}: Art function returned None (DB disabled or no art found).")
            raise HTTPException(status_code=404, detail=f"{config.error_message}: Art not found or DB disabled")

        title = "Unknown"
        if isinstance(result, tuple):
            data, fetched_title = result
            if fetched_title:
                title = fetched_title
        else:
            data = result

        await handle_vestaboard_action(
            lambda: connector.send_array(data, source=config.source, **kwargs),
            config.error_message
        )
        log.info(f"Successfully sent art to board: {config.success_message}")
        return {"message": config.success_message, "title": title}
    except HTTPException:
        raise
    except ConnectionError as e:
        log.error(f"Database connection error getting art: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"{config.error_message}: Database unavailable")
    except Exception as e:
        log.exception(f"Unexpected error in art process: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{config.error_message}: An unexpected internal error occurred")


@app.post("/games/boggle", status_code=202)
async def start_boggle_game(
    item: BoggleClass,
    background_tasks: BackgroundTasks,
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
):
    if item.size not in (4, 5):
        raise HTTPException(status_code=400, detail="Invalid Boggle size. Must be 4 or 5.")

    try:
        start_grid, end_grid = bg.generate_boggle_grids(item.size)
    except Exception as e:
        log.exception(f"Error generating Boggle grids: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating game grids")

    async def schedule_end_boggle_display(grid: List[List[int]], conn: VestaboardConnector):
        await asyncio.sleep(200)
        log.info("Boggle timer finished. Sending end grid.")
        try:
            await conn.send_array(grid, source='rw')
            log.info("Successfully sent Boggle end grid.")
        except Exception as e:
            log.error(f"Error sending Boggle end grid in background task: {e}", exc_info=True)

    await handle_vestaboard_action(
        lambda: connector.send_array(start_grid, source='rw'),
        f"Vestaboard error initiating Boggle {item.size}x{item.size} game"
    )

    background_tasks.add_task(schedule_end_boggle_display, end_grid, connector)
    return {"message": f"Boggle {item.size}x{item.size} game queued."}


@app.get("/sfw_quote")
async def get_sfw_quote(
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    return await get_and_send_quote(
        quote_func=say.GetSingleRandSfwS,
        config=ActionConfig(
            success_message="Random SFW quote queued",
            error_message="Error getting SFW quote",
            source='rw'
        ),
        settings=settings,
        connector=connector
    )

@app.get("/sfw_quote/local")
async def get_sfw_quote_local(
    strategy: Optional[str] = None,
    step_interval_ms: Optional[int] = None,
    step_size: Optional[int] = None,
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    return await get_and_send_quote(
        quote_func=say.GetSingleRandSfwS,
        config=ActionConfig(
            success_message="Random SFW quote queued (Local)",
            error_message="Error getting SFW quote",
            source='local'
        ),
        settings=settings,
        connector=connector,
        strategy=strategy,
        step_interval_ms=step_interval_ms,
        step_size=step_size
    )

@app.get("/nsfw_quote")
async def get_nsfw_quote(
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    return await get_and_send_quote(
        quote_func=say.GetSingleRandNsfwS,
        config=ActionConfig(
            success_message="Random NSFW quote queued",
            error_message="Error getting NSFW quote",
            source='rw'
        ),
        settings=settings,
        connector=connector
    )

@app.get("/nsfw_quote/local")
async def get_nsfw_quote_local(
    strategy: Optional[str] = None,
    step_interval_ms: Optional[int] = None,
    step_size: Optional[int] = None,
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    return await get_and_send_quote(
        quote_func=say.GetSingleRandNsfwS,
        config=ActionConfig(
            success_message="Random NSFW quote queued (Local)",
            error_message="Error getting NSFW quote",
            source='local'
        ),
        settings=settings,
        connector=connector,
        strategy=strategy,
        step_interval_ms=step_interval_ms,
        step_size=step_size
    )

@app.get("/art")
async def get_random_art(
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    return await get_and_send_art(
        art_func=say.GetSingleRandArt,
        config=ActionConfig(
            success_message="Random art queued",
            error_message="Error getting art",
            source='rw'
        ),
        settings=settings,
        connector=connector
    )

@app.get("/art/local")
async def get_random_art_local(
    strategy: Optional[str] = None,
    step_interval_ms: Optional[int] = None,
    step_size: Optional[int] = None,
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    return await get_and_send_art(
        art_func=say.GetSingleRandArt,
        config=ActionConfig(
            success_message="Random art queued (Local)",
            error_message="Error getting art",
            source='local'
        ),
        settings=settings,
        connector=connector,
        strategy=strategy,
        step_interval_ms=step_interval_ms,
        step_size=step_size
    )

@app.post("/message", status_code=200)
async def post_message(
    item: MessageClass,
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    if not item.message:
        raise HTTPException(status_code=400, detail="No message content provided.")

    await handle_vestaboard_action(
        lambda: connector.send_message(item.message, source='rw'),
        "Error sending message"
    )
    return {"message": "Message sent successfully"}

@app.post("/message/local", status_code=200)
async def post_message_local(
    item: MessageClass,
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    if not item.message:
        raise HTTPException(status_code=400, detail="No message content provided.")

    await handle_vestaboard_action(
        lambda: connector.send_message(
            item.message,
            source='local',
            strategy=item.strategy,
            step_interval_ms=item.step_interval_ms,
            step_size=item.step_size
        ),
        "Error sending message"
    )
    return {"message": "Message sent successfully (Local)"}

@app.get("/")
async def home() -> Dict[str, str]:
    return {"message": "Hello, World! I am the home automation helper"}
