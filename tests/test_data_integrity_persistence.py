"""
Tests for data integrity and persistence of emails_categorized and emails_skipped.

Based on BDD scenarios from specs/DRAFT-data-integrity-persistence.md:
- Scenario: emails_categorized persists to database
- Scenario: emails_skipped persists to database
- Scenario: Multiple increments persist as cumulative total
- Scenario: Large values persist correctly

These tests verify that:
1. Values persist through database save/load cycles
2. Accumulated increments persist as cumulative totals
3. Large values (1000+) persist correctly
4. Session close/reopen does not lose data
"""
import shutil
import tempfile
import unittest
from datetime import datetime

from sqlalchemy.orm import Session

from models.database import ProcessingRun, init_database, get_session


class TestSingleValuePersistence(unittest.TestCase):
    """
    Scenario: emails_categorized persists to database
    Scenario: emails_skipped persists to database

    Given a ProcessingRun record with emails_categorized = 42
    When the record is saved to the database
    And the database session is closed
    And a new session loads the record by ID
    Then emails_categorized equals 42
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_persistence.db"
        cls.engine = init_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_emails_categorized_persists_through_session_close(self):
        """
        Test that emails_categorized value persists through session close/reopen.

        Simulates application restart by:
        1. Creating and saving a record
        2. Closing the session
        3. Opening a new session
        4. Loading the record by ID
        5. Verifying the value persisted
        """
        # Arrange: Create session and record
        session = get_session(self.engine)
        run = ProcessingRun(
            email_address="test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_categorized=42,
            emails_skipped=0
        )

        # Act: Save and commit
        session.add(run)
        session.commit()
        run_id = run.id

        # Close session (simulate app restart)
        session.close()

        # Open new session and load record
        new_session = get_session(self.engine)
        retrieved_run = new_session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: emails_categorized value persisted
        self.assertIsNotNone(
            retrieved_run,
            "ProcessingRun should be retrievable after session close"
        )
        self.assertEqual(
            retrieved_run.emails_categorized,
            42,
            f"emails_categorized should persist as 42, got {retrieved_run.emails_categorized}"
        )

        # Cleanup
        new_session.close()

    def test_emails_skipped_persists_through_session_close(self):
        """
        Test that emails_skipped value persists through session close/reopen.

        Simulates application restart by:
        1. Creating and saving a record
        2. Closing the session
        3. Opening a new session
        4. Loading the record by ID
        5. Verifying the value persisted
        """
        # Arrange: Create session and record
        session = get_session(self.engine)
        run = ProcessingRun(
            email_address="test2@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_categorized=0,
            emails_skipped=17
        )

        # Act: Save and commit
        session.add(run)
        session.commit()
        run_id = run.id

        # Close session (simulate app restart)
        session.close()

        # Open new session and load record
        new_session = get_session(self.engine)
        retrieved_run = new_session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: emails_skipped value persisted
        self.assertIsNotNone(
            retrieved_run,
            "ProcessingRun should be retrievable after session close"
        )
        self.assertEqual(
            retrieved_run.emails_skipped,
            17,
            f"emails_skipped should persist as 17, got {retrieved_run.emails_skipped}"
        )

        # Cleanup
        new_session.close()

    def test_both_fields_persist_independently(self):
        """
        Test that both emails_categorized and emails_skipped persist independently.

        Verifies that setting both fields to non-zero values persists correctly.
        """
        # Arrange: Create session and record with both fields set
        session = get_session(self.engine)
        run = ProcessingRun(
            email_address="test3@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_categorized=42,
            emails_skipped=17
        )

        # Act: Save and commit
        session.add(run)
        session.commit()
        run_id = run.id

        # Close session
        session.close()

        # Open new session and load record
        new_session = get_session(self.engine)
        retrieved_run = new_session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: Both values persisted independently
        self.assertEqual(
            retrieved_run.emails_categorized,
            42,
            "emails_categorized should persist independently"
        )
        self.assertEqual(
            retrieved_run.emails_skipped,
            17,
            "emails_skipped should persist independently"
        )

        # Cleanup
        new_session.close()


class TestCumulativeIncrementsPersistence(unittest.TestCase):
    """
    Scenario: Multiple increments persist as cumulative total

    Given a ProcessingRun record
    When multiple updates accumulate the count
    And the record is saved to the database
    And the session is closed and reopened
    Then the cumulative total persists correctly
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_cumulative.db"
        cls.engine = init_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_cumulative_categorized_increments_persist(self):
        """
        Test that cumulative categorized increments persist as total.

        Simulates multiple increment operations followed by persistence:
        1. Start with 0
        2. Add 10 (total: 10)
        3. Add 5 (total: 15)
        4. Save and close session
        5. Reopen and verify total is 15
        """
        # Arrange: Create session and record
        session = get_session(self.engine)
        run = ProcessingRun(
            email_address="cumulative@example.com",
            start_time=datetime.utcnow(),
            state="processing",
            emails_categorized=0,
            emails_skipped=0
        )
        session.add(run)
        session.commit()

        # Act: Simulate multiple increments
        run.emails_categorized += 10  # First increment
        session.commit()

        run.emails_categorized += 5   # Second increment
        session.commit()
        run_id = run.id

        # Close session
        session.close()

        # Open new session and load record
        new_session = get_session(self.engine)
        retrieved_run = new_session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: Cumulative total persisted
        self.assertIsNotNone(
            retrieved_run,
            "ProcessingRun should be retrievable after session close"
        )
        self.assertEqual(
            retrieved_run.emails_categorized,
            15,
            f"Cumulative total should be 15, got {retrieved_run.emails_categorized}"
        )

        # Cleanup
        new_session.close()

    def test_cumulative_skipped_increments_persist(self):
        """
        Test that cumulative skipped increments persist as total.

        Simulates multiple increment operations followed by persistence:
        1. Start with 0
        2. Add 3 (total: 3)
        3. Add 7 (total: 10)
        4. Save and close session
        5. Reopen and verify total is 10
        """
        # Arrange: Create session and record
        session = get_session(self.engine)
        run = ProcessingRun(
            email_address="cumulative2@example.com",
            start_time=datetime.utcnow(),
            state="processing",
            emails_categorized=0,
            emails_skipped=0
        )
        session.add(run)
        session.commit()

        # Act: Simulate multiple increments
        run.emails_skipped += 3  # First increment
        session.commit()

        run.emails_skipped += 7  # Second increment
        session.commit()
        run_id = run.id

        # Close session
        session.close()

        # Open new session and load record
        new_session = get_session(self.engine)
        retrieved_run = new_session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: Cumulative total persisted
        self.assertIsNotNone(
            retrieved_run,
            "ProcessingRun should be retrievable after session close"
        )
        self.assertEqual(
            retrieved_run.emails_skipped,
            10,
            f"Cumulative total should be 10, got {retrieved_run.emails_skipped}"
        )

        # Cleanup
        new_session.close()

    def test_mixed_cumulative_increments_persist_independently(self):
        """
        Test that mixed increments to both fields persist independently.

        Verifies that incrementing both fields doesn't cause interference.
        """
        # Arrange: Create session and record
        session = get_session(self.engine)
        run = ProcessingRun(
            email_address="mixed@example.com",
            start_time=datetime.utcnow(),
            state="processing",
            emails_categorized=0,
            emails_skipped=0
        )
        session.add(run)
        session.commit()

        # Act: Simulate mixed increments
        run.emails_categorized += 10
        run.emails_skipped += 3
        session.commit()

        run.emails_categorized += 5
        run.emails_skipped += 7
        session.commit()
        run_id = run.id

        # Close session
        session.close()

        # Open new session and load record
        new_session = get_session(self.engine)
        retrieved_run = new_session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: Both cumulative totals persisted independently
        self.assertIsNotNone(
            retrieved_run,
            "ProcessingRun should be retrievable after session close"
        )
        self.assertEqual(
            retrieved_run.emails_categorized,
            15,
            "Categorized cumulative total should be 15"
        )
        self.assertEqual(
            retrieved_run.emails_skipped,
            10,
            "Skipped cumulative total should be 10"
        )

        # Cleanup
        new_session.close()


