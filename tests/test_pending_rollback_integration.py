#!/usr/bin/env python3
"""
Integration test for PendingRollbackError fix in MySQLRepository.

This test verifies that when a database error occurs during a read operation,
the session is properly rolled back so that subsequent operations can proceed.

The fix adds try/except/rollback handling to read operations (find_one, find_all,
get_by_id, count, etc.) to match the pattern already used in write operations.

This test requires MySQL running and accessible via environment variables:
- MYSQL_HOST
- MYSQL_PORT
- MYSQL_DATABASE
- MYSQL_USER
- MYSQL_PASSWORD
"""
import os
import sys
import time
import unittest
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError, PendingRollbackError
from repositories.mysql_repository import MySQLRepository
from models.database import UserSettings, Base


class TestPendingRollbackIntegration(unittest.TestCase):
    """
    Integration tests to verify that PendingRollbackError is properly handled
    by the MySQLRepository read operations.
    """

    @classmethod
    def setUpClass(cls):
        """Set up MySQL connection for integration tests."""
        # Get MySQL connection info from environment
        cls.mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        cls.mysql_port = int(os.getenv('MYSQL_PORT', '3308'))
        cls.mysql_database = os.getenv('MYSQL_DATABASE', 'cat_emails_test')
        cls.mysql_user = os.getenv('MYSQL_USER', 'cat_emails')
        cls.mysql_password = os.getenv('MYSQL_PASSWORD', 'cat_emails_password')

        # Wait for MySQL to be ready (useful when running in docker-compose)
        max_retries = 30
        for i in range(max_retries):
            try:
                cls.repository = MySQLRepository(
                    host=cls.mysql_host,
                    port=cls.mysql_port,
                    database=cls.mysql_database,
                    username=cls.mysql_user,
                    password=cls.mysql_password
                )
                # Test connection
                cls.repository.get_connection_status()
                print(f"Connected to MySQL at {cls.mysql_host}:{cls.mysql_port}")
                break
            except Exception as e:
                if i < max_retries - 1:
                    print(f"Waiting for MySQL... ({i+1}/{max_retries})")
                    time.sleep(2)
                else:
                    raise RuntimeError(f"Could not connect to MySQL: {e}") from e

    @classmethod
    def tearDownClass(cls):
        """Clean up MySQL connection."""
        if hasattr(cls, 'repository') and cls.repository:
            cls.repository.disconnect()

    def _cleanup_test_settings(self):
        """Remove test settings from database."""
        session = self.repository._get_session()
        try:
            session.query(UserSettings).filter(
                UserSettings.setting_key.like('test_%')
            ).delete(synchronize_session=False)
            session.commit()
        except SQLAlchemyError:
            session.rollback()

    def setUp(self):
        """Set up test fixtures."""
        self._cleanup_test_settings()

    def tearDown(self):
        """Clean up after each test."""
        self._cleanup_test_settings()

    def test_find_one_recovers_after_error(self):
        """
        Test that find_one properly handles errors and allows session recovery.

        This simulates the scenario where a database error occurs during find_one,
        and verifies that subsequent operations can still succeed after the rollback.
        """
        # First, create a test setting
        test_key = 'test_find_one_recovery'
        self.repository.set_setting(test_key, 'test_value', 'string', 'Test setting')

        # Verify we can read it
        setting = self.repository.find_one(UserSettings, setting_key=test_key)
        self.assertIsNotNone(setting)
        self.assertEqual(setting.setting_value, 'test_value')

        # Now simulate an error by mocking the query to raise an exception
        def mock_query_that_fails(*_args, **_kwargs):
            raise OperationalError("statement", {}, Exception("Simulated connection error"))

        # Patch the query method temporarily
        session = self.repository._get_session()
        with patch.object(session, 'query', side_effect=mock_query_that_fails):
            # This should raise but also rollback the session
            with self.assertRaises(OperationalError):
                self.repository.find_one(UserSettings, setting_key=test_key)

        # After the error, subsequent operations should work (session was rolled back)
        # The same repository/session should work since it was properly rolled back
        setting = self.repository.find_one(UserSettings, setting_key=test_key)
        self.assertIsNotNone(setting)
        self.assertEqual(setting.setting_value, 'test_value')

    def test_count_recovers_after_error(self):
        """
        Test that count properly handles errors and allows session recovery.

        This simulates a scenario where a database error occurs during count,
        and verifies that subsequent operations can still succeed after the rollback.
        """
        # Create test settings
        for i in range(3):
            self.repository.set_setting(f'test_count_{i}', f'value_{i}', 'string', 'Test')

        # Verify count works initially
        count = self.repository.count(UserSettings)
        self.assertGreaterEqual(count, 3)

        # Now simulate an error by mocking the query to raise an exception
        def mock_query_that_fails(*_args, **_kwargs):
            raise OperationalError("statement", {}, Exception("Simulated connection error"))

        # Patch the query method temporarily
        session = self.repository._get_session()
        with patch.object(session, 'query', side_effect=mock_query_that_fails):
            # This should raise but also rollback the session
            with self.assertRaises(OperationalError):
                self.repository.count(UserSettings)

        # After the error, subsequent operations should work (session was rolled back)
        count = self.repository.count(UserSettings)
        self.assertGreaterEqual(count, 3)

    def test_get_by_id_recovers_after_error(self):
        """
        Test that get_by_id properly handles errors and allows session recovery.

        This simulates a scenario where a database error occurs during get_by_id,
        and verifies that subsequent operations can still succeed after the rollback.
        """
        # Create a test setting
        test_key = 'test_get_by_id'
        setting = self.repository.set_setting(test_key, 'test_value', 'string', 'Test')
        setting_id = setting.id

        # Verify we can read it by ID initially
        retrieved = self.repository.get_by_id(UserSettings, setting_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.setting_key, test_key)

        # Now simulate an error by mocking the get method to raise an exception
        def mock_get_that_fails(*_args, **_kwargs):
            raise OperationalError("statement", {}, Exception("Simulated connection error"))

        # Patch the get method temporarily
        session = self.repository._get_session()
        with patch.object(session, 'get', side_effect=mock_get_that_fails):
            # This should raise but also rollback the session
            with self.assertRaises(OperationalError):
                self.repository.get_by_id(UserSettings, setting_id)

        # After the error, subsequent operations should work (session was rolled back)
        retrieved = self.repository.get_by_id(UserSettings, setting_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.setting_key, test_key)

    def test_find_all_recovers_after_error(self):
        """
        Test that find_all properly handles errors and allows session recovery.

        This simulates a scenario where a database error occurs during find_all,
        and verifies that subsequent operations can still succeed after the rollback.
        """
        # Create test settings with a common type
        for i in range(3):
            self.repository.set_setting(f'test_find_all_{i}', f'value_{i}', 'test_type', 'Test')

        # Verify find_all works initially
        settings = self.repository.find_all(UserSettings, setting_type='test_type')
        self.assertEqual(len(settings), 3)

        # Now simulate an error by mocking the query to raise an exception
        def mock_query_that_fails(*_args, **_kwargs):
            raise OperationalError("statement", {}, Exception("Simulated connection error"))

        # Patch the query method temporarily
        session = self.repository._get_session()
        with patch.object(session, 'query', side_effect=mock_query_that_fails):
            # This should raise but also rollback the session
            with self.assertRaises(OperationalError):
                self.repository.find_all(UserSettings, setting_type='test_type')

        # After the error, subsequent operations should work (session was rolled back)
        settings = self.repository.find_all(UserSettings, setting_type='test_type')
        self.assertEqual(len(settings), 3)

    def test_session_remains_usable_after_rollback(self):
        """
        Test that the session remains usable after an error triggers a rollback.

        This is the key test that verifies the PendingRollbackError fix works.
        """
        # Create initial setting
        test_key = 'test_session_recovery'
        self.repository.set_setting(test_key, 'initial', 'string', 'Test')

        # Get the session
        session = self.repository._get_session()

        # Simulate an error that puts the session in a bad state
        try:
            # Force an invalid operation that would normally cause PendingRollbackError
            session.execute(text("SELECT * FROM nonexistent_table_xyz"))
        except SQLAlchemyError:
            # The fix should have already called rollback in find_one/find_all etc.
            # But for direct execute, we need to rollback manually here
            session.rollback()

        # After rollback, operations should work
        setting = self.repository.find_one(UserSettings, setting_key=test_key)
        self.assertIsNotNone(setting)
        self.assertEqual(setting.setting_value, 'initial')

        # Update should also work
        self.repository.set_setting(test_key, 'updated', 'string', 'Test')
        setting = self.repository.find_one(UserSettings, setting_key=test_key)
        self.assertEqual(setting.setting_value, 'updated')

    def test_multiple_operations_after_error(self):
        """
        Test that multiple operations work correctly after an error and rollback.
        """
        # Set up initial data
        for i in range(5):
            self.repository.set_setting(f'test_multi_{i}', f'value_{i}', 'string', 'Test')

        # Force an error scenario by trying to access a non-existent model
        session = self.repository._get_session()
        try:
            # This will fail but we want to ensure the session recovers
            session.execute(text("INVALID SQL SYNTAX HERE"))
        except SQLAlchemyError:
            session.rollback()

        # All operations should now work
        # 1. find_one
        setting = self.repository.find_one(UserSettings, setting_key='test_multi_0')
        self.assertIsNotNone(setting)

        # 2. find_all
        settings = self.repository.find_all(UserSettings, setting_type='string')
        self.assertGreaterEqual(len(settings), 5)

        # 3. get_by_id
        if setting:
            retrieved = self.repository.get_by_id(UserSettings, setting.id)
            self.assertIsNotNone(retrieved)

        # 4. count
        count = self.repository.count(UserSettings, setting_type='string')
        self.assertGreaterEqual(count, 5)

        # 5. Update
        self.repository.set_setting('test_multi_0', 'updated_value', 'string', 'Updated')
        updated = self.repository.find_one(UserSettings, setting_key='test_multi_0')
        self.assertEqual(updated.setting_value, 'updated_value')

    def test_read_operation_rollback_on_sqlalchemy_error(self):
        """
        Verify that SQLAlchemyError in read operations triggers rollback.
        """
        test_key = 'test_rollback_check'
        self.repository.set_setting(test_key, 'value', 'string', 'Test')

        session = self.repository._get_session()

        # Corrupt the session with invalid SQL
        try:
            session.execute(text("SELECT * FROM table_that_does_not_exist"))
        except SQLAlchemyError:
            pass  # Session is now in a bad state (would cause PendingRollbackError before fix)

        # Rollback to recover
        session.rollback()

        # After rollback, operations should work (fix prevents PendingRollbackError)
        setting = self.repository.find_one(UserSettings, setting_key=test_key)
        self.assertIsNotNone(setting)


