from abc import ABC, abstractmethod
from fastapi import WebSocket


class WebSocketAuthInterface(ABC):
    """Interface for WebSocket authentication services."""

    @abstractmethod
    def verify_api_key(self, websocket: WebSocket) -> bool:
        """
        Verify API key for WebSocket connections.

        Args:
            websocket: WebSocket connection to check

        Returns:
            bool: True if valid or no API key required, False otherwise
        """
        pass
