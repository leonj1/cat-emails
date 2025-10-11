"""
Rate limiter service for API endpoints

Provides thread-safe rate limiting functionality to prevent abuse
of resource-intensive operations like force email processing.
"""
import logging
from utils.logger import get_logger
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict

logger = get_logger(__name__)


class RateLimiterService:
    """
    Thread-safe rate limiter for API operations.

    Tracks request timestamps per key (e.g., email address) and enforces
    minimum intervals between requests.
    """

    def __init__(self, default_interval_seconds: int = 300):
        """
        Initialize the rate limiter.

        Args:
            default_interval_seconds: Default minimum interval between requests (default: 300 = 5 minutes)
        """
        self._lock = threading.RLock()
        self._last_request_times: Dict[str, datetime] = {}
        self._default_interval = default_interval_seconds
        self.logger = get_logger(__name__)

        self.logger.info(f"RateLimiterService initialized with {default_interval_seconds}s interval")

    def check_rate_limit(self, key: str, interval_seconds: Optional[int] = None) -> tuple[bool, Optional[float]]:
        """
        Check if a request is allowed based on rate limiting.

        Args:
            key: Unique identifier for the rate limit (e.g., email address)
            interval_seconds: Override for the default interval, or None to use default

        Returns:
            Tuple of (allowed: bool, seconds_until_allowed: Optional[float])
            - If allowed is True, seconds_until_allowed is None
            - If allowed is False, seconds_until_allowed is the remaining cooldown time
        """
        interval = interval_seconds if interval_seconds is not None else self._default_interval

        with self._lock:
            now = datetime.now()
            last_request = self._last_request_times.get(key)

            if last_request is None:
                # First request for this key - always allowed
                self._last_request_times[key] = now
                self.logger.info(f"Rate limit check for '{key}': ALLOWED (first request)")
                return True, None

            # Calculate time since last request
            time_since_last = (now - last_request).total_seconds()

            if time_since_last >= interval:
                # Enough time has passed - allow the request
                self._last_request_times[key] = now
                self.logger.info(f"Rate limit check for '{key}': ALLOWED ({time_since_last:.1f}s since last)")
                return True, None
            else:
                # Too soon - deny the request
                seconds_remaining = interval - time_since_last
                self.logger.warning(
                    f"Rate limit check for '{key}': DENIED "
                    f"({time_since_last:.1f}s since last, {seconds_remaining:.1f}s remaining)"
                )
                return False, seconds_remaining

    def record_request(self, key: str) -> None:
        """
        Manually record a request timestamp.

        Use this when you want to record a request separately from checking the rate limit.

        Args:
            key: Unique identifier for the rate limit
        """
        with self._lock:
            self._last_request_times[key] = datetime.now()
            self.logger.debug(f"Recorded request for '{key}'")

    def reset_key(self, key: str) -> bool:
        """
        Reset the rate limit for a specific key.

        Args:
            key: Unique identifier to reset

        Returns:
            True if key existed and was reset, False if key didn't exist
        """
        with self._lock:
            if key in self._last_request_times:
                del self._last_request_times[key]
                self.logger.info(f"Reset rate limit for '{key}'")
                return True
            return False

    def clear_all(self) -> None:
        """Clear all rate limit data."""
        with self._lock:
            count = len(self._last_request_times)
            self._last_request_times.clear()
            self.logger.info(f"Cleared all rate limit data ({count} keys)")

    def get_time_until_allowed(self, key: str, interval_seconds: Optional[int] = None) -> Optional[float]:
        """
        Get the time remaining until a request would be allowed.

        Args:
            key: Unique identifier for the rate limit
            interval_seconds: Override for the default interval

        Returns:
            Seconds until allowed, or None if request would be allowed now
        """
        interval = interval_seconds if interval_seconds is not None else self._default_interval

        with self._lock:
            last_request = self._last_request_times.get(key)

            if last_request is None:
                return None  # No previous request - allowed now

            time_since_last = (datetime.now() - last_request).total_seconds()

            if time_since_last >= interval:
                return None  # Enough time has passed - allowed now
            else:
                return interval - time_since_last

    def get_stats(self) -> Dict:
        """
        Get statistics about the rate limiter.

        Returns:
            Dictionary with rate limiter statistics
        """
        with self._lock:
            return {
                'total_tracked_keys': len(self._last_request_times),
                'default_interval_seconds': self._default_interval,
                'tracked_keys': list(self._last_request_times.keys())
            }
