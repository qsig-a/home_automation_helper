import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.config import Settings
from fastapi import HTTPException
import app.sayings.sayings as say

@pytest.mark.parametrize(
    "endpoint_path, strategy, step_interval_ms, step_size",
    [
        ("/nsfw_quote/local", None, None, None),
        ("/nsfw_quote/local?strategy=column&step_interval_ms=1000&step_size=2", "column", 1000, 2),
    ]
)
@patch("app.main.get_and_send_quote", new_callable=AsyncMock)
def test_get_nsfw_quote_local_success(
    mock_get_and_send_quote: AsyncMock,
    endpoint_path: str,
    strategy: str | None,
    step_interval_ms: int | None,
    step_size: int | None,
    client: TestClient,
    mock_settings: Settings,
    mock_vestaboard_connector: AsyncMock
):
    """Tests successful NSFW quote retrieval and sending via Local API by mocking get_and_send_quote."""
    expected_response = {"message": "Random NSFW quote queued (Local)"}
    mock_get_and_send_quote.return_value = expected_response

    response = client.get(endpoint_path)

    assert response.status_code == 200
    assert response.json() == expected_response

    # Verify get_and_send_quote was called with the correct parameters
    mock_get_and_send_quote.assert_called_once()
    kwargs = mock_get_and_send_quote.call_args.kwargs
    assert kwargs.get("quote_func") == say.GetSingleRandNsfwS
    assert kwargs.get("success_message") == "Random NSFW quote queued (Local)"
    assert kwargs.get("error_message") == "Error getting NSFW quote"
    assert kwargs.get("settings") == mock_settings
    assert kwargs.get("connector") == mock_vestaboard_connector
    assert kwargs.get("source") == 'local'

@patch("app.main.get_and_send_quote", new_callable=AsyncMock)
def test_get_nsfw_quote_local_not_found(
    mock_get_and_send_quote: AsyncMock,
    client: TestClient
):
    """Tests NSFW quote local endpoint when get_and_send_quote raises 404."""
    mock_get_and_send_quote.side_effect = HTTPException(status_code=404, detail="Error getting NSFW quote: Quote not found or DB disabled")

    response = client.get("/nsfw_quote/local")

    assert response.status_code == 404
    assert "Error getting NSFW quote: Quote not found or DB disabled" in response.json()["detail"]

@patch("app.main.get_and_send_quote", new_callable=AsyncMock)
def test_get_nsfw_quote_local_error(
    mock_get_and_send_quote: AsyncMock,
    client: TestClient
):
    """Tests NSFW quote local endpoint when get_and_send_quote raises 500."""
    mock_get_and_send_quote.side_effect = HTTPException(status_code=500, detail="Error getting NSFW quote: An unexpected internal error occurred")

    response = client.get("/nsfw_quote/local")

    assert response.status_code == 500
    assert "Error getting NSFW quote: An unexpected internal error occurred" in response.json()["detail"]
