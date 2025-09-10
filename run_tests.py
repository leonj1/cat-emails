#!/usr/bin/env python3
"""
Simple test runner script to run the email interface tests locally.
This avoids the need to set up the full environment with all dependencies.
"""

import sys
import os
import unittest

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Run specific test modules
    test_modules = [
        'tests.test_email_models',
        'tests.test_email_service',
        'tests.test_repeat_offender_service',
        'tests.test_repeat_offender_integration',
        'tests.test_email_deduplication_integration',
        'tests.test_processed_email_tracking',
    ]
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for module_name in test_modules:
        try:
            module = loader.loadTestsFromName(module_name)
            suite.addTests(module)
        except ImportError as e:
            print(f"Warning: Could not load {module_name}: {e}")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)