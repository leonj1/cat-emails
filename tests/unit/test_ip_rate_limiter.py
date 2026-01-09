"""
Unit tests for IP Rate Limiter.

Tests derived from Gherkin scenarios for OAuth State Init Endpoint feature.
These tests define the expected behavior for IP-based rate limiting.

Scenarios covered:
- Rate limiting rejects excessive requests from same IP
- Rate limit resets after time window
- First request is always allowed
- Different IPs have independent rate limits
"""

import pytest
from typing import Protocol, Tuple, Optional
from datetime import datetime, timedelta
from unittest.mock import Mock, patch


class IPRateLimiterProtocol(Protocol):
    """Protocol for IP-based rate limiting.

    The implementation should:
    - Track requests per IP address
    - Limit to 10 requests per minute per IP
    - Use sliding window algorithm
    - Return whether request is allowed and time until reset
    """

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
        ...

    def record_request(self, ip_address: str) -> None:
        """
        Record a request from the given IP.

        Args:
            ip_address: The client IP address
        """
        ...


class TestIPRateLimiterBasicBehavior:
    """Tests for basic rate limiter behavior."""

    def test_first_request_is_allowed(self):
        """First request from any IP should always be allowed."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ip_address = "192.168.1.100"

        # Act
        allowed, wait_time = limiter.check_rate_limit(ip_address)

        # Assert
        assert allowed is True, "First request should be allowed"
        assert wait_time is None, "No wait time for allowed requests"

    def test_ten_requests_within_window_are_allowed(self):
        """First 10 requests within the time window should be allowed."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ip_address = "192.168.1.100"

        # Act & Assert - 10 requests should all be allowed
        for i in range(10):
            allowed, wait_time = limiter.check_rate_limit(ip_address)
            assert allowed is True, f"Request {i+1} should be allowed"
            assert wait_time is None, f"No wait time for request {i+1}"
            limiter.record_request(ip_address)

    def test_eleventh_request_is_rejected(self):
        """
        Scenario: Rate limiting rejects excessive requests from same IP

        Given 10 state token registrations have been made from the same IP in the last minute
        When the frontend requests state token registration
        Then the request should be rejected with rate limit exceeded
        """
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ip_address = "192.168.1.100"

        # Make 10 requests
        for _ in range(10):
            limiter.check_rate_limit(ip_address)
            limiter.record_request(ip_address)

        # Act - 11th request
        allowed, wait_time = limiter.check_rate_limit(ip_address)

        # Assert
        assert allowed is False, "11th request should be rejected"
        assert wait_time is not None, "Should return wait time"
        assert wait_time > 0, "Wait time should be positive"

    def test_rate_limit_applies_per_ip(self):
        """Different IPs should have independent rate limits."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ip1 = "192.168.1.100"
        ip2 = "192.168.1.101"

        # Max out rate limit for IP1
        for _ in range(10):
            limiter.check_rate_limit(ip1)
            limiter.record_request(ip1)

        # Act - request from IP2 (should be allowed)
        allowed, wait_time = limiter.check_rate_limit(ip2)

        # Assert
        assert allowed is True, "Request from different IP should be allowed"
        assert wait_time is None


class TestIPRateLimiterTimeWindow:
    """Tests for rate limiter time window behavior."""

    def test_rate_limit_resets_after_window(self):
        """
        Scenario: Rate limit resets after time window

        Given 10 state token registrations were made from the same IP
        And the rate limit time window has elapsed
        When the frontend requests state token registration with a valid token
        Then the request should be allowed
        """
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ip_address = "192.168.1.100"

        # Max out rate limit
        for _ in range(10):
            limiter.check_rate_limit(ip_address)
            limiter.record_request(ip_address)

        # Verify rate limit is exceeded
        allowed, _ = limiter.check_rate_limit(ip_address)
        assert allowed is False, "Should be rate limited initially"

        # Simulate time passing (mock datetime)
        with patch('services.ip_rate_limiter.datetime') as mock_datetime:
            # Set current time to 61 seconds in the future
            future_time = datetime.now() + timedelta(seconds=61)
            mock_datetime.now.return_value = future_time

            # Act - request after window elapsed
            allowed, wait_time = limiter.check_rate_limit(ip_address)

            # Assert
            assert allowed is True, "Request should be allowed after window reset"
            assert wait_time is None

    def test_sliding_window_allows_new_requests_as_old_expire(self):
        """Sliding window should allow new requests as old ones expire."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ip_address = "192.168.1.100"

        # Initial time
        base_time = datetime.now()

        with patch('services.ip_rate_limiter.datetime') as mock_datetime:
            mock_datetime.now.return_value = base_time

            # Make 10 requests at t=0
            for _ in range(10):
                limiter.check_rate_limit(ip_address)
                limiter.record_request(ip_address)

            # Verify rate limited
            allowed, _ = limiter.check_rate_limit(ip_address)
            assert allowed is False

            # Move time forward 61 seconds (first requests should expire)
            mock_datetime.now.return_value = base_time + timedelta(seconds=61)

            # Act - should now be allowed
            allowed, wait_time = limiter.check_rate_limit(ip_address)

            # Assert
            assert allowed is True, "Should be allowed after old requests expire"

    def test_partial_window_expiry(self):
        """After partial time elapsed, some requests should still count."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ip_address = "192.168.1.100"
        base_time = datetime.now()

        with patch('services.ip_rate_limiter.datetime') as mock_datetime:
            # Make 5 requests at t=0
            mock_datetime.now.return_value = base_time
            for _ in range(5):
                limiter.check_rate_limit(ip_address)
                limiter.record_request(ip_address)

            # Make 5 requests at t=30s
            mock_datetime.now.return_value = base_time + timedelta(seconds=30)
            for _ in range(5):
                limiter.check_rate_limit(ip_address)
                limiter.record_request(ip_address)

            # 11th request at t=30s should be blocked
            allowed, _ = limiter.check_rate_limit(ip_address)
            assert allowed is False

            # Move to t=65s (first 5 requests should expire, leaving 5)
            mock_datetime.now.return_value = base_time + timedelta(seconds=65)

            # Should now have room for 5 more requests
            for i in range(5):
                allowed, _ = limiter.check_rate_limit(ip_address)
                assert allowed is True, f"Request {i+1} after partial expiry should be allowed"
                limiter.record_request(ip_address)

            # 6th request should be blocked
            allowed, _ = limiter.check_rate_limit(ip_address)
            assert allowed is False


class TestIPRateLimiterConfiguration:
    """Tests for rate limiter configuration."""

    def test_rate_limit_is_10_per_minute(self):
        """Rate limit should be exactly 10 requests per minute per IP."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()

        # Assert configuration
        assert hasattr(limiter, 'max_requests') or hasattr(limiter, 'MAX_REQUESTS'), \
            "Limiter should have max_requests attribute"
        assert hasattr(limiter, 'window_seconds') or hasattr(limiter, 'WINDOW_SECONDS'), \
            "Limiter should have window_seconds attribute"

        # Get actual values
        max_requests = getattr(limiter, 'max_requests', getattr(limiter, 'MAX_REQUESTS', None))
        window_seconds = getattr(limiter, 'window_seconds', getattr(limiter, 'WINDOW_SECONDS', None))

        assert max_requests == 10, f"Max requests should be 10, got {max_requests}"
        assert window_seconds == 60, f"Window should be 60 seconds, got {window_seconds}"

    def test_custom_configuration(self):
        """Rate limiter should support custom configuration."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter(max_requests=5, window_seconds=30)

        # Make 5 requests
        ip_address = "192.168.1.100"
        for _ in range(5):
            limiter.check_rate_limit(ip_address)
            limiter.record_request(ip_address)

        # Act - 6th request
        allowed, _ = limiter.check_rate_limit(ip_address)

        # Assert
        assert allowed is False, "6th request should be blocked with max_requests=5"


class TestIPRateLimiterWaitTime:
    """Tests for rate limiter wait time calculation."""

    def test_wait_time_returned_when_rate_limited(self):
        """When rate limited, should return time until next request is allowed."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ip_address = "192.168.1.100"

        # Max out rate limit
        for _ in range(10):
            limiter.check_rate_limit(ip_address)
            limiter.record_request(ip_address)

        # Act
        allowed, wait_time = limiter.check_rate_limit(ip_address)

        # Assert
        assert allowed is False
        assert wait_time is not None
        assert isinstance(wait_time, (int, float))
        assert 0 < wait_time <= 60, f"Wait time should be between 0 and 60 seconds, got {wait_time}"

    def test_wait_time_decreases_over_time(self):
        """Wait time should decrease as time passes."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ip_address = "192.168.1.100"
        base_time = datetime.now()

        with patch('services.ip_rate_limiter.datetime') as mock_datetime:
            mock_datetime.now.return_value = base_time

            # Max out rate limit
            for _ in range(10):
                limiter.check_rate_limit(ip_address)
                limiter.record_request(ip_address)

            # Get initial wait time
            _, wait_time_1 = limiter.check_rate_limit(ip_address)

            # Move time forward 30 seconds
            mock_datetime.now.return_value = base_time + timedelta(seconds=30)

            # Get updated wait time
            _, wait_time_2 = limiter.check_rate_limit(ip_address)

            # Assert
            assert wait_time_2 < wait_time_1, "Wait time should decrease over time"


class TestIPRateLimiterReset:
    """Tests for rate limiter reset functionality."""

    def test_reset_clears_rate_limit_for_ip(self):
        """Resetting should clear rate limit for specific IP."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ip_address = "192.168.1.100"

        # Max out rate limit
        for _ in range(10):
            limiter.check_rate_limit(ip_address)
            limiter.record_request(ip_address)

        # Verify rate limited
        allowed, _ = limiter.check_rate_limit(ip_address)
        assert allowed is False

        # Act - reset
        limiter.reset(ip_address)

        # Assert - should be allowed now
        allowed, wait_time = limiter.check_rate_limit(ip_address)
        assert allowed is True, "Request should be allowed after reset"
        assert wait_time is None

    def test_reset_all_clears_all_rate_limits(self):
        """Reset all should clear rate limits for all IPs."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ips = ["192.168.1.100", "192.168.1.101", "192.168.1.102"]

        # Max out rate limit for all IPs
        for ip in ips:
            for _ in range(10):
                limiter.check_rate_limit(ip)
                limiter.record_request(ip)

        # Verify all rate limited
        for ip in ips:
            allowed, _ = limiter.check_rate_limit(ip)
            assert allowed is False

        # Act - reset all
        limiter.reset_all()

        # Assert - all should be allowed now
        for ip in ips:
            allowed, wait_time = limiter.check_rate_limit(ip)
            assert allowed is True, f"Request from {ip} should be allowed after reset_all"


class TestIPRateLimiterEdgeCases:
    """Edge case tests for rate limiter."""

    def test_empty_ip_address(self):
        """Empty IP address should be handled gracefully."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()

        # Act & Assert - should not raise exception
        allowed, _ = limiter.check_rate_limit("")
        assert isinstance(allowed, bool)

    def test_ipv6_address(self):
        """IPv6 addresses should be supported."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ip_address = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"

        # Act
        allowed, wait_time = limiter.check_rate_limit(ip_address)

        # Assert
        assert allowed is True
        assert wait_time is None

    def test_compressed_ipv6_address(self):
        """Compressed IPv6 addresses should be supported."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()
        ip_address = "::1"  # localhost in IPv6

        # Act
        allowed, wait_time = limiter.check_rate_limit(ip_address)

        # Assert
        assert allowed is True
        assert wait_time is None

    def test_high_volume_ips(self):
        """Rate limiter should handle many different IPs efficiently."""
        from services.ip_rate_limiter import IPRateLimiter

        # Arrange
        limiter = IPRateLimiter()

        # Act - create rate limit entries for 1000 IPs
        for i in range(1000):
            ip = f"192.168.{i // 256}.{i % 256}"
            limiter.check_rate_limit(ip)
            limiter.record_request(ip)

        # Assert - should still work correctly
        test_ip = "192.168.0.1"
        allowed, _ = limiter.check_rate_limit(test_ip)
        # Second request should still be allowed (only made 1 request before)
        assert allowed is True


class TestIPRateLimiterThreadSafety:
    """Tests for rate limiter thread safety."""

    def test_concurrent_requests_same_ip(self):
        """Rate limiter should be thread-safe for concurrent requests."""
        from services.ip_rate_limiter import IPRateLimiter
        import threading
        import time

        # Arrange
        limiter = IPRateLimiter()
        ip_address = "192.168.1.100"
        results = []
        errors = []

        def make_request():
            try:
                allowed, wait_time = limiter.check_rate_limit(ip_address)
                if allowed:
                    limiter.record_request(ip_address)
                results.append(allowed)
            except Exception as e:
                errors.append(str(e))

        # Act - create 20 concurrent threads
        threads = [threading.Thread(target=make_request) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        assert len(errors) == 0, f"Should not have errors: {errors}"
        assert len(results) == 20, "Should have 20 results"
        # Exactly 10 should be allowed (first 10 requests)
        allowed_count = sum(1 for r in results if r)
        assert allowed_count == 10, f"Exactly 10 requests should be allowed, got {allowed_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
