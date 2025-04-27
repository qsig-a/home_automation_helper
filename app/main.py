from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic_settings import BaseSettings 
from typing import Optional 
from app.models import MessageClass, BoggleClass 

import asyncio
import app.games.boggle as bg
import app.connectors.vestaboard as board
import app.sayings.sayings as say

# --- Configuration Management ---
class Settings(BaseSettings):
    saying_db_user: Optional[str] = None
    saying_db_pass: Optional[str] = None
    saying_db_host: Optional[str] = None
    saying_db_port: Optional[str] = None
    saying_db_name: Optional[str] = None
    saying_db_enable: str = "0" # Default to disabled

    # This tells Pydantic to read from environment variables
    class Config:
        env_file = '.env' # Optional: load from a .env file
        extra = 'ignore' # Ignore extra env vars not defined here

# Dependency function to get settings
def get_settings() -> Settings:
    # This ensures settings are loaded only once if needed multiple times
    return Settings()

# --- FastAPI Application ---
app = FastAPI(
    title="Home Automation Helper API",
    description="API for controlling Vestaboard, playing games, and getting sayings."
)

# --- Helper Functions ---

# Define the background task for ending the Boggle game
async def schedule_end_boggle(end_grid: list):
    """
    Waits for the game duration and then sends the end grid to the board.
    Uses asyncio.sleep for non-blocking wait within an async function.
    """
    await asyncio.sleep(200) # Game duration: 3 minutes and 20 seconds
    try:
        # Note: If board.SendArray is a blocking I/O call, it should be run
        # in a thread pool: await asyncio.to_thread(board.SendArray, end_grid)
        result = board.SendArray(end_grid) 
        if result != 0:
            # Log error or add more robust error handling/reporting here
            print(f"Error sending Boggle end grid. Result: {result}") 
            
    except Exception as e:
        # Log exception or add more robust error handling/reporting here
        print(f"Exception during schedule_end_boggle: {e}") 

def _get_and_send_quote(quote_func: callable, success_message: str, error_message: str, settings: Settings = Depends(get_settings)):
    """Helper function to get and send a quote, handling DB enable check and board communication."""
    if settings.saying_db_enable != "1":
        raise HTTPException(status_code=405, detail="Sayings DB Not Enabled")

    try:
        data = quote_func()
        if not data: # Check if data is empty or None
             raise HTTPException(status_code=500, detail=f"{error_message}: No data received from DB")

        # Assumes board.SendMessage is blocking; FastAPI handles it in a threadpool for sync routes.
        send_result = board.SendMessage(data)

        if send_result == 0:
            return {"message": success_message}
        else:
            # Log the specific error if possible
            print(f"Error sending quote to Vestaboard. Result: {send_result}")
            raise HTTPException(status_code=500, detail=f"{error_message}: Error sending to board")

    except Exception as e:
        # Log the exception
        print(f"Error in quote fetching/sending: {e}")
        raise HTTPException(status_code=500, detail=f"{error_message}: An unexpected error occurred")


# --- API Endpoints ---

@app.post("/games/boggle", status_code=202) # 202 Accepted is suitable for background tasks
async def start_boggle_game(item: BoggleClass, background_tasks: BackgroundTasks, settings: Settings = Depends(get_settings)):
    """
    Starts a 4x4 or 5x5 Boggle game.
    Sends the start grid immediately and schedules the end grid display after ~3m20s.
    """
    if item.size not in (4, 5):
        raise HTTPException(status_code=400, detail="Invalid Boggle size. Must be 4 or 5.")

    try:
        start_grid, end_grid = bg.generate_boggle_grids(item.size)
        if not start_grid or not end_grid: # Basic check if generation failed
             raise ValueError("Failed to generate Boggle grids.")

    except Exception as e:
        print(f"Error generating Boggle grids: {e}") # Log error
        raise HTTPException(status_code=500, detail="Error creating game grids")

    try:
        # Assumes board.SendArray is blocking. If it's async, use 'await'.
        send_result = board.SendArray(start_grid) 

        if send_result != 0:
             # Log error
             print(f"Error sending Boggle start grid. Result: {send_result}")
             raise HTTPException(status_code=500, detail="Error sending start grid to board")

        # If sending the start grid was successful, schedule the end grid
        background_tasks.add_task(schedule_end_boggle, end_grid)
        return {"message": f"Boggle {item.size}x{item.size} game queued."}

    except HTTPException as http_exc:
        raise http_exc # Re-raise HTTP exceptions
    except Exception as e:
        print(f"Error sending Boggle start grid: {e}") # Log error
        raise HTTPException(status_code=500, detail="Error initiating game on board")


@app.get("/sfw_quote")
def get_sfw_quote(quote_data: dict = Depends(lambda: _get_and_send_quote(
        say.GetSingleRandSfwS,
        "Random SFW quote queued",
        "Error getting SFW quote"
    ))):
    """Gets a random SFW saying from the local DB and sends it to the board."""
    return quote_data # Return the result from the helper function

@app.get("/nsfw_quote")
def get_nsfw_quote(quote_data: dict = Depends(lambda: _get_and_send_quote(
        say.GetSingleRandNsfwS,
        "Random NSFW quote queued",
        "Error getting NSFW quote"
    ))):
    """Gets a random NSFW saying from the local DB and sends it to the board."""
    return quote_data # Return the result from the helper function


@app.post("/message", status_code=200)
def post_message(item: MessageClass, settings: Settings = Depends(get_settings)):
    """Posts a message directly to the Vestaboard."""
    if not item.message: # Simplified check for None or empty string
        raise HTTPException(status_code=400, detail="No message content provided.")

    try:
        # Assumes board.SendMessage is blocking. If it's async, change endpoint to async def and use await.
        send_result = board.SendMessage(item.message)

        if send_result == 0:
            return {"message": "Message sent successfully"}
        elif send_result == 1:
            # Log error if possible
            print("Error sending message to Vestaboard (Code 1)")
            raise HTTPException(status_code=500, detail="Error sending message to board")
        elif send_result == 2:
            raise HTTPException(
                status_code=422,
                detail="Invalid characters in message. See Vestaboard documentation."
            )
        else:
            # Handle unexpected return codes
            print(f"Unexpected result from board.SendMessage: {send_result}")
            raise HTTPException(status_code=500, detail="Unknown error sending message")

    except HTTPException as http_exc:
        raise http_exc # Re-raise HTTP exceptions
    except Exception as e:
        # Log the exception
        print(f"Exception posting message: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while sending the message")


@app.get("/")
async def home():
    """Basic health check / home endpoint."""
    return {"message": "Hello, World! I am the home automation helper"}