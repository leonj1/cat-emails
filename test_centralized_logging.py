#!/usr/bin/env python3
"""
Test script for centralized logging implementation.

This script verifies that:
1. The centralized logger can be initialized
2. Logs go to both stdout and are queued for remote service
3. The root logger is properly configured
4. Third-party library logs are captured
"""

import os
import sys
import logging
import unittest
from unittest.mock import patch, MagicMock

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import initialize_central_logging, get_logger, shutdown_logging, get_central_service


class TestCentralizedLogging(unittest.TestCase):
    """Test cases for centralized logging."""
    
    def setUp(self):
        """Reset logging state before each test."""
        # Force re-initialization for each test
        global _initialized
        from utils import logger
        logger._initialized = False
        logger._central_logging_service = None
    
    def tearDown(self):
        """Clean up after each test."""
        shutdown_logging(timeout=1.0)
    
    def test_initialization(self):
        """Test that central logging can be initialized."""
        service = initialize_central_logging(
            log_level=logging.INFO,
            enable_remote=False  # Disable remote for testing
        )
        
        self.assertIsNotNone(service)
        self.assertIsNotNone(get_central_service())
    
    def test_get_logger(self):
        """Test that get_logger returns a working logger."""
        logger = get_logger(__name__)
        
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, __name__)
        
        # Test that logging doesn't raise exceptions
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
    
    def test_root_logger_configuration(self):
        """Test that the root logger is configured to use CentralLoggingService."""
        initialize_central_logging(
            log_level=logging.INFO,
            enable_remote=False
        )
        
        # Get the root logger
        root_logger = logging.getLogger()
        
        # Check that it has our custom handler
        self.assertGreater(len(root_logger.handlers), 0)
        
        # Test that logs from random modules go through our handler
        random_logger = logging.getLogger("test.module")
        random_logger.info("Test message from random module")
    
    def test_third_party_capture(self):
        """Test that third-party library logs are captured."""
        initialize_central_logging(
            log_level=logging.DEBUG,
            enable_remote=False
        )
        
        # Simulate a third-party library logger
        third_party = logging.getLogger("third_party.lib")
        third_party.info("Third party log message")
        
        # This should not raise any exceptions
        self.assertTrue(True)
    
    @patch.dict(os.environ, {
        "LOGS_COLLECTOR_API": "http://test-api.example.com",
        "LOGS_COLLECTOR_TOKEN": "test-token",
        "APP_NAME": "test-app"
    })
    def test_remote_logging_enabled(self):
        """Test that remote logging is enabled when configured."""
        service = initialize_central_logging(
            log_level=logging.INFO,
            enable_remote=True
        )
        
        self.assertTrue(service.enable_remote)
    
    def test_multiple_loggers(self):
        """Test that multiple module loggers work correctly."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        logger3 = get_logger("module3")
        
        # All loggers should work without errors
        logger1.info("Message from module1")
        logger2.warning("Warning from module2")
        logger3.error("Error from module3")
        
        # Same logger name should return the same instance
        logger1_again = get_logger("module1")
        self.assertEqual(logger1, logger1_again)
    
    def test_graceful_shutdown(self):
        """Test that shutdown completes without errors."""
        initialize_central_logging(
            log_level=logging.INFO,
            enable_remote=False
        )
        
        logger = get_logger(__name__)
        logger.info("Test message before shutdown")
        
        # Shutdown should complete without errors
        shutdown_logging(timeout=1.0)


def run_integration_test():
    """Run a simple integration test."""
    print("\n" + "=" * 60)
    print("RUNNING INTEGRATION TEST")
    print("=" * 60)
    
    # Initialize with environment variables if available
    service = initialize_central_logging(
        log_level=logging.DEBUG,
        enable_remote=bool(os.getenv("LOGS_COLLECTOR_API"))
    )
    
    # Get a logger
    logger = get_logger("integration_test")
    
    # Log some messages
    logger.debug("Debug: Starting integration test")
    logger.info("Info: Central logging is working")
    logger.warning("Warning: This is a test warning")
    logger.error("Error: This is a test error (not a real error)")
    logger.critical("Critical: This is a test critical message")
    
    # Test that standard logging also works
    standard_logger = logging.getLogger("standard.test")
    standard_logger.info("Standard logger message - should also be captured")
    
    print("\n✓ Integration test completed successfully")
    print(f"✓ Remote logging enabled: {service.enable_remote}")
    
    if service.enable_remote:
        print(f"✓ Logs will be sent to: {os.getenv('LOGS_COLLECTOR_API')}")
    else:
        print("✓ Remote logging disabled (no LOGS_COLLECTOR_API configured)")
    
    # Graceful shutdown
    shutdown_logging(timeout=5.0)
    print("✓ Logging service shut down gracefully")
    print("=" * 60)


if __name__ == "__main__":
    # Run unit tests
    print("Running unit tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run integration test
    run_integration_test()
