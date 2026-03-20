import pytest
import httpx
from unittest.mock import AsyncMock
from app.connectors.vestaboard import VestaboardConnector, VestaboardError
from app.config import Settings

from pydantic import SecretStr

@pytest.fixture
def real_settings():
    settings = Settings()
    settings.vestaboard_rw_api_key = SecretStr("rw_key")
    settings.vestaboard_local_api_key = SecretStr("local_key")
    settings.vestaboard_local_api_ip = "192.168.1.100"
    return settings

@pytest.mark.asyncio
async def test_convert_text_to_array(real_settings):
    connector = VestaboardConnector(real_settings)

    text = "Hi"
    array = connector.convert_text_to_array(text)

    assert len(array) == 6
    assert len(array[0]) == 22

    # 'H' is 8, 'i' is 9 (lowercase 'i' -> 9)
    assert array[0][0] == 8
    assert array[0][1] == 9
    assert array[0][2] == 0

@pytest.mark.asyncio
async def test_convert_text_to_array_newline(real_settings):
    connector = VestaboardConnector(real_settings)

    text = "A\nB"
    array = connector.convert_text_to_array(text)

    assert array[0][0] == 1 # A
    assert array[1][0] == 2 # B (next row)
    assert array[0][1] == 0

@pytest.mark.asyncio
async def test_send_message_rw(real_settings):
    connector = VestaboardConnector(real_settings)
    connector._rw_client.post = AsyncMock(return_value=AsyncMock(status_code=200))

    await connector.send_message("Test", source="rw")

    connector._rw_client.post.assert_called_once()
    args, kwargs = connector._rw_client.post.call_args
    assert kwargs['json'] == {'text': 'Test'}
    assert kwargs['headers']['X-Vestaboard-Read-Write-Key'] == "rw_key"

@pytest.mark.asyncio
async def test_send_message_local(real_settings):
    connector = VestaboardConnector(real_settings)
    connector._local_client.post = AsyncMock(return_value=AsyncMock(status_code=200))

    await connector.send_message("A", source="local")

    connector._local_client.post.assert_called_once()
    args, kwargs = connector._local_client.post.call_args
    # Based on implementation, send_message('local') -> convert -> send_array('local') -> if no opts -> raw list
    assert isinstance(kwargs['json'], list)
    assert kwargs['json'][0][0] == 1
    assert kwargs['headers']['X-Vestaboard-Local-Api-Key'] == "local_key"

@pytest.mark.asyncio
async def test_send_array_local_with_options(real_settings):
    connector = VestaboardConnector(real_settings)
    connector._local_client.post = AsyncMock(return_value=AsyncMock(status_code=200))

    chars = [[0]*22]*6
    await connector.send_array(chars, source="local", strategy="column", step_size=2)

    connector._local_client.post.assert_called_once()
    args, kwargs = connector._local_client.post.call_args
    payload = kwargs['json']
    assert isinstance(payload, dict)
    assert payload['strategy'] == "column"
    assert payload['step_size'] == 2
    assert payload['characters'] == chars

@pytest.mark.asyncio
async def test_post_rw_http_error(real_settings):

    connector = VestaboardConnector(real_settings)

    # Create a mock response with an error status
    mock_response = httpx.Response(status_code=400, request=httpx.Request("POST", "/"), text="Bad Request")

    # Mock the client's post method to raise an HTTPStatusError
    connector._rw_client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
        "Error", request=mock_response.request, response=mock_response
    ))

    with pytest.raises(VestaboardError) as exc_info:
        await connector._post_rw({"text": "Test Error"})

    assert "RW API error: 400" in str(exc_info.value)
    connector._rw_client.post.assert_called_once()

@pytest.mark.asyncio
async def test_post_rw_request_error(real_settings):

    connector = VestaboardConnector(real_settings)

    # Mock the client's post method to raise a RequestError
    connector._rw_client.post = AsyncMock(side_effect=httpx.RequestError(
        "Network Unreachable", request=httpx.Request("POST", "/")
    ))

    with pytest.raises(VestaboardError) as exc_info:
        await connector._post_rw({"text": "Test Network Error"})

    assert "RW API network error: Network Unreachable" in str(exc_info.value)
    connector._rw_client.post.assert_called_once()
