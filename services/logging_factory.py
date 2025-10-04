"""Factory functions for creating logging service instances."""

import os
import logging
from typing import Optional

from services.logging_service import CentralLoggingService
from clients.logs_collector_client import (
    LogsCollectorClient,
    RemoteLogsCollectorClient,
    FakeLogsCollectorClient
)


def create_logging_service(
    logger_name: str = "cat-emails",
    log_level: int = logging.INFO,
    enable_remote: bool = True,
    queue_maxsize: int = 1000,
    logs_collector_client: Optional[LogsCollectorClient] = None
) -> CentralLoggingService:
    """
    Factory function to create a CentralLoggingService with proper client setup.

    This factory automatically configures the appropriate LogsCollectorClient based on
    environment variables or uses a provided client instance.

    Environment Variables:
        LOGS_COLLECTOR_API: Base URL of the central logging API
        LOGS_COLLECTOR_TOKEN: Bearer token for authentication
        APP_NAME: Application name (default: "cat-emails")

    Args:
        logger_name: Name for the local logger
        log_level: Logging level for local logger
        enable_remote: Whether to send logs to remote collector
        queue_maxsize: Maximum size of the remote logging queue
        logs_collector_client: Optional pre-configured client (overrides auto-detection)

    Returns:
        Configured CentralLoggingService instance

    Examples:
        # Basic usage with environment variables
        logger = create_logging_service()

        # Custom logger name and level
        logger = create_logging_service(
            logger_name="my-service",
            log_level=logging.DEBUG
        )

        # Local-only logging (no remote)
        logger = create_logging_service(enable_remote=False)

        # Custom client
        client = RemoteLogsCollectorClient(...)
        logger = create_logging_service(logs_collector_client=client)
    """
    # If client is provided, use it directly
    if logs_collector_client is not None:
        return CentralLoggingService(
            logs_collector_client=logs_collector_client,
            logger_name=logger_name,
            log_level=log_level,
            enable_remote=enable_remote,
            queue_maxsize=queue_maxsize
        )

    # Get configuration from environment
    api_url = os.getenv("LOGS_COLLECTOR_API", "").rstrip("/")
    api_token = os.getenv("LOGS_COLLECTOR_TOKEN", "")
    app_name = os.getenv("APP_NAME", "cat-emails")

    # Choose appropriate client implementation
    if enable_remote and api_url and api_token:
        client = RemoteLogsCollectorClient(
            logs_collector_url=api_url,
            application_name=app_name,
            logs_collector_token=api_token
        )
    else:
        # Use fake client when remote is disabled or not configured
        client = FakeLogsCollectorClient(
            logs_collector_url=api_url or "http://localhost",
            application_name=app_name,
            logs_collector_token=api_token or "fake-token"
        )
        enable_remote = False

    return CentralLoggingService(
        logs_collector_client=client,
        logger_name=logger_name,
        log_level=log_level,
        enable_remote=enable_remote,
        queue_maxsize=queue_maxsize
    )


__all__ = ["create_logging_service"]
