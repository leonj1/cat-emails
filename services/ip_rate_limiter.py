"""
IP-based Rate Limiter for OAuth State Init Endpoint.

Implements sliding window rate limiting:
- 10 requests per minute per IP address
- Thread-safe using locks
- Automatic cleanup of expired entries
"""

import threading
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


class IPRateLimiter:
    """IP-based rate limiter using sliding window algorithm."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize the rate limiter.

        Args:
            max_requests: Maximum number of requests per window (default: 10)
            window_seconds: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[datetime]] = {}
        self._lock = threading.Lock()

    def check_rate_limit(self, ip_address: str) -> Tuple[bool, Optional[float]]:
        """
        Check if a request from the given IP is allowed.

        Args:
            ip_address: The client IP address

        Returns:
            Tuple of (allowed: bool, seconds_until_allowed: Optional[float])
            - If allowed is True, seconds_until_allowed is None
            - If allowed is False, seconds_until_allowed indicates when to retry
        """
        with self._lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)

            # Get request history for this IP
            if ip_address not in self._requests:
                return True, None

            # Remove requests outside the window
            request_times = self._requests[ip_address]
            valid_requests = [ts for ts in request_times if ts > window_start]
            self._requests[ip_address] = valid_requests

            # Check if limit is exceeded
            if len(valid_requests) >= self.max_requests:
                # Calculate wait time until oldest request expires
                oldest_request = min(valid_requests)
                wait_time = (oldest_request + timedelta(seconds=self.window_seconds) - now).total_seconds()
                return False, max(0, wait_time)

            return True, None

    def allow_request(self, ip_address: str) -> Tuple[bool, Optional[float]]:
        """
        Atomically check rate limit and record request if allowed.

        This method performs check and record in a single atomic operation,
        preventing race conditions and ensuring all requests (valid or invalid)
        are counted toward the rate limit.

        Args:
            ip_address: The client IP address

        Returns:
            Tuple of (allowed: bool, seconds_until_allowed: Optional[float])
            - If allowed is True, request was recorded and seconds_until_allowed is None
            - If allowed is False, request was NOT recorded and seconds_until_allowed indicates retry time
        """
        with self._lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)

            # Get request history for this IP
            if ip_address not in self._requests:
                self._requests[ip_address] = []

            # Remove requests outside the window
            request_times = self._requests[ip_address]
            valid_requests = [ts for ts in request_times if ts > window_start]
            self._requests[ip_address] = valid_requests

            # Check if limit is exceeded
            if len(valid_requests) >= self.max_requests:
                # Calculate wait time until oldest request expires
                oldest_request = min(valid_requests)
                wait_time = (oldest_request + timedelta(seconds=self.window_seconds) - now).total_seconds()
                return False, max(0, wait_time)

            # Record this request
            self._requests[ip_address].append(now)
            return True, None

    def record_request(self, ip_address: str) -> None:
        """
        Record a request from the given IP.

        DEPRECATED: Use allow_request() instead for atomic check-and-record.
        This method is kept for backward compatibility but should not be used
        with check_rate_limit() as it creates a race condition.

        Args:
            ip_address: The client IP address
        """
        with self._lock:
            now = datetime.now()
            if ip_address not in self._requests:
                self._requests[ip_address] = []
            self._requests[ip_address].append(now)

    def reset(self, ip_address: str) -> None:
        """
        Reset rate limit for a specific IP address.

        Args:
            ip_address: The client IP address to reset
        """
        with self._lock:
            if ip_address in self._requests:
                del self._requests[ip_address]

    def reset_all(self) -> None:
        """Reset rate limits for all IP addresses."""
        with self._lock:
            self._requests.clear()
