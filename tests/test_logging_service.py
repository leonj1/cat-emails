import unittest
from unittest.mock import patch, Mock, MagicMock
import logging
import os
from services.logging_service import CentralLoggingService
from models.log_models import LogLevel


class TestCentralLoggingService(unittest.TestCase):
    """Test cases for CentralLoggingService."""

    def setUp(self):
        """Set up test fixtures."""
        # Save original environment variables
        self.original_env = {
            'LOGS_COLLECTOR_API': os.getenv('LOGS_COLLECTOR_API'),
            'LOGS_COLLECTOR_TOKEN': os.getenv('LOGS_COLLECTOR_TOKEN'),
            'APP_NAME': os.getenv('APP_NAME'),
            'APP_VERSION': os.getenv('APP_VERSION'),
            'APP_ENVIRONMENT': os.getenv('APP_ENVIRONMENT')
        }

    def tearDown(self):
        """Clean up after tests."""
        # Restore original environment variables
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_init_with_remote_disabled(self):
        """Test initialization with remote logging disabled."""
        service = CentralLoggingService(enable_remote=False)
        self.assertFalse(service.enable_remote)
        self.assertIsNotNone(service.logger)

    def test_init_without_api_url(self):
        """Test initialization without LOGS_COLLECTOR_API."""
        os.environ.pop('LOGS_COLLECTOR_API', None)
        os.environ.pop('LOGS_COLLECTOR_TOKEN', None)

        with patch('logging.Logger.warning') as mock_warning:
            service = CentralLoggingService(enable_remote=True)
            self.assertFalse(service.enable_remote)

    def test_init_without_api_token(self):
        """Test initialization without LOGS_COLLECTOR_TOKEN."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ.pop('LOGS_COLLECTOR_TOKEN', None)

        with patch('logging.Logger.warning') as mock_warning:
            service = CentralLoggingService(enable_remote=True)
            self.assertFalse(service.enable_remote)

    def test_init_with_valid_config(self):
        """Test initialization with valid configuration."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'
        os.environ['APP_NAME'] = 'test-app'
        os.environ['APP_VERSION'] = '2.0.0'
        os.environ['APP_ENVIRONMENT'] = 'testing'

        service = CentralLoggingService(enable_remote=True)

        self.assertTrue(service.enable_remote)
        self.assertEqual(service.api_base_url, 'http://test.example.com')
        self.assertEqual(service.api_token, 'test-token')
        self.assertEqual(service.app_name, 'test-app')
        self.assertEqual(service.app_version, '2.0.0')
        self.assertEqual(service.app_environment, 'testing')

    def test_map_log_level(self):
        """Test log level mapping."""
        service = CentralLoggingService(enable_remote=False)

        self.assertEqual(
            service._map_log_level(logging.DEBUG),
            LogLevel.DEBUG
        )
        self.assertEqual(
            service._map_log_level(logging.INFO),
            LogLevel.INFO
        )
        self.assertEqual(
            service._map_log_level(logging.WARNING),
            LogLevel.WARNING
        )
        self.assertEqual(
            service._map_log_level(logging.ERROR),
            LogLevel.ERROR
        )
        self.assertEqual(
            service._map_log_level(logging.CRITICAL),
            LogLevel.CRITICAL
        )

    @patch('requests.post')
    def test_send_to_remote_success(self, mock_post):
        """Test successful remote log sending."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        service = CentralLoggingService(enable_remote=True)
        result = service._send_to_remote(
            LogLevel.INFO,
            "Test message",
            "trace-123"
        )

        self.assertTrue(result)
        mock_post.assert_called_once()

        # Verify the call arguments
        call_args = mock_post.call_args
        # URL is the first positional argument
        self.assertEqual(call_args[0][0], 'http://test.example.com/logs')
        self.assertIn('Authorization', call_args[1]['headers'])
        self.assertEqual(
            call_args[1]['headers']['Authorization'],
            'Bearer test-token'
        )

    @patch('requests.post')
    def test_send_to_remote_http_error(self, mock_post):
        """Test remote log sending with HTTP error."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'

        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        service = CentralLoggingService(enable_remote=True)
        result = service._send_to_remote(
            LogLevel.INFO,
            "Test message",
            "trace-123"
        )

        self.assertFalse(result)

    @patch('requests.post')
    def test_send_to_remote_timeout(self, mock_post):
        """Test remote log sending with timeout."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'

        # Mock timeout
        mock_post.side_effect = Exception("Timeout")

        service = CentralLoggingService(enable_remote=True)
        result = service._send_to_remote(
            LogLevel.INFO,
            "Test message",
            "trace-123"
        )

        self.assertFalse(result)

    @patch('services.logging_service.CentralLoggingService._send_to_remote')
    def test_info_logging(self, mock_send):
        """Test info level logging."""
        service = CentralLoggingService(enable_remote=True)

        with patch.object(service.logger, 'info') as mock_logger_info:
            service.info("Test info message", "trace-123")
            mock_logger_info.assert_called_once_with("Test info message")
            mock_send.assert_called_once_with(
                LogLevel.INFO,
                "Test info message",
                "trace-123"
            )

    @patch('services.logging_service.CentralLoggingService._send_to_remote')
    def test_debug_logging(self, mock_send):
        """Test debug level logging."""
        service = CentralLoggingService(enable_remote=True)

        with patch.object(service.logger, 'debug') as mock_logger_debug:
            service.debug("Test debug message", "trace-456")
            mock_logger_debug.assert_called_once_with("Test debug message")
            mock_send.assert_called_once_with(
                LogLevel.DEBUG,
                "Test debug message",
                "trace-456"
            )

    @patch('services.logging_service.CentralLoggingService._send_to_remote')
    def test_warning_logging(self, mock_send):
        """Test warning level logging."""
        service = CentralLoggingService(enable_remote=True)

        with patch.object(service.logger, 'warning') as mock_logger_warning:
            service.warning("Test warning message")
            mock_logger_warning.assert_called_once_with("Test warning message")
            mock_send.assert_called_once()

    @patch('services.logging_service.CentralLoggingService._send_to_remote')
    def test_error_logging(self, mock_send):
        """Test error level logging."""
        service = CentralLoggingService(enable_remote=True)

        with patch.object(service.logger, 'error') as mock_logger_error:
            service.error("Test error message")
            mock_logger_error.assert_called_once_with("Test error message")
            mock_send.assert_called_once()

    @patch('services.logging_service.CentralLoggingService._send_to_remote')
    def test_critical_logging(self, mock_send):
        """Test critical level logging."""
        service = CentralLoggingService(enable_remote=True)

        with patch.object(service.logger, 'critical') as mock_logger_critical:
            service.critical("Test critical message")
            mock_logger_critical.assert_called_once_with("Test critical message")
            mock_send.assert_called_once()

    @patch('services.logging_service.CentralLoggingService._send_to_remote')
    def test_log_with_level(self, mock_send):
        """Test log method with custom level."""
        service = CentralLoggingService(enable_remote=True)

        with patch.object(service.logger, 'log') as mock_logger_log:
            service.log(logging.WARNING, "Test custom level message")
            mock_logger_log.assert_called_once_with(
                logging.WARNING,
                "Test custom level message"
            )
            mock_send.assert_called_once_with(
                LogLevel.WARNING,
                "Test custom level message",
                None
            )

    def test_remote_disabled_no_send(self):
        """Test that remote logging is skipped when disabled."""
        service = CentralLoggingService(enable_remote=False)

        with patch('requests.post') as mock_post:
            service.info("Test message")
            mock_post.assert_not_called()

    @patch('requests.post')
    def test_auto_trace_id_generation(self, mock_post):
        """Test automatic trace ID generation when not provided."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'

        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        service = CentralLoggingService(enable_remote=True)
        service.info("Test without trace ID")

        # Verify that a trace ID was generated
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertIn('trace_id', payload)
        self.assertIsNotNone(payload['trace_id'])


if __name__ == '__main__':
    unittest.main()
