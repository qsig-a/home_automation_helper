from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.config import Settings
from fastapi import HTTPException
import app.sayings.sayings as say
from app.main import ActionConfig

@patch("app.main.get_and_send_quote", new_callable=AsyncMock)
def test_get_sfw_quote_success(
    mock_get_and_send_quote: AsyncMock,
    client: TestClient,
    mock_settings: Settings,
    mock_vestaboard_connector: AsyncMock
):
    """Tests successful SFW quote retrieval and sending by mocking get_and_send_quote."""
    expected_response = {"message": "Random SFW quote queued"}
    mock_get_and_send_quote.return_value = expected_response

    response = client.get("/sfw_quote")

    assert response.status_code == 200
    assert response.json() == expected_response

    mock_get_and_send_quote.assert_called_once_with(
        config=ActionConfig(
            func=say.GetSingleRandSfwS,
            success_message="Random SFW quote queued",
            error_message="Error getting SFW quote",
            source='rw'
        ),
        settings=mock_settings,
        connector=mock_vestaboard_connector
    )

@patch("app.main.get_and_send_quote", new_callable=AsyncMock)
def test_get_sfw_quote_not_found(
    mock_get_and_send_quote: AsyncMock,
    client: TestClient
):
    """Tests SFW quote endpoint when get_and_send_quote raises 404."""
    mock_get_and_send_quote.side_effect = HTTPException(status_code=404, detail="Error getting SFW quote: Quote not found or DB disabled")

    response = client.get("/sfw_quote")

    assert response.status_code == 404
    assert "Error getting SFW quote: Quote not found or DB disabled" in response.json()["detail"]

@patch("app.main.get_and_send_quote", new_callable=AsyncMock)
def test_get_sfw_quote_error(
    mock_get_and_send_quote: AsyncMock,
    client: TestClient
):
    """Tests SFW quote endpoint when get_and_send_quote raises 500."""
    mock_get_and_send_quote.side_effect = HTTPException(status_code=500, detail="Error getting SFW quote: An unexpected internal error occurred")

    response = client.get("/sfw_quote")

    assert response.status_code == 500
    assert "Error getting SFW quote: An unexpected internal error occurred" in response.json()["detail"]
