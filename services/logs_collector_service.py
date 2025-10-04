"""
Service for sending logs to LOGS_COLLECTOR_API.
"""
import os
import logging
import requests
from typing import Dict, Optional, Any
from datetime import datetime
import json


logger = logging.getLogger(__name__)


class LogsCollectorService:
    """Service for sending application logs to LOGS_COLLECTOR_API."""

    def __init__(self, api_url: Optional[str] = None, api_token: Optional[str] = None):
        """
        Initialize the logs collector service.

        Args:
            api_url: URL of the logs collector API (defaults to LOGS_COLLECTOR_API env var)
            api_token: Authentication token for the API (defaults to LOGS_COLLECTOR_API_TOKEN env var)
        """
        self.api_url = api_url or os.getenv("LOGS_COLLECTOR_API")
        self.api_token = api_token or os.getenv("LOGS_COLLECTOR_API_TOKEN")

        if not self.api_url:
            logger.warning("LOGS_COLLECTOR_API not configured. Logs will not be sent to collector.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"LogsCollectorService initialized with API: {self.api_url}")

    def send_log(self,
                 level: str,
                 message: str,
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
        if not self.enabled:
            return False

        try:
            payload = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": level.upper(),
                "message": message,
                "source": source or "cat-emails",
                "context": context or {}
            }

            headers = {
                "Content-Type": "application/json"
            }

            # Add authentication token if available
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=5  # 5 second timeout to avoid blocking
            )

            response.raise_for_status()
            logger.debug(f"Log sent to collector: {level} - {message[:50]}...")
            return True

        except requests.exceptions.Timeout:
            logger.warning("Timeout sending log to collector")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send log to collector: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending log to collector: {str(e)}")
            return False

    def send_bulk_logs(self, logs: list) -> Dict[str, int]:
        """
        Send multiple log entries to the logs collector API in bulk.

        Args:
            logs: List of log dictionaries with keys: level, message, context, source

        Returns:
            dict: Dictionary with 'success' and 'failed' counts
        """
        if not self.enabled:
            return {"success": 0, "failed": len(logs)}

        results = {"success": 0, "failed": 0}

        for log_entry in logs:
            level = log_entry.get("level", "INFO")
            message = log_entry.get("message", "")
            context = log_entry.get("context")
            source = log_entry.get("source")

            if self.send_log(level, message, context, source):
                results["success"] += 1
            else:
                results["failed"] += 1

        logger.info(f"Bulk log send complete: {results['success']} success, {results['failed']} failed")
        return results

    def send_processing_run_log(self,
                               run_id: str,
                               status: str,
                               metrics: Optional[Dict[str, Any]] = None,
                               error: Optional[str] = None,
                               source: Optional[str] = None) -> bool:
        """
        Send a processing run log entry.

        Args:
            run_id: Unique identifier for the processing run
            status: Status of the run (started, completed, failed)
            metrics: Processing metrics (emails processed, deleted, etc.)
            error: Error message if the run failed
            source: Source of the log (defaults to "email-processor")

        Returns:
            bool: True if log was sent successfully
        """
        context = {
            "run_id": run_id,
            "status": status,
            "metrics": metrics or {}
        }

        if error:
            context["error"] = error

        level = "ERROR" if error else "INFO"
        message = f"Processing run {status}: {run_id}"

        return self.send_log(level, message, context, source or "email-processor")

    def send_email_processing_log(self,
                                  message_id: str,
                                  category: str,
                                  action: str,
                                  sender: str,
                                  processing_time: Optional[float] = None,
                                  source: Optional[str] = None) -> bool:
        """
        Send a log entry for a processed email.

        Args:
            message_id: Email message ID
            category: Assigned category
            action: Action taken (kept/deleted/archived)
            sender: Email sender
            processing_time: Time taken to process the email
            source: Source of the log (defaults to "email-processor")

        Returns:
            bool: True if log was sent successfully
        """
        context = {
            "message_id": message_id,
            "category": category,
            "action": action,
            "sender": sender
        }

        if processing_time is not None:
            context["processing_time_seconds"] = processing_time

        message = f"Email processed: {category} - {action}"

        return self.send_log("INFO", message, context, source or "email-processor")
