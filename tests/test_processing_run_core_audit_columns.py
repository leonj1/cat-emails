"""
Tests for ProcessingRun Core Audit Fields Database Columns.

Based on BDD scenarios from tests/bdd/core_fields_audit_records.feature:
- Scenario: ProcessingRun model includes emails_categorized column
- Scenario: ProcessingRun model includes emails_skipped column

These tests follow TDD approach (Red phase) - tests will FAIL until the
ProcessingRun model is updated with the required audit count columns.

The implementation should add to models/database.py ProcessingRun class:
    emails_categorized = Column(Integer, default=0, nullable=False)
    emails_skipped = Column(Integer, default=0, nullable=False)
"""
import shutil
import tempfile
import unittest
from datetime import datetime

from sqlalchemy import Integer, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from models.database import ProcessingRun, Base, init_database, get_session


class TestProcessingRunModelEmailsCategorizedColumn(unittest.TestCase):
    """
    Scenario: ProcessingRun model includes emails_categorized column

    Given a processing run is initiated for an account
    When the processing completes with some emails categorized
    Then the processing run record stores the emails_categorized count
    And the count reflects the actual number of emails that were categorized
    """

    def test_processing_run_has_emails_categorized_attribute(self):
        """
        Test that ProcessingRun model has emails_categorized attribute.

        The implementation should add to ProcessingRun class:
            emails_categorized = Column(Integer, default=0, nullable=False)
        """
        # Assert: ProcessingRun model has emails_categorized attribute
        self.assertTrue(
            hasattr(ProcessingRun, 'emails_categorized'),
            "ProcessingRun model should have 'emails_categorized' attribute"
        )

    def test_emails_categorized_column_is_integer_type(self):
        """
        Test that emails_categorized column is Integer type.

        The implementation should define:
            emails_categorized = Column(Integer, ...)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_categorized column exists and is Integer
        self.assertIn(
            'emails_categorized',
            columns,
            "emails_categorized column should exist in ProcessingRun table"
        )
        column = columns['emails_categorized']
        self.assertIsInstance(
            column.type,
            Integer,
            f"emails_categorized should be Integer type, got {type(column.type)}"
        )

    def test_emails_categorized_column_default_is_zero(self):
        """
        Test that emails_categorized column defaults to 0.

        The implementation should define:
            emails_categorized = Column(Integer, default=0, ...)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_categorized has default of 0
        column = columns['emails_categorized']
        self.assertIsNotNone(
            column.default,
            "emails_categorized should have a default value"
        )
        self.assertEqual(
            column.default.arg,
            0,
            f"emails_categorized default should be 0, got {column.default.arg}"
        )

    def test_emails_categorized_column_not_nullable(self):
        """
        Test that emails_categorized column does not accept null values.

        The implementation should define:
            emails_categorized = Column(Integer, ..., nullable=False)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_categorized is not nullable
        column = columns['emails_categorized']
        self.assertFalse(
            column.nullable,
            "emails_categorized should not be nullable"
        )


class TestProcessingRunModelEmailsSkippedColumn(unittest.TestCase):
    """
    Scenario: ProcessingRun model includes emails_skipped column

    Given a processing run is initiated for an account
    When the processing completes with some emails skipped
    Then the processing run record stores the emails_skipped count
    And the count reflects the actual number of emails that were skipped
    """

    def test_processing_run_has_emails_skipped_attribute(self):
        """
        Test that ProcessingRun model has emails_skipped attribute.

        The implementation should add to ProcessingRun class:
            emails_skipped = Column(Integer, default=0, nullable=False)
        """
        # Assert: ProcessingRun model has emails_skipped attribute
        self.assertTrue(
            hasattr(ProcessingRun, 'emails_skipped'),
            "ProcessingRun model should have 'emails_skipped' attribute"
        )

    def test_emails_skipped_column_is_integer_type(self):
        """
        Test that emails_skipped column is Integer type.

        The implementation should define:
            emails_skipped = Column(Integer, ...)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_skipped column exists and is Integer
        self.assertIn(
            'emails_skipped',
            columns,
            "emails_skipped column should exist in ProcessingRun table"
        )
        column = columns['emails_skipped']
        self.assertIsInstance(
            column.type,
            Integer,
            f"emails_skipped should be Integer type, got {type(column.type)}"
        )

    def test_emails_skipped_column_default_is_zero(self):
        """
        Test that emails_skipped column defaults to 0.

        The implementation should define:
            emails_skipped = Column(Integer, default=0, ...)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_skipped has default of 0
        column = columns['emails_skipped']
        self.assertIsNotNone(
            column.default,
            "emails_skipped should have a default value"
        )
        self.assertEqual(
            column.default.arg,
            0,
            f"emails_skipped default should be 0, got {column.default.arg}"
        )

    def test_emails_skipped_column_not_nullable(self):
        """
        Test that emails_skipped column does not accept null values.

        The implementation should define:
            emails_skipped = Column(Integer, ..., nullable=False)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_skipped is not nullable
        column = columns['emails_skipped']
        self.assertFalse(
            column.nullable,
            "emails_skipped should not be nullable"
        )


