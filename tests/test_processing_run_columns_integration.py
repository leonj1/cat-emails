#!/usr/bin/env python3
"""
Integration test for ProcessingRun emails_categorized and emails_skipped columns.

This test verifies that:
1. The Flyway V3 migration was applied (columns exist in MySQL)
2. ProcessingRun records can be created with emails_categorized and emails_skipped
3. The values are correctly stored and retrieved

Root cause being tested:
- Error: (pymysql.err.OperationalError) (1054, "Unknown column 'emails_categorized' in 'field list'")
- The SQLAlchemy model defines columns that require migration V3__add_categorized_skipped_columns.sql

This test requires MySQL running with Flyway migrations applied:
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
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from repositories.mysql_repository import MySQLRepository
from models.database import ProcessingRun


class TestProcessingRunColumnsIntegration(unittest.TestCase):
    """
    Integration tests to verify that emails_categorized and emails_skipped columns
    exist in the processing_runs table and work correctly.
    """

    @classmethod
    def setUpClass(cls):
        """Set up MySQL connection for integration tests."""
        cls.mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        cls.mysql_port = int(os.getenv('MYSQL_PORT', '3308'))
        cls.mysql_database = os.getenv('MYSQL_DATABASE', 'cat_emails_test')
        cls.mysql_user = os.getenv('MYSQL_USER', 'cat_emails')
        cls.mysql_password = os.getenv('MYSQL_PASSWORD', 'cat_emails_password')

        # Wait for MySQL to be ready
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

    def _cleanup_test_processing_runs(self):
        """Remove test processing runs from database."""
        session = self.repository._get_session()
        try:
            session.query(ProcessingRun).filter(
                ProcessingRun.email_address.like('test_%@example.com')
            ).delete(synchronize_session=False)
            session.commit()
        except SQLAlchemyError:
            session.rollback()

    def setUp(self):
        """Set up test fixtures."""
        self._cleanup_test_processing_runs()

    def tearDown(self):
        """Clean up after each test."""
        self._cleanup_test_processing_runs()

    def test_emails_categorized_column_exists(self):
        """
        Test that emails_categorized column exists in processing_runs table.

        This verifies V3 migration was applied.
        """
        session = self.repository._get_session()

        # Query the column from information_schema
        result = session.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :database
            AND TABLE_NAME = 'processing_runs'
            AND COLUMN_NAME = 'emails_categorized'
        """), {'database': self.mysql_database})

        row = result.fetchone()
        self.assertIsNotNone(row, "emails_categorized column does not exist - V3 migration not applied")
        self.assertEqual(row[0], 'emails_categorized')

    def test_emails_skipped_column_exists(self):
        """
        Test that emails_skipped column exists in processing_runs table.

        This verifies V3 migration was applied.
        """
        session = self.repository._get_session()

        # Query the column from information_schema
        result = session.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :database
            AND TABLE_NAME = 'processing_runs'
            AND COLUMN_NAME = 'emails_skipped'
        """), {'database': self.mysql_database})

        row = result.fetchone()
        self.assertIsNotNone(row, "emails_skipped column does not exist - V3 migration not applied")
        self.assertEqual(row[0], 'emails_skipped')

    def test_create_processing_run_with_categorized_skipped(self):
        """
        Test creating a ProcessingRun with emails_categorized and emails_skipped values.

        This is the exact scenario that caused the original error:
        (pymysql.err.OperationalError) (1054, "Unknown column 'emails_categorized' in 'field list'")
        """
        session = self.repository._get_session()

        # Create a ProcessingRun with all audit columns
        processing_run = ProcessingRun(
            email_address='test_create@example.com',
            start_time=datetime.utcnow(),
            state='started',
            emails_found=10,
            emails_processed=8,
            emails_reviewed=5,
            emails_tagged=3,
            emails_deleted=2,
            emails_categorized=7,
            emails_skipped=1
        )

        try:
            session.add(processing_run)
            session.commit()

            # Verify the record was created
            self.assertIsNotNone(processing_run.id)

            # Refresh from database to verify values
            session.refresh(processing_run)

            self.assertEqual(processing_run.emails_categorized, 7)
            self.assertEqual(processing_run.emails_skipped, 1)

        except OperationalError as e:
            self.fail(f"Failed to create ProcessingRun - migration V3 may not be applied: {e}")

    def test_update_processing_run_categorized_skipped(self):
        """
        Test updating emails_categorized and emails_skipped values.
        """
        session = self.repository._get_session()

        # Create initial record
        processing_run = ProcessingRun(
            email_address='test_update@example.com',
            start_time=datetime.utcnow(),
            state='started',
            emails_categorized=0,
            emails_skipped=0
        )
        session.add(processing_run)
        session.commit()

        run_id = processing_run.id

        # Update the values
        processing_run.emails_categorized = 15
        processing_run.emails_skipped = 5
        processing_run.state = 'completed'
        processing_run.end_time = datetime.utcnow()
        session.commit()

        # Retrieve fresh from database
        retrieved = session.query(ProcessingRun).filter_by(id=run_id).first()

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.emails_categorized, 15)
        self.assertEqual(retrieved.emails_skipped, 5)
        self.assertEqual(retrieved.state, 'completed')

    def test_processing_run_default_values(self):
        """
        Test that emails_categorized and emails_skipped default to 0.
        """
        session = self.repository._get_session()

        # Create record without specifying categorized/skipped
        processing_run = ProcessingRun(
            email_address='test_defaults@example.com',
            start_time=datetime.utcnow(),
            state='started'
        )
        session.add(processing_run)
        session.commit()

        # Refresh from database
        session.refresh(processing_run)

        # Verify defaults
        self.assertEqual(processing_run.emails_categorized, 0)
        self.assertEqual(processing_run.emails_skipped, 0)

    def test_find_processing_run_with_categorized_skipped(self):
        """
        Test querying ProcessingRun records filters work with new columns.
        """
        session = self.repository._get_session()

        # Create multiple records
        run1 = ProcessingRun(
            email_address='test_query@example.com',
            start_time=datetime.utcnow(),
            state='completed',
            emails_categorized=10,
            emails_skipped=2
        )
        run2 = ProcessingRun(
            email_address='test_query@example.com',
            start_time=datetime.utcnow(),
            state='completed',
            emails_categorized=20,
            emails_skipped=5
        )
        session.add_all([run1, run2])
        session.commit()

        # Query for runs with high categorized count
        high_categorized = session.query(ProcessingRun).filter(
            ProcessingRun.email_address == 'test_query@example.com',
            ProcessingRun.emails_categorized >= 15
        ).all()

        self.assertEqual(len(high_categorized), 1)
        self.assertEqual(high_categorized[0].emails_categorized, 20)

    def test_all_audit_columns_together(self):
        """
        Test that all audit columns work together correctly.

        Audit columns: emails_reviewed, emails_tagged, emails_deleted,
                      emails_categorized, emails_skipped
        """
        session = self.repository._get_session()

        processing_run = ProcessingRun(
            email_address='test_all_audit@example.com',
            start_time=datetime.utcnow(),
            state='completed',
            end_time=datetime.utcnow(),
            emails_found=100,
            emails_processed=95,
            emails_reviewed=90,
            emails_tagged=50,
            emails_deleted=25,
            emails_categorized=85,
            emails_skipped=10
        )
        session.add(processing_run)
        session.commit()

        # Retrieve and verify all values
        run_id = processing_run.id
        session.expire_all()  # Clear cache

        retrieved = session.query(ProcessingRun).filter_by(id=run_id).first()

        self.assertEqual(retrieved.emails_found, 100)
        self.assertEqual(retrieved.emails_processed, 95)
        self.assertEqual(retrieved.emails_reviewed, 90)
        self.assertEqual(retrieved.emails_tagged, 50)
        self.assertEqual(retrieved.emails_deleted, 25)
        self.assertEqual(retrieved.emails_categorized, 85)
        self.assertEqual(retrieved.emails_skipped, 10)


class TestFlywayMigrationV3Applied(unittest.TestCase):
    """
    Test that Flyway migration V3 was applied correctly.
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

    def test_flyway_schema_history_contains_v3(self):
        """
        Verify V3 migration is recorded in Flyway schema history.
        """
        session = self.repository._get_session()

        try:
            result = session.execute(text("""
                SELECT version, description, success
                FROM flyway_schema_history
                WHERE version = '3'
            """))

            row = result.fetchone()
            self.assertIsNotNone(
                row,
                "V3 migration not found in flyway_schema_history - migration was not applied"
            )
            self.assertEqual(row[0], '3')
            self.assertIn('categorized', row[1].lower())
            self.assertTrue(row[2], "V3 migration failed according to flyway_schema_history")

        except OperationalError as e:
            if "flyway_schema_history" in str(e).lower():
                self.skipTest("Flyway schema history table does not exist - running without Flyway")
            raise

    def test_processing_runs_table_schema(self):
        """
        Verify the processing_runs table has all expected columns.
        """
        session = self.repository._get_session()

        result = session.execute(text("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :database
            AND TABLE_NAME = 'processing_runs'
            ORDER BY ORDINAL_POSITION
        """), {'database': self.mysql_database})

        columns = {row[0]: {'type': row[1], 'nullable': row[2], 'default': row[3]}
                   for row in result.fetchall()}

        # Verify original audit columns from V1
        self.assertIn('emails_reviewed', columns)
        self.assertIn('emails_tagged', columns)
        self.assertIn('emails_deleted', columns)

        # Verify new audit columns from V3
        self.assertIn('emails_categorized', columns,
                      "emails_categorized column missing - V3 migration not applied")
        self.assertIn('emails_skipped', columns,
                      "emails_skipped column missing - V3 migration not applied")

        # Verify column types
        self.assertEqual(columns['emails_categorized']['type'], 'int')
        self.assertEqual(columns['emails_skipped']['type'], 'int')


if __name__ == '__main__':
    unittest.main(verbosity=2)
