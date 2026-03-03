import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.config import Settings
from fastapi import HTTPException
import app.sayings.sayings as say
from app.main import ActionConfig

@patch("app.main.get_and_send_quote", new_callable=AsyncMock)
def test_get_nsfw_quote_success(
    mock_get_and_send_quote: AsyncMock,
    client: TestClient,
    mock_settings: Settings,
    mock_vestaboard_connector: AsyncMock
):
    """Tests successful NSFW quote retrieval and sending by mocking get_and_send_quote."""
    expected_response = {"message": "Random NSFW quote queued"}
    mock_get_and_send_quote.return_value = expected_response

    response = client.get("/nsfw_quote")

    assert response.status_code == 200
    assert response.json() == expected_response

    # Verify get_and_send_quote was called with the correct parameters
    mock_get_and_send_quote.assert_called_once_with(
        quote_func=say.GetSingleRandNsfwS,
        config=ActionConfig(
            success_message="Random NSFW quote queued",
            error_message="Error getting NSFW quote",
            source='rw'
        ),
        settings=mock_settings,
        connector=mock_vestaboard_connector
    )

@patch("app.main.get_and_send_quote", new_callable=AsyncMock)
def test_get_nsfw_quote_not_found(
    mock_get_and_send_quote: AsyncMock,
    client: TestClient
):
    """Tests NSFW quote endpoint when get_and_send_quote raises 404."""
    mock_get_and_send_quote.side_effect = HTTPException(status_code=404, detail="Error getting NSFW quote: Quote not found or DB disabled")

    response = client.get("/nsfw_quote")

    assert response.status_code == 404
    assert "Error getting NSFW quote: Quote not found or DB disabled" in response.json()["detail"]

@patch("app.main.get_and_send_quote", new_callable=AsyncMock)
def test_get_nsfw_quote_error(
    mock_get_and_send_quote: AsyncMock,
    client: TestClient
):
    """Tests NSFW quote endpoint when get_and_send_quote raises 500."""
    mock_get_and_send_quote.side_effect = HTTPException(status_code=500, detail="Error getting NSFW quote: An unexpected internal error occurred")

    response = client.get("/nsfw_quote")

    assert response.status_code == 500
    assert "Error getting NSFW quote: An unexpected internal error occurred" in response.json()["detail"]