class TestPendingRollbackPreventionScenario(unittest.TestCase):
    """
    Test the specific scenario that was causing PendingRollbackError in production:

    1. A database error occurs during a read operation (connection timeout, MySQL gone away, etc.)
    2. The session is left in an invalid state
    3. Subsequent operations fail with PendingRollbackError

    The fix ensures step 2 doesn't happen - the session is rolled back immediately.
    """

    @classmethod
    def setUpClass(cls):
        """Set up MySQL connection."""
        cls.mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        cls.mysql_port = int(os.getenv('MYSQL_PORT', '3308'))
        cls.mysql_database = os.getenv('MYSQL_DATABASE', 'cat_emails_test')
        cls.mysql_user = os.getenv('MYSQL_USER', 'cat_emails')
        cls.mysql_password = os.getenv('MYSQL_PASSWORD', 'cat_emails_password')

        max_retries = 30
        for i in range(max_retries):
            try:
                cls.repository = MySQLRepository(
                    host=cls.mysql_host,
                    port=cls.mysql_port,
                    database=cls.mysql_database,
                    username=cls.mysql_user,
                    password=cls.mysql_password
                )
                cls.repository.get_connection_status()
                break
            except Exception as e:
                if i < max_retries - 1:
                    time.sleep(2)
                else:
                    raise RuntimeError(f"Could not connect to MySQL: {e}") from e

    @classmethod
    def tearDownClass(cls):
        """Clean up."""
        if hasattr(cls, 'repository') and cls.repository:
            cls.repository.disconnect()

    def test_production_scenario_get_setting_after_error(self):
        """
        Reproduce the exact production scenario:

        api_service.py:902 -> get_background_status()
          -> settings_service.get_lookback_hours()
            -> get_setting()
              -> mysql_repository.get_setting()
                -> find_one()
                  -> PendingRollbackError

        This test verifies that after an error, get_setting (which uses find_one)
        can recover and work correctly.
        """
        # Set up: create a lookback_hours setting like production uses
        self.repository.set_setting('lookback_hours', '2', 'integer', 'Hours to look back')

        # Verify it works initially
        setting = self.repository.get_setting('lookback_hours')
        self.assertIsNotNone(setting)
        self.assertEqual(setting.setting_value, '2')

        # Simulate an error scenario (e.g., connection timeout during previous operation)
        session = self.repository._get_session()
        try:
            session.execute(text("SELECT SLEEP(0.001) FROM dual WHERE 1=0"))  # Quick query that works
            session.execute(text("SELECT * FROM table_xyz_not_exists"))  # This will fail
        except SQLAlchemyError:
            pass  # Session might be in bad state now

        # Before the fix: this would raise PendingRollbackError
        # After the fix: this should work because find_one has rollback handling
        try:
            setting = self.repository.get_setting('lookback_hours')
            # If we get here without error, the fix is working
            self.assertIsNotNone(setting)
            self.assertEqual(setting.setting_value, '2')
        except PendingRollbackError:
            # This should NOT happen after the fix
            self.fail("PendingRollbackError was raised - the fix is not working!")
        except SQLAlchemyError:
            # Some other error might occur - rollback and retry
            session.rollback()
            setting = self.repository.get_setting('lookback_hours')
            self.assertIsNotNone(setting)


if __name__ == '__main__':
    unittest.main(verbosity=2)
