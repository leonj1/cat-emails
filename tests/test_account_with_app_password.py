#!/usr/bin/env python3
"""
Test for AccountCategoryClient with app_password parameter.

This test verifies that the get_or_create_account method correctly
accepts and stores the app_password field.
"""
import unittest
import tempfile
import os
import string
import random

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import init_database, get_session, EmailAccount
from clients.account_category_client import AccountCategoryClient


class TestAccountWithAppPassword(unittest.TestCase):
    """Test that AccountCategoryClient properly handles app_password."""

    def setUp(self):
        """Set up test database."""
        self.test_counter = 0

        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        # Initialize database
        self.engine = init_database(self.temp_db_path)
        self.session = get_session(self.engine)

        # Create client with session
        self.client = AccountCategoryClient(db_session=self.session)

    def tearDown(self):
        """Clean up test database."""
        if hasattr(self, 'session'):
            self.session.close()
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def _generate_email(self):
        """Generate a unique test email."""
        self.test_counter += 1
        return f"test.user{self.test_counter}@gmail.com"

    def _generate_password(self):
        """Generate a random password."""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(16))

    def _generate_name(self):
        """Generate a test name."""
        self.test_counter += 1
        return f"Test User {self.test_counter}"

    def test_create_account_with_app_password(self):
        """Test creating a new account with app_password."""
        # Generate test data
        test_email = self._generate_email()
        test_password = self._generate_password()
        test_display_name = self._generate_name()

        # Create account with app_password
        account = self.client.get_or_create_account(
            email_address=test_email,
            auth_method=None,
            oauth_refresh_token=None,
            display_name=test_display_name,
            app_password=test_password
        )

        # Verify account was created with correct fields
        self.assertIsNotNone(account)
        self.assertEqual(account.email_address, test_email.lower())
        self.assertEqual(account.display_name, test_display_name)
        self.assertEqual(account.app_password, test_password)
        self.assertTrue(account.is_active)

    def test_update_existing_account_with_app_password(self):
        """Test updating an existing account with a new app_password."""
        # Generate test data
        test_email = self._generate_email()
        initial_password = self._generate_password()
        initial_display_name = self._generate_name()

        # Create account with initial password
        account1 = self.client.get_or_create_account(
            email_address=test_email,
            auth_method=None,
            oauth_refresh_token=None,
            display_name=initial_display_name,
            app_password=initial_password
        )

        # Verify initial creation
        self.assertEqual(account1.app_password, initial_password)

        # Update account with new password
        new_password = self._generate_password()
        account2 = self.client.get_or_create_account(
            email_address=test_email,
            display_name=None,
            auth_method=None,
            oauth_refresh_token=None,
            app_password=new_password
        )

        # Verify password was updated
        self.assertEqual(account2.email_address, test_email.lower())
        self.assertEqual(account2.app_password, new_password)
        self.assertEqual(account2.id, account1.id)  # Same account ID

    def test_create_account_without_app_password(self):
        """Test that account can still be created without app_password (backward compatibility)."""
        # Generate test data
        test_email = self._generate_email()
        test_display_name = self._generate_name()

        # Create account without app_password
        account = self.client.get_or_create_account(
            email_address=test_email,
            app_password=None,
            auth_method=None,
            oauth_refresh_token=None,
            display_name=test_display_name
            # No app_password parameter
        )

        # Verify account was created
        self.assertIsNotNone(account)
        self.assertEqual(account.email_address, test_email.lower())
        self.assertEqual(account.display_name, test_display_name)
        self.assertIsNone(account.app_password)  # Should be None

    def test_update_account_preserve_password_when_not_provided(self):
        """Test that existing app_password is preserved when not provided in update."""
        # Generate test data
        test_email = self._generate_email()
        test_password = self._generate_password()
        initial_display_name = "Initial Name"
        new_display_name = "Updated Name"

        # Create account with password
        account1 = self.client.get_or_create_account(
            email_address=test_email,
            auth_method=None,
            oauth_refresh_token=None,
            display_name=initial_display_name,
            app_password=test_password
        )

        # Update account with new display name but no password
        account2 = self.client.get_or_create_account(
            email_address=test_email,
            app_password=None,
            auth_method=None,
            oauth_refresh_token=None,
            display_name=new_display_name
            # No app_password - should preserve existing
        )

        # Verify password was preserved and display name was updated
        self.assertEqual(account2.app_password, test_password)
        self.assertEqual(account2.display_name, new_display_name)

    def test_retrieve_account_with_app_password(self):
        """Test retrieving an account and verifying app_password persists."""
        # Generate test data
        test_email = self._generate_email()
        test_password = self._generate_password()
        test_display_name = self._generate_name()

        # Create account with app_password
        created_account = self.client.get_or_create_account(
            email_address=test_email,
            auth_method=None,
            oauth_refresh_token=None,
            display_name=test_display_name,
            app_password=test_password
        )

        # Retrieve the account
        retrieved_account = self.client.get_account_by_email(test_email)

        # Verify retrieved account has the app_password
        self.assertIsNotNone(retrieved_account)
        self.assertEqual(retrieved_account.email_address, test_email.lower())
        self.assertEqual(retrieved_account.app_password, test_password)
        self.assertEqual(retrieved_account.display_name, test_display_name)

    def test_multiple_accounts_with_different_passwords(self):
        """Test that multiple accounts can have different app_passwords."""
        accounts_data = []

        # Create multiple accounts
        for _ in range(3):
            email = self._generate_email()
            password = self._generate_password()
            display_name = self._generate_name()

            account = self.client.get_or_create_account(
                email_address=email,
                auth_method=None,
                oauth_refresh_token=None,
                display_name=display_name,
                app_password=password
            )

            accounts_data.append({
                'email': email.lower(),
                'password': password,
                'display_name': display_name
            })

        # Verify each account has its own password
        for data in accounts_data:
            account = self.client.get_account_by_email(data['email'])
            self.assertIsNotNone(account)
            self.assertEqual(account.app_password, data['password'])
            self.assertEqual(account.display_name, data['display_name'])


if __name__ == '__main__':
    unittest.main()