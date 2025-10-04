import logging
import os
import socket
import uuid
from datetime import datetime
from typing import Optional
import requests
from models.log_models import LogPayload, LogLevel, LogResponse


class CentralLoggingService:
    """
    Logging service that logs to stdout and sends logs to a central logging collector.

    This service provides a unified logging interface that:
    1. Logs messages to stdout using Python's standard logging
    2. Asynchronously sends log messages to a central logging API

    Environment Variables:
        LOGS_COLLECTOR_API: Base URL of the central logging API (required)
        LOGS_COLLECTOR_TOKEN: Bearer token for authentication (required)
        APP_NAME: Application name (default: "cat-emails")
        APP_VERSION: Application version (default: "1.0.0")
        APP_ENVIRONMENT: Environment name (default: "production")
    """

    def __init__(
        self,
        logger_name: str = "cat-emails",
        log_level: int = logging.INFO,
        enable_remote: bool = True
    ):
        """
        Initialize the central logging service.

        Args:
            logger_name: Name for the local logger
            log_level: Logging level for local logger
            enable_remote: Whether to send logs to remote collector
        """
        # Initialize local logger
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(log_level)

        # Create console handler if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Remote logging configuration
        self.enable_remote = enable_remote
        self.api_base_url = os.getenv("LOGS_COLLECTOR_API", "").rstrip("/")
        self.api_token = os.getenv("LOGS_COLLECTOR_TOKEN", "")
        self.app_name = os.getenv("APP_NAME", "cat-emails")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.app_environment = os.getenv("APP_ENVIRONMENT", "production")
        self.hostname = socket.gethostname()

        # Validate remote logging configuration
        if self.enable_remote:
            if not self.api_base_url:
                self.logger.warning(
                    "LOGS_COLLECTOR_API not set. Remote logging disabled."
                )
                self.enable_remote = False
            elif not self.api_token:
                self.logger.warning(
                    "LOGS_COLLECTOR_TOKEN not set. Remote logging disabled."
                )
                self.enable_remote = False

    def _map_log_level(self, level: int) -> LogLevel:
        """Map Python logging level to LogLevel enum."""
        if level >= logging.CRITICAL:
            return LogLevel.CRITICAL
        elif level >= logging.ERROR:
            return LogLevel.ERROR
        elif level >= logging.WARNING:
            return LogLevel.WARNING
        elif level >= logging.INFO:
            return LogLevel.INFO
        else:
            return LogLevel.DEBUG

    def _send_to_remote(
        self,
        level: LogLevel,
        message: str,
        trace_id: Optional[str] = None
    ) -> bool:
        """
        Send log to central logging service.

        Args:
            level: Log level
            message: Log message
            trace_id: Optional trace ID for distributed tracing

        Returns:
            True if log was sent successfully, False otherwise
        """
        if not self.enable_remote:
            return False

        try:
            # Generate trace ID if not provided
            if trace_id is None:
                trace_id = str(uuid.uuid4())

            # Create log payload
            payload = LogPayload(
                application_name=self.app_name,
                environment=self.app_environment,
                hostname=self.hostname,
                level=level,
                message=message,
                timestamp=datetime.utcnow().isoformat() + "Z",
                trace_id=trace_id,
                version=self.app_version
            )

            # Send to API
            url = f"{self.api_base_url}/logs"
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                url,
                json=payload.model_dump(),
                headers=headers,
                timeout=5  # 5 second timeout
            )

            # Check response
            if response.status_code == 202:
                return True
            else:
                self.logger.warning(
                    f"Failed to send log to remote collector: "
                    f"HTTP {response.status_code}"
                )
                return False

        except requests.exceptions.Timeout:
            self.logger.warning("Timeout sending log to remote collector")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error sending log to remote collector: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error in remote logging: {e}")
            return False

    def debug(self, message: str, trace_id: Optional[str] = None):
        """Log a debug message."""
        self.logger.debug(message)
        self._send_to_remote(LogLevel.DEBUG, message, trace_id)

    def info(self, message: str, trace_id: Optional[str] = None):
        """Log an info message."""
        self.logger.info(message)
        self._send_to_remote(LogLevel.INFO, message, trace_id)

    def warning(self, message: str, trace_id: Optional[str] = None):
        """Log a warning message."""
        self.logger.warning(message)
        self._send_to_remote(LogLevel.WARNING, message, trace_id)

    def error(self, message: str, trace_id: Optional[str] = None):
        """Log an error message."""
        self.logger.error(message)
        self._send_to_remote(LogLevel.ERROR, message, trace_id)

    def critical(self, message: str, trace_id: Optional[str] = None):
        """Log a critical message."""
        self.logger.critical(message)
        self._send_to_remote(LogLevel.CRITICAL, message, trace_id)

    def log(
        self,
        level: int,
        message: str,
        trace_id: Optional[str] = None
    ):
        """
        Log a message at the specified level.

        Args:
            level: Python logging level (e.g., logging.INFO)
            message: Log message
            trace_id: Optional trace ID
        """
        self.logger.log(level, message)
        log_level = self._map_log_level(level)
        self._send_to_remote(log_level, message, trace_id)
