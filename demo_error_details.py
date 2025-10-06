#!/usr/bin/env python3
"""
Demonstration script showing that error details from logs-collector API
are now properly displayed in stdout.
"""

import json
from unittest.mock import MagicMock, patch
import sys

# Add the repo to the path
sys.path.insert(0, '/root/repo')

from services.logs_collector_service import LogsCollectorService
from clients.logs_collector_client import RemoteLogsCollectorClient, LogEntry


def demonstrate_logs_collector_service_error_details():
    """Demonstrate LogsCollectorService displaying error details"""
    print("=" * 60)
    print("DEMONSTRATING: LogsCollectorService Error Details Display")
    print("=" * 60)

    with patch('services.logs_collector_service.requests.post') as mock_post:
        import requests

        # Create a mock response with error details
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'details': 'Invalid trace_id format: must be a valid UUID',
            'error': 'Bad Request'
        }

        # Create HTTP error with the response
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = http_error

        service = LogsCollectorService(
            api_url="https://logs-collector-production.up.railway.app",
            api_token="test-token"
        )

        print("\nSending a log with invalid trace_id...")
        result = service.send_log(
            level="ERROR",
            message="Test error message",
            context={"trace_id": "invalid-trace-id"},
            source="demo-script"
        )

        print(f"Result: {result}")
        print("\n✅ The error details are now displayed above!")
    print()


def demonstrate_logs_collector_client_error_details():
    """Demonstrate RemoteLogsCollectorClient displaying error details"""
    print("=" * 60)
    print("DEMONSTRATING: RemoteLogsCollectorClient Error Details Display")
    print("=" * 60)

    with patch('clients.logs_collector_client.requests.post') as mock_post:
        import requests

        # Create a mock response with error details
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            'details': 'Authentication failed: token expired on 2024-01-01',
            'error': 'Unauthorized'
        }

        # Create HTTP error with the response
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = http_error

        client = RemoteLogsCollectorClient(
            logs_collector_url="https://logs-collector-production.up.railway.app",
            application_name="demo-app",
            logs_collector_token="expired-token"
        )

        log_entry = LogEntry(
            application_name="demo-app",
            message="Test log message",
            level="error"
        )

        print("\nSending a log with expired token...")
        result = client.send(log_entry)

        print(f"Result: {result}")
        print("\n✅ The error details are now displayed above!")
    print()


def main():
    print("\n" + "🚀" * 30)
    print("ERROR DETAILS DISPLAY DEMONSTRATION")
    print("🚀" * 30 + "\n")

    print("This script demonstrates that error details from the logs-collector API")
    print("are now properly displayed in stdout to help developers debug issues.\n")

    # Demonstrate both implementations
    demonstrate_logs_collector_service_error_details()
    demonstrate_logs_collector_client_error_details()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("\n✅ Both LogsCollectorService and RemoteLogsCollectorClient now:")
    print("   1. Extract the 'details' field from API error responses")
    print("   2. Display the error details to stdout with 'ERROR:' prefix")
    print("   3. Include the details in log messages for debugging")
    print("\nThis helps developers immediately understand what went wrong")
    print("when the logs-collector API returns an error.\n")


if __name__ == "__main__":
    main()