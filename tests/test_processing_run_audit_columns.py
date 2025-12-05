"""
Tests for ProcessingRun Audit Count Database Columns.

Based on BDD scenarios from tests/bdd/audit-counts-phase1-database.feature:
- Scenario: ProcessingRun model includes emails_reviewed column
- Scenario: ProcessingRun model includes emails_tagged column
- Scenario: ProcessingRun model includes emails_deleted column
- Scenario: ProcessingRun record stores custom audit count values
- Scenario: New ProcessingRun records default audit counts to zero

These tests follow TDD approach (Red phase) - tests will FAIL until the
ProcessingRun model is updated with the required audit count columns.

The implementation should add to models/database.py ProcessingRun class:
    emails_reviewed = Column(Integer, default=0, nullable=False)
    emails_tagged = Column(Integer, default=0, nullable=False)
    emails_deleted = Column(Integer, default=0, nullable=False)
"""
import shutil
import tempfile
import unittest
from datetime import datetime

from sqlalchemy import Integer, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from models.database import ProcessingRun, Base, init_database, get_session


class TestProcessingRunModelEmailsReviewedColumn(unittest.TestCase):
    """
    Scenario: ProcessingRun model includes emails_reviewed column

    When a new ProcessingRun record is created
    Then the record should have an "emails_reviewed" field
    And the "emails_reviewed" field should be an integer
    And the "emails_reviewed" field should default to 0
    And the "emails_reviewed" field should not accept null values
    """

    def test_processing_run_has_emails_reviewed_attribute(self):
        """
        Test that ProcessingRun model has emails_reviewed attribute.

        The implementation should add to ProcessingRun class:
            emails_reviewed = Column(Integer, default=0, nullable=False)
        """
        # Assert: ProcessingRun model has emails_reviewed attribute
        self.assertTrue(
            hasattr(ProcessingRun, 'emails_reviewed'),
            "ProcessingRun model should have 'emails_reviewed' attribute"
        )

    def test_emails_reviewed_column_is_integer_type(self):
        """
        Test that emails_reviewed column is Integer type.

        The implementation should define:
            emails_reviewed = Column(Integer, ...)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_reviewed column exists and is Integer
        self.assertIn(
            'emails_reviewed',
            columns,
            "emails_reviewed column should exist in ProcessingRun table"
        )
        column = columns['emails_reviewed']
        self.assertIsInstance(
            column.type,
            Integer,
            f"emails_reviewed should be Integer type, got {type(column.type)}"
        )

    def test_emails_reviewed_column_default_is_zero(self):
        """
        Test that emails_reviewed column defaults to 0.

        The implementation should define:
            emails_reviewed = Column(Integer, default=0, ...)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_reviewed has default of 0
        column = columns['emails_reviewed']
        self.assertIsNotNone(
            column.default,
            "emails_reviewed should have a default value"
        )
        self.assertEqual(
            column.default.arg,
            0,
            f"emails_reviewed default should be 0, got {column.default.arg}"
        )

    def test_emails_reviewed_column_not_nullable(self):
        """
        Test that emails_reviewed column does not accept null values.

        The implementation should define:
            emails_reviewed = Column(Integer, ..., nullable=False)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_reviewed is not nullable
        column = columns['emails_reviewed']
        self.assertFalse(
            column.nullable,
            "emails_reviewed should not be nullable"
        )


class TestProcessingRunModelEmailsTaggedColumn(unittest.TestCase):
    """
    Scenario: ProcessingRun model includes emails_tagged column

    When a new ProcessingRun record is created
    Then the record should have an "emails_tagged" field
    And the "emails_tagged" field should be an integer
    And the "emails_tagged" field should default to 0
    And the "emails_tagged" field should not accept null values
    """

    def test_processing_run_has_emails_tagged_attribute(self):
        """
        Test that ProcessingRun model has emails_tagged attribute.

        The implementation should add to ProcessingRun class:
            emails_tagged = Column(Integer, default=0, nullable=False)
        """
        # Assert: ProcessingRun model has emails_tagged attribute
        self.assertTrue(
            hasattr(ProcessingRun, 'emails_tagged'),
            "ProcessingRun model should have 'emails_tagged' attribute"
        )

    def test_emails_tagged_column_is_integer_type(self):
        """
        Test that emails_tagged column is Integer type.

        The implementation should define:
            emails_tagged = Column(Integer, ...)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_tagged column exists and is Integer
        self.assertIn(
            'emails_tagged',
            columns,
            "emails_tagged column should exist in ProcessingRun table"
        )
        column = columns['emails_tagged']
        self.assertIsInstance(
            column.type,
            Integer,
            f"emails_tagged should be Integer type, got {type(column.type)}"
        )

    def test_emails_tagged_column_default_is_zero(self):
        """
        Test that emails_tagged column defaults to 0.

        The implementation should define:
            emails_tagged = Column(Integer, default=0, ...)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_tagged has default of 0
        column = columns['emails_tagged']
        self.assertIsNotNone(
            column.default,
            "emails_tagged should have a default value"
        )
        self.assertEqual(
            column.default.arg,
            0,
            f"emails_tagged default should be 0, got {column.default.arg}"
        )

    def test_emails_tagged_column_not_nullable(self):
        """
        Test that emails_tagged column does not accept null values.

        The implementation should define:
            emails_tagged = Column(Integer, ..., nullable=False)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_tagged is not nullable
        column = columns['emails_tagged']
        self.assertFalse(
            column.nullable,
            "emails_tagged should not be nullable"
        )


