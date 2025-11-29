"""
Basic unit tests for force process implementation components
These tests can run without FastAPI dependencies
"""
import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.processing_status_manager import ProcessingStatusManager, ProcessingState
from services.rate_limiter_service import RateLimiterService
from models.force_process_response import ForceProcessResponse, ProcessingInfo


class TestForceProcessModels(unittest.TestCase):
    """Test suite for force process response models"""

    def test_force_process_response_creation(self):
        """Test creating a ForceProcessResponse model"""
        response = ForceProcessResponse(
            status="success",
            message="Test message",
            email_address="test@example.com",
            timestamp="2025-10-07T10:30:00Z"
        )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "Test message")
        self.assertEqual(response.email_address, "test@example.com")
        self.assertEqual(response.timestamp, "2025-10-07T10:30:00Z")
        self.assertIsNone(response.processing_info)

    def test_force_process_response_with_processing_info(self):
        """Test creating a ForceProcessResponse with ProcessingInfo"""
        processing_info = ProcessingInfo(
            hours=24,
            status_url="/api/status",
            websocket_url="/ws/status",
            state="PROCESSING",
            current_step="Processing email 5 of 20"
        )

        response = ForceProcessResponse(
            status="already_processing",
            message="Account is being processed",
            email_address="test@example.com",
            timestamp="2025-10-07T10:30:00Z",
            processing_info=processing_info
        )

        self.assertEqual(response.status, "already_processing")
        self.assertIsNotNone(response.processing_info)
        self.assertEqual(response.processing_info.hours, 24)
        self.assertEqual(response.processing_info.state, "PROCESSING")
        self.assertEqual(response.processing_info.current_step, "Processing email 5 of 20")

    def test_processing_info_optional_fields(self):
        """Test ProcessingInfo with only some fields"""
        info = ProcessingInfo(
            hours=2,
            status_url="/api/status"
        )

        self.assertEqual(info.hours, 2)
        self.assertEqual(info.status_url, "/api/status")
        self.assertIsNone(info.websocket_url)
        self.assertIsNone(info.state)
        self.assertIsNone(info.current_step)


class TestRateLimiterService(unittest.TestCase):
    """Test suite for RateLimiterService"""

    def setUp(self):
        """Set up test fixtures"""
        self.rate_limiter = RateLimiterService(default_interval_seconds=5)

    def test_first_request_allowed(self):
        """Test that first request is always allowed"""
        allowed, remaining = self.rate_limiter.check_rate_limit("test@example.com")
        self.assertTrue(allowed)
        self.assertIsNone(remaining)

    def test_second_request_too_soon_denied(self):
        """Test that second request too soon is denied"""
        # First request
        self.rate_limiter.check_rate_limit("test@example.com")

        # Second request immediately
        allowed, remaining = self.rate_limiter.check_rate_limit("test@example.com")
        self.assertFalse(allowed)
        self.assertIsNotNone(remaining)
        self.assertGreater(remaining, 0)
        self.assertLessEqual(remaining, 5)

    def test_different_keys_independent(self):
        """Test that different keys have independent rate limits"""
        # First key
        allowed1, _ = self.rate_limiter.check_rate_limit("test1@example.com")
        self.assertTrue(allowed1)

        # Different key should be allowed
        allowed2, _ = self.rate_limiter.check_rate_limit("test2@example.com")
        self.assertTrue(allowed2)

    def test_case_sensitive_keys(self):
        """Test that keys are case-sensitive"""
        # First request with lowercase
        self.rate_limiter.check_rate_limit("test@example.com")

        # Different case should be treated as different key
        allowed, _ = self.rate_limiter.check_rate_limit("TEST@EXAMPLE.COM")
        self.assertTrue(allowed)

    def test_reset_key(self):
        """Test resetting a specific key"""
        # Make a request
        self.rate_limiter.check_rate_limit("test@example.com")

        # Reset the key
        result = self.rate_limiter.reset_key("test@example.com")
        self.assertTrue(result)

        # Next request should be allowed
        allowed, _ = self.rate_limiter.check_rate_limit("test@example.com")
        self.assertTrue(allowed)

    def test_reset_nonexistent_key(self):
        """Test resetting a key that doesn't exist"""
        result = self.rate_limiter.reset_key("nonexistent@example.com")
        self.assertFalse(result)

    def test_clear_all(self):
        """Test clearing all rate limit data"""
        # Make multiple requests
        self.rate_limiter.check_rate_limit("test1@example.com")
        self.rate_limiter.check_rate_limit("test2@example.com")

        # Clear all
        self.rate_limiter.clear_all()

        # Both should be allowed again
        allowed1, _ = self.rate_limiter.check_rate_limit("test1@example.com")
        allowed2, _ = self.rate_limiter.check_rate_limit("test2@example.com")
        self.assertTrue(allowed1)
        self.assertTrue(allowed2)

    def test_get_stats(self):
        """Test getting rate limiter statistics"""
        self.rate_limiter.check_rate_limit("test1@example.com")
        self.rate_limiter.check_rate_limit("test2@example.com")

        stats = self.rate_limiter.get_stats()
        self.assertEqual(stats['total_tracked_keys'], 2)
        self.assertEqual(stats['default_interval_seconds'], 5)
        self.assertIn('test1@example.com', stats['tracked_keys'])
        self.assertIn('test2@example.com', stats['tracked_keys'])

    def test_get_time_until_allowed_first_request(self):
        """Test get_time_until_allowed for first request"""
        time_remaining = self.rate_limiter.get_time_until_allowed("test@example.com")
        self.assertIsNone(time_remaining)

    def test_get_time_until_allowed_after_request(self):
        """Test get_time_until_allowed after making a request"""
        self.rate_limiter.check_rate_limit("test@example.com")

        time_remaining = self.rate_limiter.get_time_until_allowed("test@example.com")
        self.assertIsNotNone(time_remaining)
        self.assertGreater(time_remaining, 0)
        self.assertLessEqual(time_remaining, 5)

    def test_record_request_manually(self):
        """Test manually recording a request"""
        self.rate_limiter.record_request("test@example.com")

        # Next check should be denied
        allowed, remaining = self.rate_limiter.check_rate_limit("test@example.com")
        self.assertFalse(allowed)
        self.assertIsNotNone(remaining)

    def test_custom_interval(self):
        """Test rate limiter with custom interval"""
        rate_limiter = RateLimiterService(default_interval_seconds=10)

        # First request allowed
        allowed, _ = rate_limiter.check_rate_limit("test@example.com")
        self.assertTrue(allowed)

        # Second request denied
        allowed, remaining = rate_limiter.check_rate_limit("test@example.com")
        self.assertFalse(allowed)
        self.assertGreater(remaining, 5)  # Should be more than 5 seconds


