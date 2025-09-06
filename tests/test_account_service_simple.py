"""
Simple unit tests for AccountCategoryService to demonstrate core functionality.
This is a subset of tests that are easier to run and debug.
"""
import unittest
from unittest.mock import Mock, patch
import tempfile
import os
from datetime import datetime, date, timedelta

from services.account_category_service import AccountCategoryService
from models.database import init_database


class TestAccountCategoryServiceSimple(unittest.TestCase):
    """Simple test cases for AccountCategoryService."""

    def setUp(self):
        """Set up test fixtures with in-memory database."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Initialize database
        self.engine = init_database(self.db_path)
        
        # Create service instance
        self.service = AccountCategoryService(db_path=self.db_path)
        
        # Test data
        self.test_email = "test@gmail.com"
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.engine.dispose()
        
        # Remove temp database file
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_service_initialization(self):
        """Test service can be initialized."""
        service = AccountCategoryService(db_path=self.db_path)
        self.assertIsNotNone(service)
        self.assertTrue(service.owns_session)

    def test_email_validation_valid(self):
        """Test email validation with valid emails."""
        valid_emails = [
            "test@gmail.com",
            "user.name@example.org",
            "firstname.lastname@company.co.uk",
        ]
        
        for email in valid_emails:
            result = self.service._validate_email_address(email)
            self.assertEqual(result, email.lower())

    def test_email_validation_invalid(self):
        """Test email validation with invalid emails."""
        invalid_emails = ["", "invalid-email", "@gmail.com", "test@", None]
        
        for invalid_email in invalid_emails:
            with self.assertRaises(ValueError):
                self.service._validate_email_address(invalid_email)

    def test_create_new_account(self):
        """Test creating a new account."""
        account = self.service.get_or_create_account(self.test_email, "Test User")
        
        self.assertIsNotNone(account)
        self.assertEqual(account.email_address, self.test_email)
        self.assertEqual(account.display_name, "Test User")
        self.assertTrue(account.is_active)

    def test_get_existing_account(self):
        """Test retrieving an existing account."""
        # Create account first
        created_account = self.service.get_or_create_account(self.test_email, "Original Name")
        
        # Retrieve same account
        retrieved_account = self.service.get_account_by_email(self.test_email)
        
        self.assertIsNotNone(retrieved_account)
        self.assertEqual(retrieved_account.id, created_account.id)
        self.assertEqual(retrieved_account.email_address, self.test_email)

    def test_get_nonexistent_account(self):
        """Test retrieving non-existent account returns None."""
        account = self.service.get_account_by_email("nonexistent@gmail.com")
        self.assertIsNone(account)

    def test_update_last_scan(self):
        """Test updating last scan timestamp."""
        # Create account first
        self.service.get_or_create_account(self.test_email, "Test User")
        
        # Update last scan
        before = datetime.utcnow()
        self.service.update_account_last_scan(self.test_email)
        after = datetime.utcnow()
        
        # Verify timestamp was updated
        account = self.service.get_account_by_email(self.test_email)
        self.assertIsNotNone(account.last_scan_at)
        self.assertGreaterEqual(account.last_scan_at, before)
        self.assertLessEqual(account.last_scan_at, after)

    def test_record_category_stats(self):
        """Test recording category statistics."""
        # Create account first
        self.service.get_or_create_account(self.test_email, "Test User")
        
        # Record stats
        stats_date = date.today()
        category_stats = {
            "Marketing": {"total": 10, "deleted": 8, "kept": 2, "archived": 0},
            "Personal": {"total": 5, "deleted": 0, "kept": 5, "archived": 0}
        }
        
        # Should not raise exception
        try:
            self.service.record_category_stats(self.test_email, stats_date, category_stats)
        except Exception as e:
            self.fail(f"record_category_stats raised exception: {e}")

    def test_get_top_categories_basic(self):
        """Test getting top categories (basic functionality)."""
        # Create account and record some stats
        self.service.get_or_create_account(self.test_email, "Test User")
        
        stats_date = date.today()
        category_stats = {
            "Marketing": {"total": 10, "deleted": 5, "kept": 5, "archived": 0},
            "Personal": {"total": 3, "deleted": 0, "kept": 3, "archived": 0}
        }
        self.service.record_category_stats(self.test_email, stats_date, category_stats)
        
        # Get top categories
        response = self.service.get_top_categories(self.test_email, days=1)
        
        # Verify response structure
        self.assertEqual(response.email_address, self.test_email)
        self.assertEqual(response.period.days, 1)
        self.assertGreaterEqual(len(response.top_categories), 1)
        
        # Verify top category is Marketing (higher count)
        top_category = response.top_categories[0]
        self.assertEqual(top_category.category, "Marketing")
        self.assertEqual(top_category.total_count, 10)

    def test_get_all_accounts(self):
        """Test getting all accounts."""
        # Create a few accounts
        emails = ["user1@gmail.com", "user2@gmail.com", "user3@gmail.com"]
        for email in emails:
            self.service.get_or_create_account(email, f"User {email}")
        
        # Get all accounts
        accounts = self.service.get_all_accounts()
        
        self.assertEqual(len(accounts), 3)
        account_emails = {acc.email_address for acc in accounts}
        self.assertEqual(account_emails, set(emails))

    def test_deactivate_account(self):
        """Test deactivating an account."""
        # Create account
        self.service.get_or_create_account(self.test_email, "Test User")
        
        # Deactivate
        result = self.service.deactivate_account(self.test_email)
        self.assertTrue(result)
        
        # Verify deactivation
        account = self.service.get_account_by_email(self.test_email)
        self.assertFalse(account.is_active)

    def test_deactivate_nonexistent_account(self):
        """Test deactivating non-existent account."""
        result = self.service.deactivate_account("nonexistent@gmail.com")
        self.assertFalse(result)

    def test_invalid_parameter_validation(self):
        """Test parameter validation in get_top_categories."""
        self.service.get_or_create_account(self.test_email, "Test User")
        
        # Test invalid days
        with self.assertRaises(ValueError):
            self.service.get_top_categories(self.test_email, days=0)
        
        with self.assertRaises(ValueError):
            self.service.get_top_categories(self.test_email, days=366)
        
        # Test invalid limit
        with self.assertRaises(ValueError):
            self.service.get_top_categories(self.test_email, days=7, limit=0)
        
        with self.assertRaises(ValueError):
            self.service.get_top_categories(self.test_email, days=7, limit=51)

    def test_nonexistent_account_top_categories(self):
        """Test getting top categories for non-existent account."""
        with self.assertRaises(ValueError):
            self.service.get_top_categories("nonexistent@gmail.com", days=7)


if __name__ == "__main__":
    unittest.main()