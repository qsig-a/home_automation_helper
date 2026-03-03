import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.config import Settings
from fastapi import HTTPException

@pytest.mark.parametrize(
    "endpoint_path, strategy, step_interval_ms, step_size",
    [
        ("/sfw_quote/local", None, None, None),
        ("/sfw_quote/local?strategy=column&step_interval_ms=1000&step_size=2", "column", 1000, 2),
    ]
)
@patch("app.main.get_and_send_quote", new_callable=AsyncMock)
def test_get_sfw_quote_local_success(
    mock_get_and_send_quote: AsyncMock,
    endpoint_path: str,
    strategy: str | None,
    step_interval_ms: int | None,
    step_size: int | None,
    client: TestClient,
    mock_settings: Settings,
    mock_vestaboard_connector: AsyncMock
):
    """Tests successful SFW quote retrieval and sending via Local API by mocking get_and_send_quote."""
    expected_response = {"message": "Random SFW quote queued (Local)"}
    mock_get_and_send_quote.return_value = expected_response

    response = client.get(endpoint_path)

    assert response.status_code == 200
    assert response.json() == expected_response

    # Verify get_and_send_quote was called with the correct parameters
    import app.sayings.sayings as say
    mock_get_and_send_quote.assert_called_once_with(
        quote_func=say.GetSingleRandSfwS,
        success_message="Random SFW quote queued (Local)",
        error_message="Error getting SFW quote",
        settings=mock_settings,
        connector=mock_vestaboard_connector,
        source='local',
        strategy=strategy,
        step_interval_ms=step_interval_ms,
        step_size=step_size
    )

@patch("app.main.get_and_send_quote", new_callable=AsyncMock)
def test_get_sfw_quote_local_not_found(
    mock_get_and_send_quote: AsyncMock,
    client: TestClient
):
    """Tests SFW quote local endpoint when get_and_send_quote raises 404."""
    mock_get_and_send_quote.side_effect = HTTPException(status_code=404, detail="Error getting SFW quote: Quote not found or DB disabled")

    response = client.get("/sfw_quote/local")

    assert response.status_code == 404
    assert "Error getting SFW quote: Quote not found or DB disabled" in response.json()["detail"]

@patch("app.main.get_and_send_quote", new_callable=AsyncMock)
def test_get_sfw_quote_local_error(
    mock_get_and_send_quote: AsyncMock,
    client: TestClient
):
    """Tests SFW quote local endpoint when get_and_send_quote raises 500."""
    mock_get_and_send_quote.side_effect = HTTPException(status_code=500, detail="Error getting SFW quote: An unexpected internal error occurred")

    response = client.get("/sfw_quote/local")

    assert response.status_code == 500
    assert "Error getting SFW quote: An unexpected internal error occurred" in response.json()["detail"]
