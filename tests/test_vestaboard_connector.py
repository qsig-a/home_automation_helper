import pytest
from unittest.mock import AsyncMock
from app.connectors.vestaboard import VestaboardConnector
from app.config import Settings

@pytest.fixture
def real_settings():
    settings = Settings()
    settings.vestaboard_rw_api_key = "rw_key"
    settings.vestaboard_local_api_key = "local_key"
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
