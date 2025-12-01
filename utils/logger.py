"""
Central logger configuration for Cat-Emails project.

This module provides centralized logging configuration using Python's standard logging.
All modules should import get_logger from this module instead of using
logging.getLogger directly.

Usage:
    from utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("This message goes to stdout/stderr")
"""

import sys
import logging
from typing import Optional, Dict
from threading import Lock


# Global initialization state
_initialized: bool = False
_lock = Lock()

# Cache of module loggers
_logger_cache: Dict[str, logging.Logger] = {}


def initialize_central_logging(
    log_level: int = logging.INFO,
    enable_remote: bool = True,
    queue_maxsize: int = 1000,
    force: bool = False
) -> None:
    """
    Initialize the central logging service.

    This should be called once at application startup before any logging occurs.
    If not called explicitly, it will be initialized with default settings on first use.

    Args:
        log_level: Default logging level (default: logging.INFO)
        enable_remote: Deprecated - remote logging has been removed
        queue_maxsize: Deprecated - remote logging has been removed
        force: Force re-initialization even if already initialized

    Returns:
        None (no-op for backward compatibility)
    """
    global _initialized

    with _lock:
        if _initialized and not force:
            return None

        # Configure the root logger
        _configure_root_logger(log_level)

        _initialized = True

        return None


def _configure_root_logger(log_level: int):
    """
    Configure the root logger for stdout/stderr output.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add a StreamHandler for stderr output
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance.

    This is a drop-in replacement for logging.getLogger() that ensures
    consistent logging configuration.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        A logging.Logger instance

    Example:
        from utils.logger import get_logger

        logger = get_logger(__name__)
        logger.info("Application started")
    """
    global _initialized, _logger_cache

    # Initialize logging if not already done
    if not _initialized:
        initialize_central_logging()

    # Use module name or default
    logger_name = name or "cat-emails"

    # Return cached logger if it exists
    if logger_name in _logger_cache:
        return _logger_cache[logger_name]

    # Create a new logger
    logger = logging.getLogger(logger_name)

    # Cache and return
    _logger_cache[logger_name] = logger
    return logger


def get_central_service() -> Optional[object]:
    """
    Get the central logging service instance.

    Returns:
        None - remote logging service has been removed
    """
    return None


def shutdown_logging(timeout: float = 5.0):
    """
    Gracefully shutdown the logging service.

    This is kept for backward compatibility but is now a no-op
    since remote logging has been removed.

    Args:
        timeout: Deprecated - no longer used
    """
    # No-op - standard logging doesn't need explicit shutdown
    pass
