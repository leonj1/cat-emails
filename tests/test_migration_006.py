"""
Tests for Migration 006: Add emails_categorized and emails_skipped columns.

Based on BDD scenarios from specs/DRAFT-python-migration-006-core.md:
- Scenario: Migration creates columns when missing
- Scenario: Migration is idempotent - safe to run multiple times
- Scenario: Migration downgrade removes columns

These tests follow TDD approach (Red phase) - tests will FAIL until the
migration script is implemented at migrations/006_add_categorized_skipped_columns.py.

The migration should:
1. Add emails_categorized column (INTEGER, DEFAULT 0)
2. Add emails_skipped column (INTEGER, DEFAULT 0)
3. Be idempotent - safe to run multiple times without error
4. Support downgrade to remove the columns
"""
import shutil
import tempfile
import unittest
from datetime import datetime

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker


class TestMigration006Upgrade(unittest.TestCase):
    """
    Scenario: Migration creates columns when missing

    Given the processing_runs table does NOT have emails_categorized column
    And the processing_runs table does NOT have emails_skipped column
    When the migration upgrade() is executed
    Then emails_categorized column exists with INTEGER type
    And emails_categorized column has DEFAULT 0
    And emails_skipped column exists with INTEGER type
    And emails_skipped column has DEFAULT 0
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_migration_006_upgrade.db"

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Set up a fresh database for each test without the target columns."""
        # Create a minimal processing_runs table WITHOUT emails_categorized/emails_skipped
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)

        with self.engine.connect() as conn:
            # Drop existing table if it exists
            conn.execute(text("DROP TABLE IF EXISTS processing_runs"))

            # Create table without the migration 006 columns
            conn.execute(text("""
                CREATE TABLE processing_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_address TEXT NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    state TEXT NOT NULL,
                    current_step TEXT,
                    emails_found INTEGER DEFAULT 0,
                    emails_processed INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    emails_reviewed INTEGER DEFAULT 0,
                    emails_tagged INTEGER DEFAULT 0,
                    emails_deleted INTEGER DEFAULT 0
                )
            """))
            conn.commit()

    def tearDown(self):
        """Clean up after each test."""
        self.engine.dispose()

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        inspector = inspect(self.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns

    def _get_column_info(self, table_name: str, column_name: str) -> dict:
        """Get column information from the database."""
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_name)
        for col in columns:
            if col['name'] == column_name:
                return col
        return {}

    def test_upgrade_creates_emails_categorized_column(self):
        """
        Test that migration upgrade() creates emails_categorized column.

        The migration should execute:
            ALTER TABLE processing_runs ADD COLUMN emails_categorized INTEGER DEFAULT 0
        """
        # Arrange: Import and run migration
        from migrations.migration_006_add_categorized_skipped_columns import upgrade

        # Verify column does not exist before migration
        self.assertFalse(
            self._column_exists('processing_runs', 'emails_categorized'),
            "emails_categorized column should NOT exist before migration"
        )

        # Act: Run the migration upgrade
        upgrade(engine=self.engine)

        # Assert: emails_categorized column now exists
        self.assertTrue(
            self._column_exists('processing_runs', 'emails_categorized'),
            "emails_categorized column should exist after migration upgrade"
        )

    def test_upgrade_creates_emails_skipped_column(self):
        """
        Test that migration upgrade() creates emails_skipped column.

        The migration should execute:
            ALTER TABLE processing_runs ADD COLUMN emails_skipped INTEGER DEFAULT 0
        """
        # Arrange: Import and run migration
        from migrations.migration_006_add_categorized_skipped_columns import upgrade

        # Verify column does not exist before migration
        self.assertFalse(
            self._column_exists('processing_runs', 'emails_skipped'),
            "emails_skipped column should NOT exist before migration"
        )

        # Act: Run the migration upgrade
        upgrade(engine=self.engine)

        # Assert: emails_skipped column now exists
        self.assertTrue(
            self._column_exists('processing_runs', 'emails_skipped'),
            "emails_skipped column should exist after migration upgrade"
        )

    def test_upgrade_sets_emails_categorized_default_to_zero(self):
        """
        Test that emails_categorized column has DEFAULT 0.

        When inserting a record without specifying emails_categorized,
        the default value should be 0.
        """
        # Arrange: Import and run migration
        from migrations.migration_006_add_categorized_skipped_columns import upgrade
        upgrade(engine=self.engine)

        # Act: Insert a record without specifying emails_categorized
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO processing_runs
                (email_address, start_time, state)
                VALUES ('test@example.com', datetime('now'), 'completed')
            """))
            conn.commit()

            # Retrieve the record
            result = conn.execute(text(
                "SELECT emails_categorized FROM processing_runs LIMIT 1"
            )).fetchone()

        # Assert: Default value is 0
        self.assertEqual(
            result[0],
            0,
            f"emails_categorized should default to 0, got {result[0]}"
        )

    def test_upgrade_sets_emails_skipped_default_to_zero(self):
        """
        Test that emails_skipped column has DEFAULT 0.

        When inserting a record without specifying emails_skipped,
        the default value should be 0.
        """
        # Arrange: Import and run migration
        from migrations.migration_006_add_categorized_skipped_columns import upgrade
        upgrade(engine=self.engine)

        # Act: Insert a record without specifying emails_skipped
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO processing_runs
                (email_address, start_time, state)
                VALUES ('test@example.com', datetime('now'), 'completed')
            """))
            conn.commit()

            # Retrieve the record
            result = conn.execute(text(
                "SELECT emails_skipped FROM processing_runs LIMIT 1"
            )).fetchone()

        # Assert: Default value is 0
        self.assertEqual(
            result[0],
            0,
            f"emails_skipped should default to 0, got {result[0]}"
        )

    def test_upgrade_creates_integer_type_columns(self):
        """
        Test that both columns are INTEGER type.

        The migration should create INTEGER columns for proper numeric storage.
        """
        # Arrange: Import and run migration
        from migrations.migration_006_add_categorized_skipped_columns import upgrade
        upgrade(engine=self.engine)

        # Act: Insert a record with integer values
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO processing_runs
                (email_address, start_time, state, emails_categorized, emails_skipped)
                VALUES ('test@example.com', datetime('now'), 'completed', 42, 17)
            """))
            conn.commit()

            # Retrieve the record
            result = conn.execute(text(
                "SELECT emails_categorized, emails_skipped FROM processing_runs LIMIT 1"
            )).fetchone()

        # Assert: Values are stored as integers
        self.assertEqual(
            result[0],
            42,
            f"emails_categorized should store integer 42, got {result[0]}"
        )
        self.assertEqual(
            result[1],
            17,
            f"emails_skipped should store integer 17, got {result[1]}"
        )


class TestMigration006Idempotency(unittest.TestCase):
    """
    Scenario: Migration is idempotent - safe to run multiple times

    Given the processing_runs table already has emails_categorized column
    And the processing_runs table already has emails_skipped column
    When the migration upgrade() is executed
    Then no error is raised
    And the columns remain unchanged
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_migration_006_idempotent.db"

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Set up a fresh database for each test without the target columns."""
        # Create a minimal processing_runs table WITHOUT emails_categorized/emails_skipped
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)

        with self.engine.connect() as conn:
            # Drop existing table if it exists
            conn.execute(text("DROP TABLE IF EXISTS processing_runs"))

            # Create table without the migration 006 columns
            conn.execute(text("""
                CREATE TABLE processing_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_address TEXT NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    state TEXT NOT NULL,
                    current_step TEXT,
                    emails_found INTEGER DEFAULT 0,
                    emails_processed INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    emails_reviewed INTEGER DEFAULT 0,
                    emails_tagged INTEGER DEFAULT 0,
                    emails_deleted INTEGER DEFAULT 0
                )
            """))
            conn.commit()

    def tearDown(self):
        """Clean up after each test."""
        self.engine.dispose()

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        inspector = inspect(self.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns

    def test_upgrade_does_not_error_when_run_twice(self):
        """
        Test that running upgrade() twice does not raise an error.

        The migration should be safe to run multiple times.
        """
        # Arrange: Import migration
        from migrations.migration_006_add_categorized_skipped_columns import upgrade

        # Act: Run upgrade twice
        upgrade(engine=self.engine)  # First run

        # Assert: Second run should not raise an error
        try:
            upgrade(engine=self.engine)  # Second run
        except Exception as e:
            self.fail(f"Second upgrade() call should not raise an error, got: {e}")

    def test_upgrade_preserves_existing_data_on_rerun(self):
        """
        Test that running upgrade() a second time preserves existing data.

        Data inserted after first migration should remain after second migration run.
        """
        # Arrange: Import migration and run once
        from migrations.migration_006_add_categorized_skipped_columns import upgrade
        upgrade(engine=self.engine)

        # Insert test data
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO processing_runs
                (email_address, start_time, state, emails_categorized, emails_skipped)
                VALUES ('test@example.com', datetime('now'), 'completed', 100, 50)
            """))
            conn.commit()

        # Act: Run upgrade again
        upgrade(engine=self.engine)

        # Assert: Data should still be there
        with self.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT emails_categorized, emails_skipped FROM processing_runs LIMIT 1"
            )).fetchone()

        self.assertEqual(
            result[0],
            100,
            f"emails_categorized should be preserved as 100, got {result[0]}"
        )
        self.assertEqual(
            result[1],
            50,
            f"emails_skipped should be preserved as 50, got {result[1]}"
        )

    def test_upgrade_columns_exist_after_multiple_runs(self):
        """
        Test that columns exist after running upgrade() three times.

        This ensures idempotency across multiple invocations.
        """
        # Arrange: Import migration
        from migrations.migration_006_add_categorized_skipped_columns import upgrade

        # Act: Run upgrade three times
        upgrade(engine=self.engine)
        upgrade(engine=self.engine)
        upgrade(engine=self.engine)

        # Assert: Both columns should exist
        self.assertTrue(
            self._column_exists('processing_runs', 'emails_categorized'),
            "emails_categorized column should exist after multiple upgrade runs"
        )
        self.assertTrue(
            self._column_exists('processing_runs', 'emails_skipped'),
            "emails_skipped column should exist after multiple upgrade runs"
        )


