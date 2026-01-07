"""
Tests for OAuth functionality in AccountCategoryClient.

Tests the OAuth-related methods: update_oauth_tokens, get_oauth_status, clear_oauth_tokens.
"""
import unittest
import tempfile
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from clients.account_category_client import AccountCategoryClient
from models.database import Base, EmailAccount


class TestAccountCategoryClientOAuth(unittest.TestCase):
    """Test cases for OAuth methods in AccountCategoryClient."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        self.engine = create_engine(f'sqlite:///{self.temp_db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.service = AccountCategoryClient(db_session=self.session)
        self.test_email = "oauth_test@gmail.com"

    def tearDown(self):
        """Clean up test fixtures."""
        self.session.close()
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_get_or_create_account_with_oauth(self):
        """Test creating account with OAuth authentication."""
        account = self.service.get_or_create_account(
            email_address=self.test_email,
            display_name=None,
            app_password=None,
            auth_method="oauth",
            oauth_refresh_token="test_refresh_token",
        )

        self.assertIsNotNone(account)
        self.assertEqual(account.email_address, self.test_email)
        self.assertEqual(account.auth_method, "oauth")
        self.assertEqual(account.oauth_refresh_token, "test_refresh_token")

    def test_get_or_create_account_default_imap(self):
        """Test that account defaults to IMAP auth method."""
        account = self.service.get_or_create_account(
            email_address=self.test_email,
            display_name=None,
            auth_method=None,
            oauth_refresh_token=None,
            app_password="test_password",
        )

        self.assertIsNotNone(account)
        self.assertEqual(account.auth_method, "imap")

    def test_update_oauth_tokens(self):
        """Test updating OAuth tokens for an account."""
        # First create an account
        self.service.get_or_create_account(
            email_address=self.test_email,
            display_name=None,
            auth_method=None,
            oauth_refresh_token=None,
            app_password="initial_password",
        )

        # Update with OAuth tokens
        token_expiry = datetime.utcnow() + timedelta(hours=1)
        scopes = ["gmail.readonly", "gmail.labels"]

        account = self.service.update_oauth_tokens(
            email_address=self.test_email,
            refresh_token="new_refresh_token",
            access_token="new_access_token",
            token_expiry=token_expiry,
            scopes=scopes,
        )

        self.assertIsNotNone(account)
        self.assertEqual(account.auth_method, "oauth")
        self.assertEqual(account.oauth_refresh_token, "new_refresh_token")
        self.assertEqual(account.oauth_access_token, "new_access_token")
        self.assertIsNotNone(account.oauth_token_expiry)

    def test_update_oauth_tokens_nonexistent_account(self):
        """Test updating OAuth tokens for nonexistent account returns None."""
        result = self.service.update_oauth_tokens(
            email_address="nonexistent@gmail.com",
            refresh_token="token",
            access_token="access",
            token_expiry=datetime.utcnow(),
            scopes=[],
        )

        self.assertIsNone(result)

    def test_get_oauth_status_oauth_account(self):
        """Test getting OAuth status for OAuth-authenticated account."""
        # Create account with OAuth
        self.service.get_or_create_account(
            email_address=self.test_email,
            display_name=None,
            app_password=None,
            auth_method="oauth",
            oauth_refresh_token="refresh_token",
        )

        # Update with full OAuth tokens
        token_expiry = datetime.utcnow() + timedelta(hours=1)
        self.service.update_oauth_tokens(
            email_address=self.test_email,
            refresh_token="refresh_token",
            access_token="access_token",
            token_expiry=token_expiry,
            scopes=["gmail.readonly"],
        )

        status = self.service.get_oauth_status(self.test_email)

        self.assertIsNotNone(status)
        self.assertTrue(status['connected'])
        self.assertEqual(status['auth_method'], 'oauth')
        self.assertIsNotNone(status['scopes'])
        self.assertIn("gmail.readonly", status['scopes'])

    def test_get_oauth_status_imap_account(self):
        """Test getting OAuth status for IMAP-authenticated account."""
        self.service.get_or_create_account(
            email_address=self.test_email,
            display_name=None,
            auth_method=None,
            oauth_refresh_token=None,
            app_password="password",
        )

        status = self.service.get_oauth_status(self.test_email)

        self.assertIsNotNone(status)
        self.assertFalse(status['connected'])
        self.assertEqual(status['auth_method'], 'imap')
        self.assertIsNone(status['scopes'])

    def test_get_oauth_status_nonexistent_account(self):
        """Test getting OAuth status for nonexistent account returns None."""
        status = self.service.get_oauth_status("nonexistent@gmail.com")

        self.assertIsNone(status)

    def test_clear_oauth_tokens(self):
        """Test clearing OAuth tokens from an account."""
        # Create OAuth account
        self.service.get_or_create_account(
            email_address=self.test_email,
            display_name=None,
            app_password=None,
            auth_method="oauth",
            oauth_refresh_token="refresh_token",
        )

        # Add full OAuth tokens
        self.service.update_oauth_tokens(
            email_address=self.test_email,
            refresh_token="refresh_token",
            access_token="access_token",
            token_expiry=datetime.utcnow() + timedelta(hours=1),
            scopes=["gmail.readonly"],
        )

        # Clear tokens
        result = self.service.clear_oauth_tokens(self.test_email)

        self.assertTrue(result)

        # Verify tokens are cleared
        status = self.service.get_oauth_status(self.test_email)
        self.assertFalse(status['connected'])
        self.assertEqual(status['auth_method'], 'imap')

    def test_clear_oauth_tokens_nonexistent_account(self):
        """Test clearing OAuth tokens from nonexistent account returns False."""
        result = self.service.clear_oauth_tokens("nonexistent@gmail.com")

        self.assertFalse(result)

    def test_detach_account_includes_oauth_fields(self):
        """Test that detached account includes OAuth fields."""
        # Create OAuth account
        self.service.get_or_create_account(
            email_address=self.test_email,
            display_name=None,
            app_password=None,
            auth_method="oauth",
            oauth_refresh_token="refresh_token",
        )

        # Retrieve account
        account = self.service.get_account_by_email(self.test_email)

        # Verify OAuth fields are present
        self.assertTrue(hasattr(account, 'auth_method'))
        self.assertTrue(hasattr(account, 'oauth_refresh_token'))
        self.assertTrue(hasattr(account, 'oauth_access_token'))
        self.assertTrue(hasattr(account, 'oauth_token_expiry'))
        self.assertTrue(hasattr(account, 'oauth_scopes'))

    def test_update_existing_account_to_oauth(self):
        """Test updating existing IMAP account to use OAuth."""
        # Create IMAP account
        self.service.get_or_create_account(
            email_address=self.test_email,
            display_name=None,
            auth_method=None,
            oauth_refresh_token=None,
            app_password="password",
        )

        # Update to OAuth
        account = self.service.get_or_create_account(
            email_address=self.test_email,
            display_name=None,
            app_password=None,
            auth_method="oauth",
            oauth_refresh_token="new_refresh_token",
        )

        self.assertEqual(account.auth_method, "oauth")
        self.assertEqual(account.oauth_refresh_token, "new_refresh_token")

    def test_oauth_scopes_stored_as_json(self):
        """Test that OAuth scopes are stored as JSON and retrieved as list."""
        self.service.get_or_create_account(
            email_address=self.test_email,
            display_name=None,
            app_password=None,
            auth_method="oauth",
            oauth_refresh_token="token",
        )

        scopes = ["gmail.readonly", "gmail.labels", "gmail.modify"]

        self.service.update_oauth_tokens(
            email_address=self.test_email,
            refresh_token="token",
            access_token="access",
            token_expiry=datetime.utcnow() + timedelta(hours=1),
            scopes=scopes,
        )

        status = self.service.get_oauth_status(self.test_email)

        self.assertEqual(len(status['scopes']), 3)
        self.assertEqual(set(status['scopes']), set(scopes))


if __name__ == '__main__':
    unittest.main()
