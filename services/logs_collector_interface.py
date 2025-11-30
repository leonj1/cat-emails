"""
Interface for log collection services.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ILogsCollector(ABC):
    """Interface for log collection services."""

    @abstractmethod
    def send_log(self, level: str, message: str,
                 context: Optional[Dict[str, Any]] = None,
                 source: Optional[str] = None) -> bool:
        """
        Send a log entry to the logs collector API.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            context: Additional context data
            source: Source of the log (e.g., service name, module name)

        Returns:
            bool: True if log was sent successfully, False otherwise
        """
        pass

    @property
    @abstractmethod
    def is_send_enabled(self) -> bool:
        """
        Check if log sending is enabled.

        Returns:
            bool: True if log sending is enabled, False otherwise
        """
        pass
