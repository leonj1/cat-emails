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
        self.assertEqual(payload['level'], "info")  # API expects lowercase
        self.assertEqual(payload['message'], "Test message")
        self.assertEqual(payload['application_name'], "test-source")
        # Context is not a separate field - trace_id should be at top level
        self.assertIn('trace_id', payload)  # Should have auto-generated trace_id

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

        # Verify the payload - note that context data is passed but implementation
        # uses trace_id from context at top level
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertIn('trace_id', payload)  # Should have auto-generated or from context
        self.assertEqual(payload['message'], "Processing run completed: run-123")

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

        # Verify the payload structure - context is passed but trace_id is at top level
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertIn('trace_id', payload)  # Should have auto-generated trace_id
        self.assertEqual(payload['message'], "Email processed: Marketing - deleted")
        self.assertEqual(payload['application_name'], "email-processor")

    @patch('services.logs_collector_service.requests.post')
    def test_send_log_without_trace_id_generates_uuid(self, mock_post):
        """Verify that a UUID trace_id is auto-generated when not provided."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            api_url="https://api.example.com/logs",
            api_token="test-token"
        )

        result = service.send_log(
            level="INFO",
            message="Test log - auto-generated trace_id",
            context={"test": "data"},
            source="test-fix"
        )

        self.assertTrue(result)
        call_args = mock_post.call_args
        payload = call_args[1]['json']

        # Verify trace_id exists and is a valid UUID format
        self.assertIn('trace_id', payload)
        self.assertEqual(len(payload['trace_id']), 36)  # UUID string length with hyphens
        self.assertEqual(payload['trace_id'].count('-'), 4)  # UUIDs have 4 hyphens

    @patch('services.logs_collector_service.requests.post')
    def test_send_log_with_explicit_trace_id(self, mock_post):
        """Verify that an explicit trace_id is preserved."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            api_url="https://api.example.com/logs",
            api_token="test-token"
        )

        expected_trace_id = "explicit-trace-123"
        result = service.send_log(
            level="INFO",
            message="Test log - explicit trace_id",
            context={"trace_id": expected_trace_id, "test": "data"},
            source="test-fix"
        )

        self.assertTrue(result)
        call_args = mock_post.call_args
        payload = call_args[1]['json']

        # Verify the explicit trace_id was used
        self.assertEqual(payload['trace_id'], expected_trace_id)

    @patch('services.logs_collector_service.requests.post')
    def test_send_log_no_context_generates_uuid(self, mock_post):
        """Verify that a UUID trace_id is generated when no context is provided."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            api_url="https://api.example.com/logs",
            api_token="test-token"
        )

        result = service.send_log(
            level="INFO",
            message="Test log - no context",
            context=None,
            source="test-fix"
        )

        self.assertTrue(result)
        call_args = mock_post.call_args
        payload = call_args[1]['json']

        # Verify trace_id exists and is a valid UUID format
        self.assertIn('trace_id', payload)
        self.assertEqual(len(payload['trace_id']), 36)
        self.assertEqual(payload['trace_id'].count('-'), 4)

    @patch('services.logs_collector_service.requests.post')
    @patch('builtins.print')
    def test_send_log_http_error_with_details(self, mock_print, mock_post):
        """Test that error details from API are properly displayed"""
        import requests

        # Create a mock response with error details
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'details': 'Invalid trace_id format: must be a valid UUID',
            'error': 'Bad Request'
        }
        mock_response.text = '{"details":"Invalid trace_id format: must be a valid UUID","error":"Bad Request"}'

        # Create HTTP error with the response
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = http_error

        service = LogsCollectorService(
            api_url="https://api.example.com/logs",
            api_token="test-token"
        )

        result = service.send_log(
            level="INFO",
            message="Test message",
            context={"trace_id": "invalid-trace-id"},
            source="test"
        )

        self.assertFalse(result)

        # Verify that error details were printed to stdout
        mock_print.assert_called_with("ERROR: Logs collector API error details: Invalid trace_id format: must be a valid UUID")

    @patch('services.logs_collector_service.requests.post')
    @patch('builtins.print')
    def test_send_log_http_error_without_details(self, mock_print, mock_post):
        """Test error handling when API doesn't return details field"""
        import requests

        # Create a mock response without details field
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            'error': 'Internal Server Error'
        }
        mock_response.text = '{"error":"Internal Server Error"}'

        # Create HTTP error with the response
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = http_error

        service = LogsCollectorService(
            api_url="https://api.example.com/logs",
            api_token="test-token"
        )

        result = service.send_log("ERROR", "Test error message")

        self.assertFalse(result)

        # Verify that details were NOT printed since they don't exist
        mock_print.assert_not_called()


if __name__ == '__main__':
    unittest.main()