class TestLargeValuesPersistence(unittest.TestCase):
    """
    Scenario: Large values persist correctly

    Given a ProcessingRun record with large count values (1000+)
    When the record is saved to the database
    And the session is closed and reopened
    Then the large values persist without data loss or overflow
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_large_values.db"
        cls.engine = init_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_large_categorized_value_persists(self):
        """
        Test that large emails_categorized value (1000+) persists correctly.

        Verifies no overflow or truncation for large counts.
        """
        # Arrange: Create session and record with large value
        session = get_session(self.engine)
        large_value = 9999
        run = ProcessingRun(
            email_address="large@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_categorized=large_value,
            emails_skipped=0
        )

        # Act: Save and commit
        session.add(run)
        session.commit()
        run_id = run.id

        # Close session
        session.close()

        # Open new session and load record
        new_session = get_session(self.engine)
        retrieved_run = new_session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: Large value persisted without overflow
        self.assertIsNotNone(
            retrieved_run,
            "ProcessingRun should be retrievable after session close"
        )
        self.assertEqual(
            retrieved_run.emails_categorized,
            large_value,
            f"Large value should persist as {large_value}, got {retrieved_run.emails_categorized}"
        )

        # Cleanup
        new_session.close()

    def test_large_skipped_value_persists(self):
        """
        Test that large emails_skipped value (1000+) persists correctly.

        Verifies no overflow or truncation for large counts.
        """
        # Arrange: Create session and record with large value
        session = get_session(self.engine)
        large_value = 8888
        run = ProcessingRun(
            email_address="large2@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_categorized=0,
            emails_skipped=large_value
        )

        # Act: Save and commit
        session.add(run)
        session.commit()
        run_id = run.id

        # Close session
        session.close()

        # Open new session and load record
        new_session = get_session(self.engine)
        retrieved_run = new_session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: Large value persisted without overflow
        self.assertIsNotNone(
            retrieved_run,
            "ProcessingRun should be retrievable after session close"
        )
        self.assertEqual(
            retrieved_run.emails_skipped,
            large_value,
            f"Large value should persist as {large_value}, got {retrieved_run.emails_skipped}"
        )

        # Cleanup
        new_session.close()

    def test_very_large_cumulative_value_persists(self):
        """
        Test that very large cumulative values (10000+) persist correctly.

        Simulates high-volume email processing scenario.
        """
        # Arrange: Create session and record
        session = get_session(self.engine)
        run = ProcessingRun(
            email_address="verylarge@example.com",
            start_time=datetime.utcnow(),
            state="processing",
            emails_categorized=0,
            emails_skipped=0
        )
        session.add(run)
        session.commit()

        # Act: Simulate large batch increments
        run.emails_categorized += 5000
        session.commit()

        run.emails_categorized += 7500
        session.commit()

        run.emails_skipped += 2500
        session.commit()
        run_id = run.id

        # Close session
        session.close()

        # Open new session and load record
        new_session = get_session(self.engine)
        retrieved_run = new_session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: Very large cumulative values persisted correctly
        self.assertIsNotNone(
            retrieved_run,
            "ProcessingRun should be retrievable after session close"
        )
        self.assertEqual(
            retrieved_run.emails_categorized,
            12500,
            "Very large cumulative categorized value should persist"
        )
        self.assertEqual(
            retrieved_run.emails_skipped,
            2500,
            "Large cumulative skipped value should persist"
        )

        # Cleanup
        new_session.close()


class TestZeroValuesPersistence(unittest.TestCase):
    """
    Edge case: Zero values persist correctly (not NULL)

    Given a ProcessingRun record with emails_categorized = 0
    When the record is saved to the database
    And the session is closed and reopened
    Then emails_categorized equals 0 (not NULL)
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_zero_values.db"
        cls.engine = init_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_zero_values_persist_as_zero_not_null(self):
        """
        Test that zero values persist as integer 0, not NULL.

        Ensures default initialization is correctly persisted.
        """
        # Arrange: Create session and record with explicit zeros
        session = get_session(self.engine)
        run = ProcessingRun(
            email_address="zero@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_categorized=0,
            emails_skipped=0
        )

        # Act: Save and commit
        session.add(run)
        session.commit()
        run_id = run.id

        # Close session
        session.close()

        # Open new session and load record
        new_session = get_session(self.engine)
        retrieved_run = new_session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: Zero values persisted (not None)
        self.assertIsNotNone(
            retrieved_run.emails_categorized,
            "emails_categorized should not be NULL"
        )
        self.assertEqual(
            retrieved_run.emails_categorized,
            0,
            "emails_categorized should be 0"
        )
        self.assertIsNotNone(
            retrieved_run.emails_skipped,
            "emails_skipped should not be NULL"
        )
        self.assertEqual(
            retrieved_run.emails_skipped,
            0,
            "emails_skipped should be 0"
        )

        # Cleanup
        new_session.close()


if __name__ == '__main__':
    unittest.main()
