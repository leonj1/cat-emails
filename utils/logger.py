"""
Central logger configuration for Cat-Emails project.

This module provides centralized logging configuration using CentralLoggingService.
All modules should import get_logger from this module instead of using
logging.getLogger directly.

Usage:
    from utils.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("This message goes to both stdout and central logging service")
"""

import os
import sys
import logging
from typing import Optional, Dict
from threading import Lock

from services.logging_factory import create_logging_service
from services.logging_service import CentralLoggingService


# Global central logging service instance
_central_logging_service: Optional[CentralLoggingService] = None
_initialized: bool = False
_lock = Lock()

# Cache of module loggers that use the central service
_logger_cache: Dict[str, logging.Logger] = {}


def initialize_central_logging(
    log_level: int = logging.INFO,
    enable_remote: bool = True,
    queue_maxsize: int = 1000,
    force: bool = False
) -> CentralLoggingService:
    """
    Initialize the central logging service.

    This should be called once at application startup before any logging occurs.
    If not called explicitly, it will be initialized with default settings on first use.

    Args:
        log_level: Default logging level (default: logging.INFO)
        enable_remote: Preferred default for sending logs to the remote collector
            when DISABLE_REMOTE_LOGS is not set (default: True)
        queue_maxsize: Maximum size of remote logging queue (default: 1000)
        force: Force re-initialization even if already initialized

    Returns:
        The initialized CentralLoggingService instance

    Environment Variables:
        DISABLE_REMOTE_LOGS: When set to a truthy value ("true", "1", or "yes",
            case-insensitive), remote logging is forcibly disabled regardless
            of the enable_remote argument.
    """
    global _central_logging_service, _initialized

    with _lock:
        if _initialized and not force:
            return _central_logging_service

        # Create the central logging service
        # Note: DISABLE_REMOTE_LOGS env var is checked in create_logging_service(),
        # and will forcibly disable remote logging even if enable_remote=True here.
        _central_logging_service = create_logging_service(
            logger_name="cat-emails",
            log_level=log_level,
            enable_remote=enable_remote,
            queue_maxsize=queue_maxsize
        )
        
        # Configure the root logger to use CentralLoggingService
        _configure_root_logger(log_level)
        
        _initialized = True
        
        return _central_logging_service


def _configure_root_logger(log_level: int):
    """
    Configure the root logger to redirect all logging through CentralLoggingService.
    
    This ensures that even libraries using logging.getLogger() directly will
    have their logs routed through our central service.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create a custom handler that routes logs through CentralLoggingService
    class CentralLoggingHandler(logging.Handler):
        """Handler that routes logs through CentralLoggingService."""
        
        def emit(self, record):
            try:
                # Format the message using the handler's formatter
                if self.formatter:
                    msg = self.formatter.format(record)
                else:
                    msg = record.getMessage()
                
                # If there's exception info, append it to the message
                if record.exc_info:
                    import traceback
                    exc_text = ''.join(traceback.format_exception(*record.exc_info))
                    msg = msg + '\n' + exc_text
                
                # Skip logs from the CentralLoggingService itself to avoid recursion
                if record.name == "cat-emails" or record.name.startswith("cat-emails."):
                    # For the central logging service itself, use standard stderr output
                    sys.stderr.write(msg + '\n')
                    sys.stderr.flush()
                    return
                
                # Directly call the internal methods of CentralLoggingService
                # without going through the logger to avoid recursion
                if _central_logging_service:
                    _central_logging_service._send_to_remote(
                        _central_logging_service._map_log_level(record.levelno), 
                        msg
                    )
                
                # Always output to stderr for all logs (including third-party)
                # Use sys.stderr dynamically so it works with test mocking
                sys.stderr.write(msg + '\n')
                sys.stderr.flush()
                
            except Exception as e:
                # Fallback to stderr if central logging fails
                import traceback
                sys.stderr.write(f"Error in logging handler: {e}\n")
                traceback.print_exc(file=sys.stderr)
                self.handleError(record)
    
    # Add our custom handler to the root logger
    handler = CentralLoggingHandler()
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance that uses the central logging service.
    
    This is a drop-in replacement for logging.getLogger() that ensures
    all logging goes through CentralLoggingService.
    
    Args:
        name: Logger name (typically __name__ from the calling module)
        
    Returns:
        A logging.Logger instance configured to use CentralLoggingService
        
    Example:
        from utils.logger import get_logger
        
        logger = get_logger(__name__)
        logger.info("Application started")
    """
    global _initialized, _logger_cache
    
    # Initialize central logging if not already done
    if not _initialized:
        initialize_central_logging()
    
    # Use module name or default
    logger_name = name or "cat-emails"
    
    # Return cached logger if it exists
    if logger_name in _logger_cache:
        return _logger_cache[logger_name]
    
    # Create a new logger
    logger = logging.getLogger(logger_name)
    
    # The logger will inherit the root logger's configuration
    # which routes through CentralLoggingService
    
    # Cache and return
    _logger_cache[logger_name] = logger
    return logger


def get_central_service() -> Optional[CentralLoggingService]:
    """
    Get the central logging service instance.
    
    Returns:
        The CentralLoggingService instance, or None if not initialized
    """
    return _central_logging_service


def shutdown_logging(timeout: float = 5.0):
    """
    Gracefully shutdown the central logging service.
    
    This should be called at application shutdown to ensure all
    queued logs are sent to the remote collector.
    
    Args:
        timeout: Maximum seconds to wait for queue to empty
    """
    if _central_logging_service:
        _central_logging_service.shutdown(timeout=timeout)


# Configure logging on module import if running as main application
# This ensures logging is configured even if initialize_central_logging() is not called
if os.getenv("APP_NAME") or os.getenv("LOGS_COLLECTOR_API"):
    # Auto-initialize if environment suggests we're in production
    initialize_central_logging()
