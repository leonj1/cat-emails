import unittest
from unittest.mock import patch, Mock, MagicMock
import logging
import os
import time
from services.logging_service import CentralLoggingService
from models.log_models import LogLevel
from clients.logs_collector_client import FakeLogsCollectorClient, LogsCollectorClient


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

        # Clean up any service instances that may have background threads
        if hasattr(self, 'service') and self.service is not None:
            self.service.shutdown(timeout=2.0)

    def test_init_with_remote_disabled(self):
        """Test initialization with remote logging disabled."""
        fake_client = FakeLogsCollectorClient("http://test.example.com", "test-app", "test-token")
        service = CentralLoggingService(logs_collector_client=fake_client, enable_remote=False)
        self.assertFalse(service.enable_remote)
        self.assertIsNotNone(service.logger)

    def test_init_without_api_url(self):
        """Test initialization without LOGS_COLLECTOR_API."""
        os.environ.pop('LOGS_COLLECTOR_API', None)
        os.environ.pop('LOGS_COLLECTOR_TOKEN', None)

        with patch('logging.Logger.warning') as mock_warning:
            fake_client = FakeLogsCollectorClient("http://test.example.com", "test-app", "test-token")
            service = CentralLoggingService(logs_collector_client=fake_client, enable_remote=True)
            self.assertTrue(service.enable_remote)

    def test_init_without_api_token(self):
        """Test initialization without LOGS_COLLECTOR_TOKEN."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ.pop('LOGS_COLLECTOR_TOKEN', None)

        with patch('logging.Logger.warning') as mock_warning:
            fake_client = FakeLogsCollectorClient("http://test.example.com", "test-app", "test-token")
            service = CentralLoggingService(logs_collector_client=fake_client, enable_remote=True)
            self.assertTrue(service.enable_remote)

    def test_init_with_valid_config(self):
        """Test initialization with valid configuration."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'
        os.environ['APP_NAME'] = 'test-app'
        os.environ['APP_VERSION'] = '2.0.0'
        os.environ['APP_ENVIRONMENT'] = 'testing'

        fake_client = FakeLogsCollectorClient("http://test.example.com", "test-app", "test-token")
        service = CentralLoggingService(logs_collector_client=fake_client, enable_remote=True)

        self.assertTrue(service.enable_remote)
        self.assertEqual(service.app_name, 'test-app')
        self.assertEqual(service.app_version, '2.0.0')
        self.assertEqual(service.app_environment, 'testing')
        # Verify background thread was started
        self.assertIsNotNone(service.worker_thread)
        self.assertTrue(service.worker_thread.is_alive())
        service.shutdown()

    def test_map_log_level(self):
        """Test log level mapping."""
        fake_client = FakeLogsCollectorClient("http://test.example.com", "test-app", "test-token")
        service = CentralLoggingService(logs_collector_client=fake_client, enable_remote=False)

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
        """Test successful remote log sending (async via queue)."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        # Use mock client that calls requests.post
        mock_client = Mock(spec=LogsCollectorClient)
        mock_client.send = Mock(return_value=True)

        service = CentralLoggingService(logs_collector_client=mock_client, enable_remote=True)

        # Send log via queue (non-blocking)
        service._send_to_remote(
            LogLevel.INFO,
            "Test message",
            "trace-123"
        )

        # Wait for background worker to process
        service.log_queue.join()
        time.sleep(0.1)  # Brief wait for worker processing

        # Verify client send was called
        mock_client.send.assert_called_once()

        service.shutdown()

    @patch('requests.post')
    def test_send_to_remote_http_error(self, mock_post):
        """Test remote log sending with HTTP error."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'

        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        # Use mock client that returns False on error
        mock_client = Mock(spec=LogsCollectorClient)
        mock_client.send = Mock(return_value=False)

        service = CentralLoggingService(logs_collector_client=mock_client, enable_remote=True)

        # Queue the log
        service._send_to_remote(
            LogLevel.INFO,
            "Test message",
            "trace-123"
        )

        # Wait for processing
        service.log_queue.join()
        time.sleep(0.1)

        # Verify client send was called (even though it failed)
        mock_client.send.assert_called_once()
        service.shutdown()

    @patch('requests.post')
    def test_send_to_remote_timeout(self, mock_post):
        """Test remote log sending with timeout."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'

        # Mock timeout
        mock_post.side_effect = Exception("Timeout")

        # Use mock client that raises exception
        mock_client = Mock(spec=LogsCollectorClient)
        mock_client.send = Mock(side_effect=Exception("Timeout"))

        service = CentralLoggingService(logs_collector_client=mock_client, enable_remote=True)

        # Suppress error logs during this test (expected behavior)
        with patch.object(service.logger, 'exception'):
            # Queue the log
            service._send_to_remote(
                LogLevel.INFO,
                "Test message",
                "trace-123"
            )

            # Wait for processing
            service.log_queue.join()
            time.sleep(0.1)

            # Verify client send was attempted
            mock_client.send.assert_called_once()

        service.shutdown()

    @patch('services.logging_service.CentralLoggingService._send_to_remote')
    def test_info_logging(self, mock_send):
        """Test info level logging."""
        fake_client = FakeLogsCollectorClient("http://test.example.com", "test-app", "test-token")
        service = CentralLoggingService(logs_collector_client=fake_client, enable_remote=True)

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
        fake_client = FakeLogsCollectorClient("http://test.example.com", "test-app", "test-token")
        service = CentralLoggingService(logs_collector_client=fake_client, enable_remote=True)

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
        fake_client = FakeLogsCollectorClient("http://test.example.com", "test-app", "test-token")
        service = CentralLoggingService(logs_collector_client=fake_client, enable_remote=True)

        with patch.object(service.logger, 'warning') as mock_logger_warning:
            service.warning("Test warning message")
            mock_logger_warning.assert_called_once_with("Test warning message")
            mock_send.assert_called_once()

    @patch('services.logging_service.CentralLoggingService._send_to_remote')
    def test_error_logging(self, mock_send):
        """Test error level logging."""
        fake_client = FakeLogsCollectorClient("http://test.example.com", "test-app", "test-token")
        service = CentralLoggingService(logs_collector_client=fake_client, enable_remote=True)

        with patch.object(service.logger, 'error') as mock_logger_error:
            service.error("Test error message")
            mock_logger_error.assert_called_once_with("Test error message")
            mock_send.assert_called_once()

    @patch('services.logging_service.CentralLoggingService._send_to_remote')
    def test_critical_logging(self, mock_send):
        """Test critical level logging."""
        fake_client = FakeLogsCollectorClient("http://test.example.com", "test-app", "test-token")
        service = CentralLoggingService(logs_collector_client=fake_client, enable_remote=True)

        with patch.object(service.logger, 'critical') as mock_logger_critical:
            service.critical("Test critical message")
            mock_logger_critical.assert_called_once_with("Test critical message")
            mock_send.assert_called_once()

    @patch('services.logging_service.CentralLoggingService._send_to_remote')
    def test_log_with_level(self, mock_send):
        """Test log method with custom level."""
        fake_client = FakeLogsCollectorClient("http://test.example.com", "test-app", "test-token")
        service = CentralLoggingService(logs_collector_client=fake_client, enable_remote=True)

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
        fake_client = FakeLogsCollectorClient("http://test.example.com", "test-app", "test-token")
        service = CentralLoggingService(logs_collector_client=fake_client, enable_remote=False)

        with patch('requests.post') as mock_post:
            service.info("Test message")
            mock_post.assert_not_called()

    def test_non_blocking_behavior(self):
        """Test that logging returns immediately without blocking on HTTP requests."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'

        # Create a slow mock that would block if called synchronously
        def slow_send(*args, **kwargs):
            time.sleep(2)  # Simulate slow network
            return True

        mock_client = Mock(spec=LogsCollectorClient)
        mock_client.send = Mock(side_effect=slow_send)

        service = CentralLoggingService(logs_collector_client=mock_client, enable_remote=True)

        # Measure time for log call (should be instant, not wait for HTTP)
        start = time.time()
        service.info("Test message")
        elapsed = time.time() - start

        # Should return in < 100ms (not 2 seconds)
        self.assertLess(elapsed, 0.1,
            "Log call blocked on HTTP request instead of returning immediately")

        # Wait for background processing and verify request was made
        service.log_queue.join()
        mock_client.send.assert_called_once()
        service.shutdown()

    @patch('requests.post')
    def test_auto_trace_id_generation(self, mock_post):
        """Test automatic trace ID generation when not provided."""
        os.environ['LOGS_COLLECTOR_API'] = 'http://test.example.com'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'

        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        # Mock client to capture the log entry
        captured_entry = None
        def capture_send(entry):
            nonlocal captured_entry
            captured_entry = entry
            return True

        mock_client = Mock(spec=LogsCollectorClient)
        mock_client.send = Mock(side_effect=capture_send)

        service = CentralLoggingService(logs_collector_client=mock_client, enable_remote=True)
        service.info("Test without trace ID")

        # Wait for background processing
        service.log_queue.join()
        time.sleep(0.1)

        # Verify that a trace ID was generated
        self.assertIsNotNone(captured_entry)
        self.assertIsNotNone(captured_entry.trace_id)
        service.shutdown()

    @patch('requests.post')
    def test_payload_structure_matches_api_spec(self, mock_post):
        """Test that the payload sent to API exactly matches the expected structure."""
        os.environ['LOGS_COLLECTOR_API'] = 'https://logs-collector-production.up.railway.app'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token-123'
        os.environ['APP_NAME'] = 'my-app'
        os.environ['APP_VERSION'] = '1.0.0'
        os.environ['APP_ENVIRONMENT'] = 'production'

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        # Mock client to capture the log entry
        captured_entry = None
        def capture_send(entry):
            nonlocal captured_entry
            captured_entry = entry
            return True

        mock_client = Mock(spec=LogsCollectorClient)
        mock_client.send = Mock(side_effect=capture_send)

        service = CentralLoggingService(logs_collector_client=mock_client, enable_remote=True)

        # Send a log message
        service.info("User logged in successfully", trace_id="abc123xyz")

        # Wait for background processing
        service.log_queue.join()
        time.sleep(0.1)

        # Get the payload that was sent
        self.assertIsNotNone(captured_entry)
        payload = captured_entry.model_dump(exclude_none=True)

        # Validate all required fields are present
        required_fields = {
            'application_name',
            'environment',
            'hostname',
            'level',
            'message',
            'timestamp',
            'trace_id',
            'version'
        }
        self.assertEqual(set(payload.keys()), required_fields)

        # Validate field values
        self.assertEqual(payload['application_name'], 'my-app')
        self.assertEqual(payload['environment'], 'production')
        self.assertIsInstance(payload['hostname'], str)
        self.assertGreater(len(payload['hostname']), 0)
        self.assertEqual(payload['level'], 'info')
        self.assertEqual(payload['message'], 'User logged in successfully')
        self.assertEqual(payload['trace_id'], 'abc123xyz')
        self.assertEqual(payload['version'], '1.0.0')

        # Validate timestamp format (ISO 8601 with Z suffix)
        self.assertIsInstance(payload['timestamp'], str)
        self.assertTrue(payload['timestamp'].endswith('Z'))
        # Validate timestamp is parseable
        from datetime import datetime
        try:
            datetime.fromisoformat(payload['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            self.fail(f"Invalid timestamp format: {payload['timestamp']}")

        # Validate field types
        self.assertIsInstance(payload['application_name'], str)
        self.assertIsInstance(payload['environment'], str)
        self.assertIsInstance(payload['hostname'], str)
        self.assertIsInstance(payload['level'], str)
        self.assertIsInstance(payload['message'], str)
        self.assertIsInstance(payload['timestamp'], str)
        self.assertIsInstance(payload['trace_id'], str)
        self.assertIsInstance(payload['version'], str)
        service.shutdown()

    @patch('requests.post')
    def test_payload_matches_example_structure(self, mock_post):
        """Test that payload structure matches the exact example from API spec."""
        os.environ['LOGS_COLLECTOR_API'] = 'https://logs-collector-production.up.railway.app'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'
        os.environ['APP_NAME'] = 'my-app'
        os.environ['APP_VERSION'] = '1.0.0'
        os.environ['APP_ENVIRONMENT'] = 'production'

        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        # Mock client to capture the log entries
        captured_entries = []
        def capture_send(entry):
            captured_entries.append(entry)
            return True

        mock_client = Mock(spec=LogsCollectorClient)
        mock_client.send = Mock(side_effect=capture_send)

        service = CentralLoggingService(logs_collector_client=mock_client, enable_remote=True)

        # Test with different log levels
        test_cases = [
            ('info', 'User logged in successfully'),
            ('debug', 'Debugging database query'),
            ('warning', 'High memory usage detected'),
            ('error', 'Failed to connect to database'),
            ('critical', 'System out of memory')
        ]

        for level_name, message in test_cases:
            # Send log at specific level
            getattr(service, level_name)(message, trace_id="test-trace-id")

            # Wait for background processing
            service.log_queue.join()
            time.sleep(0.05)

        # Verify all payloads
        self.assertEqual(len(captured_entries), len(test_cases))
        for i, (level_name, message) in enumerate(test_cases):
            entry = captured_entries[i]
            payload = entry.model_dump(exclude_none=True)

            # Check that it has exactly the expected shape
            self.assertIn('application_name', payload)
            self.assertIn('environment', payload)
            self.assertIn('hostname', payload)
            self.assertIn('level', payload)
            self.assertIn('message', payload)
            self.assertIn('timestamp', payload)
            self.assertIn('trace_id', payload)
            self.assertIn('version', payload)

            # Verify level matches
            self.assertEqual(payload['level'], level_name)
            self.assertEqual(payload['message'], message)

        service.shutdown()

    @patch('requests.post')
    def test_payload_serialization_to_json(self, mock_post):
        """Test that Pydantic model serializes correctly to JSON for API."""
        os.environ['LOGS_COLLECTOR_API'] = 'https://logs-collector-production.up.railway.app'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'

        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        # Mock client to capture the log entry
        captured_entry = None
        def capture_send(entry):
            nonlocal captured_entry
            captured_entry = entry
            return True

        mock_client = Mock(spec=LogsCollectorClient)
        mock_client.send = Mock(side_effect=capture_send)

        service = CentralLoggingService(logs_collector_client=mock_client, enable_remote=True)
        service.info("Test message", trace_id="trace-123")

        # Wait for background processing
        service.log_queue.join()
        time.sleep(0.1)

        # Verify the payload is JSON-serializable dict
        self.assertIsNotNone(captured_entry)
        payload = captured_entry.model_dump(exclude_none=True)

        # Should be a dict, not a Pydantic model
        self.assertIsInstance(payload, dict)

        # Verify it can be JSON serialized (no weird objects)
        import json
        try:
            json_str = json.dumps(payload)
            # And deserialized back
            deserialized = json.loads(json_str)
            self.assertEqual(payload, deserialized)
        except (TypeError, ValueError) as e:
            self.fail(f"Payload is not JSON-serializable: {e}")

        service.shutdown()


if __name__ == '__main__':
    unittest.main()
