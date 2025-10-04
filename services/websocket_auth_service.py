import logging
from typing import Optional
from fastapi import WebSocket
from services.websocket_auth_interface import WebSocketAuthInterface

logger = logging.getLogger(__name__)


class WebSocketAuthService(WebSocketAuthInterface):
    """Service for authenticating WebSocket connections."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the WebSocket auth service.

        Args:
            api_key: The API key to validate against, None if auth is disabled
        """
        self.api_key = api_key

    def verify_api_key(self, websocket: WebSocket) -> bool:
        """
        Verify API key for WebSocket connections.

        Args:
            websocket: WebSocket connection to check

        Returns:
            bool: True if valid or no API key required, False otherwise
        """
        if not self.api_key:
            return True

        # Check for API key in query parameters first
        api_key = websocket.query_params.get("api_key")

        # If not in query params, check headers
        if not api_key:
            api_key = websocket.headers.get("x-api-key")

        # Verify the API key
        if not api_key or api_key != self.api_key:
            logger.warning("WebSocket connection rejected: Invalid or missing API key")
            return False

        return True
