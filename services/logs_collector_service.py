"""
Service for sending logs to LOGS_COLLECTOR_API.
"""
import os
import logging
from utils.logger import get_logger
import requests
import socket
import uuid
import time
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse
import json

from services.logs_collector_interface import ILogsCollector


logger = get_logger(__name__)


class LogsCollectorService(ILogsCollector):
    """Service for sending application logs to LOGS_COLLECTOR_API."""

    def __init__(self, send_logs: bool, api_url: Optional[str] = None, api_token: Optional[str] = None):
        """
        Initialize the logs collector service.

        Args:
            send_logs: Whether to enable log sending
            api_url: URL of the logs collector API (defaults to LOGS_COLLECTOR_API env var)
            api_token: Authentication token for the API (defaults to LOGS_COLLECTOR_TOKEN or LOGS_COLLECTOR_API_TOKEN env var)
        """
        self._send_logs = send_logs
        self.api_url = api_url or os.getenv("LOGS_COLLECTOR_API")
        # Support both LOGS_COLLECTOR_TOKEN (deployment) and LOGS_COLLECTOR_API_TOKEN (local) env vars
        self.api_token = api_token or os.getenv("LOGS_COLLECTOR_TOKEN") or os.getenv("LOGS_COLLECTOR_API_TOKEN")

        # DNS cache for Railway domains
        self._dns_cache: Dict[str, Tuple[str, datetime]] = {}
        self._dns_cache_ttl = timedelta(minutes=5)  # Cache DNS for 5 minutes

        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1  # Initial retry delay in seconds

        if not self.api_url:
            logger.warning("LOGS_COLLECTOR_API not configured. Logs will not be sent to collector.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"LogsCollectorService initialized with API: {self.api_url}")
            # Pre-resolve DNS on initialization
            self._resolve_dns(self.api_url)

    @property
    def is_send_enabled(self) -> bool:
        """
        Check if log sending is enabled.

        Returns:
            bool: True if log sending is enabled, False otherwise
        """
        return self._send_logs

    def _resolve_dns(self, url: str) -> Optional[str]:
        """
        Resolve and cache DNS for a given URL.

        Args:
            url: The URL to resolve

        Returns:
            The resolved IP address or None if resolution fails
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname

            if not hostname:
                return None

            # Check cache first
            if hostname in self._dns_cache:
                cached_ip, cached_time = self._dns_cache[hostname]
                if datetime.now() - cached_time < self._dns_cache_ttl:
                    logger.debug(f"Using cached DNS for {hostname}: {cached_ip}")
                    return cached_ip

            # Resolve DNS
            ip_address = socket.gethostbyname(hostname)
            self._dns_cache[hostname] = (ip_address, datetime.now())
            logger.debug(f"Resolved DNS for {hostname}: {ip_address}")
            return ip_address

        except socket.gaierror as e:
            logger.warning(f"Failed to resolve DNS for {url}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error during DNS resolution for {url}: {e}")
            return None

    def _make_request_with_retry(self, endpoint: str, payload: dict, headers: dict) -> requests.Response:
        """
        Make an HTTP request with retry logic and DNS fallback.

        Args:
            endpoint: The API endpoint
            payload: The request payload
            headers: The request headers

        Returns:
            The response object

        Raises:
            requests.exceptions.RequestException: If all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                # Try to pre-resolve DNS before making the request
                if attempt > 0:
                    self._resolve_dns(endpoint)
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff

                response = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=5 + (attempt * 2)  # Increase timeout with each retry
                )
                return response

            except requests.exceptions.ConnectionError as e:
                # Check if it's a DNS resolution error
                if "NameResolutionError" in str(e) or "Failed to resolve" in str(e):
                    logger.warning(f"DNS resolution failed (attempt {attempt + 1}/{self.max_retries}): {endpoint}")

                    # Try using IP directly if we have it cached
                    parsed = urlparse(endpoint)
                    hostname = parsed.hostname
                    if hostname and hostname in self._dns_cache:
                        cached_ip, _ = self._dns_cache[hostname]
                        # Construct URL with IP
                        ip_endpoint = endpoint.replace(hostname, cached_ip)
                        # Add Host header for proper routing
                        headers_with_host = headers.copy()
                        headers_with_host["Host"] = hostname

                        try:
                            logger.info(f"Retrying with cached IP: {cached_ip}")
                            response = requests.post(
                                ip_endpoint,
                                json=payload,
                                headers=headers_with_host,
                                timeout=5 + (attempt * 2),
                                verify=False  # Skip SSL verification when using IP directly
                            )
                            return response
                        except Exception as ip_error:
                            logger.warning(f"Failed to connect using IP directly: {ip_error}")

                last_exception = e

            except requests.exceptions.Timeout as e:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries})")
                last_exception = e

            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt == self.max_retries - 1:
                    raise

        # All retries failed
        if last_exception:
            raise last_exception
        else:
            raise requests.exceptions.RequestException(f"Failed after {self.max_retries} attempts")

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
        # Check send_logs flag FIRST
        if not self._send_logs:
            logger.debug("Log sending disabled by feature flag")
            return False

        if not self.enabled:
            logger.debug("Log sending disabled: no API URL configured")
            return False

        try:
            # Required fields for logs-collector API
            # Generate a default trace_id if not provided (API requires non-empty trace_id)
            default_trace_id = str(uuid.uuid4())

            payload = {
                "application_name": source or "cat-emails",
                "environment": os.getenv("ENVIRONMENT", "production"),
                "message": message,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": level.lower(),  # logs-collector expects lowercase levels
                "trace_id": context.get("trace_id", default_trace_id) if context else default_trace_id,
                "version": os.getenv("APP_VERSION", "1.0.0"),
                "hostname": socket.gethostname()
            }

            headers = {
                "Content-Type": "application/json"
            }

            # Add authentication token if available
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            # Ensure we're posting to the /logs endpoint
            endpoint = f"{self.api_url.rstrip('/')}/logs"

            # Use the retry mechanism
            response = self._make_request_with_retry(endpoint, payload, headers)

            response.raise_for_status()
            logger.debug(f"Log sent to collector: {level} - {message[:50]}...")
            return True

        except requests.exceptions.Timeout:
            logger.warning("Timeout sending log to collector after retries")
            return False
        except requests.exceptions.HTTPError as e:
            # Extract error details from response if available
            error_msg = f"Failed to send log to collector: {str(e)}"
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
                except (json.JSONDecodeError, KeyError):
                    # If response is not JSON or doesn't have expected fields
                    error_msg += f" - Response: {e.response.text[:500]}"
            logger.error(error_msg)
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
