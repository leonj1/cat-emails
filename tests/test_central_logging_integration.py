#!/usr/bin/env python3
"""
Integration test to validate that the central logging service is actually
intercepting and processing all log messages from various modules.

This test verifies that:
1. Log messages from modules using get_logger() go through CentralLoggingService
2. Log messages from third-party libraries are captured
3. Remote logging queue receives messages when enabled
4. Log messages appear in stdout/stderr
"""

import unittest
import logging
import sys
import os
from io import StringIO
from unittest.mock import patch, MagicMock, call
from queue import Queue
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import (
    initialize_central_logging, 
    get_logger, 
    get_central_service,
    shutdown_logging
)
from services.logging_service import CentralLoggingService, LogLevel


class TestCentralLoggingIntegration(unittest.TestCase):
    """Test that central logging is properly intercepting all log messages."""
    
    def setUp(self):
        """Reset logging state before each test."""
        # Force re-initialization for each test
        from utils import logger
        logger._initialized = False
        logger._central_logging_service = None
        logger._logger_cache.clear()
        
        # Clear any existing handlers from root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    def tearDown(self):
        """Clean up after each test."""
        shutdown_logging(timeout=1.0)
    
    def test_get_logger_uses_central_service(self):
        """Test that get_logger() routes through CentralLoggingService."""
        # Initialize with remote disabled for testing
        service = initialize_central_logging(
            log_level=logging.INFO,
            enable_remote=False
        )
        
        # Get a logger
        logger = get_logger("test.module")
        
        # Capture stderr output
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            # Log a message
            logger.info("Test message from module")
            
            # Check that message appeared in stderr
            output = mock_stderr.getvalue()
            self.assertIn("Test message from module", output)
            self.assertIn("test.module", output)
    
    def test_third_party_library_capture(self):
        """Test that third-party library logs are captured."""
        # Initialize central logging
        initialize_central_logging(
            log_level=logging.DEBUG,
            enable_remote=False
        )
        
        # Simulate a third-party library logger
        third_party_logger = logging.getLogger("urllib3.connectionpool")
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            # Log from "third-party" library
            third_party_logger.debug("Starting new HTTPS connection")
            
            # Check that message was captured
            output = mock_stderr.getvalue()
            self.assertIn("Starting new HTTPS connection", output)
            self.assertIn("urllib3.connectionpool", output)
    
    def test_remote_logging_queue(self):
        """Test that messages are queued for remote logging when enabled."""
        # Mock the logs collector client
        mock_client = MagicMock()
        mock_client.send.return_value = True
        
        # Initialize with remote enabled
        service = CentralLoggingService(
            logs_collector_client=mock_client,
            logger_name="test",
            log_level=logging.INFO,
            enable_remote=True,
            queue_maxsize=10
        )
        
        # Log some messages
        service.info("Test info message")
        service.error("Test error message")
        service.warning("Test warning message")
        
        # Wait a bit for the background thread to process
        time.sleep(0.5)
        
        # Check that the client was called
        self.assertGreater(mock_client.send.call_count, 0)
        
        # Verify the messages were sent with correct log levels
        calls = mock_client.send.call_args_list
        messages_sent = [call[0][0].message for call in calls]
        
        self.assertIn("Test info message", messages_sent)
        self.assertIn("Test error message", messages_sent)
        self.assertIn("Test warning message", messages_sent)
        
        # Cleanup
        service.shutdown(timeout=1.0)
    
    def test_logging_hierarchy_capture(self):
        """Test that child loggers inherit central logging configuration."""
        initialize_central_logging(
            log_level=logging.INFO,
            enable_remote=False
        )
        
        # Create parent and child loggers
        parent_logger = get_logger("myapp")
        child_logger = get_logger("myapp.submodule")
        grandchild_logger = get_logger("myapp.submodule.component")
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            # Log from different levels
            parent_logger.info("Parent message")
            child_logger.info("Child message")
            grandchild_logger.info("Grandchild message")
            
            output = mock_stderr.getvalue()
            
            # All messages should be captured
            self.assertIn("Parent message", output)
            self.assertIn("Child message", output)
            self.assertIn("Grandchild message", output)
            
            # Logger names should be preserved
            self.assertIn("myapp", output)
            self.assertIn("myapp.submodule", output)
            self.assertIn("myapp.submodule.component", output)
    
    def test_log_level_filtering(self):
        """Test that log level filtering works correctly."""
        initialize_central_logging(
            log_level=logging.WARNING,  # Only WARNING and above
            enable_remote=False
        )
        
        logger = get_logger("test.filtering")
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            # Log at various levels
            logger.debug("Debug message - should not appear")
            logger.info("Info message - should not appear")
            logger.warning("Warning message - should appear")
            logger.error("Error message - should appear")
            logger.critical("Critical message - should appear")
            
            output = mock_stderr.getvalue()
            
            # Check filtering
            self.assertNotIn("Debug message", output)
            self.assertNotIn("Info message", output)
            self.assertIn("Warning message", output)
            self.assertIn("Error message", output)
            self.assertIn("Critical message", output)
    
    def test_multiple_module_simulation(self):
        """Simulate multiple modules logging to verify central service handles all."""
        initialize_central_logging(
            log_level=logging.INFO,
            enable_remote=False
        )
        
        # Simulate different modules
        modules = [
            "services.email_processor",
            "services.gmail_fetcher",
            "clients.account_client",
            "utils.helpers",
            "models.email"
        ]
        
        loggers = {name: get_logger(name) for name in modules}
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            # Each module logs
            for name, logger in loggers.items():
                logger.info(f"Message from {name}")
            
            output = mock_stderr.getvalue()
            
            # Verify all messages were captured
            for name in modules:
                self.assertIn(f"Message from {name}", output)
                self.assertIn(name, output)
    
    def test_exception_logging(self):
        """Test that exceptions are properly logged through central service."""
        initialize_central_logging(
            log_level=logging.INFO,
            enable_remote=False
        )
        
        logger = get_logger("test.exceptions")
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            try:
                # Cause an exception
                raise ValueError("Test exception")
            except ValueError:
                logger.exception("An error occurred")
            
            output = mock_stderr.getvalue()
            
            # Check that exception was logged
            self.assertIn("An error occurred", output)
            self.assertIn("ValueError", output)
            self.assertIn("Test exception", output)
            self.assertIn("Traceback", output)
    
    @patch.dict(os.environ, {
        "LOGS_COLLECTOR_API": "http://test-api.example.com",
        "LOGS_COLLECTOR_TOKEN": "test-token",
        "APP_NAME": "test-app"
    })
    def test_environment_based_configuration(self):
        """Test that environment variables properly configure remote logging."""
        # Initialize with environment variables
        service = initialize_central_logging(
            log_level=logging.INFO,
            enable_remote=True
        )
        
        # Verify remote logging is enabled
        self.assertTrue(service.enable_remote)
        self.assertEqual(service.app_name, "test-app")
        
        # Verify logging still works
        logger = get_logger("test.env")
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            logger.info("Environment-based logging test")
            
            output = mock_stderr.getvalue()
            self.assertIn("Environment-based logging test", output)
    
    def test_concurrent_logging(self):
        """Test that central logging handles concurrent log messages correctly."""
        import threading
        
        initialize_central_logging(
            log_level=logging.INFO,
            enable_remote=False
        )
        
        messages_logged = []
        
        def log_messages(thread_id, count):
            """Log messages from a thread."""
            logger = get_logger(f"thread.{thread_id}")
            for i in range(count):
                msg = f"Thread {thread_id} message {i}"
                logger.info(msg)
                messages_logged.append(msg)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_messages, args=(i, 10))
            threads.append(thread)
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            # Start all threads
            for thread in threads:
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            output = mock_stderr.getvalue()
            
            # Verify all messages were logged
            self.assertEqual(len(messages_logged), 50)  # 5 threads * 10 messages
            
            # Spot check some messages
            self.assertIn("Thread 0 message 0", output)
            self.assertIn("Thread 4 message 9", output)


