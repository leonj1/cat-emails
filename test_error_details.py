#!/usr/bin/env python3
"""
Test script to verify that error details from logs-collector API are properly displayed.
"""

import os
import sys
from services.logs_collector_service import LogsCollectorService
from clients.logs_collector_client import RemoteLogsCollectorClient, LogEntry

def test_logs_collector_service():
    """Test LogsCollectorService error handling"""
    print("Testing LogsCollectorService error handling...")

    # Use a fake API URL that will likely return an error
    service = LogsCollectorService(
        api_url="https://logs-collector-production.up.railway.app",
        api_token="invalid_token_for_testing"
    )

    # Try to send a log with invalid credentials
    result = service.send_log(
        level="ERROR",
        message="Test error message",
        context={"test": "data"},
        source="test-script"
    )

    print(f"LogsCollectorService send result: {result}")
    print()

def test_logs_collector_client():
    """Test RemoteLogsCollectorClient error handling"""
    print("Testing RemoteLogsCollectorClient error handling...")

    # Create client with invalid credentials
    client = RemoteLogsCollectorClient(
        logs_collector_url="https://logs-collector-production.up.railway.app",
        application_name="test-app",
        logs_collector_token="invalid_token_for_testing"
    )

    # Create a test log entry
    log_entry = LogEntry(
        application_name="test-app",
        message="Test log message",
        environment="test",
        level="error",
        trace_id="test-trace-123"
    )

    # Try to send the log
    result = client.send(log_entry)

    print(f"RemoteLogsCollectorClient send result: {result}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Testing error details display for logs-collector API")
    print("=" * 60)
    print()

    # Test both implementations
    test_logs_collector_service()
    test_logs_collector_client()

    print("=" * 60)
    print("Test complete. Check the output above for error details.")
    print("If the API returns error details, they should be displayed.")
    print("=" * 60)