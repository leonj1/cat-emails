#!/usr/bin/env python3
"""
Example usage of the CentralLoggingService.

This example demonstrates how to use the logging service to log messages
both locally (stdout) and remotely (central logging collector).

Before running:
    export LOGS_COLLECTOR_API="https://logs-collector-production.up.railway.app"
    export LOGS_COLLECTOR_TOKEN="your-bearer-token"
    export APP_NAME="cat-emails"
    export APP_VERSION="1.0.0"
    export APP_ENVIRONMENT="production"
"""

import os
import sys
import logging

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.logging_factory import create_logging_service


def example_basic_logging():
    """Example: Basic logging at different levels."""
    print("\n=== Example 1: Basic Logging ===\n")

    # Initialize the logging service using factory
    log_service = create_logging_service(
        logger_name="example-app",
        log_level=logging.DEBUG
    )

    # Log messages at different levels
    log_service.debug("This is a debug message")
    log_service.info("This is an info message")
    log_service.warning("This is a warning message")
    log_service.error("This is an error message")
    log_service.critical("This is a critical message")


def example_with_trace_id():
    """Example: Logging with trace IDs for distributed tracing."""
    print("\n=== Example 2: Logging with Trace IDs ===\n")

    log_service = create_logging_service(logger_name="traced-app")

    # Simulate processing a request with a trace ID
    request_trace_id = "req-12345-abcde"

    log_service.info(
        f"Starting request processing",
        trace_id=request_trace_id
    )
    log_service.info(
        f"Fetching data from database",
        trace_id=request_trace_id
    )
    log_service.info(
        f"Processing complete",
        trace_id=request_trace_id
    )


def example_email_processing():
    """Example: Using logging service in email processing context."""
    print("\n=== Example 3: Email Processing Logging ===\n")

    log_service = create_logging_service(logger_name="email-processor")

    # Simulate email processing workflow
    email_id = "msg_67890"
    trace_id = f"email-{email_id}"

    log_service.info(f"Fetching email {email_id}", trace_id=trace_id)
    log_service.info(f"Analyzing email content", trace_id=trace_id)
    log_service.info(f"Categorized as: Marketing", trace_id=trace_id)
    log_service.info(f"Applied label: Advertising", trace_id=trace_id)
    log_service.info(f"Email processing complete", trace_id=trace_id)


def example_error_handling():
    """Example: Logging errors with context."""
    print("\n=== Example 4: Error Handling ===\n")

    log_service = create_logging_service(logger_name="error-handler")

    try:
        # Simulate an error
        result = 10 / 0
    except ZeroDivisionError as e:
        log_service.error(
            f"Division error occurred: {str(e)}",
            trace_id="error-trace-001"
        )
        log_service.info("Attempting recovery", trace_id="error-trace-001")


def example_remote_disabled():
    """Example: Using logging service with remote logging disabled."""
    print("\n=== Example 5: Local-only Logging ===\n")

    # This is useful for development or when you want only stdout logging
    log_service = create_logging_service(
        logger_name="local-only",
        enable_remote=False
    )

    log_service.info("This message only goes to stdout")
    log_service.warning("Remote logging is disabled")


def example_custom_log_level():
    """Example: Using the generic log() method with custom levels."""
    print("\n=== Example 6: Custom Log Levels ===\n")

    log_service = create_logging_service(logger_name="custom-logger")

    # Using the generic log() method
    log_service.log(logging.INFO, "Info via log() method")
    log_service.log(logging.WARNING, "Warning via log() method")
    log_service.log(logging.ERROR, "Error via log() method", trace_id="custom-001")


def main():
    """Run all examples."""
    print("=" * 60)
    print("CentralLoggingService Examples")
    print("=" * 60)

    # Check if remote logging is configured
    if os.getenv("LOGS_COLLECTOR_API") and os.getenv("LOGS_COLLECTOR_TOKEN"):
        print("\n✓ Remote logging is ENABLED")
        print(f"  API: {os.getenv('LOGS_COLLECTOR_API')}")
        print(f"  App: {os.getenv('APP_NAME', 'cat-emails')}")
        print(f"  Env: {os.getenv('APP_ENVIRONMENT', 'production')}")
    else:
        print("\n⚠ Remote logging is DISABLED")
        print("  Set LOGS_COLLECTOR_API and LOGS_COLLECTOR_TOKEN to enable")

    # Run examples
    example_basic_logging()
    example_with_trace_id()
    example_email_processing()
    example_error_handling()
    example_remote_disabled()
    example_custom_log_level()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
