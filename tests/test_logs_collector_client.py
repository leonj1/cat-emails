"""
Unit tests for LogsCollectorClient
"""
import unittest
from unittest.mock import patch, MagicMock
import json

from clients.logs_collector_client import RemoteLogsCollectorClient, LogEntry


class TestRemoteLogsCollectorClient(unittest.TestCase):
    """Test cases for RemoteLogsCollectorClient"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = RemoteLogsCollectorClient(
            logs_collector_url="https://logs-collector-api.example.com",
            application_name="test-app",
            logs_collector_token="test-token"
        )

    @patch('clients.logs_collector_client.requests.post')
    @patch('builtins.print')
    def test_send_with_http_error_and_details(self, mock_print, mock_post):
        """Test that error details from API are properly displayed"""
        import requests

        # Create a mock response with error details
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'details': 'Invalid authentication token: token expired',
            'error': 'Unauthorized'
        }
        mock_response.text = json.dumps({
            'details': 'Invalid authentication token: token expired',
            'error': 'Unauthorized'
        })

        # Create HTTP error with the response
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = http_error

        log_entry = LogEntry(
            application_name="test-app",
            message="Test log message",
            level="error"
        )

        result = self.client.send(log_entry)

        self.assertFalse(result)

        # Verify that error details were printed to stdout
        mock_print.assert_any_call("ERROR: Logs collector API error details: Invalid authentication token: token expired")

    @patch('clients.logs_collector_client.requests.post')
    @patch('builtins.print')
    def test_send_with_http_error_message_field(self, mock_print, mock_post):
        """Test error handling with 'message' field instead of 'details'"""
        import requests

        # Create a mock response with message field
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            'message': 'Validation error: missing required field',
            'error': 'Unprocessable Entity'
        }
        mock_response.text = json.dumps({
            'message': 'Validation error: missing required field',
            'error': 'Unprocessable Entity'
        })

        # Create HTTP error with the response
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = http_error

        log_entry = LogEntry(
            application_name="test-app",
            message="Test log message",
            level="info"
        )

        result = self.client.send(log_entry)

        self.assertFalse(result)

        # Should not print ERROR line for 'message' field, only in error_msg
        print_calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(any("Message: Validation error" in call for call in print_calls))

    @patch('clients.logs_collector_client.requests.post')
    @patch('builtins.print')
    def test_send_with_http_error_no_json_response(self, mock_print, mock_post):
        """Test error handling when response is not JSON"""
        import requests

        # Create a mock response with non-JSON content
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        mock_response.text = "<html><body>Internal Server Error</body></html>"

        # Create HTTP error with the response
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = http_error

        log_entry = LogEntry(
            application_name="test-app",
            message="Test log message",
            level="warning"
        )

        result = self.client.send(log_entry)

        self.assertFalse(result)

        # Should include response text in error message
        print_calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(any("Response:" in call and "Internal Server Error" in call for call in print_calls))

    @patch('clients.logs_collector_client.requests.post')
    def test_send_success(self, mock_post):
        """Test successful log sending"""
        # Create a mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        log_entry = LogEntry(
            application_name="test-app",
            message="Test log message",
            level="info",
            trace_id="test-trace-123"
        )

        result = self.client.send(log_entry)

        self.assertTrue(result)
        mock_post.assert_called_once()

        # Verify the request was made correctly
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://logs-collector-api.example.com/logs")

        # Verify headers
        headers = call_args[1]['headers']
        self.assertEqual(headers['Authorization'], "Bearer test-token")
        self.assertEqual(headers['Content-Type'], "application/json")

        # Verify payload
        payload = call_args[1]['json']
        self.assertEqual(payload['application_name'], "test-app")
        self.assertEqual(payload['message'], "Test log message")
        self.assertEqual(payload['level'], "info")
        self.assertEqual(payload['trace_id'], "test-trace-123")

    @patch('clients.logs_collector_client.requests.post')
    @patch('builtins.print')
    def test_send_network_error(self, mock_print, mock_post):
        """Test handling of network errors"""
        import requests

        # Simulate a connection error
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        log_entry = LogEntry(
            application_name="test-app",
            message="Test log message",
            level="error"
        )

        result = self.client.send(log_entry)

        self.assertFalse(result)

        # Verify error was printed
        mock_print.assert_called_with("Failed to send log to collector: Connection refused")

    @patch('clients.logs_collector_client.requests.post')
    @patch('builtins.print')
    def test_send_timeout_error(self, mock_print, mock_post):
        """Test handling of timeout errors"""
        import requests

        # Simulate a timeout error
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        log_entry = LogEntry(
            application_name="test-app",
            message="Test log message",
            level="debug"
        )

        result = self.client.send(log_entry)

        self.assertFalse(result)

        # Verify error was printed
        mock_print.assert_called_with("Failed to send log to collector: Request timed out")


if __name__ == '__main__':
    unittest.main()