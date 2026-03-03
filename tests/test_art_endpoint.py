import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.config import Settings
from fastapi import HTTPException
import app.sayings.sayings as say

@patch("app.main.get_and_send_art", new_callable=AsyncMock)
def test_get_random_art_success(
    mock_get_and_send_art: AsyncMock,
    client: TestClient,
    mock_settings: Settings,
    mock_vestaboard_connector: AsyncMock
):
    """Tests successful random art retrieval and sending by mocking get_and_send_art."""
    expected_response = {"message": "Random art queued", "title": "Test Title"}
    mock_get_and_send_art.return_value = expected_response

    response = client.get("/art")

    assert response.status_code == 200
    assert response.json() == expected_response

    # Verify get_and_send_art was called with the correct parameters
    mock_get_and_send_art.assert_called_once_with(
        art_func=say.GetSingleRandArt,
        success_message="Random art queued",
        error_message="Error getting art",
        settings=mock_settings,
        connector=mock_vestaboard_connector,
        source='rw'
    )

@patch("app.main.get_and_send_art", new_callable=AsyncMock)
def test_get_random_art_not_found(
    mock_get_and_send_art: AsyncMock,
    client: TestClient
):
    """Tests art endpoint when get_and_send_art raises 404."""
    mock_get_and_send_art.side_effect = HTTPException(status_code=404, detail="Error getting art: Art not found or DB disabled")

    response = client.get("/art")

    assert response.status_code == 404
    assert "Error getting art: Art not found or DB disabled" in response.json()["detail"]

@patch("app.main.get_and_send_art", new_callable=AsyncMock)
def test_get_random_art_internal_error(
    mock_get_and_send_art: AsyncMock,
    client: TestClient
):
    """Tests art endpoint when get_and_send_art raises 500."""
    mock_get_and_send_art.side_effect = HTTPException(status_code=500, detail="Error getting art: An unexpected internal error occurred")

    response = client.get("/art")

    assert response.status_code == 500
    assert "Error getting art: An unexpected internal error occurred" in response.json()["detail"]
