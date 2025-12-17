#!/usr/bin/env python3
"""
Integration test for AccountCategoryClient session detachment fix.

This test verifies that when AccountCategoryClient owns its session (owns_session=True),
the returned EmailAccount objects are properly detached from the session to avoid
"Instance <EmailAccount> is not bound to a session" errors.

This specifically tests the fix for the API error that was occurring when creating
accounts via the /api/accounts endpoint.
"""
import unittest
import tempfile
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import init_database, EmailAccount
from clients.account_category_client import AccountCategoryClient
from repositories.sqlalchemy_repository import SQLAlchemyRepository


class TestAccountSessionDetachmentIntegration(unittest.TestCase):
    """
    Integration test to verify that AccountCategoryClient properly detaches
    EmailAccount objects from sessions when owns_session=True.

    This reproduces the exact scenario that was causing the API error:
    "Database error in create_account: Instance <EmailAccount> is not bound to a session"
    """

    def setUp(self):
        """Set up test with a temporary SQLite database."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        # Track created test emails for cleanup
        self.test_emails = []

    def tearDown(self):
        """Clean up temporary database."""
        # Remove temp database file
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_create_account_with_owns_session_true(self):
        """
        Test that creating an account with owns_session=True returns a detached object.

        This simulates the API scenario where AccountCategoryClient is created without
        a session parameter, causing owns_session to be True.
        """
        # Create repository and client (owns_session will be True)
        repository = SQLAlchemyRepository(self.temp_db_path)
        client = AccountCategoryClient(repository=repository)

        # Create test account
        test_email = "test_detached@example.com"
        test_display_name = "Test User"
        test_app_password = "test_password_123"

        # Create account (this would fail with session binding error before the fix)
        account = client.get_or_create_account(
            email_address=test_email,
            display_name=test_display_name,
            app_password=test_app_password
        )

        # Verify account was created
        self.assertIsNotNone(account)
        self.assertEqual(account.email_address, test_email.lower())
        self.assertEqual(account.display_name, test_display_name)
        self.assertEqual(account.app_password, test_app_password)
        self.assertTrue(account.is_active)

        # Key test: Try to access account attributes after session is closed
        # This would fail with "not bound to session" error before the fix
        try:
            # Access all attributes that might trigger lazy loading
            _ = account.id
            _ = account.email_address
            _ = account.display_name
            _ = account.app_password
            _ = account.is_active
            _ = account.created_at
            _ = account.updated_at
            _ = account.last_scan_at

            # If we get here without error, the fix is working
            self.assertTrue(True, "Successfully accessed all account attributes")
        except Exception as e:
            self.fail(f"Failed to access account attributes: {str(e)}")

    def test_update_account_with_owns_session_true(self):
        """
        Test that updating an existing account with owns_session=True returns a detached object.
        """
        # Create repository and client (owns_session will be True)
        repository = SQLAlchemyRepository(self.temp_db_path)
        client = AccountCategoryClient(repository=repository)

        test_email = "test_update@example.com"

        # Create account first
        account1 = client.get_or_create_account(
            email_address=test_email,
            display_name="Initial Name",
            app_password="initial_password"
        )

        # Update account
        account2 = client.get_or_create_account(
            email_address=test_email,
            display_name="Updated Name",
            app_password="updated_password"
        )

        # Verify update worked and object is detached
        self.assertEqual(account2.email_address, test_email.lower())
        self.assertEqual(account2.display_name, "Updated Name")
        self.assertEqual(account2.app_password, "updated_password")
        self.assertEqual(account2.id, account1.id)  # Same account

        # Try to access all attributes (would fail if not detached)
        try:
            _ = account2.id
            _ = account2.email_address
            _ = account2.display_name
            _ = account2.app_password
            _ = account2.is_active
            _ = account2.created_at
            _ = account2.updated_at
            self.assertTrue(True, "Successfully accessed updated account attributes")
        except Exception as e:
            self.fail(f"Failed to access updated account attributes: {str(e)}")

    def test_retrieve_account_with_owns_session_true(self):
        """
        Test that retrieving an account with owns_session=True returns a detached object.
        """
        # Create repository and client (owns_session will be True)
        repository = SQLAlchemyRepository(self.temp_db_path)
        client = AccountCategoryClient(repository=repository)

        test_email = "test_retrieve@example.com"

        # Create account first
        client.get_or_create_account(
            email_address=test_email,
            display_name="Test User",
            app_password="test_pass"
        )

        # Retrieve account using get_account_by_email
        retrieved = client.get_account_by_email(test_email)

        # Verify retrieval worked
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.email_address, test_email.lower())
        self.assertEqual(retrieved.display_name, "Test User")
        self.assertEqual(retrieved.app_password, "test_pass")

        # Try to access all attributes (would fail if not detached)
        try:
            _ = retrieved.id
            _ = retrieved.email_address
            _ = retrieved.display_name
            _ = retrieved.app_password
            _ = retrieved.is_active
            _ = retrieved.created_at
            _ = retrieved.updated_at
            self.assertTrue(True, "Successfully accessed retrieved account attributes")
        except Exception as e:
            self.fail(f"Failed to access retrieved account attributes: {str(e)}")

    def test_list_accounts_with_owns_session_true(self):
        """
        Test that listing accounts with owns_session=True returns detached objects.

        Note: get_all_accounts already had the fix, but let's verify it still works.
        """
        # Create repository and client (owns_session will be True)
        repository = SQLAlchemyRepository(self.temp_db_path)
        client = AccountCategoryClient(repository=repository)

        # Create multiple test accounts
        test_accounts = [
            ("test1@example.com", "User 1", "pass1"),
            ("test2@example.com", "User 2", "pass2"),
            ("test3@example.com", "User 3", "pass3"),
        ]

        for email, name, password in test_accounts:
            client.get_or_create_account(
                email_address=email,
                display_name=name,
                app_password=password
            )

        # Get all accounts
        accounts = client.get_all_accounts(active_only=True)

        # Verify we got all accounts
        self.assertEqual(len(accounts), 3)

        # Try to access attributes of all accounts (would fail if not detached)
        for account in accounts:
            try:
                _ = account.id
                _ = account.email_address
                _ = account.display_name
                _ = account.is_active
                _ = account.created_at
                _ = account.updated_at
                _ = account.last_scan_at
            except Exception as e:
                self.fail(f"Failed to access account attributes for {account.email_address}: {str(e)}")

        self.assertTrue(True, "Successfully accessed all account attributes in list")

    def test_api_simulation_complete_flow(self):
        """
        Simulate the complete API flow that was causing the error.

        This reproduces exactly what happens when the API's create_account endpoint is called.
        """
        # Step 1: API creates AccountCategoryClient without session (like in get_account_service)
        client = AccountCategoryClient(db_path=self.temp_db_path)

        # Step 2: API calls get_or_create_account (like in create_account endpoint)
        test_email = "api_test@example.com"
        account = client.get_or_create_account(
            email_address=test_email,
            display_name="API Test User",
            app_password="api_password"
        )

        # Step 3: API tries to access account properties for response
        # This is where the "not bound to session" error occurred
        try:
            # Simulate building the API response
            response_data = {
                "id": account.id,
                "email_address": account.email_address,
                "display_name": account.display_name,
                "is_active": account.is_active,
                "created_at": account.created_at.isoformat() if account.created_at else None,
                "updated_at": account.updated_at.isoformat() if account.updated_at else None,
            }

            # Verify response data is complete
            self.assertIsNotNone(response_data["id"])
            self.assertEqual(response_data["email_address"], test_email.lower())
            self.assertEqual(response_data["display_name"], "API Test User")
            self.assertTrue(response_data["is_active"])
            self.assertIsNotNone(response_data["created_at"])

            self.assertTrue(True, "Successfully simulated API response building")
        except Exception as e:
            self.fail(f"Failed to build API response: {str(e)}")

    def test_account_not_found_returns_none(self):
        """
        Test that get_account_by_email returns None for non-existent accounts.
        """
        # Create repository and client (owns_session will be True)
        repository = SQLAlchemyRepository(self.temp_db_path)
        client = AccountCategoryClient(repository=repository)

        # Try to retrieve non-existent account
        account = client.get_account_by_email("nonexistent@example.com")

        # Should return None, not raise an error
        self.assertIsNone(account)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)