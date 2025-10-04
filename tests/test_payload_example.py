#!/usr/bin/env python3
"""
Standalone test to validate that the logging service produces the exact
payload structure specified in the API documentation.

This test can be run independently to verify the payload format:
    python tests/test_payload_example.py
"""

import unittest
import os
import json
import time
from unittest.mock import patch, Mock


class TestExactPayloadFormat(unittest.TestCase):
    """Test that validates the exact payload format from API spec."""

    def setUp(self):
        """Set up test environment."""
        # Save original environment
        self.original_env = dict(os.environ)

        # Set test environment
        os.environ['LOGS_COLLECTOR_API'] = 'https://logs-collector-production.up.railway.app'
        os.environ['LOGS_COLLECTOR_TOKEN'] = 'test-token'
        os.environ['APP_NAME'] = 'my-app'
        os.environ['APP_VERSION'] = '1.0.0'
        os.environ['APP_ENVIRONMENT'] = 'production'

    def tearDown(self):
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(self.original_env)

        # Clean up any service instances
        if hasattr(self, 'service') and self.service is not None:
            self.service.shutdown(timeout=2.0)

    @patch('socket.gethostname')
    @patch('requests.post')
    def test_exact_api_spec_payload(self, mock_post, mock_hostname):
        """
        Test that the service produces a payload matching the API spec example:

        {
          "application_name": "my-app",
          "environment": "production",
          "hostname": "server-01",
          "level": "info",
          "message": "User logged in successfully",
          "timestamp": "2024-01-15T14:30:00Z",
          "trace_id": "abc123xyz",
          "version": "1.0.0"
        }
        """
        # Import here to use the environment variables we just set
        from services.logging_service import CentralLoggingService

        # Mock hostname to match example
        mock_hostname.return_value = 'server-01'

        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "message": "Log received",
            "status": "accepted"
        }
        mock_post.return_value = mock_response

        # Create service and send log
        service = CentralLoggingService(enable_remote=True)
        self.service = service  # Store for cleanup
        service.info("User logged in successfully", trace_id="abc123xyz")

        # Wait for background processing
        service.log_queue.join()
        time.sleep(0.1)

        # Verify the API was called
        self.assertTrue(mock_post.called)

        # Get the actual payload sent
        call_args = mock_post.call_args
        actual_payload = call_args[1]['json']

        # Print the payload for manual verification
        print("\n" + "="*60)
        print("ACTUAL PAYLOAD SENT TO API:")
        print("="*60)
        print(json.dumps(actual_payload, indent=2))
        print("="*60 + "\n")

        # Verify exact structure
        expected_keys = {
            'application_name',
            'environment',
            'hostname',
            'level',
            'message',
            'timestamp',
            'trace_id',
            'version'
        }
        self.assertEqual(set(actual_payload.keys()), expected_keys,
                        "Payload must contain exactly these 8 fields")

        # Verify exact values (except timestamp which is dynamic)
        self.assertEqual(actual_payload['application_name'], 'my-app')
        self.assertEqual(actual_payload['environment'], 'production')
        self.assertEqual(actual_payload['hostname'], 'server-01')
        self.assertEqual(actual_payload['level'], 'info')
        self.assertEqual(actual_payload['message'], 'User logged in successfully')
        self.assertEqual(actual_payload['trace_id'], 'abc123xyz')
        self.assertEqual(actual_payload['version'], '1.0.0')

        # Verify timestamp format
        self.assertRegex(
            actual_payload['timestamp'],
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$',
            "Timestamp must be ISO 8601 format with Z suffix"
        )

        # Verify all values are strings
        for key, value in actual_payload.items():
            self.assertIsInstance(value, str,
                                f"Field '{key}' must be a string")

        # Verify payload is JSON serializable
        json_str = json.dumps(actual_payload)
        self.assertIsInstance(json_str, str)

        # Verify can be deserialized
        deserialized = json.loads(json_str)
        self.assertEqual(actual_payload, deserialized)

        print("✓ Payload structure matches API spec exactly!\n")


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
