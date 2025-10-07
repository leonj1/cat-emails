"""
Test for DNS resolution fix in LogsCollectorService.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import socket
import requests
from services.logs_collector_service import LogsCollectorService


class TestLogsCollectorDNSFix(unittest.TestCase):
    """Test DNS resolution and retry logic in LogsCollectorService."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_url = "https://logs-collector-production.up.railway.app"
        self.api_token = "test-token"

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    def test_dns_resolution_retry_logic(self, mock_gethostbyname, mock_post):
        """Test that the service retries on DNS failure."""
        # Setup: First call fails with DNS error, second succeeds
        dns_error = requests.exceptions.ConnectionError(
            "HTTPSConnectionPool(host='logs-collector-production.up.railway.app', port=443): "
            "Max retries exceeded with url: /logs (Caused by NameResolutionError"
        )

        # Mock response for successful call
        success_response = Mock()
        success_response.raise_for_status = Mock()

        # First call raises DNS error, second succeeds
        mock_post.side_effect = [dns_error, success_response]

        # Mock DNS resolution
        mock_gethostbyname.return_value = "66.33.22.175"

        # Create service and send log
        service = LogsCollectorService(api_url=self.api_url, api_token=self.api_token)

        result = service.send_log(
            level="ERROR",
            message="Test message",
            context={"trace_id": "test-123"},
            source="test-source"
        )

        # Verify retry was attempted
        self.assertEqual(mock_post.call_count, 2)
        self.assertTrue(result)

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    def test_dns_cache_usage(self, mock_gethostbyname, mock_post):
        """Test that DNS cache is used for subsequent requests."""
        # Setup
        mock_gethostbyname.return_value = "66.33.22.175"

        success_response = Mock()
        success_response.raise_for_status = Mock()
        mock_post.return_value = success_response

        # Create service
        service = LogsCollectorService(api_url=self.api_url, api_token=self.api_token)

        # First call should resolve DNS
        service.send_log("INFO", "First log", context={"trace_id": "test-1"})
        first_dns_calls = mock_gethostbyname.call_count

        # Second call should use cached DNS
        service.send_log("INFO", "Second log", context={"trace_id": "test-2"})
        second_dns_calls = mock_gethostbyname.call_count

        # DNS should only be called once (initial resolution)
        self.assertEqual(first_dns_calls, 1)
        self.assertEqual(second_dns_calls, 1)  # No additional DNS calls

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    def test_exponential_backoff(self, mock_gethostbyname, mock_post):
        """Test exponential backoff between retries."""
        # Setup: All calls fail with timeout
        timeout_error = requests.exceptions.Timeout("Request timeout")
        mock_post.side_effect = [timeout_error, timeout_error, timeout_error]
        mock_gethostbyname.return_value = "66.33.22.175"

        # Create service with mocked time
        with patch('services.logs_collector_service.time.sleep') as mock_sleep:
            service = LogsCollectorService(api_url=self.api_url, api_token=self.api_token)

            result = service.send_log(
                level="INFO",
                message="Test message",
                context={"trace_id": "test-123"}
            )

            # Should have retried max times
            self.assertEqual(mock_post.call_count, 3)
            self.assertFalse(result)

            # Check exponential backoff was applied
            sleep_calls = mock_sleep.call_args_list
            if len(sleep_calls) > 0:
                # First retry: delay * 2^1 = 2 seconds
                self.assertEqual(sleep_calls[0][0][0], 2)
            if len(sleep_calls) > 1:
                # Second retry: delay * 2^2 = 4 seconds
                self.assertEqual(sleep_calls[1][0][0], 4)

    @patch('services.logs_collector_service.socket.gethostbyname')
    def test_dns_resolution_failure_handling(self, mock_gethostbyname):
        """Test graceful handling of DNS resolution failures."""
        # Setup: DNS resolution fails
        mock_gethostbyname.side_effect = socket.gaierror("Failed to resolve")

        # Create service - should not raise exception
        service = LogsCollectorService(api_url=self.api_url, api_token=self.api_token)
        self.assertTrue(service.enabled)

        # DNS resolution failure should be logged but not crash
        with patch('services.logs_collector_service.logger.warning') as mock_warning:
            result = service._resolve_dns(self.api_url)
            self.assertIsNone(result)
            mock_warning.assert_called()

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    def test_fallback_to_ip_on_dns_failure(self, mock_gethostbyname, mock_post):
        """Test fallback to cached IP when DNS fails."""
        # Initial DNS resolution succeeds
        mock_gethostbyname.return_value = "66.33.22.175"

        # Create service (DNS gets cached)
        service = LogsCollectorService(api_url=self.api_url, api_token=self.api_token)

        # Now simulate DNS failure on actual request
        dns_error = requests.exceptions.ConnectionError(
            "Failed to resolve 'logs-collector-production.up.railway.app'"
        )

        success_response = Mock()
        success_response.raise_for_status = Mock()

        # First call with hostname fails, second with IP succeeds
        mock_post.side_effect = [dns_error, success_response]

        result = service.send_log(
            level="ERROR",
            message="Test with DNS failure",
            context={"trace_id": "test-dns-fallback"}
        )

        # Should have tried twice (once with hostname, once with IP)
        self.assertEqual(mock_post.call_count, 2)

        # Check that second call used IP with Host header
        second_call_kwargs = mock_post.call_args_list[1][1]
        headers = second_call_kwargs.get('headers', {})
        self.assertIn('Host', headers)
        self.assertEqual(headers['Host'], 'logs-collector-production.up.railway.app')


if __name__ == '__main__':
    unittest.main()