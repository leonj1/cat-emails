"""Logs Collector Client - Interface and implementation for sending logs to a remote logs collector service."""

from abc import ABC, abstractmethod
from datetime import datetime
import socket
from typing import Optional

from pydantic import BaseModel, Field

try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False


class LogEntry(BaseModel):
    """Pydantic model representing a log entry payload for the logs collector API."""

    application_name: str = Field(..., description="Name of the application")
    message: str = Field(..., description="Actual log content")
    environment: Optional[str] = Field(None, description="Deployment environment (e.g., 'production', 'staging')")
    hostname: Optional[str] = Field(None, description="Server/host sending the log")
    level: Optional[str] = Field(None, description="Log severity level (e.g., 'info', 'warning', 'error')")
    timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp")
    trace_id: Optional[str] = Field(None, description="Unique trace identifier")
    version: Optional[str] = Field(None, description="Application version")


class LogsCollectorClient(ABC):
    """Abstract interface for logs collector clients."""

    @abstractmethod
    def send(self, log_entry: LogEntry) -> bool:
        """
        Send a log entry to the logs collector service.

        Args:
            log_entry: LogEntry Pydantic model containing log data

        Returns:
            bool: True if successful, False otherwise
        """
        pass


class RemoteLogsCollectorClient(LogsCollectorClient):
    """Concrete implementation of LogsCollectorClient for sending logs to a remote service."""

    def __init__(self, logs_collector_url: str, application_name: str, logs_collector_token: str):
        """
        Initialize the logs collector client.

        Args:
            logs_collector_url: Base URL of the logs collector service
            application_name: Name of the application sending logs
            logs_collector_token: Authentication token for the logs collector API
        """
        self.logs_collector_url = logs_collector_url.rstrip('/')
        self.application_name = application_name
        self.logs_collector_token = logs_collector_token
        self.endpoint = f"{self.logs_collector_url}/logs"

    def send(self, log_entry: LogEntry) -> bool:
        """
        Send a log entry to the logs collector service.

        Args:
            log_entry: LogEntry Pydantic model containing log data

        Returns:
            bool: True if log was sent successfully, False otherwise
        """
        if not _HAS_REQUESTS:
            print("Error: requests library not available")
            return False

        try:
            # Ensure application_name is set
            if not log_entry.application_name:
                log_entry.application_name = self.application_name

            # Set default timestamp if not provided
            if not log_entry.timestamp:
                log_entry.timestamp = datetime.utcnow().isoformat() + 'Z'

            # Set default hostname if not provided
            if not log_entry.hostname:
                log_entry.hostname = socket.gethostname()

            # Prepare headers with authentication
            headers = {
                'Authorization': f'Bearer {self.logs_collector_token}',
                'Content-Type': 'application/json'
            }

            # Send POST request
            response = requests.post(
                self.endpoint,
                json=log_entry.model_dump(exclude_none=True),
                headers=headers,
                timeout=10
            )

            # Check if request was successful
            response.raise_for_status()
            return True

        except requests.exceptions.HTTPError as e:
            # Extract error details from response if available
            error_msg = f"Failed to send log to collector: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    if 'details' in error_data:
                        error_msg += f" - Details: {error_data['details']}"
                        print(f"ERROR: Logs collector API error details: {error_data['details']}")
                    elif 'message' in error_data:
                        error_msg += f" - Message: {error_data['message']}"
                    elif 'error' in error_data:
                        error_msg += f" - Error: {error_data['error']}"
                except Exception:
                    # If response is not JSON or doesn't have expected fields
                    error_msg += f" - Response: {e.response.text[:500]}"
            print(error_msg)
            return False
        except requests.exceptions.RequestException as e:
            # Log error locally
            print(f"Failed to send log to collector: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error sending log: {e}")
            return False


class FakeLogsCollectorClient(LogsCollectorClient):
    """Fake implementation of LogsCollectorClient for testing purposes. Makes no external calls."""

    def __init__(self, logs_collector_url: str, application_name: str, logs_collector_token: str):
        """
        Initialize the fake logs collector client.

        Args:
            logs_collector_url: Base URL of the logs collector service (unused)
            application_name: Name of the application sending logs (unused)
            logs_collector_token: Authentication token for the logs collector API (unused)
        """
        self.logs_collector_url = logs_collector_url
        self.application_name = application_name
        self.logs_collector_token = logs_collector_token

    def send(self, log_entry: LogEntry) -> bool:
        """
        Fake send method that does nothing and always returns True.

        Args:
            log_entry: LogEntry Pydantic model containing log data

        Returns:
            bool: Always True
        """
        pass
        return True


__all__ = ["LogEntry", "LogsCollectorClient", "RemoteLogsCollectorClient", "FakeLogsCollectorClient"]
