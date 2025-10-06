#!/usr/bin/env python3
"""Test the logs collector service fix for 401 error."""
import os
import sys
from services.logs_collector_service import LogsCollectorService

# Set up the environment variables
os.environ["LOGS_COLLECTOR_API"] = "https://logs-collector-production.up.railway.app"

# Token should be set in your environment before running this script
# export LOGS_COLLECTOR_TOKEN="your-token-here"
if "LOGS_COLLECTOR_TOKEN" not in os.environ:
    print("ERROR: LOGS_COLLECTOR_TOKEN environment variable must be set")
    print("Please set it with: export LOGS_COLLECTOR_TOKEN='your-token-here'")
    sys.exit(1)

# Initialize the service
service = LogsCollectorService()

# Test sending a log without a trace_id (should auto-generate one now)
result = service.send_log(
    level="INFO",
    message="Test log after fix - auto-generated trace_id",
    context={"test": "data"},
    source="test-fix"
)

print(f"Test 1 (no trace_id): {'SUCCESS' if result else 'FAILED'}")

# Test sending a log with explicit trace_id
result2 = service.send_log(
    level="INFO",
    message="Test log after fix - explicit trace_id",
    context={"trace_id": "explicit-trace-123", "test": "data"},
    source="test-fix"
)

print(f"Test 2 (explicit trace_id): {'SUCCESS' if result2 else 'FAILED'}")