"""
Example demonstrating centralized logging with CentralLoggingService.

This example shows how to migrate from standard Python logging to
the centralized logging approach that sends logs to both stdout and
a remote logging service.
"""

import os
import logging

# Set environment variables for demonstration
os.environ["LOGS_COLLECTOR_API"] = "http://localhost:8080"
os.environ["LOGS_COLLECTOR_TOKEN"] = "demo-token"
os.environ["APP_NAME"] = "cat-emails"

# OLD APPROACH - Direct use of logging module
# This only logs to stdout/stderr
def old_logging_approach():
    """Example of the old logging approach."""
    print("\n=== OLD APPROACH - Standard Python Logging ===")
    
    # Configure basic logging (typically done at app startup)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get logger in each module
    logger = logging.getLogger(__name__)
    
    # Log messages only go to stdout
    logger.info("This message only goes to stdout")
    logger.error("This error only goes to stdout")


# NEW APPROACH - Centralized logging with CentralLoggingService
# This logs to both stdout AND remote logging service
def new_logging_approach():
    """Example of the new centralized logging approach."""
    print("\n=== NEW APPROACH - Centralized Logging ===")
    
    from utils.logger import initialize_central_logging, get_logger, shutdown_logging
    
    # Initialize central logging once at app startup
    # This replaces logging.basicConfig()
    initialize_central_logging(
        log_level=logging.INFO,
        enable_remote=True,  # Enable sending to remote service
        queue_maxsize=1000
    )
    
    # Get logger in each module (same API as before!)
    logger = get_logger(__name__)
    
    # Log messages go to BOTH stdout and remote service
    logger.info("This message goes to stdout AND remote logging service")
    logger.error("This error goes to stdout AND remote logging service")
    
    # Optional: Graceful shutdown at app exit
    shutdown_logging(timeout=5.0)


# MIGRATION EXAMPLE - Minimal changes needed
def migration_example():
    """Example showing how easy it is to migrate existing code."""
    print("\n=== MIGRATION EXAMPLE ===")
    print("To migrate existing code, you only need to change two lines:")
    print()
    print("OLD CODE:")
    print("-" * 50)
    print("""
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Processing email")
""")
    
    print("\nNEW CODE:")
    print("-" * 50)
    print("""
from utils.logger import get_logger, initialize_central_logging

initialize_central_logging(log_level=logging.INFO)  # Only at app startup
logger = get_logger(__name__)
logger.info("Processing email")  # Now goes to stdout + remote!
""")


# AUTOMATIC CAPTURE - Even third-party libraries get captured
def automatic_capture_example():
    """Example showing that even third-party library logs are captured."""
    print("\n=== AUTOMATIC CAPTURE ===")
    
    from utils.logger import initialize_central_logging
    
    # Initialize central logging
    initialize_central_logging(log_level=logging.DEBUG)
    
    # Even libraries using standard logging.getLogger() are captured!
    import urllib3
    urllib_logger = logging.getLogger("urllib3")
    urllib_logger.debug("This urllib3 log also goes through central logging!")
    
    # Any module using standard logging is automatically routed
    random_logger = logging.getLogger("some.random.module")
    random_logger.info("Even this random module's logs are centralized!")


def main():
    """Run all examples."""
    # Show the old approach
    old_logging_approach()
    
    # Show the new approach
    new_logging_approach()
    
    # Show migration steps
    migration_example()
    
    # Show automatic capture
    automatic_capture_example()
    
    print("\n" + "=" * 60)
    print("BENEFITS OF CENTRALIZED LOGGING:")
    print("1. All logs go to both stdout AND remote logging service")
    print("2. Single configuration point for entire application")
    print("3. Even third-party library logs are captured")
    print("4. Drop-in replacement - minimal code changes needed")
    print("5. Async remote logging doesn't block application")
    print("6. Automatic retry and queue management")
    print("=" * 60)


if __name__ == "__main__":
    main()
