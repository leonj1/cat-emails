"""
Tests for log sending behavior controlled by send_logs flag.

These tests verify that LogsCollectorService properly controls log transmission/suppression
based on the send_logs flag and API configuration.

The implementation should:
- Check send_logs flag FIRST before any API operations in send_log() method
- If send_logs=False, log debug message and return False without making API calls
- If send_logs=True but no API URL, log debug message and return False
- Only transmit logs if send_logs=True AND api_url is configured

Debug logging messages expected:
- "Log sending disabled by feature flag" when send_logs=False
- "Log sending disabled: no API URL configured" when no URL
"""
import unittest
from unittest.mock import Mock, patch, MagicMock

from services.logs_collector_service import LogsCollectorService


class TestLogSendingWithSendLogsEnabled(unittest.TestCase):
    """Test cases for log transmission when send_logs=True and API is configured."""

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    def test_logs_are_transmitted_when_send_logs_true_and_api_configured(
        self,
        mock_gethostbyname,
        mock_post
    ):
        """
        Scenario: Logs are transmitted when send_logs is True and API is configured

        Given a LogsCollectorService with send_logs=True
        And the LOGS_API_URL is configured
        And the LOGS_API_TOKEN is configured
        When a log entry is collected and flushed
        Then the log should be transmitted to the remote API

        The implementation should:
        - Check send_logs flag first
        - Proceed with API transmission since send_logs=True and api_url is set
        - Make HTTP POST request to the API endpoint
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://logs-api.example.com",
            api_token="test-token-123"
        )

        # Act
        result = service.send_log(
            level="INFO",
            message="Test log message",
            context={"trace_id": "test-trace-123"},
            source="test-source"
        )

        # Assert
        self.assertTrue(
            result,
            "send_log should return True when send_logs=True and API is configured"
        )
        mock_post.assert_called_once()

        # Verify the API endpoint was called correctly
        call_args = mock_post.call_args
        endpoint = call_args[0][0]
        self.assertEqual(
            endpoint,
            "https://logs-api.example.com/logs",
            "Should call the /logs endpoint"
        )

        # Verify authorization header was set
        headers = call_args[1]['headers']
        self.assertEqual(
            headers['Authorization'],
            "Bearer test-token-123",
            "Should include Bearer token in Authorization header"
        )

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    def test_flush_returns_true_when_sending_succeeds(
        self,
        mock_gethostbyname,
        mock_post
    ):
        """
        Scenario: Flush returns True when sending succeeds

        Given a LogsCollectorService with send_logs=True
        And the API is configured and accessible
        And there are collected logs
        When flush() is called (via send_log)
        Then the return value should be True
        And the collected logs should be cleared

        The implementation should:
        - Return True from send_log when transmission succeeds
        - Successfully transmit the log to the API
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="ERROR",
            message="Error occurred during processing",
            context=None,
            source="email-processor"
        )

        # Assert
        self.assertTrue(
            result,
            "send_log should return True when transmission succeeds"
        )
        self.assertEqual(
            mock_post.call_count,
            1,
            "Should make exactly one API call"
        )


class TestLogSuppressionWithSendLogsFalse(unittest.TestCase):
    """Test cases for log suppression when send_logs=False."""

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.logger')
    def test_logs_not_transmitted_when_send_logs_false(
        self,
        mock_logger,
        mock_post
    ):
        """
        Scenario: Logs are suppressed when send_logs is False

        Given a LogsCollectorService with send_logs=False
        And the LOGS_API_URL is configured
        When a log entry is collected and flushed
        Then the log should NOT be transmitted to the remote API
        And a debug message should indicate log sending is disabled

        The implementation should:
        - Check send_logs flag FIRST in send_log() method
        - Return False immediately without making any API calls
        - Log debug message: "Log sending disabled by feature flag"
        """
        # Arrange
        service = LogsCollectorService(
            send_logs=False,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="INFO",
            message="This log should not be transmitted",
            context={"trace_id": "test-123"},
            source="test-source"
        )

        # Assert
        self.assertFalse(
            result,
            "send_log should return False when send_logs=False"
        )
        mock_post.assert_not_called()

        # Verify debug message was logged
        debug_calls = [
            call for call in mock_logger.debug.call_args_list
            if "disabled" in str(call).lower() and "flag" in str(call).lower()
        ]
        self.assertGreater(
            len(debug_calls),
            0,
            "Should log debug message indicating log sending is disabled by feature flag"
        )

    @patch('services.logs_collector_service.requests.post')
    def test_flush_returns_false_when_send_logs_disabled(self, mock_post):
        """
        Scenario: Flush returns False when sending is disabled

        Given a LogsCollectorService with send_logs=False
        When flush() is called (via send_log)
        Then the return value should be False

        The implementation should:
        - Return False from send_log when send_logs=False
        - Never call the API
        """
        # Arrange
        service = LogsCollectorService(
            send_logs=False,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="WARNING",
            message="Warning message",
            context=None,
            source="test-service"
        )

        # Assert
        self.assertFalse(
            result,
            "send_log should return False when send_logs=False"
        )
        mock_post.assert_not_called()

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.logger')
    def test_debug_message_logged_when_send_logs_false(
        self,
        mock_logger,
        mock_post
    ):
        """
        Test that a debug message is logged when send_logs=False.

        The implementation should log:
        "Log sending disabled by feature flag"
        """
        # Arrange
        service = LogsCollectorService(
            send_logs=False,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )

        # Act
        service.send_log(
            level="INFO",
            message="Test message",
            context=None,
            source="test"
        )

        # Assert - verify debug was called with message about feature flag
        mock_logger.debug.assert_any_call("Log sending disabled by feature flag")