class TestProcessingRunModelEmailsDeletedColumn(unittest.TestCase):
    """
    Scenario: ProcessingRun model includes emails_deleted column

    When a new ProcessingRun record is created
    Then the record should have an "emails_deleted" field
    And the "emails_deleted" field should be an integer
    And the "emails_deleted" field should default to 0
    And the "emails_deleted" field should not accept null values
    """

    def test_processing_run_has_emails_deleted_attribute(self):
        """
        Test that ProcessingRun model has emails_deleted attribute.

        The implementation should add to ProcessingRun class:
            emails_deleted = Column(Integer, default=0, nullable=False)
        """
        # Assert: ProcessingRun model has emails_deleted attribute
        self.assertTrue(
            hasattr(ProcessingRun, 'emails_deleted'),
            "ProcessingRun model should have 'emails_deleted' attribute"
        )

    def test_emails_deleted_column_is_integer_type(self):
        """
        Test that emails_deleted column is Integer type.

        The implementation should define:
            emails_deleted = Column(Integer, ...)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_deleted column exists and is Integer
        self.assertIn(
            'emails_deleted',
            columns,
            "emails_deleted column should exist in ProcessingRun table"
        )
        column = columns['emails_deleted']
        self.assertIsInstance(
            column.type,
            Integer,
            f"emails_deleted should be Integer type, got {type(column.type)}"
        )

    def test_emails_deleted_column_default_is_zero(self):
        """
        Test that emails_deleted column defaults to 0.

        The implementation should define:
            emails_deleted = Column(Integer, default=0, ...)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_deleted has default of 0
        column = columns['emails_deleted']
        self.assertIsNotNone(
            column.default,
            "emails_deleted should have a default value"
        )
        self.assertEqual(
            column.default.arg,
            0,
            f"emails_deleted default should be 0, got {column.default.arg}"
        )

    def test_emails_deleted_column_not_nullable(self):
        """
        Test that emails_deleted column does not accept null values.

        The implementation should define:
            emails_deleted = Column(Integer, ..., nullable=False)
        """
        # Arrange: Get column from ProcessingRun mapper
        mapper = inspect(ProcessingRun)
        columns = {col.key: col for col in mapper.columns}

        # Assert: emails_deleted is not nullable
        column = columns['emails_deleted']
        self.assertFalse(
            column.nullable,
            "emails_deleted should not be nullable"
        )


