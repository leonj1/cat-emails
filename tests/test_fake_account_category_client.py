"""
Tests for FakeAccountCategoryClient to ensure it properly implements the interface.
"""
import unittest
from datetime import date, datetime
from tests.fake_account_category_client import FakeAccountCategoryClient, FakeEmailAccount


class TestFakeAccountCategoryClient(unittest.TestCase):
    """Test cases for FakeAccountCategoryClient."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = FakeAccountCategoryClient()
        self.test_email = "test@example.com"
        self.test_display_name = "Test User"

    def test_get_or_create_account_creates_new(self):
        """Test creating a new account."""
        account = self.client.get_or_create_account(self.test_email, self.test_display_name, None, None)

        self.assertIsInstance(account, FakeEmailAccount)
        self.assertEqual(account.email_address, self.test_email)
        self.assertEqual(account.display_name, self.test_display_name)
        self.assertTrue(account.is_active)
        self.assertIsNone(account.last_scan_at)

    def test_get_or_create_account_returns_existing(self):
        """Test that get_or_create returns existing account."""
        # Create account
        account1 = self.client.get_or_create_account(self.test_email, self.test_display_name, None, None)

        # Get the same account
        account2 = self.client.get_or_create_account(self.test_email, "Different Name", None, None)

        # Should be the same account
        self.assertEqual(account1.id, account2.id)
        self.assertEqual(account1.email_address, account2.email_address)
        # Display name should not change
        self.assertEqual(account2.display_name, self.test_display_name)

    def test_get_or_create_account_invalid_email(self):
        """Test that invalid email raises ValueError."""
        with self.assertRaises(ValueError):
            self.client.get_or_create_account("", None, None, None)

        with self.assertRaises(ValueError):
            self.client.get_or_create_account("   ", None, None, None)

    def test_get_account_by_email_found(self):
        """Test retrieving an existing account."""
        # Create account
        created = self.client.get_or_create_account(self.test_email, None, None, None)

        # Retrieve it
        retrieved = self.client.get_account_by_email(self.test_email)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, created.id)
        self.assertEqual(retrieved.email_address, self.test_email)

    def test_get_account_by_email_not_found(self):
        """Test retrieving a non-existent account returns None."""
        result = self.client.get_account_by_email("nonexistent@example.com")
        self.assertIsNone(result)

    def test_get_account_by_email_invalid(self):
        """Test that invalid email raises ValueError."""
        with self.assertRaises(ValueError):
            self.client.get_account_by_email("")

    def test_update_account_last_scan(self):
        """Test updating last scan timestamp."""
        # Create account
        account = self.client.get_or_create_account(self.test_email, None, None, None)
        self.assertIsNone(account.last_scan_at)

        # Update last scan
        self.client.update_account_last_scan(self.test_email)

        # Verify it was updated
        updated = self.client.get_account_by_email(self.test_email)
        self.assertIsNotNone(updated.last_scan_at)
        self.assertIsInstance(updated.last_scan_at, datetime)

    def test_update_account_last_scan_invalid_email(self):
        """Test that invalid email raises ValueError."""
        with self.assertRaises(ValueError):
            self.client.update_account_last_scan("")

    def test_record_category_stats(self):
        """Test recording category statistics."""
        # Create account first
        self.client.get_or_create_account(self.test_email, None, None, None)

        # Record stats
        stats_date = date.today()
        category_stats = {
            "Marketing": {"total": 10, "deleted": 8, "kept": 2, "archived": 0},
            "Personal": {"total": 5, "deleted": 0, "kept": 5, "archived": 0}
        }

        self.client.record_category_stats(self.test_email, stats_date, category_stats)

        # Verify stats were stored
        self.assertIn(self.test_email, self.client.category_stats)
        self.assertEqual(len(self.client.category_stats[self.test_email]), 1)

    def test_record_category_stats_invalid_email(self):
        """Test that invalid email raises ValueError."""
        with self.assertRaises(ValueError):
            self.client.record_category_stats("", date.today(), {})

    def test_get_top_categories(self):
        """Test retrieving top categories."""
        # Create account
        self.client.get_or_create_account(self.test_email, None, None, None)

        # Record some stats
        stats_date = date.today()
        category_stats = {
            "Marketing": {"total": 10, "deleted": 8, "kept": 2, "archived": 0},
            "Personal": {"total": 5, "deleted": 0, "kept": 5, "archived": 0},
            "Work": {"total": 15, "deleted": 5, "kept": 10, "archived": 0}
        }
        self.client.record_category_stats(self.test_email, stats_date, category_stats)

        # Get top categories
        response = self.client.get_top_categories(self.test_email, days=30, limit=10)

        self.assertEqual(response.email_address, self.test_email)
        self.assertEqual(response.period.days, 30)
        self.assertEqual(len(response.top_categories), 3)
        self.assertEqual(response.total_emails, 30)  # 10 + 5 + 15

        # Should be sorted by total
        self.assertEqual(response.top_categories[0].category, 'Work')
        self.assertEqual(response.top_categories[0].total_count, 15)
        self.assertEqual(response.top_categories[1].category, 'Marketing')
        self.assertEqual(response.top_categories[1].total_count, 10)
        self.assertEqual(response.top_categories[2].category, 'Personal')
        self.assertEqual(response.top_categories[2].total_count, 5)

    def test_get_top_categories_with_counts(self):
        """Test retrieving top categories with detailed counts."""
        # Create account
        self.client.get_or_create_account(self.test_email, None, None, None)

        # Record some stats
        category_stats = {
            "Marketing": {"total": 10, "deleted": 8, "kept": 2, "archived": 0}
        }
        self.client.record_category_stats(self.test_email, date.today(), category_stats)

        # Get top categories with counts
        response = self.client.get_top_categories(
            self.test_email,
            days=30,
            limit=10,
            include_counts=True
        )

        self.assertEqual(len(response.top_categories), 1)
        category = response.top_categories[0]
        self.assertEqual(category.category, 'Marketing')
        self.assertEqual(category.total_count, 10)
        self.assertEqual(category.deleted_count, 8)
        self.assertEqual(category.kept_count, 2)
        self.assertEqual(category.archived_count, 0)

    def test_get_top_categories_limit(self):
        """Test that limit parameter works correctly."""
        # Create account
        self.client.get_or_create_account(self.test_email, None, None, None)

        # Record stats for 5 categories
        category_stats = {
            f"Category{i}": {"total": i * 5, "deleted": 0, "kept": i * 5, "archived": 0}
            for i in range(1, 6)
        }
        self.client.record_category_stats(self.test_email, date.today(), category_stats)

        # Get top 3 categories
        response = self.client.get_top_categories(self.test_email, days=30, limit=3)

        self.assertEqual(len(response.top_categories), 3)
        # Total emails should be the sum of the top 3 only
        self.assertEqual(response.total_emails, 5 * 5 + 4 * 5 + 3 * 5)  # Category5 + Category4 + Category3

    def test_get_top_categories_account_not_found(self):
        """Test that getting categories for non-existent account raises ValueError."""
        with self.assertRaises(ValueError):
            self.client.get_top_categories("nonexistent@example.com", days=30)

    def test_get_top_categories_invalid_days(self):
        """Test that invalid days parameter raises ValueError."""
        self.client.get_or_create_account(self.test_email, None, None, None)

        with self.assertRaises(ValueError):
            self.client.get_top_categories(self.test_email, days=0)

        with self.assertRaises(ValueError):
            self.client.get_top_categories(self.test_email, days=366)

    def test_get_top_categories_invalid_limit(self):
        """Test that invalid limit parameter raises ValueError."""
        self.client.get_or_create_account(self.test_email, None, None, None)

        with self.assertRaises(ValueError):
            self.client.get_top_categories(self.test_email, days=30, limit=0)

        with self.assertRaises(ValueError):
            self.client.get_top_categories(self.test_email, days=30, limit=51)

    def test_get_all_accounts_empty(self):
        """Test getting all accounts when none exist."""
        accounts = self.client.get_all_accounts(active_only=True)
        self.assertEqual(len(accounts), 0)

    def test_get_all_accounts_with_data(self):
        """Test getting all accounts."""
        # Create multiple accounts
        self.client.get_or_create_account("user1@example.com", None, None, None)
        self.client.get_or_create_account("user2@example.com", None, None, None)
        self.client.get_or_create_account("user3@example.com", None, None, None)

        accounts = self.client.get_all_accounts(active_only=True)
        self.assertEqual(len(accounts), 3)

    def test_get_all_accounts_active_only(self):
        """Test filtering accounts by active status."""
        # Create accounts
        self.client.get_or_create_account("user1@example.com", None, None, None)
        self.client.get_or_create_account("user2@example.com", None, None, None)

        # Deactivate one
        self.client.deactivate_account("user1@example.com")

        # Get active accounts only
        active_accounts = self.client.get_all_accounts(active_only=True)
        self.assertEqual(len(active_accounts), 1)
        self.assertEqual(active_accounts[0].email_address, "user2@example.com")

        # Get all accounts
        all_accounts = self.client.get_all_accounts(active_only=False)
        self.assertEqual(len(all_accounts), 2)

    def test_deactivate_account(self):
        """Test deactivating an account."""
        # Create account
        self.client.get_or_create_account(self.test_email, None, None, None)

        # Deactivate it
        result = self.client.deactivate_account(self.test_email)
        self.assertTrue(result)

        # Verify it's deactivated
        account = self.client.get_account_by_email(self.test_email)
        self.assertFalse(account.is_active)

    def test_deactivate_account_not_found(self):
        """Test deactivating a non-existent account returns False."""
        result = self.client.deactivate_account("nonexistent@example.com")
        self.assertFalse(result)

    def test_deactivate_account_invalid_email(self):
        """Test that invalid email raises ValueError."""
        with self.assertRaises(ValueError):
            self.client.deactivate_account("")

    def test_email_case_insensitive(self):
        """Test that email addresses are case-insensitive."""
        # Create account with uppercase
        account1 = self.client.get_or_create_account("Test@Example.COM", None, None, None)

        # Retrieve with lowercase
        account2 = self.client.get_account_by_email("test@example.com")

        self.assertIsNotNone(account2)
        self.assertEqual(account1.id, account2.id)

    def test_record_category_stats_integer_format(self):
        """Test recording category stats with integer counts (simplified format)."""
        # Create account
        self.client.get_or_create_account(self.test_email, None, None, None)

        # Record stats with integer format
        category_stats = {
            "Marketing": 10,
            "Personal": 5
        }
        self.client.record_category_stats(self.test_email, date.today(), category_stats)

        # Get top categories
        response = self.client.get_top_categories(self.test_email, days=30)

        self.assertEqual(len(response.top_categories), 2)
        self.assertEqual(response.top_categories[0].category, 'Marketing')
        self.assertEqual(response.top_categories[0].total_count, 10)


if __name__ == '__main__':
    unittest.main()