class TestMigration006Downgrade(unittest.TestCase):
    """
    Scenario: Migration downgrade removes columns

    Given the processing_runs table has emails_categorized column
    And the processing_runs table has emails_skipped column
    When the migration downgrade() is executed
    Then emails_categorized column no longer exists
    And emails_skipped column no longer exists
    And all other columns are preserved
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_migration_006_downgrade.db"

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Set up a database WITH the target columns (simulating post-upgrade state)."""
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)

        with self.engine.connect() as conn:
            # Drop existing table if it exists
            conn.execute(text("DROP TABLE IF EXISTS processing_runs"))

            # Create table WITH the migration 006 columns (post-upgrade state)
            conn.execute(text("""
                CREATE TABLE processing_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_address TEXT NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    state TEXT NOT NULL,
                    current_step TEXT,
                    emails_found INTEGER DEFAULT 0,
                    emails_processed INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    emails_reviewed INTEGER DEFAULT 0,
                    emails_tagged INTEGER DEFAULT 0,
                    emails_deleted INTEGER DEFAULT 0,
                    emails_categorized INTEGER DEFAULT 0,
                    emails_skipped INTEGER DEFAULT 0
                )
            """))
            conn.commit()

    def tearDown(self):
        """Clean up after each test."""
        self.engine.dispose()

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        inspector = inspect(self.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns

    def _get_column_names(self, table_name: str) -> list:
        """Get all column names from a table."""
        inspector = inspect(self.engine)
        return [col['name'] for col in inspector.get_columns(table_name)]

    def test_downgrade_removes_emails_categorized_column(self):
        """
        Test that migration downgrade() removes emails_categorized column.

        After downgrade, emails_categorized should no longer exist.
        """
        # Arrange: Import migration
        from migrations.migration_006_add_categorized_skipped_columns import downgrade

        # Verify column exists before downgrade
        self.assertTrue(
            self._column_exists('processing_runs', 'emails_categorized'),
            "emails_categorized column should exist before downgrade"
        )

        # Act: Run the migration downgrade
        downgrade(engine=self.engine)

        # Assert: emails_categorized column should not exist
        self.assertFalse(
            self._column_exists('processing_runs', 'emails_categorized'),
            "emails_categorized column should NOT exist after downgrade"
        )

    def test_downgrade_removes_emails_skipped_column(self):
        """
        Test that migration downgrade() removes emails_skipped column.

        After downgrade, emails_skipped should no longer exist.
        """
        # Arrange: Import migration
        from migrations.migration_006_add_categorized_skipped_columns import downgrade

        # Verify column exists before downgrade
        self.assertTrue(
            self._column_exists('processing_runs', 'emails_skipped'),
            "emails_skipped column should exist before downgrade"
        )

        # Act: Run the migration downgrade
        downgrade(engine=self.engine)

        # Assert: emails_skipped column should not exist
        self.assertFalse(
            self._column_exists('processing_runs', 'emails_skipped'),
            "emails_skipped column should NOT exist after downgrade"
        )

    def test_downgrade_preserves_other_columns(self):
        """
        Test that downgrade() preserves all other columns.

        The core processing_runs columns should remain after downgrade.
        """
        # Arrange: Import migration
        from migrations.migration_006_add_categorized_skipped_columns import downgrade

        # Expected columns to be preserved (everything except the migration 006 columns)
        expected_columns = [
            'id', 'email_address', 'start_time', 'end_time', 'state',
            'current_step', 'emails_found', 'emails_processed', 'error_message',
            'created_at', 'updated_at', 'emails_reviewed', 'emails_tagged', 'emails_deleted'
        ]

        # Act: Run the migration downgrade
        downgrade(engine=self.engine)

        # Assert: All expected columns still exist
        remaining_columns = self._get_column_names('processing_runs')
        for col_name in expected_columns:
            self.assertIn(
                col_name,
                remaining_columns,
                f"Column '{col_name}' should be preserved after downgrade"
            )

    def test_downgrade_preserves_existing_data(self):
        """
        Test that downgrade() preserves data in other columns.

        Data in non-migration columns should remain intact after downgrade.
        """
        # Arrange: Insert test data
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO processing_runs
                (email_address, start_time, state, emails_found, emails_processed,
                 emails_reviewed, emails_tagged, emails_deleted,
                 emails_categorized, emails_skipped)
                VALUES
                ('preserve_test@example.com', datetime('now'), 'completed',
                 100, 95, 90, 10, 5, 75, 25)
            """))
            conn.commit()

        # Arrange: Import migration
        from migrations.migration_006_add_categorized_skipped_columns import downgrade

        # Act: Run the migration downgrade
        downgrade(engine=self.engine)

        # Assert: Original data should still be there
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT email_address, emails_found, emails_processed,
                       emails_reviewed, emails_tagged, emails_deleted
                FROM processing_runs LIMIT 1
            """)).fetchone()

        self.assertEqual(
            result[0],
            'preserve_test@example.com',
            f"email_address should be preserved, got {result[0]}"
        )
        self.assertEqual(
            result[1],
            100,
            f"emails_found should be preserved as 100, got {result[1]}"
        )
        self.assertEqual(
            result[2],
            95,
            f"emails_processed should be preserved as 95, got {result[2]}"
        )
        self.assertEqual(
            result[3],
            90,
            f"emails_reviewed should be preserved as 90, got {result[3]}"
        )
        self.assertEqual(
            result[4],
            10,
            f"emails_tagged should be preserved as 10, got {result[4]}"
        )
        self.assertEqual(
            result[5],
            5,
            f"emails_deleted should be preserved as 5, got {result[5]}"
        )

    def test_downgrade_preserves_indexes(self):
        """
        Test that downgrade() recreates necessary indexes.

        Processing runs table should have indexes after downgrade.
        """
        # Arrange: Create indexes that exist in the original schema
        with self.engine.connect() as conn:
            # Create indexes before downgrade
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_processing_runs_email_address ON processing_runs(email_address)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_processing_runs_start_time ON processing_runs(start_time)"
            ))
            conn.commit()

        # Arrange: Import migration
        from migrations.migration_006_add_categorized_skipped_columns import downgrade

        # Act: Run the migration downgrade
        downgrade(engine=self.engine)

        # Assert: Table should exist and have the email_address column (index target)
        inspector = inspect(self.engine)
        indexes = inspector.get_indexes('processing_runs')
        index_names = [idx['name'] for idx in indexes]

        # Verify at least the email_address index exists
        self.assertIn(
            'idx_processing_runs_email_address',
            index_names,
            "idx_processing_runs_email_address index should be preserved after downgrade"
        )


if __name__ == '__main__':
    unittest.main()
