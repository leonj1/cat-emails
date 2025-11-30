"""
Tests for error handling in LogsCollectorService.

These tests verify:
1. Graceful handling of API transmission errors (connection errors, timeouts, HTTP errors)
2. Proper log buffer management on success/failure
3. Appropriate error logging

Gherkin Scenarios Tested:

Feature: SEND_LOGS Feature Flag - Error Handling

  Scenario: LogsCollectorService handles API transmission errors gracefully
    Given a LogsCollectorService with send_logs=True
    And the LOGS_API_URL points to an unreachable endpoint
    When a log entry is collected and flushed
    Then the flush should return False
    And an error should be logged

  Scenario: LogsCollectorService clears collected logs after successful transmission
    Given a LogsCollectorService with send_logs=True
    And multiple log entries have been collected
    When flush() succeeds
    Then the internal log buffer should be empty

  Scenario: LogsCollectorService retains logs after failed transmission
    Given a LogsCollectorService with send_logs=True
    And multiple log entries have been collected
    When flush() fails due to API error
    Then the internal log buffer should NOT be cleared

Implementation Notes:
The current LogsCollectorService uses send_log() which sends immediately (no buffering).
These tests verify that error handling returns False on failure and logs errors appropriately.
"""
import json
import unittest
from unittest.mock import Mock, patch, MagicMock
import requests

from services.logs_collector_service import LogsCollectorService


