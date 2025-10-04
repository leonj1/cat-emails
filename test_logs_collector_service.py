"""
Unit tests for LogsCollectorService
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import json

from services.logs_collector_service import LogsCollectorService


class TestLogsCollectorService(unittest.TestCase):
    """Test cases for LogsCollectorService"""

    def setUp(self):
        """Set up test fixtures"""
        # Clear environment variables
        if 'LOGS_COLLECTOR_API' in os.environ:
            del os.environ['LOGS_COLLECTOR_API']
        if 'LOGS_COLLECTOR_API_TOKEN' in os.environ:
            del os.environ['LOGS_COLLECTOR_API_TOKEN']

    def test_initialization_without_config(self):
        """Test service initialization without configuration"""
        service = LogsCollectorService()
        self.assertFalse(service.enabled)
        self.assertIsNone(service.api_url)

    def test_initialization_with_config(self):
        """Test service initialization with configuration"""
        service = LogsCollectorService(
            api_url="https://api.example.com/logs",
            api_token="test-token"
        )
        self.assertTrue(service.enabled)
        self.assertEqual(service.api_url, "https://api.example.com/logs")
        self.assertEqual(service.api_token, "test-token")

    def test_initialization_with_env_vars(self):
        """Test service initialization with environment variables"""
        os.environ['LOGS_COLLECTOR_API'] = "https://api.example.com/logs"
        os.environ['LOGS_COLLECTOR_API_TOKEN'] = "env-token"

        service = LogsCollectorService()
        self.assertTrue(service.enabled)
        self.assertEqual(service.api_url, "https://api.example.com/logs")
        self.assertEqual(service.api_token, "env-token")

    def test_send_log_when_disabled(self):
        """Test that send_log returns False when service is disabled"""
        service = LogsCollectorService()
        result = service.send_log("INFO", "test message")
        self.assertFalse(result)

    @patch('services.logs_collector_service.requests.post')
    def test_send_log_success(self, mock_post):
        """Test successful log sending"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            api_url="https://api.example.com/logs",
            api_token="test-token"
        )

        result = service.send_log(
            "INFO",
            "Test message",
            {"key": "value"},
            "test-source"
        )

        self.assertTrue(result)
        mock_post.assert_called_once()

        # Verify the request payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertEqual(payload['level'], "INFO")
        self.assertEqual(payload['message'], "Test message")
        self.assertEqual(payload['source'], "test-source")
        self.assertEqual(payload['context'], {"key": "value"})

        # Verify headers
        headers = call_args[1]['headers']
        self.assertEqual(headers['Authorization'], "Bearer test-token")

    @patch('services.logs_collector_service.requests.post')
    def test_send_log_network_error(self, mock_post):
        """Test log sending with network error"""
        mock_post.side_effect = Exception("Network error")

        service = LogsCollectorService(
            api_url="https://api.example.com/logs"
        )

        result = service.send_log("ERROR", "Test error message")
        self.assertFalse(result)

    @patch('services.logs_collector_service.requests.post')
    def test_send_log_timeout(self, mock_post):
        """Test log sending with timeout"""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        service = LogsCollectorService(
            api_url="https://api.example.com/logs"
        )

        result = service.send_log("INFO", "Test message")
        self.assertFalse(result)

    @patch('services.logs_collector_service.requests.post')
    def test_send_bulk_logs(self, mock_post):
        """Test bulk log sending"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            api_url="https://api.example.com/logs"
        )

        logs = [
            {"level": "INFO", "message": "Log 1"},
            {"level": "ERROR", "message": "Log 2", "context": {"key": "value"}},
            {"level": "WARNING", "message": "Log 3", "source": "custom-source"}
        ]

        result = service.send_bulk_logs(logs)
        self.assertEqual(result['success'], 3)
        self.assertEqual(result['failed'], 0)
        self.assertEqual(mock_post.call_count, 3)

    @patch('services.logs_collector_service.requests.post')
    def test_send_processing_run_log(self, mock_post):
        """Test sending processing run log"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            api_url="https://api.example.com/logs"
        )

        result = service.send_processing_run_log(
            run_id="run-123",
            status="completed",
            metrics={"processed": 10, "deleted": 5}
        )

        self.assertTrue(result)

        # Verify the context includes run details
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertEqual(payload['context']['run_id'], "run-123")
        self.assertEqual(payload['context']['status'], "completed")
        self.assertEqual(payload['context']['metrics']['processed'], 10)

    @patch('services.logs_collector_service.requests.post')
    def test_send_email_processing_log(self, mock_post):
        """Test sending email processing log"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            api_url="https://api.example.com/logs"
        )

        result = service.send_email_processing_log(
            message_id="msg-123",
            category="Marketing",
            action="deleted",
            sender="test@example.com",
            processing_time=1.5
        )

        self.assertTrue(result)

        # Verify the context includes email details
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertEqual(payload['context']['message_id'], "msg-123")
        self.assertEqual(payload['context']['category'], "Marketing")
        self.assertEqual(payload['context']['action'], "deleted")
        self.assertEqual(payload['context']['sender'], "test@example.com")
        self.assertEqual(payload['context']['processing_time_seconds'], 1.5)


if __name__ == '__main__':
    unittest.main()
