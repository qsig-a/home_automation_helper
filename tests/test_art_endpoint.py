import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
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

    mock_to_thread.return_value = test_art

    response = client.get("/art")

    assert response.status_code == 200
    assert response.json() == {"message": "Random art queued"}
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