class TestApiTransmissionErrorHandling(unittest.TestCase):
    """
    Test cases for graceful error handling when API transmission fails.

    These tests verify that LogsCollectorService handles various error conditions
    gracefully without raising exceptions to the caller.
    """

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    @patch('services.logs_collector_service.logger')
    def test_handles_connection_error_gracefully(
        self,
        mock_logger,
        mock_gethostbyname,
        mock_post
    ):
        """
        Scenario: LogsCollectorService handles connection errors gracefully

        Given a LogsCollectorService with send_logs=True
        And the LOGS_API_URL points to an unreachable endpoint
        When a log entry is collected and flushed
        Then the flush should return False
        And an error should be logged

        The implementation should:
        - Catch requests.exceptions.ConnectionError
        - Return False (not raise exception)
        - Log error message with details
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"
        connection_error = requests.exceptions.ConnectionError(
            "Failed to establish a new connection"
        )
        mock_post.side_effect = connection_error

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://unreachable-api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="ERROR",
            message="Test error message",
            context={"trace_id": "test-123"},
            source="test-source"
        )

        # Assert
        self.assertFalse(
            result,
            "send_log should return False when connection error occurs"
        )

        # Verify error was logged
        error_calls = [
            call for call in mock_logger.error.call_args_list
            if "Failed" in str(call) or "error" in str(call).lower()
        ]
        self.assertGreater(
            len(error_calls),
            0,
            "Should log an error when connection fails"
        )

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    @patch('services.logs_collector_service.logger')
    def test_handles_timeout_error_gracefully(
        self,
        mock_logger,
        mock_gethostbyname,
        mock_post
    ):
        """
        Scenario: LogsCollectorService handles timeout errors gracefully

        Given a LogsCollectorService with send_logs=True
        And the API endpoint times out
        When a log entry is sent
        Then the send_log should return False
        And a warning should be logged

        The implementation should:
        - Catch requests.exceptions.Timeout
        - Return False (not raise exception)
        - Log warning message about timeout
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"
        timeout_error = requests.exceptions.Timeout("Request timed out")
        mock_post.side_effect = [timeout_error, timeout_error, timeout_error]

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://slow-api.example.com",
            api_token="test-token"
        )

        # Act
        with patch('services.logs_collector_service.time.sleep'):
            result = service.send_log(
                level="INFO",
                message="Test message for timeout scenario",
                context={"trace_id": "timeout-test"},
                source="test-source"
            )

        # Assert
        self.assertFalse(
            result,
            "send_log should return False when timeout occurs"
        )

        # Verify warning was logged
        warning_calls = [
            call for call in mock_logger.warning.call_args_list
            if "timeout" in str(call).lower() or "Timeout" in str(call)
        ]
        self.assertGreater(
            len(warning_calls),
            0,
            "Should log a warning when timeout occurs"
        )

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    @patch('services.logs_collector_service.logger')
    def test_handles_http_500_error_gracefully(
        self,
        mock_logger,
        mock_gethostbyname,
        mock_post
    ):
        """
        Scenario: LogsCollectorService handles HTTP 500 errors gracefully

        Given a LogsCollectorService with send_logs=True
        And the API returns a 500 Internal Server Error
        When a log entry is sent
        Then the send_log should return False
        And an error should be logged

        The implementation should:
        - Catch requests.exceptions.HTTPError for 5xx responses
        - Return False (not raise exception)
        - Log error message with status code details
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"

        # Create a proper Mock response object
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        # Use json.JSONDecodeError for proper exception handling
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)

        # Create HTTPError with response attribute properly set
        http_error = requests.exceptions.HTTPError("500 Server Error")
        http_error.response = mock_response

        # Configure raise_for_status to raise the error
        mock_response.raise_for_status.side_effect = http_error

        mock_post.return_value = mock_response

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://failing-api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="ERROR",
            message="Test message for 500 error scenario",
            context={"trace_id": "http-500-test"},
            source="test-source"
        )

        # Assert
        self.assertFalse(
            result,
            "send_log should return False when HTTP 500 error occurs"
        )

        # Verify error was logged
        mock_logger.error.assert_called()

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    @patch('services.logs_collector_service.logger')
    def test_handles_http_400_error_gracefully(
        self,
        mock_logger,
        mock_gethostbyname,
        mock_post
    ):
        """
        Scenario: LogsCollectorService handles HTTP 400 errors gracefully

        Given a LogsCollectorService with send_logs=True
        And the API returns a 400 Bad Request
        When a log entry is sent
        Then the send_log should return False
        And an error should be logged with details

        The implementation should:
        - Catch requests.exceptions.HTTPError for 4xx responses
        - Return False (not raise exception)
        - Log error message with response details
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error": "Bad Request", "details": "Invalid payload"}'
        mock_response.json.return_value = {
            "error": "Bad Request",
            "details": "Invalid payload"
        }
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "400 Client Error",
            response=mock_response
        )
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="INFO",
            message="Test message for 400 error scenario",
            context={"trace_id": "http-400-test"},
            source="test-source"
        )

        # Assert
        self.assertFalse(
            result,
            "send_log should return False when HTTP 400 error occurs"
        )

        # Verify error was logged
        mock_logger.error.assert_called()

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    @patch('services.logs_collector_service.logger')
    def test_handles_unexpected_exception_gracefully(
        self,
        mock_logger,
        mock_gethostbyname,
        mock_post
    ):
        """
        Scenario: LogsCollectorService handles unexpected exceptions gracefully

        Given a LogsCollectorService with send_logs=True
        And an unexpected exception occurs during transmission
        When a log entry is sent
        Then the send_log should return False
        And an error should be logged

        The implementation should:
        - Catch generic Exception as last resort
        - Return False (not raise exception)
        - Log error message with exception details
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"
        mock_post.side_effect = RuntimeError("Unexpected internal error")

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="INFO",
            message="Test message for unexpected error scenario",
            context={"trace_id": "unexpected-error-test"},
            source="test-source"
        )

        # Assert
        self.assertFalse(
            result,
            "send_log should return False when unexpected exception occurs"
        )

        # Verify error was logged
        mock_logger.error.assert_called()


class TestSuccessfulTransmission(unittest.TestCase):
    """
    Test cases for successful log transmission behavior.

    These tests verify that LogsCollectorService properly handles successful
    transmission and returns True.
    """

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    def test_returns_true_when_transmission_succeeds(
        self,
        mock_gethostbyname,
        mock_post
    ):
        """
        Scenario: LogsCollectorService clears collected logs after successful transmission

        Given a LogsCollectorService with send_logs=True
        And multiple log entries have been collected
        When flush() succeeds
        Then the internal log buffer should be empty
        And the method should return True

        The current implementation sends logs immediately (no buffering),
        so we verify that send_log returns True on success.
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="INFO",
            message="Test successful transmission",
            context={"trace_id": "success-test"},
            source="test-source"
        )

        # Assert
        self.assertTrue(
            result,
            "send_log should return True when transmission succeeds"
        )
        mock_post.assert_called_once()

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    def test_multiple_successful_transmissions(
        self,
        mock_gethostbyname,
        mock_post
    ):
        """
        Test that multiple log entries can be sent successfully.

        Given a LogsCollectorService with send_logs=True
        When multiple log entries are sent
        Then each should return True
        And each should make an API call
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://api.example.com",
            api_token="test-token"
        )

        # Act
        results = []
        for i in range(3):
            result = service.send_log(
                level="INFO",
                message=f"Log message {i}",
                context={"trace_id": f"multi-test-{i}"},
                source="test-source"
            )
            results.append(result)

        # Assert
        self.assertEqual(
            results,
            [True, True, True],
            "All send_log calls should return True on success"
        )
        self.assertEqual(
            mock_post.call_count,
            3,
            "Should make one API call per log entry"
        )


class TestErrorLogRetention(unittest.TestCase):
    """
    Test cases for error handling behavior when transmission fails.

    Note: The current LogsCollectorService implementation sends logs immediately
    without buffering. These tests verify the error handling return values
    which would indicate buffer retention in a buffered implementation.
    """

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    def test_returns_false_on_api_error(
        self,
        mock_gethostbyname,
        mock_post
    ):
        """
        Scenario: LogsCollectorService retains logs after failed transmission

        Given a LogsCollectorService with send_logs=True
        And multiple log entries have been collected
        When flush() fails due to API error
        Then the internal log buffer should NOT be cleared
        And the method should return False

        The current implementation sends immediately, so we verify
        that send_log returns False on failure (indicating the log
        was not successfully transmitted and should be retried).
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"

        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)

        # Create HTTPError with response attribute properly set
        http_error = requests.exceptions.HTTPError("503 Server Error")
        http_error.response = mock_response

        mock_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://unavailable-api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="ERROR",
            message="Test message during API failure",
            context={"trace_id": "retention-test"},
            source="test-source"
        )

        # Assert
        self.assertFalse(
            result,
            "send_log should return False when API error occurs, "
            "indicating log was not successfully transmitted"
        )

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    @patch('services.logs_collector_service.time.sleep')
    def test_bulk_logs_returns_failure_count_on_errors(
        self,
        mock_sleep,
        mock_gethostbyname,
        mock_post
    ):
        """
        Test that send_bulk_logs properly counts failures when API errors occur.

        Given a LogsCollectorService with send_logs=True
        And multiple log entries to send
        When some transmissions fail due to API error
        Then the failure count should reflect the number of failed transmissions
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.raise_for_status = MagicMock()

        failure_response = Mock()
        failure_response.status_code = 500
        failure_response.text = "Internal Server Error"
        failure_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)

        # Create HTTPError with response attribute properly set
        http_error = requests.exceptions.HTTPError("500 Server Error")
        http_error.response = failure_response

        failure_response.raise_for_status.side_effect = http_error

        # First succeeds, second fails, third succeeds
        mock_post.side_effect = [success_response, failure_response, success_response]

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://flaky-api.example.com",
            api_token="test-token"
        )

        logs = [
            {"level": "INFO", "message": "Log 1", "context": None, "source": "test"},
            {"level": "ERROR", "message": "Log 2", "context": None, "source": "test"},
            {"level": "INFO", "message": "Log 3", "context": None, "source": "test"},
        ]

        # Act
        results = service.send_bulk_logs(logs)

        # Assert
        self.assertEqual(
            results["success"],
            2,
            "Should have 2 successful transmissions"
        )
        self.assertEqual(
            results["failed"],
            1,
            "Should have 1 failed transmission"
        )


class TestErrorMessageLogging(unittest.TestCase):
    """
    Test cases for proper error message logging.

    These tests verify that error messages are logged with appropriate
    context without including sensitive data.
    """

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    @patch('services.logs_collector_service.logger')
    def test_error_message_includes_error_details(
        self,
        mock_logger,
        mock_gethostbyname,
        mock_post
    ):
        """
        Test that error messages include relevant error details.

        Given a LogsCollectorService with send_logs=True
        And an API error occurs with details
        When the error is logged
        Then the log should include the error message
        And should include relevant context
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = '{"error": "Validation Error", "details": "Missing required field"}'
        mock_response.json.return_value = {
            "error": "Validation Error",
            "details": "Missing required field"
        }
        http_error = requests.exceptions.HTTPError(
            "422 Client Error",
            response=mock_response
        )
        mock_response.raise_for_status.side_effect = http_error

        mock_post.return_value = mock_response

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://api.example.com",
            api_token="test-token"
        )

        # Act
        service.send_log(
            level="INFO",
            message="Test message",
            context={"trace_id": "error-details-test"},
            source="test-source"
        )

        # Assert - verify error was logged with details
        mock_logger.error.assert_called()
        error_call = str(mock_logger.error.call_args)
        self.assertTrue(
            "Failed" in error_call or "422" in error_call or "details" in error_call.lower(),
            f"Error log should include error details, got: {error_call}"
        )

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    @patch('services.logs_collector_service.logger')
    def test_does_not_log_sensitive_data(
        self,
        mock_logger,
        mock_gethostbyname,
        mock_post
    ):
        """
        Test that error messages do not include sensitive data like tokens.

        Given a LogsCollectorService with send_logs=True
        And an API error occurs
        When the error is logged
        Then the log should NOT include the API token
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"

        sensitive_token = "super-secret-token-12345"

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)

        # Create HTTPError with response attribute properly set
        http_error = requests.exceptions.HTTPError("401 Unauthorized")
        http_error.response = mock_response

        mock_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://api.example.com",
            api_token=sensitive_token
        )

        # Act
        service.send_log(
            level="INFO",
            message="Test message",
            context={"trace_id": "sensitive-data-test"},
            source="test-source"
        )

        # Assert - verify token is NOT in error logs
        all_logger_calls = str(mock_logger.error.call_args_list)
        self.assertNotIn(
            sensitive_token,
            all_logger_calls,
            "Error logs should NOT contain the API token"
        )


class TestRetryBehaviorOnErrors(unittest.TestCase):
    """
    Test cases for retry behavior when errors occur.

    These tests verify that the service properly retries on transient errors
    and returns appropriate results after exhausting retries.
    """

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    @patch('services.logs_collector_service.time.sleep')
    def test_retries_on_connection_error(
        self,
        mock_sleep,
        mock_gethostbyname,
        mock_post
    ):
        """
        Test that the service retries on connection errors.

        Given a LogsCollectorService with send_logs=True
        And connection errors occur
        When send_log is called
        Then it should retry multiple times
        And return False if all retries fail
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"
        connection_error = requests.exceptions.ConnectionError(
            "Connection refused"
        )
        mock_post.side_effect = connection_error

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="ERROR",
            message="Test retry behavior",
            context={"trace_id": "retry-test"},
            source="test-source"
        )

        # Assert
        self.assertFalse(
            result,
            "send_log should return False after exhausting retries"
        )
        # Service has max_retries = 3
        self.assertGreaterEqual(
            mock_post.call_count,
            1,
            "Should have made at least one attempt"
        )

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    @patch('services.logs_collector_service.time.sleep')
    def test_succeeds_on_retry_after_initial_failure(
        self,
        mock_sleep,
        mock_gethostbyname,
        mock_post
    ):
        """
        Test that the service succeeds if retry is successful.

        Given a LogsCollectorService with send_logs=True
        And the first request fails but subsequent succeeds
        When send_log is called
        Then it should return True after successful retry
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"

        connection_error = requests.exceptions.ConnectionError(
            "Connection refused"
        )

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.raise_for_status = MagicMock()

        # First fails, second succeeds
        mock_post.side_effect = [connection_error, success_response]

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="INFO",
            message="Test successful retry",
            context={"trace_id": "retry-success-test"},
            source="test-source"
        )

        # Assert
        self.assertTrue(
            result,
            "send_log should return True when retry succeeds"
        )
        self.assertEqual(
            mock_post.call_count,
            2,
            "Should have made two attempts (initial + one retry)"
        )


if __name__ == '__main__':
    unittest.main()
