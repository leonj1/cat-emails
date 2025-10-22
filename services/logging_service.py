import logging
import os
import socket
import uuid
from datetime import datetime, timezone
from typing import Optional
from queue import Queue, Empty, Full
from threading import Thread, Event
import atexit
from models.log_models import LogPayload, LogLevel, LogResponse
from clients.logs_collector_client import LogsCollectorClient, LogEntry


class CentralLoggingService:
    """
    Logging service that logs to stdout and sends logs to a central logging collector.

    This service provides a unified logging interface that:
    1. Logs messages to stdout using Python's standard logging
    2. Asynchronously sends log messages to a central logging API via LogsCollectorClient

    Environment Variables:
        APP_NAME: Application name (default: "cat-emails")
        APP_VERSION: Application version (default: "1.0.0")
        APP_ENVIRONMENT: Environment name (default: "production")
    """

    def __init__(
        self,
        logs_collector_client: LogsCollectorClient,
        logger_name: str = "cat-emails",
        log_level: int = logging.INFO,
        enable_remote: bool = True,
        queue_maxsize: int = 1000
    ):
        """
        Initialize the central logging service.

        Args:
            logs_collector_client: Client for sending logs to remote collector (required)
            logger_name: Name for the local logger
            log_level: Logging level for local logger
            enable_remote: Whether to send logs to remote collector
            queue_maxsize: Maximum size of the remote logging queue (default: 1000)
        """
        self.logs_collector_client = logs_collector_client
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
        self.app_name = os.getenv("APP_NAME", "cat-emails")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.app_environment = os.getenv("APP_ENVIRONMENT", "production")
        self.hostname = socket.gethostname()

        # Background thread for async remote logging
        self.log_queue: Optional[Queue] = None
        self.worker_thread: Optional[Thread] = None
        self.shutdown_event: Optional[Event] = None
        self.queue_maxsize = queue_maxsize

        if self.enable_remote:
            self.log_queue = Queue(maxsize=queue_maxsize)
            self.shutdown_event = Event()
            self.worker_thread = Thread(
                target=self._remote_logging_worker,
                daemon=True,
                name="RemoteLoggingWorker"
            )
            self.worker_thread.start()
            # Register cleanup handler
            atexit.register(self.shutdown)

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

    def _remote_logging_worker(self):
        """
        Background worker thread that processes the log queue.
        Runs continuously until shutdown_event is set.
        """
        while True:
            try:
                log_entry = self.log_queue.get(timeout=1.0)
            except Empty:
                if self.shutdown_event.is_set():
                    break
                continue

            if log_entry is None:  # Sentinel value for shutdown
                self.log_queue.task_done()
                break

            level, message, trace_id = log_entry
            try:
                self._send_to_remote_sync(level, message, trace_id)
            finally:
                self.log_queue.task_done()

    def _send_to_remote_sync(
        self,
        level: LogLevel,
        message: str,
        trace_id: Optional[str] = None
    ) -> bool:
        """
        Synchronously send log to central logging service via LogsCollectorClient.
        This method is called by the background worker thread.

        Args:
            level: Log level
            message: Log message
            trace_id: Optional trace ID for distributed tracing

        Returns:
            True if log was sent successfully, False otherwise
        """
        try:
            # Generate trace ID if not provided
            if trace_id is None:
                trace_id = str(uuid.uuid4())

            # Create log entry using LogEntry model from client
            # Format timestamp with 'Z' suffix instead of '+00:00' for UTC
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

            log_entry = LogEntry(
                application_name=self.app_name,
                message=message,
                environment=self.app_environment,
                hostname=self.hostname,
                level=level.value,
                timestamp=timestamp,
                trace_id=trace_id,
                version=self.app_version
            )

            # Send via client interface
            return self.logs_collector_client.send(log_entry)

        except Exception as e:
            self.logger.exception(f"Unexpected error in remote logging: {e}")
            return False

    def _send_to_remote(
        self,
        level: LogLevel,
        message: str,
        trace_id: Optional[str] = None
    ):
        """
        Queue log for asynchronous sending to central logging service.
        Returns immediately without blocking.

        When the queue is full, this method will drop the oldest log entry
        to make room for the new one, preventing memory bloat.

        Args:
            level: Log level
            message: Log message
            trace_id: Optional trace ID for distributed tracing
        """
        if not self.enable_remote or self.log_queue is None:
            return

        try:
            # Non-blocking queue put
            self.log_queue.put_nowait((level, message, trace_id))
        except Full:
            # Queue is full - drop the oldest entry to make room for the new one
            # This prevents memory bloat when the remote collector is down
            try:
                # Remove oldest entry
                old_entry = self.log_queue.get_nowait()
                old_level, old_msg, old_trace = old_entry
                self.logger.warning(
                    f"Remote logging queue full (size={self.queue_maxsize}). "
                    f"Dropping oldest log entry: level={old_level.value}, "
                    f"trace_id={old_trace}, message_preview={old_msg[:50]}..."
                )
                # Add the new entry
                self.log_queue.put_nowait((level, message, trace_id))
            except (Empty, Full) as e:
                # Rare edge case - log but don't block
                self.logger.warning(
                    f"Failed to apply queue saturation policy: {e}. "
                    f"Dropping new log entry: level={level.value}, trace_id={trace_id}"
                )

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

    def shutdown(self, timeout: float = 5.0):
        """
        Gracefully shutdown the remote logging worker.
        Waits for queued logs to be sent before stopping.

        Args:
            timeout: Maximum seconds to wait for queue to empty
        """
        if not self.enable_remote or self.worker_thread is None:
            return

        if self.log_queue is None or self.shutdown_event is None:
            return

        # Let the worker finish everything already queued
        self.log_queue.join()

        # Tell the worker to exit and wake it with a sentinel
        self.shutdown_event.set()
        self.log_queue.put_nowait(None)

        # Wait for worker thread to finish
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=timeout)
