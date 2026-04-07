import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from fastapi import Request, HTTPException
from app.main import rate_limiter, RATE_LIMIT_DELAY

@pytest.fixture(autouse=True)
def reset_rate_limiter_state():
    """Reset the global state dictionary before each test execution to ensure tests run in isolation."""
    import app.main
    app.main._client_request_times.clear()
    yield

@pytest.mark.asyncio
async def test_rate_limiter_allows_first_request():
    mock_request = MagicMock(spec=Request)
    mock_request.client.host = "192.168.1.1"

    # The first request should not raise an HTTPException
    await rate_limiter(mock_request)

@pytest.mark.asyncio
async def test_rate_limiter_blocks_second_request_same_ip():
    mock_request = MagicMock(spec=Request)
    mock_request.client.host = "192.168.1.1"

    await rate_limiter(mock_request)

    with pytest.raises(HTTPException) as exc_info:
        await rate_limiter(mock_request)

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
    assert "Retry-After" in exc_info.value.headers

@pytest.mark.asyncio
async def test_rate_limiter_allows_second_request_different_ip():
    mock_request1 = MagicMock(spec=Request)
    mock_request1.client.host = "192.168.1.1"

    mock_request2 = MagicMock(spec=Request)
    mock_request2.client.host = "192.168.1.2"

    await rate_limiter(mock_request1)

    # Second request from a different IP should be allowed
    await rate_limiter(mock_request2)

@pytest.mark.asyncio
async def test_rate_limiter_expires_entry():
    mock_request = MagicMock(spec=Request)
    mock_request.client.host = "192.168.1.1"

    with patch("time.monotonic") as mock_monotonic:
        # First request at t=100.0 (using non-zero to avoid the default 0.0 value issue in `_client_request_times.get(client_ip, 0.0)`)
        mock_monotonic.return_value = 100.0
        await rate_limiter(mock_request)

        # Second request at t=100.0 + RATE_LIMIT_DELAY + 1
        mock_monotonic.return_value = 100.0 + RATE_LIMIT_DELAY + 1.0
        # Should not raise an exception
        await rate_limiter(mock_request)

@pytest.mark.asyncio
async def test_rate_limiter_fallback_ip():
    mock_request = MagicMock(spec=Request)
    mock_request.client = None

    await rate_limiter(mock_request)

    with pytest.raises(HTTPException) as exc_info:
        await rate_limiter(mock_request)

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
