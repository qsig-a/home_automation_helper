import pytest
from unittest.mock import AsyncMock, MagicMock

from app.main import get_and_send_quote, ActionConfig
from app.connectors.vestaboard import VestaboardFingerprintError, VestaboardError


def _quote_config(func):
    return ActionConfig(
        func=func,
        success_message="Random SFW quote queued",
        error_message="Error getting SFW quote",
        source="rw",
    )


@pytest.mark.asyncio
async def test_reroll_on_fingerprint_then_succeeds(mock_settings):
    """When the board already displays the first quote (409 FingerprintMatch),
    the endpoint should fetch a different quote and retry, then succeed."""
    connector = AsyncMock()
    # First send collides with what's on the board; second send goes through.
    connector.send_message = AsyncMock(
        side_effect=[VestaboardFingerprintError("dup"), None]
    )
    quote_func = MagicMock(side_effect=["Quote already up", "A fresh quote"])

    result = await get_and_send_quote(
        config=_quote_config(quote_func),
        settings=mock_settings,
        connector=connector,
    )

    assert connector.send_message.call_count == 2
    # The second (fresh) quote is what actually got sent.
    assert connector.send_message.call_args_list[1].args[0] == "A fresh quote"
    assert result == {"message": "Random SFW quote queued"}


@pytest.mark.asyncio
async def test_reroll_gives_up_gracefully(mock_settings):
    """If every re-roll keeps matching the board, give up gracefully with a
    non-error response rather than surfacing a 502/500."""
    connector = AsyncMock()
    connector.send_message = AsyncMock(side_effect=VestaboardFingerprintError("dup"))
    quote_func = MagicMock(return_value="Same quote every time")

    result = await get_and_send_quote(
        config=_quote_config(quote_func),
        settings=mock_settings,
        connector=connector,
    )

    assert connector.send_message.call_count == 3
    assert "already displayed" in result["message"].lower()


@pytest.mark.asyncio
async def test_non_fingerprint_error_is_not_retried(mock_settings):
    """A genuine Vestaboard failure (not a fingerprint match) must not be
    re-rolled; it should propagate as an HTTP 502."""
    from fastapi import HTTPException

    connector = AsyncMock()
    connector.send_message = AsyncMock(side_effect=VestaboardError("RW API error: 500"))
    quote_func = MagicMock(return_value="Some quote")

    with pytest.raises(HTTPException) as exc_info:
        await get_and_send_quote(
            config=_quote_config(quote_func),
            settings=mock_settings,
            connector=connector,
        )

    assert exc_info.value.status_code == 502
    connector.send_message.assert_called_once()
