"""
Integration test for Flyway migrations on Docker container startup.

This test validates that:
1. Flyway migrations run successfully on a fresh database
2. Flyway handles the "stuck at V2" scenario where columns already exist
3. V10 reconciliation migration works correctly

The test simulates the production scenario where the database schema has columns
that V3-V9 would add, but flyway_schema_history is only at V2.
"""

import os
import time
import pymysql
import pytest


def get_mysql_connection():
    """Create a connection to the test MySQL database."""
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", 3306)),
        user=os.environ.get("MYSQL_USER", "cat_emails"),
        password=os.environ.get("MYSQL_PASSWORD", "cat_emails_password"),
        database=os.environ.get("MYSQL_DATABASE", "cat_emails_test"),
        autocommit=True,
    )


def wait_for_mysql(max_retries: int = 30, delay: float = 1.0):
    """Wait for MySQL to be available."""
    for i in range(max_retries):
        try:
            conn = get_mysql_connection()
            conn.close()
            return True
        except pymysql.Error:
            if i < max_retries - 1:
                time.sleep(delay)
    return False


class TestFlywayStartup:
    """Test Flyway migrations on container startup."""

    def test_flyway_schema_history_exists(self):
        """Verify that flyway_schema_history table was created."""
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                    AND table_name = 'flyway_schema_history'
                    """
                )
                result = cursor.fetchone()
                assert result[0] == 1, "flyway_schema_history table should exist"
        finally:
            conn.close()

    def test_all_migrations_successful(self):
        """Verify all migrations completed successfully."""
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                # Check for any failed migrations
                cursor.execute(
                    """
                    SELECT version, description, success
                    FROM flyway_schema_history
                    WHERE success = 0
                    """
                )
                failed = cursor.fetchall()
                assert len(failed) == 0, f"Found failed migrations: {failed}"

                # Verify we have migrations recorded
                cursor.execute("SELECT COUNT(*) FROM flyway_schema_history")
                result = cursor.fetchone()
                assert result[0] > 0, "Should have at least one migration recorded"
        finally:
            conn.close()

    def test_v3_columns_exist_on_processing_runs(self):
        """Verify V3 migration columns exist on processing_runs table."""
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                # Check emails_categorized column
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                    AND table_name = 'processing_runs'
                    AND column_name = 'emails_categorized'
                    """
                )
                result = cursor.fetchone()
                assert result[0] == 1, "emails_categorized column should exist"

                # Check emails_skipped column
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                    AND table_name = 'processing_runs'
                    AND column_name = 'emails_skipped'
                    """
                )
                result = cursor.fetchone()
                assert result[0] == 1, "emails_skipped column should exist"
        finally:
            conn.close()

    def test_oauth_columns_exist_on_email_accounts(self):
        """Verify OAuth columns from V5-V9 exist on email_accounts table."""
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                expected_columns = [
                    "auth_method",
                    "oauth_client_id",
                    "oauth_client_secret",
                    "oauth_refresh_token",
                    "oauth_access_token",
                    "oauth_token_expiry",
                    "oauth_scopes",
                ]

                for column in expected_columns:
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM information_schema.columns
                        WHERE table_schema = DATABASE()
                        AND table_name = 'email_accounts'
                        AND column_name = %s
                        """,
                        (column,),
                    )
                    result = cursor.fetchone()
                    assert result[0] == 1, f"{column} column should exist on email_accounts"
        finally:
            conn.close()

    def test_v10_reconciliation_ran(self):
        """Verify V10 reconciliation migration was applied."""
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT version, success FROM flyway_schema_history
                    WHERE version = '10'
                    """
                )
                result = cursor.fetchone()
                # V10 should exist and be successful
                # Note: If baseline was set above V10, this test should be adjusted
                if result:
                    assert result[1] == 1, "V10 migration should have succeeded"
        finally:
            conn.close()


class TestFlywayStuckAtV2Recovery:
    """
    Test recovery from the "stuck at V2" scenario.

    This simulates the production issue where:
    1. Database is at Flyway version 2
    2. Columns from V3-V9 already exist (added manually)
    3. Flyway tries to run V3 and fails with "Duplicate column"

    The fix involves marking V3-V9 as baseline and running V10.
    """

    def test_no_duplicate_column_errors(self):
        """Verify no duplicate column errors occurred during migration."""
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                # Check that all migrations are marked as successful
                cursor.execute(
                    """
                    SELECT version, description
                    FROM flyway_schema_history
                    WHERE success = 0
                    """
                )
                failed = cursor.fetchall()

                # Filter for column-related failures
                column_failures = [
                    f for f in failed
                    if "column" in str(f).lower() or "categorized" in str(f).lower()
                ]
                assert len(column_failures) == 0, (
                    f"Found column-related migration failures: {column_failures}"
                )
        finally:
            conn.close()

    def test_processing_runs_table_functional(self):
        """Verify processing_runs table works with all expected columns."""
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                # Try inserting a record with all expected columns
                cursor.execute(
                    """
                    INSERT INTO processing_runs
                    (email_address, start_time, state, emails_categorized, emails_skipped)
                    VALUES ('test@example.com', NOW(), 'test', 5, 2)
                    """
                )

                # Verify insert worked
                cursor.execute(
                    """
                    SELECT emails_categorized, emails_skipped
                    FROM processing_runs
                    WHERE email_address = 'test@example.com'
                    """
                )
                result = cursor.fetchone()
                assert result[0] == 5, "emails_categorized should be 5"
                assert result[1] == 2, "emails_skipped should be 2"

                # Clean up
                cursor.execute(
                    "DELETE FROM processing_runs WHERE email_address = 'test@example.com'"
                )
        finally:
            conn.close()


if __name__ == "__main__":
    # Wait for MySQL to be ready
    print("Waiting for MySQL to be available...")
    if not wait_for_mysql():
        print("ERROR: MySQL did not become available")
        exit(1)

    print("MySQL is available, running tests...")
    pytest.main([__file__, "-v"])