class TestProcessingStatusManagerNewMethod(unittest.TestCase):
    """Test suite for ProcessingStatusManager.is_processing_account()"""

    def setUp(self):
        """Set up test fixtures"""
        self.manager = ProcessingStatusManager()

    def test_is_processing_account_when_idle(self):
        """Test that is_processing_account returns False when idle"""
        self.assertFalse(self.manager.is_processing_account("test@example.com"))

    def test_is_processing_account_same_account(self):
        """Test that is_processing_account returns True for same account"""
        self.manager.start_processing("test@example.com")
        self.assertTrue(self.manager.is_processing_account("test@example.com"))
        self.manager.complete_processing()

    def test_is_processing_account_different_account(self):
        """Test that is_processing_account returns False for different account"""
        self.manager.start_processing("test@example.com")
        self.assertFalse(self.manager.is_processing_account("other@example.com"))
        self.manager.complete_processing()

    def test_is_processing_account_case_insensitive(self):
        """Test that is_processing_account is case-insensitive"""
        self.manager.start_processing("test@example.com")
        self.assertTrue(self.manager.is_processing_account("TEST@EXAMPLE.COM"))
        self.assertTrue(self.manager.is_processing_account("Test@Example.Com"))
        self.manager.complete_processing()

    def test_is_processing_account_after_completion(self):
        """Test that is_processing_account returns False after completion"""
        self.manager.start_processing("test@example.com")
        self.assertTrue(self.manager.is_processing_account("test@example.com"))

        self.manager.complete_processing()
        self.assertFalse(self.manager.is_processing_account("test@example.com"))

    def test_is_processing_account_thread_safe(self):
        """Test that is_processing_account is thread-safe"""
        import threading

        results = []

        def check_processing():
            result = self.manager.is_processing_account("test@example.com")
            results.append(result)

        # Start processing
        self.manager.start_processing("test@example.com")

        # Create multiple threads checking simultaneously
        threads = [threading.Thread(target=check_processing) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should return True
        self.assertEqual(len(results), 10)
        self.assertTrue(all(results))

        self.manager.complete_processing()


if __name__ == '__main__':
    unittest.main()
