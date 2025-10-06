#!/usr/bin/env python3
"""Test script to verify logs collector authentication fix."""

import os
import sys
from datetime import datetime

# Set test environment variables if not already set
if not os.getenv("LOGS_COLLECTOR_API"):
    # Using a test endpoint - update this to your actual endpoint
    os.environ["LOGS_COLLECTOR_API"] = "https://logs-collector-production.up.railway.app"
    print("Using default LOGS_COLLECTOR_API endpoint")

token_value = os.getenv("LOGS_COLLECTOR_TOKEN") or os.getenv("LOGS_COLLECTOR_API_TOKEN")
# The token should be set in the deployment environment
if not token_value:
    print("WARNING: No logs collector token found - authentication will fail")
    print("Please set LOGS_COLLECTOR_TOKEN (preferred) or LOGS_COLLECTOR_API_TOKEN with a valid token")

from services.logs_collector_service import LogsCollectorService

def test_logs_collector():
    """Test the logs collector service."""
    print("\n=== Testing Logs Collector Service ===")
    print(f"API URL: {os.getenv('LOGS_COLLECTOR_API', 'Not set')}")
    print(f"Token present: {'Yes' if token_value else 'No'}")

    # Initialize the service
    service = LogsCollectorService()

    if not service.enabled:
        print("\nERROR: Logs collector service is not enabled.")
        print("Please set LOGS_COLLECTOR_API environment variable.")
        return False

    # Test sending a log
    print("\nSending test log...")

    context = {
        "test": True,
        "trace_id": f"test-{datetime.utcnow().isoformat()}",
        "script": "test_logs_auth_fix.py"
    }

    success = service.send_log(
        level="INFO",
        message="Test log from authentication fix verification",
        context=context,
        source="cat-emails-test"
    )

    if success:
        print("✅ SUCCESS: Log was sent successfully!")
        print("The authentication and payload format are working correctly.")
    else:
        print("❌ FAILED: Log could not be sent.")
        print("Check the error messages above for details.")
        print("\nCommon issues:")
        print("1. LOGS_COLLECTOR_TOKEN or LOGS_COLLECTOR_API_TOKEN not set or invalid")
        print("2. LOGS_COLLECTOR_API endpoint is incorrect")
        print("3. Network connectivity issues")

    return success

if __name__ == "__main__":
    success = test_logs_collector()
    sys.exit(0 if success else 1)