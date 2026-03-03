# app/connectors/vestaboard.py

import httpx
import re
import logging
from typing import Optional, List, Dict, Any, Union

# Import central settings configuration
from app.config import Settings

# Setup logger for this module
log = logging.getLogger(__name__)

# --- Custom Exceptions ---
class VestaboardError(Exception):
    """Base class for Vestaboard connector errors."""
    pass

class VestaboardAuthError(VestaboardError):
    """Error related to authentication (API keys)."""
    pass

class VestaboardInvalidCharsError(VestaboardError):
    """Error for invalid characters in a text message."""
    pass

# Pre-compiled regex for validating characters in messages
VALID_CHARS_REGEX = re.compile(r"^[A-Za-z0-9!@$\(\)\-+&=;:'\"\%,./?° \n]*$")

# Character mapping for Vestaboard
CHAR_CODE_MAP = {
    ' ': 0,
    'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8, 'I': 9, 'J': 10,
    'K': 11, 'L': 12, 'M': 13, 'N': 14, 'O': 15, 'P': 16, 'Q': 17, 'R': 18, 'S': 19, 'T': 20,
    'U': 21, 'V': 22, 'W': 23, 'X': 24, 'Y': 25, 'Z': 26,
    'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7, 'h': 8, 'i': 9, 'j': 10,
    'k': 11, 'l': 12, 'm': 13, 'n': 14, 'o': 15, 'p': 16, 'q': 17, 'r': 18, 's': 19, 't': 20,
    'u': 21, 'v': 22, 'w': 23, 'x': 24, 'y': 25, 'z': 26,
    '1': 27, '2': 28, '3': 29, '4': 30, '5': 31, '6': 32, '7': 33, '8': 34, '9': 35, '0': 36,
    '!': 37, '@': 38, '#': 39, '$': 40, '(': 41, ')': 42, '-': 44, '+': 46, '&': 47, '=': 48,
    ';': 49, ':': 50, "'": 52, '"': 53, '%': 54, ',': 55, '.': 56, '/': 59, '?': 60, '°': 62
}

class VestaboardConnector:
    """
    An asynchronous connector for interacting with the Vestaboard API.
    Supports both Read/Write (RW) API and Local API.
    """
    def __init__(self, settings: Settings):
        self._settings = settings
        self._rw_api_key = settings.vestaboard_rw_api_key
        self._local_api_key = settings.vestaboard_local_api_key
        self._local_api_ip = settings.vestaboard_local_api_ip

        # RW API Client
        self._rw_base_url = "https://rw.vestaboard.com"
        self._rw_headers = {
            'X-Vestaboard-Read-Write-Key': self._rw_api_key or "",
            'Content-Type': 'application/json'
        }
        self._rw_client = httpx.AsyncClient(
            base_url=self._rw_base_url,
            headers=self._rw_headers,
            timeout=20.0
        )

        # Local API Client (initialized only if IP provided)
        self._local_client = None
        if self._local_api_ip:
            self._local_base_url = f"http://{self._local_api_ip}:7000"
            self._local_headers = {
                'X-Vestaboard-Local-Api-Key': self._local_api_key or "",
                'Content-Type': 'application/json'
            }
            self._local_client = httpx.AsyncClient(
                base_url=self._local_base_url,
                headers=self._local_headers,
                timeout=20.0
            )

        log.info("VestaboardConnector initialized.")

    async def close(self):
        """Closes the underlying httpx clients."""
        if self._rw_client and not self._rw_client.is_closed:
            await self._rw_client.aclose()
        if self._local_client and not self._local_client.is_closed:
            await self._local_client.aclose()
        log.info("VestaboardConnector HTTP clients closed.")

    def convert_text_to_array(self, text: str) -> List[List[int]]:
        """
        Converts a text string into a 6x22 integer array for Vestaboard.
        """
        rows = 6
        cols = 22
        board = [[0] * cols for _ in range(rows)]

        row = 0
        col = 0

        for char in text:
            if row >= rows:
                break

            if char == '\n':
                row += 1
                col = 0
                continue

            code = CHAR_CODE_MAP.get(char, 0) # Default to blank (0) if unknown

            board[row][col] = code
            col += 1

            if col >= cols:
                col = 0
                row += 1

        return board

    async def _post_rw(self, data: Union[Dict[str, Any], List[List[int]]]):
        """Helper to POST to RW API."""
        if not self._rw_api_key:
             log.error("RW API Key not configured.")
             raise VestaboardAuthError("RW API Key not configured.")

        try:
            # Re-apply header in case key was updated or just to be safe
            headers = self._rw_headers.copy()
            headers['X-Vestaboard-Read-Write-Key'] = self._rw_api_key

            response = await self._rw_client.post("/", json=data, headers=headers)
            response.raise_for_status()
            log.info("Successfully sent message via RW API.")
        except httpx.HTTPStatusError as e:
            log.error(f"RW API HTTP error: {e.response.status_code} - {e.response.text}")
            raise VestaboardError(f"RW API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            log.error(f"RW API network error: {e}")
            raise VestaboardError(f"RW API network error: {e}") from e

    async def _post_local(self, data: Union[Dict[str, Any], List[List[int]]]):
        """Helper to POST to Local API."""
        if not self._local_client or not self._local_api_key:
             log.error("Local API not configured (Key or IP missing).")
             raise VestaboardAuthError("Local API not configured (Key or IP missing).")

        try:
             # Re-apply header
            headers = self._local_headers.copy()
            headers['X-Vestaboard-Local-Api-Key'] = self._local_api_key

            response = await self._local_client.post("/local-api/message", json=data, headers=headers)
            response.raise_for_status()
            log.info("Successfully sent message via Local API.")
        except httpx.HTTPStatusError as e:
            log.error(f"Local API HTTP error: {e.response.status_code} - {e.response.text}")
            raise VestaboardError(f"Local API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            log.error(f"Local API network error: {e}")
            raise VestaboardError(f"Local API network error: {e}") from e

    async def send_message(self, text: str, source: str = 'rw', **kwargs):
        """
        Sends a text message.
        """
        string_text = str(text)
        if not VALID_CHARS_REGEX.match(string_text):
             log.warning(f"Message contains invalid characters: '{string_text}'")
             raise VestaboardInvalidCharsError("Message contains invalid characters.")

        if source == 'local':
            # Local API only accepts arrays
            array_data = self.convert_text_to_array(string_text)
            await self.send_array(array_data, source='local', **kwargs)
        else:
            # RW API
            payload = {"text": string_text}
            await self._post_rw(payload)

    async def send_array(self, characters: List[List[int]], source: str = 'rw', **kwargs):
        """
        Sends a character array.
        """
        if not isinstance(characters, list):
             raise TypeError("Input 'characters' must be a list.")

        if source == 'local':
            # Local API supports transitions

            # Check if any transition params are present
            transition_keys = ['strategy', 'step_interval_ms', 'step_size']
            has_options = any(k in kwargs and kwargs[k] is not None for k in transition_keys)

            if has_options:
                payload = {"characters": characters}
                if kwargs.get('strategy'):
                    payload['strategy'] = kwargs['strategy']
                if kwargs.get('step_interval_ms') is not None:
                    payload['step_interval_ms'] = kwargs['step_interval_ms']
                if kwargs.get('step_size') is not None:
                    payload['step_size'] = kwargs['step_size']
                await self._post_local(payload)
            else:
                await self._post_local(characters) # Send raw list
        else:
            # RW API
            await self._post_rw(characters)