class TestLogSuppressionWithNoApiUrl(unittest.TestCase):
    """Test cases for log suppression when API URL is not configured."""

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.logger')
    def test_logs_not_transmitted_when_api_url_not_configured(
        self,
        mock_logger,
        mock_post
    ):
        """
        Scenario: Logs are suppressed when API URL is not configured

        Given a LogsCollectorService with send_logs=True
        And the LOGS_API_URL is NOT configured
        When a log entry is collected and flushed
        Then the log should NOT be transmitted
        And a debug message should indicate no API URL is configured

        The implementation should:
        - Check if api_url is configured
        - Return False if no api_url
        - Log debug message: "Log sending disabled: no API URL configured"
        """
        # Arrange
        service = LogsCollectorService(
            send_logs=True,
            api_url=None,
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="ERROR",
            message="Error that will not be sent",
            context={"error_code": "E001"},
            source="test-source"
        )

        # Assert
        self.assertFalse(
            result,
            "send_log should return False when API URL is not configured"
        )
        mock_post.assert_not_called()

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.logger')
    def test_debug_message_logged_when_api_url_missing(
        self,
        mock_logger,
        mock_post
    ):
        """
        Test that a debug message is logged when api_url is not configured.

        The implementation should log:
        "Log sending disabled: no API URL configured"
        """
        # Arrange
        service = LogsCollectorService(
            send_logs=True,
            api_url=None,
            api_token="test-token"
        )

        # Act
        service.send_log(
            level="INFO",
            message="Test message",
            context=None,
            source="test"
        )

        # Assert - verify debug was called with message about no API URL
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        matching_calls = [
            call for call in debug_calls
            if "no API URL" in call or "API URL" in call
        ]
        self.assertGreater(
            len(matching_calls),
            0,
            "Should log debug message indicating no API URL is configured"
        )


