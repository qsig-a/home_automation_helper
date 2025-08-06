import pytest
import pytest_asyncio
import asyncio # Added import for asyncio
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.config import Settings
from app.connectors.vestaboard import (
    VestaboardConnector,
    VestaboardError,
    VestaboardAuthError,
    VestaboardInvalidCharsError
)
from app.models import MessageClass, BoggleClass
import app.sayings.sayings as say
import app.games.boggle as bg

# Basic test to ensure the file is created and pytest can find it
def test_initial_setup():
    assert True


# --- Test for GET / endpoint ---
def test_home_get(client: TestClient):
    """
    Tests the home endpoint (GET /).
    - Checks for a 200 OK status.
    - Verifies the response JSON.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World! I am the home automation helper"}


# --- Tests for POST /message endpoint ---
def test_post_message_success(client: TestClient, mock_vestaboard_connector: AsyncMock):
    """Tests successful message posting."""
    test_message = "Hello Vestaboard"
    response = client.post("/message", json={"message": test_message})
    assert response.status_code == 200
    assert response.json() == {"message": "Message sent successfully"}
    mock_vestaboard_connector.send_message.assert_called_once_with(test_message)

def test_post_message_empty_payload(client: TestClient):
    """Tests posting an empty message."""
    response = client.post("/message", json={"message": ""})
    assert response.status_code == 400 # Based on current main.py logic
    # The detail could be more specific, but current main.py raises HTTPException(400) before model validation for empty string
    # assert response.json() == {"detail": "No message content provided."} # This would be ideal

def test_post_message_no_content_provided(client: TestClient):
    """Tests posting with no message content, which should be caught by pydantic model."""
    # Pydantic v2 should raise 422 for invalid model
    response = client.post("/message", json={}) # Empty JSON
    assert response.status_code == 422 # Unprocessable Entity due to Pydantic validation
    # Example of how to check for Pydantic error details if needed
    # assert any(err["type"] == "missing" and err["loc"] == ["body", "message"] for err in response.json()["detail"])


def test_post_message_invalid_chars_error(client: TestClient, mock_vestaboard_connector: AsyncMock):
    """Tests VestaboardInvalidCharsError handling."""
    test_message = "Invalid char ~"
    mock_vestaboard_connector.send_message.side_effect = VestaboardInvalidCharsError("Invalid character")
    response = client.post("/message", json={"message": test_message})
    assert response.status_code == 422
    # Updated to match handle_vestaboard_call output
    assert "Error sending message: Invalid characters. Invalid character" in response.json()["detail"]

def test_post_message_auth_error(client: TestClient, mock_vestaboard_connector: AsyncMock):
    """Tests VestaboardAuthError handling."""
    test_message = "Auth error test"
    mock_vestaboard_connector.send_message.side_effect = VestaboardAuthError("Auth failed")
    response = client.post("/message", json={"message": test_message})
    assert response.status_code == 503
    # Updated to match handle_vestaboard_call output
    assert "Error sending message: Vestaboard authentication error." in response.json()["detail"]

def test_post_message_general_vestaboard_error(client: TestClient, mock_vestaboard_connector: AsyncMock):
    """Tests general VestaboardError handling."""
    test_message = "General error test"
    mock_vestaboard_connector.send_message.side_effect = VestaboardError("API error")
    response = client.post("/message", json={"message": test_message})
    assert response.status_code == 502
    # Updated to match handle_vestaboard_call output
    assert "Error sending message: Error communicating with Vestaboard." in response.json()["detail"]

def test_post_message_unexpected_error(client: TestClient, mock_vestaboard_connector: AsyncMock):
    """Tests handling of unexpected errors during message posting."""
    test_message = "Unexpected error test"
    mock_vestaboard_connector.send_message.side_effect = Exception("Something broke")
    response = client.post("/message", json={"message": test_message})
    assert response.status_code == 500
    assert "Error sending message: An unexpected internal error occurred." in response.json()["detail"]


# --- Tests for POST /games/boggle endpoint ---
@pytest.mark.parametrize("size", [4, 5])
@patch("app.main.bg.generate_boggle_grids") # Patch where it's used
@patch("app.main.asyncio.sleep", new_callable=AsyncMock) # Mock asyncio.sleep
@pytest.mark.asyncio # Added decorator
async def test_start_boggle_game_success(
    mock_asyncio_sleep: AsyncMock, # Order matters for patch
    mock_generate_grids: MagicMock,
    size: int,
    client: TestClient,
    mock_vestaboard_connector: AsyncMock
):
    """Tests successful Boggle game start for 4x4 and 5x5."""
    start_grid_data = [[(i*j)%26+65 for i in range(size)] for j in range(size)] # Dummy grid
    end_grid_data = [[(i*j+1)%26+65 for i in range(size)] for j in range(size)] # Dummy grid
    mock_generate_grids.return_value = (start_grid_data, end_grid_data)

    response = client.post("/games/boggle", json={"size": size})

    assert response.status_code == 202 # Accepted
    assert response.json() == {"message": f"Boggle {size}x{size} game queued."}
    
    mock_generate_grids.assert_called_once_with(size)
    mock_vestaboard_connector.send_array.assert_any_call(start_grid_data) # First call is start_grid
    
    # Check that the background task was scheduled and would eventually send the end_grid
    # We can't easily test the timing or actual execution of the background task here
    # without more complex setup, but we can check if send_array was called for start_grid.
    # To test the background task itself, we would need to call it directly or use a more
    # sophisticated background task manager for testing.
    # For this unit test, we verify the immediate actions.

    # Simulate background task completion for the end grid (optional advanced check)
    # This part is tricky as the background task runs independently.
    # We've mocked asyncio.sleep, so the background task would proceed quickly if awaited.
    # However, TestClient doesn't wait for background tasks.
    # A more direct way to test the background task logic would be to test schedule_end_boggle_display directly.


def test_start_boggle_game_invalid_size(client: TestClient):
    """Tests Boggle game start with invalid size."""
    response = client.post("/games/boggle", json={"size": 3})
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Boggle size. Must be 4 or 5."}

@patch("app.main.bg.generate_boggle_grids")
def test_start_boggle_game_grid_generation_error(mock_generate_grids: MagicMock, client: TestClient):
    """Tests error during Boggle grid generation."""
    mock_generate_grids.side_effect = ValueError("Grid generation failed")
    response = client.post("/games/boggle", json={"size": 4})
    assert response.status_code == 500
    assert response.json() == {"detail": "Error creating game grids"}

@patch("app.main.bg.generate_boggle_grids")
def test_start_boggle_game_vestaboard_auth_error(
    mock_generate_grids: MagicMock,
    client: TestClient,
    mock_vestaboard_connector: AsyncMock
):
    """Tests VestaboardAuthError during initial Boggle grid send."""
    start_grid_data = [[65, 66], [67, 68]] # Dummy 2x2 for simplicity, size doesn't matter here
    end_grid_data = [[69, 70], [71, 72]]
    mock_generate_grids.return_value = (start_grid_data, end_grid_data)
    mock_vestaboard_connector.send_array.side_effect = VestaboardAuthError("Auth failed for Boggle")

    response = client.post("/games/boggle", json={"size": 4})
    assert response.status_code == 503
    # Updated to match handle_vestaboard_call output
    assert "Vestaboard error initiating Boggle 4x4 game: Vestaboard authentication error." in response.json()["detail"]

@patch("app.main.bg.generate_boggle_grids")
def test_start_boggle_game_vestaboard_general_error(
    mock_generate_grids: MagicMock,
    client: TestClient,
    mock_vestaboard_connector: AsyncMock
):
    """Tests general VestaboardError during initial Boggle grid send."""
    start_grid_data = [[65, 66], [67, 68]]
    end_grid_data = [[69, 70], [71, 72]]
    mock_generate_grids.return_value = (start_grid_data, end_grid_data)
    mock_vestaboard_connector.send_array.side_effect = VestaboardError("API error for Boggle")

    response = client.post("/games/boggle", json={"size": 5})
    assert response.status_code == 502
    # Updated to match handle_vestaboard_call output
    assert "Vestaboard error initiating Boggle 5x5 game: Error communicating with Vestaboard." in response.json()["detail"]

@patch("app.main.bg.generate_boggle_grids")
@patch("app.main.asyncio.sleep", new_callable=AsyncMock) # Mock sleep
@pytest.mark.asyncio # Added decorator
async def test_boggle_background_task_sends_end_grid(
    mock_asyncio_sleep: AsyncMock,
    mock_generate_grids: MagicMock,
    client: TestClient,
    mock_vestaboard_connector: AsyncMock
):
    """
    Test that the background task for Boggle attempts to send the end grid.
    This is a more focused test on the background task's behavior.
    """
    start_grid = [[1]]
    end_grid = [[2]]
    mock_generate_grids.return_value = (start_grid, end_grid)

    response = client.post("/games/boggle", json={"size": 4}) 
    assert response.status_code == 202

    # Check calls to VestaboardConnector.send_array
    calls = mock_vestaboard_connector.send_array.call_args_list
    
    sent_start_grid = False
    sent_end_grid = False
    start_grid_call_idx = -1
    end_grid_call_idx = -1

    for i, call_args_item in enumerate(calls):
        if call_args_item.args[0] == start_grid: # Check based on the first argument of the call
            sent_start_grid = True
            start_grid_call_idx = i
        elif call_args_item.args[0] == end_grid: # Check based on the first argument of the call
            sent_end_grid = True
            end_grid_call_idx = i
            
    assert sent_start_grid, "Start grid was not sent by send_array"
    assert sent_end_grid, "End grid was not sent by send_array"
    
    assert start_grid_call_idx != -1 and end_grid_call_idx != -1, "Both start and end grids must be found in calls"
    assert start_grid_call_idx < end_grid_call_idx, \
        f"Start grid (call {start_grid_call_idx}) was not sent before end grid (call {end_grid_call_idx})"

    mock_asyncio_sleep.assert_called_once_with(200)


@patch("app.main.bg.generate_boggle_grids")
@patch("app.main.asyncio.sleep", new_callable=AsyncMock) # Mock sleep
@patch("app.main.log.error") # Mock the logger
@pytest.mark.asyncio
async def test_boggle_background_task_sends_end_grid_error(
    mock_log_error: MagicMock,
    mock_asyncio_sleep: AsyncMock,
    mock_generate_grids: MagicMock,
    client: TestClient,
    mock_vestaboard_connector: AsyncMock
):
    """
    Test that the background task for Boggle logs an error if sending the end grid fails.
    """
    start_grid = [[1,2],[3,4]]
    end_grid = [[5,6],[7,8]]
    mock_generate_grids.return_value = (start_grid, end_grid)

    # Make the second call to send_array (for the end_grid) raise an error
    # The first call (start_grid) should succeed.
    mock_vestaboard_connector.send_array.side_effect = [
        AsyncMock(return_value=None)(), # Success for start_grid
        VestaboardError("Failed to send end grid") # Error for end_grid
    ]
    # We need to reset the side_effect for each test if it's instance-based
    # For this test structure, this should be okay as mock_vestaboard_connector is per-test.

    response = client.post("/games/boggle", json={"size": 4})
    assert response.status_code == 202

    # Wait for background task to likely complete (mocked sleep helps)
    # A small real sleep might be needed if events are not processed fast enough by TestClient
    await asyncio.sleep(0.01) # Give a tiny moment for the background task to run with mocked sleep

    # Assertions
    # Ensure the 200s sleep for the boggle timer was called
    mock_asyncio_sleep.assert_any_call(200) 
    
    # Check that send_array was called for start_grid then for end_grid
    calls = mock_vestaboard_connector.send_array.call_args_list
    assert len(calls) == 2
    assert calls[0].args[0] == start_grid
    assert calls[1].args[0] == end_grid
    
    # Check that log.error was called due to the failure in sending the end_grid
    mock_log_error.assert_called_once()
    assert "Error sending Boggle end grid in background task" in mock_log_error.call_args[0][0]


# --- Tests for Quote Endpoints (/sfw_quote, /nsfw_quote) ---

# Helper function to avoid code duplication for SFW and NSFW tests
@pytest.mark.parametrize(
    "endpoint_path, mock_say_func_path, expected_success_msg, expected_error_msg_prefix",
    [
        ("/sfw_quote", "app.main.say.GetSingleRandSfwS", "Random SFW quote queued", "Error getting SFW quote"),
        ("/nsfw_quote", "app.main.say.GetSingleRandNsfwS", "Random NSFW quote queued", "Error getting NSFW quote"),
    ]
)
@patch("app.main.asyncio.to_thread", new_callable=AsyncMock) # Mock to_thread
@pytest.mark.asyncio # Added decorator
async def test_get_quote_success(
    mock_to_thread: AsyncMock, # This will be used to mock the call to say.GetSingleRand...
    endpoint_path: str,
    mock_say_func_path: str, # Path to the function to be patched by mock_to_thread's side_effect
    expected_success_msg: str,
    expected_error_msg_prefix: str, # Not used in this success test, but part of parametrize
    client: TestClient,
    mock_settings: Settings,
    mock_vestaboard_connector: AsyncMock
):
    """Tests successful quote retrieval and sending for SFW and NSFW."""
    mock_settings.saying_db_enable = "1"
    test_quote = "This is a test quote."
    
    # Mock the behavior of asyncio.to_thread(quote_func, settings=settings)
    # The actual quote_func (e.g., say.GetSingleRandSfwS) is called within to_thread
    # So we need to mock what to_thread returns when called with that function.
    async def side_effect_for_to_thread(func, *args, **kwargs):
        if func.__name__ == mock_say_func_path.split('.')[-1]: # Check if it's the correct saying function
            return test_quote
        return await asyncio.to_thread. वास्तविक_call(func, *args, **kwargs) # Call original for other to_thread uses
    
    mock_to_thread.side_effect = side_effect_for_to_thread


    response = client.get(endpoint_path)

    assert response.status_code == 200
    assert response.json() == {"message": expected_success_msg}
    
    # Verify to_thread was called with the correct saying function and settings
    called_with_correct_func = False
    for call in mock_to_thread.call_args_list:
        args, kwargs = call
        if len(args) > 0 and args[0].__name__ == mock_say_func_path.split('.')[-1]:
            if 'settings' in kwargs and kwargs['settings'] == mock_settings:
                called_with_correct_func = True
                break
    assert called_with_correct_func, f"asyncio.to_thread not called correctly with {mock_say_func_path}"

    mock_vestaboard_connector.send_message.assert_called_once_with(test_quote)


@pytest.mark.parametrize(
    "endpoint_path, mock_say_func_path, expected_error_msg_prefix",
    [
        ("/sfw_quote", "app.main.say.GetSingleRandSfwS", "Error getting SFW quote"),
        ("/nsfw_quote", "app.main.say.GetSingleRandNsfwS", "Error getting NSFW quote"),
    ]
)
@patch("app.main.asyncio.to_thread", new_callable=AsyncMock)
@pytest.mark.asyncio # Added decorator
async def test_get_quote_db_disabled(
    mock_to_thread: AsyncMock,
    endpoint_path: str,
    mock_say_func_path: str, # Not directly used for checking call here, but part of params
    expected_error_msg_prefix: str,
    client: TestClient,
    mock_settings: Settings
):
    """Tests quote endpoints when SAYING_DB_ENABLE is '0'."""
    mock_settings.saying_db_enable = "0" # Ensure DB is disabled

    # Mock to_thread to simulate the behavior when DB is disabled (quote func might return None or not be called)
    # The logic in _get_and_send_quote checks settings before calling quote_func if to_thread is used correctly.
    # However, GetSingleRandSfwS itself checks for db_enable.
    # So, we simulate it returning None if called.
    async def side_effect_for_to_thread(func, *args, **kwargs):
        if func.__name__ == mock_say_func_path.split('.')[-1]:
            return None # Simulate quote function returning None due to DB disabled internally
        return await asyncio.to_thread. वास्तविक_call(func, *args, **kwargs)
    mock_to_thread.side_effect = side_effect_for_to_thread
    
    response = client.get(endpoint_path)
    
    assert response.status_code == 404
    assert f"{expected_error_msg_prefix}: Quote not found or DB disabled" in response.json()["detail"]


@pytest.mark.parametrize(
    "endpoint_path, mock_say_func_path, expected_error_msg_prefix",
    [
        ("/sfw_quote", "app.main.say.GetSingleRandSfwS", "Error getting SFW quote"),
        ("/nsfw_quote", "app.main.say.GetSingleRandNsfwS", "Error getting NSFW quote"),
    ]
)
@patch("app.main.asyncio.to_thread", new_callable=AsyncMock)
@pytest.mark.asyncio # Added decorator
async def test_get_quote_none_returned(
    mock_to_thread: AsyncMock,
    endpoint_path: str,
    mock_say_func_path: str,
    expected_error_msg_prefix: str,
    client: TestClient,
    mock_settings: Settings
):
    """Tests quote endpoints when the saying function returns None."""
    mock_settings.saying_db_enable = "1" # DB enabled
    
    async def side_effect_for_to_thread(func, *args, **kwargs):
        if func.__name__ == mock_say_func_path.split('.')[-1]:
            return None # Simulate no quote found
        return await asyncio.to_thread. वास्तविक_call(func, *args, **kwargs)
    mock_to_thread.side_effect = side_effect_for_to_thread

    response = client.get(endpoint_path)
    assert response.status_code == 404
    assert f"{expected_error_msg_prefix}: Quote not found or DB disabled" in response.json()["detail"]


@pytest.mark.parametrize(
    "endpoint_path, mock_say_func_path, expected_error_msg_prefix, error_to_raise, expected_status, expected_detail_part",
    [
        ("/sfw_quote", "app.main.say.GetSingleRandSfwS", "Error getting SFW quote", VestaboardInvalidCharsError("Bad char"), 422, "Invalid characters in quote"),
        ("/nsfw_quote", "app.main.say.GetSingleRandNsfwS", "Error getting NSFW quote", VestaboardInvalidCharsError("Bad char"), 422, "Invalid characters in quote"),
        ("/sfw_quote", "app.main.say.GetSingleRandSfwS", "Error getting SFW quote", VestaboardAuthError("Auth fail"), 503, "Vestaboard authentication error"),
        ("/nsfw_quote", "app.main.say.GetSingleRandNsfwS", "Error getting NSFW quote", VestaboardAuthError("Auth fail"), 503, "Vestaboard authentication error"),
        ("/sfw_quote", "app.main.say.GetSingleRandSfwS", "Error getting SFW quote", VestaboardError("General VB error"), 502, "Error communicating with Vestaboard"),
        ("/nsfw_quote", "app.main.say.GetSingleRandNsfwS", "Error getting NSFW quote", VestaboardError("General VB error"), 502, "Error communicating with Vestaboard"),
    ]
)
@patch("app.main.asyncio.to_thread", new_callable=AsyncMock)
@pytest.mark.asyncio # Added decorator
async def test_get_quote_vestaboard_errors(
    mock_to_thread: AsyncMock,
    endpoint_path: str,
    mock_say_func_path: str,
    expected_error_msg_prefix: str,
    error_to_raise: Exception,
    expected_status: int,
    expected_detail_part: str,
    client: TestClient,
    mock_settings: Settings,
    mock_vestaboard_connector: AsyncMock
):
    """Tests various Vestaboard errors for quote endpoints."""
    mock_settings.saying_db_enable = "1"
    test_quote = "A valid quote"

    async def side_effect_for_to_thread(func, *args, **kwargs):
        if func.__name__ == mock_say_func_path.split('.')[-1]:
            return test_quote
        return await asyncio.to_thread. वास्तविक_call(func, *args, **kwargs)
    mock_to_thread.side_effect = side_effect_for_to_thread
    
    mock_vestaboard_connector.send_message.side_effect = error_to_raise

    response = client.get(endpoint_path)
    assert response.status_code == expected_status
    # Updated to match handle_vestaboard_call output, which includes the original exception message for InvalidCharsError
    if isinstance(error_to_raise, VestaboardInvalidCharsError):
        assert f"{expected_error_msg_prefix}: Invalid characters. {error_to_raise}" in response.json()["detail"]
    else:
        assert f"{expected_error_msg_prefix}: {expected_detail_part}" in response.json()["detail"]


@pytest.mark.parametrize(
    "endpoint_path, mock_say_func_path, expected_error_msg_prefix",
    [
        ("/sfw_quote", "app.main.say.GetSingleRandSfwS", "Error getting SFW quote"),
        ("/nsfw_quote", "app.main.say.GetSingleRandNsfwS", "Error getting NSFW quote"),
    ]
)
@patch("app.main.asyncio.to_thread", new_callable=AsyncMock)
@pytest.mark.asyncio # Added decorator
async def test_get_quote_db_connection_error(
    mock_to_thread: AsyncMock,
    endpoint_path: str,
    mock_say_func_path: str,
    expected_error_msg_prefix: str,
    client: TestClient,
    mock_settings: Settings
):
    """Tests database connection error for quote endpoints."""
    mock_settings.saying_db_enable = "1"

    # Simulate ConnectionError being raised by the saying function (inside to_thread)
    async def side_effect_for_to_thread(func, *args, **kwargs):
        if func.__name__ == mock_say_func_path.split('.')[-1]:
            raise ConnectionError("DB connection failed")
        return await asyncio.to_thread. वास्तविक_call(func, *args, **kwargs)
    mock_to_thread.side_effect = side_effect_for_to_thread

    response = client.get(endpoint_path)
    assert response.status_code == 503
    assert f"{expected_error_msg_prefix}: Database unavailable" in response.json()["detail"]

@pytest.mark.parametrize(
    "endpoint_path, mock_say_func_path, expected_error_msg_prefix",
    [
        ("/sfw_quote", "app.sayings.GetSingleRandSfwS", "Error getting SFW quote"),
        ("/nsfw_quote", "app.sayings.GetSingleRandNsfwS", "Error getting NSFW quote"),
    ]
)
@patch("app.main.asyncio.to_thread")
def test_get_quote_unexpected_error(
    mock_to_thread: MagicMock,
    endpoint_path: str,
    mock_say_func_path: str,
    expected_error_msg_prefix: str,
    client: TestClient,
    mock_settings: Settings
):
    """Tests unexpected errors during quote retrieval."""
    mock_settings.saying_db_enable = "1"
    mock_to_thread.side_effect = Exception("Totally unexpected")

    response = client.get(endpoint_path)
    assert response.status_code == 500
    assert f"{expected_error_msg_prefix}: An unexpected internal error occurred" in response.json()["detail"]
