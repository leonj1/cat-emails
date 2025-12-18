#!/usr/bin/env python3
"""
Integration test to verify OAuth columns exist in email_accounts table.

This test validates that the V7 Flyway migration properly adds the missing
auth_method and OAuth columns to the email_accounts table, fixing the error:
"Unknown column 'email_accounts.auth_method' in 'field list'"
"""
import os
import sys
import time
import unittest
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from repositories.mysql_repository import MySQLRepository
from clients.account_category_client import AccountCategoryClient
from models.database import EmailAccount


def is_mysql_available():
    """Check if MySQL is available for connection."""
    import socket
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', '3308'))
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


# Skip all tests if MySQL is not available
pytestmark = pytest.mark.skipif(
    not is_mysql_available(),
    reason="MySQL database is not available for integration tests"
)


class TestEmailAccountOAuthColumnsIntegration(unittest.TestCase):
    """
    Integration tests to verify OAuth columns exist in email_accounts table
    after Flyway migrations run.
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

        # Create AccountCategoryClient with the repository
        cls.client = AccountCategoryClient(repository=cls.repository)

    @classmethod
    def tearDownClass(cls):
        """Clean up MySQL connection."""
        if hasattr(cls, 'client') and cls.client:
            cls.client.close()
        if hasattr(cls, 'repository') and cls.repository:
            cls.repository.disconnect()

    def _cleanup_test_accounts(self):
        """Remove test accounts from database."""
        session = self.repository._get_session()
        try:
            session.query(EmailAccount).filter(
                EmailAccount.email_address.like('test_oauth_%@example.com')
            ).delete(synchronize_session=False)
            session.commit()
        except SQLAlchemyError:
            session.rollback()

    def setUp(self):
        """Set up test fixtures."""
        self._cleanup_test_accounts()

    def tearDown(self):
        """Clean up after each test."""
        self._cleanup_test_accounts()

    def test_auth_method_column_exists(self):
        """
        Test that auth_method column exists in email_accounts table.

        This test would have caught the production error:
        "Unknown column 'email_accounts.auth_method' in 'field list'"
        """
        session = self.repository._get_session()

        # Query the information schema to verify column exists
        result = session.execute(text("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'email_accounts'
            AND COLUMN_NAME = 'auth_method'
        """))
        row = result.fetchone()

        self.assertEqual(row.cnt, 1, "auth_method column should exist in email_accounts table")

    def test_oauth_columns_exist(self):
        """
        Test that all OAuth columns exist in email_accounts table.
        """
        session = self.repository._get_session()

        oauth_columns = [
            'auth_method',
            'oauth_client_id',
            'oauth_client_secret',
            'oauth_refresh_token',
            'oauth_access_token',
            'oauth_token_expiry',
            'oauth_scopes'
        ]

        for column in oauth_columns:
            result = session.execute(text(f"""
                SELECT COUNT(*) as cnt
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'email_accounts'
                AND COLUMN_NAME = '{column}'
            """))
            row = result.fetchone()

            self.assertEqual(
                row.cnt, 1,
                f"{column} column should exist in email_accounts table"
            )

    def test_get_all_accounts_succeeds(self):
        """
        Test that get_all_accounts query succeeds without 'Unknown column' error.

        This is the exact operation that was failing in production.
        """
        # Create a test account first
        test_email = 'test_oauth_get_all@example.com'
        account = self.client.get_or_create_account(
            email_address=test_email,
            display_name='Test OAuth User',
            auth_method='imap'
        )

        # This should NOT raise:
        # OperationalError: (1054, "Unknown column 'email_accounts.auth_method' in 'field list'")
        accounts = self.client.get_all_accounts(active_only=True)

        # Verify we got results
        self.assertIsInstance(accounts, list)

        # Find our test account
        test_account = next((a for a in accounts if a.email_address == test_email), None)
        self.assertIsNotNone(test_account, "Test account should be in results")

        # Verify OAuth fields are accessible
        self.assertEqual(test_account.auth_method, 'imap')
        self.assertIsNone(test_account.oauth_client_id)
        self.assertIsNone(test_account.oauth_refresh_token)

    def test_create_account_with_oauth_auth_method(self):
        """
        Test creating an account with OAuth auth method.
        """
        test_email = 'test_oauth_create@example.com'

        account = self.client.get_or_create_account(
            email_address=test_email,
            display_name='OAuth Test User',
            auth_method='oauth',
            oauth_refresh_token='test_refresh_token_value'
        )

        # Verify account was created with OAuth settings
        self.assertEqual(account.email_address, test_email)
        self.assertEqual(account.auth_method, 'oauth')
        self.assertEqual(account.oauth_refresh_token, 'test_refresh_token_value')

    def test_update_oauth_tokens(self):
        """
        Test updating OAuth tokens for an account.
        """
        from datetime import datetime, timedelta

        test_email = 'test_oauth_update@example.com'

        # Create account first
        self.client.get_or_create_account(
            email_address=test_email,
            display_name='OAuth Update Test',
            auth_method='imap'
        )

        # Update with OAuth tokens
        token_expiry = datetime.utcnow() + timedelta(hours=1)
        updated_account = self.client.update_oauth_tokens(
            email_address=test_email,
            refresh_token='new_refresh_token',
            access_token='new_access_token',
            token_expiry=token_expiry,
            scopes=['gmail.readonly', 'gmail.modify']
        )

        # Verify update succeeded
        self.assertIsNotNone(updated_account)
        self.assertEqual(updated_account.auth_method, 'oauth')
        self.assertEqual(updated_account.oauth_refresh_token, 'new_refresh_token')
        self.assertEqual(updated_account.oauth_access_token, 'new_access_token')

    def test_detach_account_copies_oauth_fields(self):
        """
        Test that _detach_account properly copies all OAuth fields.
        """
        from datetime import datetime, timedelta

        test_email = 'test_oauth_detach@example.com'

        # Create account with OAuth
        self.client.get_or_create_account(
            email_address=test_email,
            auth_method='oauth',
            oauth_refresh_token='test_refresh'
        )

        # Update with full OAuth tokens
        token_expiry = datetime.utcnow() + timedelta(hours=1)
        self.client.update_oauth_tokens(
            email_address=test_email,
            refresh_token='refresh_value',
            access_token='access_value',
            token_expiry=token_expiry,
            scopes=['gmail.readonly']
        )

        # Get account (this uses _detach_account internally)
        account = self.client.get_account_by_email(test_email)

        # Verify all OAuth fields are present in detached copy
        self.assertEqual(account.auth_method, 'oauth')
        self.assertEqual(account.oauth_refresh_token, 'refresh_value')
        self.assertEqual(account.oauth_access_token, 'access_value')
        self.assertIsNotNone(account.oauth_token_expiry)
        self.assertIsNotNone(account.oauth_scopes)

    def test_index_on_auth_method_exists(self):
        """
        Test that index on auth_method column exists for efficient filtering.
        """
        session = self.repository._get_session()

        result = session.execute(text("""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'email_accounts'
            AND INDEX_NAME = 'idx_auth_method'
        """))
        row = result.fetchone()

        self.assertEqual(row.cnt, 1, "idx_auth_method index should exist on email_accounts table")


if __name__ == '__main__':
    unittest.main(verbosity=2)
