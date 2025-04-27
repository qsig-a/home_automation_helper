# app/connectors/vestaboard.py

import httpx
import re
import asyncio
import logging
from typing import Optional, List, Dict, Any

# Import central settings configuration
from app.config import Settings

# Setup logger for this module
log = logging.getLogger(__name__)

# --- Custom Exceptions ---
class VestaboardError(Exception):
    """Base class for Vestaboard connector errors."""
    pass

class VestaboardAuthError(VestaboardError):
    """Error related to authentication (API keys, subscription ID)."""
    pass

class VestaboardInvalidCharsError(VestaboardError):
    """Error for invalid characters in a text message."""
    pass

# --- Connector Class ---
class VestaboardConnector:
    """
    An asynchronous connector for interacting with the Vestaboard API.

    Manages API credentials, HTTP client session, and subscription ID caching.
    """
    def __init__(self, settings: Settings):
        """
        Initializes the connector with settings.

        Args:
            settings: The application's Settings object containing Vestaboard credentials.

        Raises:
            VestaboardAuthError: If API key or secret are missing in settings.
        """
        if not settings.vestaboard_api_key or not settings.vestaboard_api_secret:
            log.error("Vestaboard API Key or Secret not found in settings.")
            raise VestaboardAuthError("Vestaboard API Key or Secret not configured.")

        self._api_key = settings.vestaboard_api_key
        self._api_secret = settings.vestaboard_api_secret
        self._base_url = "https://platform.vestaboard.com"
        self._headers = {
            'X-Vestaboard-Api-Key': self._api_key,
            'X-Vestaboard-Api-Secret': self._api_secret,
            'Content-Type': 'application/json'
        }
        # Initialize httpx client (consider making timeout configurable via settings)
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=20.0 # Increased default timeout
        )
        self._subscription_id: Optional[str] = None
        self._sub_id_lock = asyncio.Lock() # Lock for async cache access/update
        log.info("VestaboardConnector initialized.")

    async def close(self):
        """Closes the underlying httpx client gracefully."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            log.info("VestaboardConnector HTTP client closed.")

    async def _get_subscription_id(self) -> str:
        """
        Gets the Vestaboard subscription ID.

        Fetches via API call only if not already cached. Uses an async lock
        to prevent race conditions during cache population.

        Returns:
            The subscription ID as a string.

        Raises:
            VestaboardAuthError: If authentication fails or ID cannot be parsed.
            VestaboardError: For network issues or other API errors.
        """
        # Quick check without lock for performance
        if self._subscription_id is not None:
            return self._subscription_id

        # Acquire lock to ensure only one coroutine fetches/updates the cache
        async with self._sub_id_lock:
            # Double-check if another coroutine populated the cache while waiting
            if self._subscription_id is not None:
                return self._subscription_id

            log.info("Fetching Vestaboard subscription ID from API...")
            try:
                # Make the API call to get subscriptions
                response = await self._client.get("/subscriptions")
                response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx

                content = response.json()
                # Safely extract the first subscription ID
                subs = content.get("subscriptions")
                if isinstance(subs, list) and len(subs) > 0:
                    sub_id = subs[0].get("_id")
                    if sub_id:
                        self._subscription_id = str(sub_id)
                        log.info(f"Fetched and cached subscription ID: {self._subscription_id}")
                        return self._subscription_id

                # If extraction failed
                log.error(f"Could not parse subscription ID from API response: {content}")
                raise VestaboardAuthError("Could not parse subscription ID from Vestaboard API response.")

            except httpx.HTTPStatusError as e:
                 log.error(f"HTTP error getting subscription ID: {e.response.status_code} - {e.response.text}", exc_info=True)
                 if e.response.status_code in [401, 403]:
                     raise VestaboardAuthError(f"Authentication failed getting subscription ID (HTTP {e.response.status_code})") from e
                 else:
                     raise VestaboardError(f"HTTP error fetching subscription ID: {e.response.status_code}") from e
            except (httpx.RequestError, ValueError, KeyError, TypeError) as e: # Catch network, JSON, data structure errors
                log.error(f"Error processing subscription ID response: {e}", exc_info=True)
                raise VestaboardError(f"Failed to get or process subscription ID: {e}") from e

    async def _post_message(self, sub_id: str, data: Dict[str, Any]):
        """Helper method to POST data to the Vestaboard message endpoint."""
        msg_url = f"/subscriptions/{sub_id}/message"
        try:
            response = await self._client.post(msg_url, json=data)
            response.raise_for_status() # Check for HTTP errors
            log.info(f"Successfully posted message to Vestaboard subscription {sub_id} (Status: {response.status_code})")
        except httpx.HTTPStatusError as e:
             log.error(f"HTTP error posting message: {e.response.status_code} - {e.response.text}", exc_info=True)
             # Check for specific Vestaboard error codes if available in docs/response
             raise VestaboardError(f"Failed to post message (HTTP {e.response.status_code})") from e
        except httpx.RequestError as e:
             log.error(f"Network error posting message: {e}", exc_info=True)
             raise VestaboardError(f"Network error posting message: {e}") from e

    async def send_array(self, characters: List[List[int]]):
        """
        Sends a message formatted as a character array (6x22 grid).

        Args:
            characters: A list representing the 6x22 character grid.

        Raises:
            TypeError: If input 'characters' is not a list.
            VestaboardAuthError: If subscription ID cannot be obtained.
            VestaboardError: For network or other API errors during posting.
        """
        if not isinstance(characters, list):
             log.warning("Invalid type provided to send_array. Expected list.")
             raise TypeError("Input 'characters' must be a list.")

        sub_id = await self._get_subscription_id()
        payload = {"characters": characters}
        log.debug(f"Sending array message to subscription {sub_id}")
        await self._post_message(sub_id, payload)

    async def send_message(self, text: str):
        """
        Sends a message formatted as text. Validates characters first.

        Args:
            text: The text string to send.

        Raises:
            VestaboardInvalidCharsError: If the text contains characters not
                allowed by Vestaboard (based on internal regex).
            VestaboardAuthError: If subscription ID cannot be obtained.
            VestaboardError: For network or other API errors during posting.
        """
        string_text = str(text) # Ensure it's a string

        # Vestaboard allowed characters regex (adjust if official docs differ)
        # Consider pre-compiling: VALID_CHARS_REGEX = re.compile(r"^[A-Za-z0-9!@$\(\)\-+&=;:\'\"\%,./?° ]*$")
        if not re.match(r"^[A-Za-z0-9!@$\(\)\-+&=;:\'\"\%,./?° ]*$", string_text):
             log.warning(f"Message contains invalid characters: '{string_text}'")
             raise VestaboardInvalidCharsError(f"Message contains invalid characters.")

        sub_id = await self._get_subscription_id()
        payload = {"text": string_text}
        log.debug(f"Sending text message to subscription {sub_id}: '{string_text}'")
        await self._post_message(sub_id, payload)