class TestSendLogsFlagPriority(unittest.TestCase):
    """Test cases to verify send_logs flag is checked FIRST before other conditions."""

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.logger')
    def test_send_logs_flag_checked_before_api_operations(
        self,
        mock_logger,
        mock_post
    ):
        """
        Test that send_logs flag is checked FIRST before any API operations.

        The implementation should:
        - Check self._send_logs FIRST in send_log() method
        - Return immediately if send_logs=False without checking api_url
        - Never attempt DNS resolution or API calls when send_logs=False

        This ensures the feature flag can completely disable log sending
        without any network operations.
        """
        # Arrange
        service = LogsCollectorService(
            send_logs=False,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="INFO",
            message="Test message",
            context=None,
            source="test"
        )

        # Assert
        self.assertFalse(
            result,
            "send_log should return False when send_logs=False"
        )
        mock_post.assert_not_called()

        # Verify the feature flag debug message was logged (indicating
        # the flag was checked first)
        mock_logger.debug.assert_any_call("Log sending disabled by feature flag")

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    def test_api_operations_only_when_send_logs_true_and_api_configured(
        self,
        mock_gethostbyname,
        mock_post
    ):
        """
        Test that API operations only happen when both conditions are met:
        - send_logs=True
        - api_url is configured

        The implementation should only make network calls when both
        conditions are satisfied.
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_log(
            level="INFO",
            message="Test message",
            context=None,
            source="test"
        )

        # Assert
        self.assertTrue(
            result,
            "send_log should return True when send_logs=True and api_url is configured"
        )
        mock_post.assert_called_once()


class TestBulkLogSendingBehavior(unittest.TestCase):
    """Test cases for bulk log sending behavior with send_logs flag."""

    @patch('services.logs_collector_service.requests.post')
    def test_bulk_logs_not_sent_when_send_logs_false(self, mock_post):
        """
        Test that send_bulk_logs does not transmit when send_logs=False.

        When send_logs=False, even bulk log operations should not transmit.
        """
        # Arrange
        service = LogsCollectorService(
            send_logs=False,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )
        logs = [
            {"level": "INFO", "message": "Log 1", "context": None, "source": "test"},
            {"level": "ERROR", "message": "Log 2", "context": None, "source": "test"},
        ]

        # Act
        results = service.send_bulk_logs(logs)

        # Assert
        mock_post.assert_not_called()
        self.assertEqual(
            results["success"],
            0,
            "No logs should succeed when send_logs=False"
        )
        self.assertEqual(
            results["failed"],
            2,
            "All logs should be marked as failed when send_logs=False"
        )

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.socket.gethostbyname')
    def test_bulk_logs_sent_when_send_logs_true_and_api_configured(
        self,
        mock_gethostbyname,
        mock_post
    ):
        """
        Test that send_bulk_logs transmits when send_logs=True and API is configured.
        """
        # Arrange
        mock_gethostbyname.return_value = "127.0.0.1"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = LogsCollectorService(
            send_logs=True,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )
        logs = [
            {"level": "INFO", "message": "Log 1", "context": None, "source": "test"},
            {"level": "ERROR", "message": "Log 2", "context": None, "source": "test"},
        ]

        # Act
        results = service.send_bulk_logs(logs)

        # Assert
        self.assertEqual(
            mock_post.call_count,
            2,
            "Should make API call for each log entry"
        )
        self.assertEqual(
            results["success"],
            2,
            "Both logs should succeed when send_logs=True and API is configured"
        )
        self.assertEqual(
            results["failed"],
            0,
            "No logs should fail when API returns success"
        )


class TestProcessingRunLogBehavior(unittest.TestCase):
    """Test cases for processing run log behavior with send_logs flag."""

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.logger')
    def test_processing_run_log_not_sent_when_send_logs_false(
        self,
        mock_logger,
        mock_post
    ):
        """
        Test that send_processing_run_log does not transmit when send_logs=False.
        """
        # Arrange
        service = LogsCollectorService(
            send_logs=False,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_processing_run_log(
            run_id="run-123",
            status="completed",
            metrics={"emails_processed": 100, "emails_deleted": 25},
            error=None,
            source="email-processor"
        )

        # Assert
        self.assertFalse(
            result,
            "send_processing_run_log should return False when send_logs=False"
        )
        mock_post.assert_not_called()


class TestEmailProcessingLogBehavior(unittest.TestCase):
    """Test cases for email processing log behavior with send_logs flag."""

    @patch('services.logs_collector_service.requests.post')
    @patch('services.logs_collector_service.logger')
    def test_email_processing_log_not_sent_when_send_logs_false(
        self,
        mock_logger,
        mock_post
    ):
        """
        Test that send_email_processing_log does not transmit when send_logs=False.
        """
        # Arrange
        service = LogsCollectorService(
            send_logs=False,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )

        # Act
        result = service.send_email_processing_log(
            message_id="msg-123",
            category="promotions",
            action="deleted",
            sender="sender@example.com",
            processing_time=0.5,
            source="email-processor"
        )

        # Assert
        self.assertFalse(
            result,
            "send_email_processing_log should return False when send_logs=False"
        )
        mock_post.assert_not_called()


class TestIsSendEnabledProperty(unittest.TestCase):
    """Test cases for is_send_enabled property integration with send_log."""

    def test_is_send_enabled_reflects_send_logs_true(self):
        """
        Test that is_send_enabled returns True when send_logs=True.
        """
        # Arrange & Act
        service = LogsCollectorService(
            send_logs=True,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )

        # Assert
        self.assertTrue(
            service.is_send_enabled,
            "is_send_enabled should return True when send_logs=True"
        )

    def test_is_send_enabled_reflects_send_logs_false(self):
        """
        Test that is_send_enabled returns False when send_logs=False.
        """
        # Arrange & Act
        service = LogsCollectorService(
            send_logs=False,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )

        # Assert
        self.assertFalse(
            service.is_send_enabled,
            "is_send_enabled should return False when send_logs=False"
        )

    @patch('services.logs_collector_service.requests.post')
    def test_send_log_behavior_matches_is_send_enabled(self, mock_post):
        """
        Test that send_log behavior is consistent with is_send_enabled property.

        When is_send_enabled is False, send_log should return False.
        """
        # Arrange
        service = LogsCollectorService(
            send_logs=False,
            api_url="https://logs-api.example.com",
            api_token="test-token"
        )

        # Act
        is_enabled = service.is_send_enabled
        send_result = service.send_log(
            level="INFO",
            message="Test",
            context=None,
            source="test"
        )

        # Assert
        self.assertFalse(
            is_enabled,
            "is_send_enabled should be False"
        )
        self.assertFalse(
            send_result,
            "send_log should return False when is_send_enabled is False"
        )
        mock_post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