class TestLoggingCompliance(unittest.TestCase):
    """Test to ensure new modules follow logging compliance."""
    
    def test_api_service_uses_central_logging(self):
        """Verify that api_service.py uses centralized logging."""
        import api_service
        
        # Check that the module has the correct imports
        self.assertTrue(hasattr(api_service, 'get_logger'))
        self.assertTrue(hasattr(api_service, 'initialize_central_logging'))
        
    def test_central_logger_module_exists(self):
        """Verify that the central logger module exists and works."""
        from utils import logger
        
        # Check required functions exist
        self.assertTrue(hasattr(logger, 'get_logger'))
        self.assertTrue(hasattr(logger, 'initialize_central_logging'))
        self.assertTrue(hasattr(logger, 'shutdown_logging'))
        self.assertTrue(hasattr(logger, 'get_central_service'))
    
    def test_logging_service_exists(self):
        """Verify that CentralLoggingService exists."""
        from services.logging_service import CentralLoggingService, LogLevel
        
        # Check class exists
        self.assertIsNotNone(CentralLoggingService)
        self.assertIsNotNone(LogLevel)
        
        # Check required methods exist
        required_methods = ['debug', 'info', 'warning', 'error', 'critical', 'log', 'shutdown']
        for method in required_methods:
            self.assertTrue(hasattr(CentralLoggingService, method))


if __name__ == "__main__":
    unittest.main()