class TestProcessingRunStoresCoreAuditValues(unittest.TestCase):
    """
    Scenario: ProcessingRun record stores emails_categorized and emails_skipped values

    Given a ProcessingRun record is created with:
      | emails_categorized | 75  |
      | emails_skipped     | 25  |
    When the record is retrieved from the database
    Then the "emails_categorized" value should be 75
    And the "emails_skipped" value should be 25
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_core_audit_counts.db"
        cls.engine = init_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Set up a fresh session for each test."""
        self.session = get_session(self.engine)

    def tearDown(self):
        """Clean up session after each test."""
        self.session.rollback()
        self.session.close()

    def test_stores_custom_emails_categorized_value(self):
        """
        Test that ProcessingRun stores custom emails_categorized value.

        The implementation should allow setting custom values:
            run = ProcessingRun(..., emails_categorized=75)
        """
        # Arrange: Create a ProcessingRun with custom emails_categorized
        run = ProcessingRun(
            email_address="test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_categorized=75,
            emails_skipped=25
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Retrieve from database
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: emails_categorized value is correct
        self.assertEqual(
            retrieved_run.emails_categorized,
            75,
            f"emails_categorized should be 75, got {retrieved_run.emails_categorized}"
        )

    def test_stores_custom_emails_skipped_value(self):
        """
        Test that ProcessingRun stores custom emails_skipped value.

        The implementation should allow setting custom values:
            run = ProcessingRun(..., emails_skipped=25)
        """
        # Arrange: Create a ProcessingRun with custom emails_skipped
        run = ProcessingRun(
            email_address="test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_categorized=75,
            emails_skipped=25
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Retrieve from database
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: emails_skipped value is correct
        self.assertEqual(
            retrieved_run.emails_skipped,
            25,
            f"emails_skipped should be 25, got {retrieved_run.emails_skipped}"
        )

    def test_stores_both_core_audit_values_together(self):
        """
        Test that ProcessingRun stores both core audit values correctly together.

        Complete integration test for storing and retrieving both core audit columns.
        """
        # Arrange: Create a ProcessingRun with both custom core audit values
        expected_categorized = 75
        expected_skipped = 25

        run = ProcessingRun(
            email_address="test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_categorized=expected_categorized,
            emails_skipped=expected_skipped
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Clear session cache to force database read
        self.session.expire_all()

        # Retrieve from database
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: Both core audit values are correct
        self.assertIsNotNone(retrieved_run, "Retrieved run should not be None")
        self.assertEqual(
            retrieved_run.emails_categorized,
            expected_categorized,
            f"emails_categorized mismatch: expected {expected_categorized}, got {retrieved_run.emails_categorized}"
        )
        self.assertEqual(
            retrieved_run.emails_skipped,
            expected_skipped,
            f"emails_skipped mismatch: expected {expected_skipped}, got {retrieved_run.emails_skipped}"
        )


class TestProcessingRunDefaultsCoreAuditCountsToZero(unittest.TestCase):
    """
    Scenario: New ProcessingRun records default core audit counts to zero

    Given a ProcessingRun record is created without specifying core audit counts
    When the record is retrieved from the database
    Then the "emails_categorized" value should be 0
    And the "emails_skipped" value should be 0
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_core_audit_defaults.db"
        cls.engine = init_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Set up a fresh session for each test."""
        self.session = get_session(self.engine)

    def tearDown(self):
        """Clean up session after each test."""
        self.session.rollback()
        self.session.close()

    def test_emails_categorized_defaults_to_zero_in_database(self):
        """
        Test that emails_categorized defaults to 0 when not specified.

        The implementation should ensure:
            emails_categorized = Column(Integer, default=0, nullable=False)
        """
        # Arrange: Create a ProcessingRun WITHOUT specifying emails_categorized
        run = ProcessingRun(
            email_address="default_test@example.com",
            start_time=datetime.utcnow(),
            state="running"
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Clear session cache to force database read
        self.session.expire_all()

        # Retrieve from database
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: emails_categorized defaults to 0
        self.assertEqual(
            retrieved_run.emails_categorized,
            0,
            f"emails_categorized should default to 0, got {retrieved_run.emails_categorized}"
        )

    def test_emails_skipped_defaults_to_zero_in_database(self):
        """
        Test that emails_skipped defaults to 0 when not specified.

        The implementation should ensure:
            emails_skipped = Column(Integer, default=0, nullable=False)
        """
        # Arrange: Create a ProcessingRun WITHOUT specifying emails_skipped
        run = ProcessingRun(
            email_address="default_test@example.com",
            start_time=datetime.utcnow(),
            state="running"
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Clear session cache to force database read
        self.session.expire_all()

        # Retrieve from database
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: emails_skipped defaults to 0
        self.assertEqual(
            retrieved_run.emails_skipped,
            0,
            f"emails_skipped should default to 0, got {retrieved_run.emails_skipped}"
        )

    def test_all_core_audit_counts_default_to_zero_together(self):
        """
        Test that all core audit counts default to 0 when not specified.

        Complete integration test for default values on both core audit columns.
        """
        # Arrange: Create a ProcessingRun WITHOUT specifying any core audit counts
        run = ProcessingRun(
            email_address="default_test@example.com",
            start_time=datetime.utcnow(),
            state="running"
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Clear session cache to force database read
        self.session.expire_all()

        # Retrieve from database
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: All core audit counts default to 0
        self.assertIsNotNone(retrieved_run, "Retrieved run should not be None")
        self.assertEqual(
            retrieved_run.emails_categorized,
            0,
            f"emails_categorized should default to 0, got {retrieved_run.emails_categorized}"
        )
        self.assertEqual(
            retrieved_run.emails_skipped,
            0,
            f"emails_skipped should default to 0, got {retrieved_run.emails_skipped}"
        )


class TestProcessingRunCoreAuditCountReflectsActualCount(unittest.TestCase):
    """
    Tests that emails_categorized and emails_skipped counts reflect actual processing results.

    This validates the scenario requirements:
    - And the count reflects the actual number of emails that were categorized
    - And the count reflects the actual number of emails that were skipped
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_core_audit_actual.db"
        cls.engine = init_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Set up a fresh session for each test."""
        self.session = get_session(self.engine)

    def tearDown(self):
        """Clean up session after each test."""
        self.session.rollback()
        self.session.close()

    def test_emails_categorized_reflects_actual_count_after_processing(self):
        """
        Test that emails_categorized stores the actual count from processing.

        When processing completes with 42 emails categorized,
        the stored count should be exactly 42.
        """
        # Arrange: Simulate processing completion with 42 emails categorized
        actual_categorized = 42
        run = ProcessingRun(
            email_address="test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_categorized=actual_categorized
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id
        self.session.expire_all()
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: Count reflects actual processing result
        self.assertEqual(
            retrieved_run.emails_categorized,
            actual_categorized,
            f"emails_categorized should reflect actual count of {actual_categorized}, "
            f"got {retrieved_run.emails_categorized}"
        )

    def test_emails_skipped_reflects_actual_count_after_processing(self):
        """
        Test that emails_skipped stores the actual count from processing.

        When processing completes with 17 emails skipped,
        the stored count should be exactly 17.
        """
        # Arrange: Simulate processing completion with 17 emails skipped
        actual_skipped = 17
        run = ProcessingRun(
            email_address="test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_skipped=actual_skipped
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id
        self.session.expire_all()
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: Count reflects actual processing result
        self.assertEqual(
            retrieved_run.emails_skipped,
            actual_skipped,
            f"emails_skipped should reflect actual count of {actual_skipped}, "
            f"got {retrieved_run.emails_skipped}"
        )

    def test_processing_run_stores_large_counts(self):
        """
        Test that ProcessingRun can store large count values.

        Validates that the column can handle realistic batch sizes.
        """
        # Arrange: Large batch processing with many emails
        large_categorized = 10000
        large_skipped = 5000
        run = ProcessingRun(
            email_address="batch@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_categorized=large_categorized,
            emails_skipped=large_skipped
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id
        self.session.expire_all()
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: Large values are stored correctly
        self.assertEqual(
            retrieved_run.emails_categorized,
            large_categorized,
            f"emails_categorized should store large value {large_categorized}, "
            f"got {retrieved_run.emails_categorized}"
        )
        self.assertEqual(
            retrieved_run.emails_skipped,
            large_skipped,
            f"emails_skipped should store large value {large_skipped}, "
            f"got {retrieved_run.emails_skipped}"
        )


if __name__ == '__main__':
    unittest.main()
