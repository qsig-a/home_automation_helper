import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.config import Settings
import asyncio

@patch("app.main.asyncio.to_thread", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_art_success(
    mock_to_thread: AsyncMock,
    client: TestClient,
    mock_settings: Settings,
    mock_vestaboard_connector: AsyncMock
):
    mock_settings.saying_db_enable = "1"
    test_art = [[1, 2], [3, 4]]
    test_title = "Test Art Title"

    mock_to_thread.return_value = (test_art, test_title)

    response = client.get("/art")

    assert response.status_code == 200
    assert response.json() == {"message": "Random art queued", "title": test_title}
    mock_vestaboard_connector.send_array.assert_called_once_with(test_art, source='rw')

@patch("app.main.asyncio.to_thread", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_get_art_not_found(
    mock_to_thread: AsyncMock,
    client: TestClient,
    mock_settings: Settings
):
    mock_settings.saying_db_enable = "1"
    mock_to_thread.return_value = None

    response = client.get("/art")

    assert response.status_code == 404
    assert "Error getting art: Art not found or DB disabled" in response.json()["detail"]

@patch("app.main.get_and_send_art", new_callable=AsyncMock)
def test_get_random_art_local_success(
    mock_get_and_send_art: AsyncMock,
    client: TestClient,
    mock_settings: Settings,
    mock_vestaboard_connector: AsyncMock
):
    expected_response = {"message": "Random art queued (Local)", "title": "Test Title"}
    mock_get_and_send_art.return_value = expected_response

    response = client.get("/art/local")

    assert response.status_code == 200
    assert response.json() == expected_response

    import app.sayings.sayings as say
    mock_get_and_send_art.assert_called_once_with(
        art_func=say.GetSingleRandArt,
        success_message="Random art queued (Local)",
        error_message="Error getting art",
        settings=mock_settings,
        connector=mock_vestaboard_connector,
        source='local',
        strategy=None,
        step_interval_ms=None,
        step_size=None
    )

@patch("app.main.get_and_send_art", new_callable=AsyncMock)
def test_get_random_art_local_success_with_params(
    mock_get_and_send_art: AsyncMock,
    client: TestClient,
    mock_settings: Settings,
    mock_vestaboard_connector: AsyncMock
):
    expected_response = {"message": "Random art queued (Local)", "title": "Test Title"}
    mock_get_and_send_art.return_value = expected_response

    response = client.get("/art/local?strategy=column&step_interval_ms=1000&step_size=2")

    assert response.status_code == 200
    assert response.json() == expected_response

    import app.sayings.sayings as say
    mock_get_and_send_art.assert_called_once_with(
        art_func=say.GetSingleRandArt,
        success_message="Random art queued (Local)",
        error_message="Error getting art",
        settings=mock_settings,
        connector=mock_vestaboard_connector,
        source='local',
        strategy="column",
        step_interval_ms=1000,
        step_size=2
    )

@patch("app.main.get_and_send_art", new_callable=AsyncMock)
def test_get_random_art_local_not_found(
    mock_get_and_send_art: AsyncMock,
    client: TestClient
):
    mock_get_and_send_art.side_effect = HTTPException(status_code=404, detail="Error getting art: Art not found or DB disabled")

    response = client.get("/art/local")

    assert response.status_code == 404
    assert "Error getting art: Art not found or DB disabled" in response.json()["detail"]

@patch("app.main.get_and_send_art", new_callable=AsyncMock)
def test_get_random_art_local_error(
    mock_get_and_send_art: AsyncMock,
    client: TestClient
):
    mock_get_and_send_art.side_effect = HTTPException(status_code=500, detail="Error getting art: An unexpected internal error occurred")

    response = client.get("/art/local")

    assert response.status_code == 500
    assert "Error getting art: An unexpected internal error occurred" in response.json()["detail"]