class TestProcessingRunStoresCustomAuditValues(unittest.TestCase):
    """
    Scenario: ProcessingRun record stores custom audit count values

    Given a ProcessingRun record is created with:
      | emails_reviewed | 150 |
      | emails_tagged   | 25  |
      | emails_deleted  | 42  |
    When the record is retrieved from the database
    Then the "emails_reviewed" value should be 150
    And the "emails_tagged" value should be 25
    And the "emails_deleted" value should be 42
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_audit_counts.db"
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

    def test_stores_custom_emails_reviewed_value(self):
        """
        Test that ProcessingRun stores custom emails_reviewed value.

        The implementation should allow setting custom values:
            run = ProcessingRun(..., emails_reviewed=150)
        """
        # Arrange: Create a ProcessingRun with custom emails_reviewed
        run = ProcessingRun(
            email_address="test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=150,
            emails_tagged=25,
            emails_deleted=42
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Retrieve from database
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: emails_reviewed value is correct
        self.assertEqual(
            retrieved_run.emails_reviewed,
            150,
            f"emails_reviewed should be 150, got {retrieved_run.emails_reviewed}"
        )

    def test_stores_custom_emails_tagged_value(self):
        """
        Test that ProcessingRun stores custom emails_tagged value.

        The implementation should allow setting custom values:
            run = ProcessingRun(..., emails_tagged=25)
        """
        # Arrange: Create a ProcessingRun with custom emails_tagged
        run = ProcessingRun(
            email_address="test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=150,
            emails_tagged=25,
            emails_deleted=42
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Retrieve from database
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: emails_tagged value is correct
        self.assertEqual(
            retrieved_run.emails_tagged,
            25,
            f"emails_tagged should be 25, got {retrieved_run.emails_tagged}"
        )

    def test_stores_custom_emails_deleted_value(self):
        """
        Test that ProcessingRun stores custom emails_deleted value.

        The implementation should allow setting custom values:
            run = ProcessingRun(..., emails_deleted=42)
        """
        # Arrange: Create a ProcessingRun with custom emails_deleted
        run = ProcessingRun(
            email_address="test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=150,
            emails_tagged=25,
            emails_deleted=42
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Retrieve from database
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: emails_deleted value is correct
        self.assertEqual(
            retrieved_run.emails_deleted,
            42,
            f"emails_deleted should be 42, got {retrieved_run.emails_deleted}"
        )

    def test_stores_all_audit_values_together(self):
        """
        Test that ProcessingRun stores all audit values correctly together.

        Complete integration test for storing and retrieving all three audit columns.
        """
        # Arrange: Create a ProcessingRun with all custom audit values
        expected_reviewed = 150
        expected_tagged = 25
        expected_deleted = 42

        run = ProcessingRun(
            email_address="test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=expected_reviewed,
            emails_tagged=expected_tagged,
            emails_deleted=expected_deleted
        )

        # Act: Persist and retrieve
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Clear session cache to force database read
        self.session.expire_all()

        # Retrieve from database
        retrieved_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()

        # Assert: All audit values are correct
        self.assertIsNotNone(retrieved_run, "Retrieved run should not be None")
        self.assertEqual(
            retrieved_run.emails_reviewed,
            expected_reviewed,
            f"emails_reviewed mismatch: expected {expected_reviewed}, got {retrieved_run.emails_reviewed}"
        )
        self.assertEqual(
            retrieved_run.emails_tagged,
            expected_tagged,
            f"emails_tagged mismatch: expected {expected_tagged}, got {retrieved_run.emails_tagged}"
        )
        self.assertEqual(
            retrieved_run.emails_deleted,
            expected_deleted,
            f"emails_deleted mismatch: expected {expected_deleted}, got {retrieved_run.emails_deleted}"
        )


class TestProcessingRunDefaultsAuditCountsToZero(unittest.TestCase):
    """
    Scenario: New ProcessingRun records default audit counts to zero

    Given a ProcessingRun record is created without specifying audit counts
    When the record is retrieved from the database
    Then the "emails_reviewed" value should be 0
    And the "emails_tagged" value should be 0
    And the "emails_deleted" value should be 0
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_audit_defaults.db"
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

    def test_emails_reviewed_defaults_to_zero_in_database(self):
        """
        Test that emails_reviewed defaults to 0 when not specified.

        The implementation should ensure:
            emails_reviewed = Column(Integer, default=0, nullable=False)
        """
        # Arrange: Create a ProcessingRun WITHOUT specifying emails_reviewed
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

        # Assert: emails_reviewed defaults to 0
        self.assertEqual(
            retrieved_run.emails_reviewed,
            0,
            f"emails_reviewed should default to 0, got {retrieved_run.emails_reviewed}"
        )

    def test_emails_tagged_defaults_to_zero_in_database(self):
        """
        Test that emails_tagged defaults to 0 when not specified.

        The implementation should ensure:
            emails_tagged = Column(Integer, default=0, nullable=False)
        """
        # Arrange: Create a ProcessingRun WITHOUT specifying emails_tagged
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

        # Assert: emails_tagged defaults to 0
        self.assertEqual(
            retrieved_run.emails_tagged,
            0,
            f"emails_tagged should default to 0, got {retrieved_run.emails_tagged}"
        )

    def test_emails_deleted_defaults_to_zero_in_database(self):
        """
        Test that emails_deleted defaults to 0 when not specified.

        The implementation should ensure:
            emails_deleted = Column(Integer, default=0, nullable=False)
        """
        # Arrange: Create a ProcessingRun WITHOUT specifying emails_deleted
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

        # Assert: emails_deleted defaults to 0
        self.assertEqual(
            retrieved_run.emails_deleted,
            0,
            f"emails_deleted should default to 0, got {retrieved_run.emails_deleted}"
        )

    def test_all_audit_counts_default_to_zero_together(self):
        """
        Test that all audit counts default to 0 when not specified.

        Complete integration test for default values on all three audit columns.
        """
        # Arrange: Create a ProcessingRun WITHOUT specifying any audit counts
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

        # Assert: All audit counts default to 0
        self.assertIsNotNone(retrieved_run, "Retrieved run should not be None")
        self.assertEqual(
            retrieved_run.emails_reviewed,
            0,
            f"emails_reviewed should default to 0, got {retrieved_run.emails_reviewed}"
        )
        self.assertEqual(
            retrieved_run.emails_tagged,
            0,
            f"emails_tagged should default to 0, got {retrieved_run.emails_tagged}"
        )
        self.assertEqual(
            retrieved_run.emails_deleted,
            0,
            f"emails_deleted should default to 0, got {retrieved_run.emails_deleted}"
        )


if __name__ == '__main__':
    unittest.main()
