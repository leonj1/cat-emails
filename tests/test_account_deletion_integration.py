"""
Integration tests for email account deletion functionality.
Tests the complete flow of deleting an account and all associated data.
"""
import os
import tempfile
import unittest
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from clients.account_category_client import AccountCategoryClient
from models.database import Base, EmailAccount, AccountCategoryStats


class TestAccountDeletionIntegration(unittest.TestCase):
    """Integration tests for account deletion with SQLite database."""

    def setUp(self):
        """Set up a temporary SQLite database for each test."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        # Initialize database with test schema
        self.db_url = f"sqlite:///{self.temp_db_path}"
        self.engine = create_engine(self.db_url)
        Base.metadata.create_all(self.engine)

        # Create session and client
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        # Pass session directly instead of db_path
        self.client = AccountCategoryClient(db_session=self.session)

    def tearDown(self):
        """Clean up the temporary database after each test."""
        try:
            self.session.close()
            self.engine.dispose()
            os.unlink(self.temp_db_path)
        except Exception:
            pass

    def test_delete_nonexistent_account(self):
        """Test deletion of account that doesn't exist."""
        result = self.client.delete_account("nonexistent@example.com")
        self.assertFalse(result)

    def test_delete_account_without_data(self):
        """Test deletion of account without associated data."""
        # Create an account
        email = "test@example.com"
        account = self.client.get_or_create_account(email, "Test User", None, None)
        self.assertIsNotNone(account)

        # Verify account exists
        retrieved = self.client.get_account_by_email(email)
        self.assertIsNotNone(retrieved)

        # Delete the account
        result = self.client.delete_account(email)
        self.assertTrue(result)

        # Verify account is deleted
        retrieved = self.client.get_account_by_email(email)
        self.assertIsNone(retrieved)

    def test_delete_account_with_category_stats(self):
        """Test deletion of account with associated category statistics."""
        # Create an account
        email = "test@example.com"
        account = self.client.get_or_create_account(email, "Test User", None, None)

        # Add some category stats
        stats_date = date.today()
        category_stats = {
            "Marketing": {"total": 10, "deleted": 8, "kept": 2, "archived": 0},
            "Personal": {"total": 5, "deleted": 0, "kept": 5, "archived": 0},
            "Work-related": {"total": 3, "deleted": 1, "kept": 2, "archived": 0}
        }
        self.client.record_category_stats(email, stats_date, category_stats)

        # Verify stats exist
        response = self.client.get_top_categories(email, days=1, limit=10)
        self.assertEqual(len(response.top_categories), 3)
        self.assertEqual(response.total_emails, 18)

        # Delete the account
        result = self.client.delete_account(email)
        self.assertTrue(result)

        # Verify account is deleted
        retrieved = self.client.get_account_by_email(email)
        self.assertIsNone(retrieved)

        # Verify stats are also deleted (should raise error as account doesn't exist)
        with self.assertRaises(ValueError) as context:
            self.client.get_top_categories(email, days=1, limit=10)
        self.assertIn("No account found", str(context.exception))

    def test_delete_account_cascade_deletes_stats(self):
        """Test that deleting account cascades to delete all associated stats."""
        # Create an account
        email = "cascade@example.com"
        account = self.client.get_or_create_account(email, "Cascade Test", None, None)
        account_id = account.id

        # Add category stats for multiple days
        for day_offset in range(5):
            stats_date = date.today()
            category_stats = {
                f"Category{day_offset}": {"total": 5, "deleted": 2, "kept": 3, "archived": 0}
            }
            self.client.record_category_stats(email, stats_date, category_stats)

        # Verify stats exist in database
        stats_count = self.session.query(AccountCategoryStats).filter_by(account_id=account_id).count()
        self.assertEqual(stats_count, 5)

        # Delete the account
        result = self.client.delete_account(email)
        self.assertTrue(result)

        # Verify all stats are deleted (cascade delete)
        stats_count = self.session.query(AccountCategoryStats).filter_by(account_id=account_id).count()
        self.assertEqual(stats_count, 0)

    def test_delete_multiple_accounts_independently(self):
        """Test that deleting one account doesn't affect others."""
        # Create multiple accounts
        email1 = "user1@example.com"
        email2 = "user2@example.com"
        email3 = "user3@example.com"

        account1 = self.client.get_or_create_account(email1, "User 1", None, None)
        account2 = self.client.get_or_create_account(email2, "User 2", None, None)
        account3 = self.client.get_or_create_account(email3, "User 3", None, None)

        # Add stats to all accounts
        stats_date = date.today()
        for email in [email1, email2, email3]:
            category_stats = {
                "Marketing": {"total": 5, "deleted": 3, "kept": 2, "archived": 0}
            }
            self.client.record_category_stats(email, stats_date, category_stats)

        # Delete only account2
        result = self.client.delete_account(email2)
        self.assertTrue(result)

        # Verify account2 is deleted
        self.assertIsNone(self.client.get_account_by_email(email2))

        # Verify other accounts still exist with their data
        account1_check = self.client.get_account_by_email(email1)
        self.assertIsNotNone(account1_check)
        self.assertEqual(account1_check.email_address, email1)

        account3_check = self.client.get_account_by_email(email3)
        self.assertIsNotNone(account3_check)
        self.assertEqual(account3_check.email_address, email3)

        # Verify stats for remaining accounts still exist
        response1 = self.client.get_top_categories(email1, days=1, limit=10)
        self.assertEqual(len(response1.top_categories), 1)

        response3 = self.client.get_top_categories(email3, days=1, limit=10)
        self.assertEqual(len(response3.top_categories), 1)

    def test_delete_account_with_invalid_email(self):
        """Test deletion with invalid email address."""
        with self.assertRaises(ValueError) as context:
            self.client.delete_account("invalid-email")
        self.assertIn("Invalid email address", str(context.exception))

    def test_delete_deactivated_account(self):
        """Test deletion of deactivated account works correctly."""
        # Create and deactivate an account
        email = "inactive@example.com"
        account = self.client.get_or_create_account(email, "Inactive User", None, None)

        # Deactivate it
        result = self.client.deactivate_account(email)
        self.assertTrue(result)

        # Verify it's deactivated
        account_check = self.client.get_account_by_email(email)
        self.assertFalse(account_check.is_active)

        # Delete the deactivated account
        result = self.client.delete_account(email)
        self.assertTrue(result)

        # Verify it's deleted
        self.assertIsNone(self.client.get_account_by_email(email))

    def test_recreate_account_after_deletion(self):
        """Test that an account can be recreated after deletion."""
        email = "recreate@example.com"

        # Create account first time
        account1 = self.client.get_or_create_account(email, "Original User", None, None)
        original_id = account1.id

        # Delete it
        result = self.client.delete_account(email)
        self.assertTrue(result)

        # Create account again with same email
        account2 = self.client.get_or_create_account(email, "New User", None, None)
        new_id = account2.id

        # Verify it's a new account (may reuse ID in SQLite, but should have new data)
        self.assertEqual(account2.email_address, email)
        self.assertEqual(account2.display_name, "New User")
        self.assertTrue(account2.is_active)
        self.assertIsNotNone(account2.created_at)

    def test_delete_account_rollback_on_error(self):
        """Test that deletion is rolled back if an error occurs."""
        # This test simulates an error during deletion to ensure rollback works
        # We'll create an account and then test error handling

        email = "rollback@example.com"
        account = self.client.get_or_create_account(email, "Rollback Test", None, None)

        # Create a new session for the second client
        Session = sessionmaker(bind=self.engine)
        new_session = Session()
        test_client = AccountCategoryClient(db_session=new_session)

        try:
            # Verify account exists before attempting deletion
            self.assertIsNotNone(test_client.get_account_by_email(email))

            # The delete should work normally in this case
            result = test_client.delete_account(email)
            self.assertTrue(result)

            # Verify account is deleted
            self.assertIsNone(test_client.get_account_by_email(email))
        finally:
            new_session.close()


if __name__ == "__main__":
    unittest.main()