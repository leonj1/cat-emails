"""
Unit tests for AccountCategoryService.
Provides comprehensive test coverage for account and category statistics management.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from datetime import datetime, date, timedelta
from typing import Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from services.account_category_service import AccountCategoryService
from models.database import Base, EmailAccount, AccountCategoryStats, init_database
from models.account_models import TopCategoriesResponse, CategoryStats, DatePeriod, EmailAccountInfo


class TestAccountCategoryService(unittest.TestCase):
    """Test cases for AccountCategoryService class."""

    def setUp(self):
        """Set up test fixtures with in-memory database."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Initialize database
        self.engine = init_database(self.db_path)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Create service instance using the test database
        self.service = AccountCategoryService(db_path=self.db_path)
        
        # Test data
        self.test_email = "test@gmail.com"
        self.invalid_emails = [
            "",
            "   ",
            "invalid-email",
            "@gmail.com",
            "test@",
            "test.gmail.com",
            None,
            123
        ]
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.session.close()
        self.engine.dispose()
        
        # Remove temp database file
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_init_with_db_path(self):
        """Test service initialization with database path."""
        service = AccountCategoryService(db_path=self.db_path)
        self.assertEqual(service.db_path, self.db_path)
        self.assertTrue(service.owns_session)
        self.assertIsNone(service.session)
        self.assertIsNotNone(service.engine)
        self.assertIsNotNone(service.Session)

    def test_init_with_session(self):
        """Test service initialization with existing session."""
        service = AccountCategoryService(db_session=self.session)
        self.assertFalse(service.owns_session)
        self.assertEqual(service.session, self.session)
        self.assertIsNone(service.engine)
        self.assertIsNone(service.Session)

    def test_validate_email_address_valid(self):
        """Test email address validation with valid emails."""
        valid_emails = [
            "test@gmail.com",
            "user.name+tag@example.org",
            "firstname.lastname@company.co.uk",
            "TEST@EXAMPLE.COM",  # Should be normalized to lowercase
        ]
        
        for email in valid_emails:
            result = self.service._validate_email_address(email)
            self.assertEqual(result, email.lower().strip())

    def test_validate_email_address_invalid(self):
        """Test email address validation with invalid emails."""
        for invalid_email in self.invalid_emails:
            with self.assertRaises(ValueError):
                self.service._validate_email_address(invalid_email)

    def test_get_or_create_account_new(self):
        """Test creating a new account."""
        display_name = "Test User"
        account = self.service.get_or_create_account(self.test_email, display_name)
        
        # Verify account properties
        self.assertIsNotNone(account.id)
        self.assertEqual(account.email_address, self.test_email)
        self.assertEqual(account.display_name, display_name)
        self.assertTrue(account.is_active)
        self.assertIsNotNone(account.created_at)
        self.assertIsNotNone(account.updated_at)
        
        # Verify account exists in database
        db_account = self.session.query(EmailAccount).filter_by(email_address=self.test_email).first()
        self.assertIsNotNone(db_account)
        self.assertEqual(db_account.email_address, self.test_email)

    def test_get_or_create_account_existing(self):
        """Test retrieving existing account."""
        # Create account first
        original_account = self.service.get_or_create_account(self.test_email, "Original Name")
        original_id = original_account.id
        
        # Retrieve same account
        retrieved_account = self.service.get_or_create_account(self.test_email, "Updated Name")
        
        # Should be same account with updated name
        self.assertEqual(retrieved_account.id, original_id)
        self.assertEqual(retrieved_account.display_name, "Updated Name")
        
        # Verify only one account exists in database
        account_count = self.session.query(EmailAccount).filter_by(email_address=self.test_email).count()
        self.assertEqual(account_count, 1)

    def test_get_or_create_account_reactivate(self):
        """Test reactivating an inactive account."""
        # Create and then deactivate account
        account = self.service.get_or_create_account(self.test_email, "Test User")
        self.service.deactivate_account(self.test_email)
        
        # Verify deactivation
        deactivated_account = self.service.get_account_by_email(self.test_email)
        self.assertFalse(deactivated_account.is_active)
        
        # Reactivate by getting/creating again
        reactivated_account = self.service.get_or_create_account(self.test_email, "Test User")
        self.assertTrue(reactivated_account.is_active)
        self.assertEqual(reactivated_account.id, account.id)

    def test_get_or_create_account_invalid_email(self):
        """Test account creation with invalid email."""
        for invalid_email in self.invalid_emails:
            with self.assertRaises(ValueError):
                self.service.get_or_create_account(invalid_email)

    @patch('services.account_category_service.logger')
    def test_get_or_create_account_database_error(self, mock_logger):
        """Test handling database errors during account creation."""
        with patch.object(self.service, '_get_or_create_account_impl') as mock_impl:
            mock_impl.side_effect = IntegrityError("Constraint violation", "orig", "stmt")
            
            with self.assertRaises(ValueError):
                self.service.get_or_create_account(self.test_email)
            
            mock_logger.error.assert_called()

    def test_get_account_by_email_existing(self):
        """Test retrieving existing account by email."""
        # Create account
        created_account = self.service.get_or_create_account(self.test_email, "Test User")
        
        # Retrieve account
        retrieved_account = self.service.get_account_by_email(self.test_email)
        
        self.assertIsNotNone(retrieved_account)
        self.assertEqual(retrieved_account.id, created_account.id)
        self.assertEqual(retrieved_account.email_address, self.test_email)

    def test_get_account_by_email_not_found(self):
        """Test retrieving non-existent account by email."""
        account = self.service.get_account_by_email("nonexistent@gmail.com")
        self.assertIsNone(account)

    def test_get_account_by_email_invalid(self):
        """Test retrieving account with invalid email."""
        for invalid_email in self.invalid_emails:
            with self.assertRaises(ValueError):
                self.service.get_account_by_email(invalid_email)

    def test_update_account_last_scan(self):
        """Test updating last scan timestamp."""
        # Create account
        self.service.get_or_create_account(self.test_email, "Test User")
        
        # Update last scan
        before_update = datetime.utcnow()
        self.service.update_account_last_scan(self.test_email)
        after_update = datetime.utcnow()
        
        # Verify timestamp was updated
        account = self.service.get_account_by_email(self.test_email)
        self.assertIsNotNone(account.last_scan_at)
        self.assertGreaterEqual(account.last_scan_at, before_update)
        self.assertLessEqual(account.last_scan_at, after_update)

    def test_update_account_last_scan_nonexistent(self):
        """Test updating last scan for non-existent account creates it."""
        # Update last scan for non-existent account
        self.service.update_account_last_scan(self.test_email)
        
        # Verify account was created
        account = self.service.get_account_by_email(self.test_email)
        self.assertIsNotNone(account)
        self.assertIsNotNone(account.last_scan_at)

    def test_record_category_stats_valid(self):
        """Test recording valid category statistics."""
        # Create account
        account = self.service.get_or_create_account(self.test_email, "Test User")
        account_id = account.id  # Get ID before potential session detachment
        
        # Test data
        stats_date = date.today()
        category_stats = {
            "Marketing": {"total": 10, "deleted": 8, "kept": 2, "archived": 0},
            "Personal": {"total": 5, "deleted": 0, "kept": 5, "archived": 0},
            "Work-related": {"total": 3, "deleted": 1, "kept": 2, "archived": 0}
        }
        
        # Record stats
        self.service.record_category_stats(self.test_email, stats_date, category_stats)
        
        # Verify stats were recorded - use fresh session query
        with self.service._get_session() as session:
            db_stats = session.query(AccountCategoryStats).filter_by(account_id=account_id).all()
            self.assertEqual(len(db_stats), 3)
            
            # Check individual stats
            marketing_stats = next((s for s in db_stats if s.category_name == "Marketing"), None)
            self.assertIsNotNone(marketing_stats)
            self.assertEqual(marketing_stats.email_count, 10)
            self.assertEqual(marketing_stats.deleted_count, 8)
            self.assertEqual(marketing_stats.kept_count, 2)
            self.assertEqual(marketing_stats.archived_count, 0)

    def test_record_category_stats_upsert(self):
        """Test updating existing category statistics (upsert behavior)."""
        # Create account and initial stats
        account = self.service.get_or_create_account(self.test_email, "Test User")
        account_id = account.id  # Get ID before potential session detachment
        stats_date = date.today()
        
        # Record initial stats
        initial_stats = {"Marketing": {"total": 5, "deleted": 3, "kept": 2, "archived": 0}}
        self.service.record_category_stats(self.test_email, stats_date, initial_stats)
        
        # Record updated stats for same date and category
        updated_stats = {"Marketing": {"total": 10, "deleted": 8, "kept": 2, "archived": 0}}
        self.service.record_category_stats(self.test_email, stats_date, updated_stats)
        
        # Verify only one record exists with updated values - use fresh session query
        with self.service._get_session() as session:
            db_stats = session.query(AccountCategoryStats).filter_by(
                account_id=account_id, 
                category_name="Marketing",
                date=stats_date
            ).all()
            self.assertEqual(len(db_stats), 1)
            self.assertEqual(db_stats[0].email_count, 10)
            self.assertEqual(db_stats[0].deleted_count, 8)

    def test_record_category_stats_invalid_data(self):
        """Test recording invalid category statistics."""
        self.service.get_or_create_account(self.test_email, "Test User")
        
        # Test invalid data types
        invalid_data_sets = [
            "not a dict",
            123,
            None,
            {"category": "not a dict"},  # Stats should be dict
            {"category": {"total": -1, "deleted": 0}},  # Negative counts
        ]
        
        for invalid_data in invalid_data_sets:
            if isinstance(invalid_data, dict) and "category" in invalid_data:
                # This should log warning but not fail
                try:
                    self.service.record_category_stats(self.test_email, date.today(), invalid_data)
                except ValueError:
                    pass  # Expected for some cases
            else:
                with self.assertRaises(ValueError):
                    self.service.record_category_stats(self.test_email, date.today(), invalid_data)

    def test_get_top_categories_valid(self):
        """Test getting top categories with valid data."""
        # Create account and stats
        account = self.service.get_or_create_account(self.test_email, "Test User")
        
        # Create test data over multiple days
        base_date = date.today()
        for i in range(3):
            stats_date = base_date - timedelta(days=i)
            category_stats = {
                "Marketing": {"total": 10 - i, "deleted": 8 - i, "kept": 2, "archived": 0},
                "Personal": {"total": 5, "deleted": 0, "kept": 5, "archived": 0},
                "Work-related": {"total": 3 + i, "deleted": 1, "kept": 2 + i, "archived": 0}
            }
            self.service.record_category_stats(self.test_email, stats_date, category_stats)
        
        # Get top categories
        response = self.service.get_top_categories(self.test_email, days=3, limit=10, include_counts=True)
        
        # Verify response structure
        self.assertIsInstance(response, TopCategoriesResponse)
        self.assertEqual(response.email_address, self.test_email)
        self.assertEqual(response.period.days, 3)
        self.assertGreater(len(response.top_categories), 0)
        
        # Verify categories are ordered by count descending
        for i in range(len(response.top_categories) - 1):
            self.assertGreaterEqual(
                response.top_categories[i].total_count, 
                response.top_categories[i + 1].total_count
            )
        
        # Verify percentages add up correctly (allowing for rounding)
        total_percentage = sum(cat.percentage for cat in response.top_categories)
        self.assertAlmostEqual(total_percentage, 100.0, places=1)

    def test_get_top_categories_include_counts(self):
        """Test getting top categories with detailed counts."""
        # Create account and stats
        self.service.get_or_create_account(self.test_email, "Test User")
        
        category_stats = {
            "Marketing": {"total": 10, "deleted": 8, "kept": 2, "archived": 0},
        }
        self.service.record_category_stats(self.test_email, date.today(), category_stats)
        
        # Get categories with counts
        response = self.service.get_top_categories(self.test_email, days=1, include_counts=True)
        
        # Verify detailed counts are included
        marketing_cat = response.top_categories[0]
        self.assertEqual(marketing_cat.category, "Marketing")
        self.assertIsNotNone(marketing_cat.kept_count)
        self.assertIsNotNone(marketing_cat.deleted_count)
        self.assertIsNotNone(marketing_cat.archived_count)
        self.assertEqual(marketing_cat.kept_count, 2)
        self.assertEqual(marketing_cat.deleted_count, 8)
        self.assertEqual(marketing_cat.archived_count, 0)

    def test_get_top_categories_exclude_counts(self):
        """Test getting top categories without detailed counts."""
        # Create account and stats
        self.service.get_or_create_account(self.test_email, "Test User")
        
        category_stats = {"Marketing": {"total": 10, "deleted": 8, "kept": 2, "archived": 0}}
        self.service.record_category_stats(self.test_email, date.today(), category_stats)
        
        # Get categories without counts
        response = self.service.get_top_categories(self.test_email, days=1, include_counts=False)
        
        # Verify detailed counts are not included
        marketing_cat = response.top_categories[0]
        self.assertIsNone(marketing_cat.kept_count)
        self.assertIsNone(marketing_cat.deleted_count)
        self.assertIsNone(marketing_cat.archived_count)

    def test_get_top_categories_invalid_params(self):
        """Test getting top categories with invalid parameters."""
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

    def test_get_top_categories_nonexistent_account(self):
        """Test getting top categories for non-existent account."""
        with self.assertRaises(ValueError):
            self.service.get_top_categories("nonexistent@gmail.com", days=7)

    def test_get_top_categories_no_data(self):
        """Test getting top categories with no category data."""
        self.service.get_or_create_account(self.test_email, "Test User")
        
        response = self.service.get_top_categories(self.test_email, days=7)
        
        self.assertEqual(response.total_emails, 0)
        self.assertEqual(len(response.top_categories), 0)

    def test_get_top_categories_limit_respected(self):
        """Test that limit parameter is respected."""
        # Create account with many categories
        self.service.get_or_create_account(self.test_email, "Test User")
        
        # Create 15 different categories
        category_stats = {
            f"Category_{i:02d}": {"total": 10 - i, "deleted": i, "kept": 10 - i, "archived": 0}
            for i in range(15)
        }
        self.service.record_category_stats(self.test_email, date.today(), category_stats)
        
        # Request top 5 categories
        response = self.service.get_top_categories(self.test_email, days=1, limit=5)
        
        self.assertEqual(len(response.top_categories), 5)

    def test_get_all_accounts_active_only(self):
        """Test getting all active accounts."""
        # Create multiple accounts
        accounts_data = [
            ("user1@gmail.com", "User 1", True),
            ("user2@gmail.com", "User 2", False),  # Will be deactivated
            ("user3@gmail.com", "User 3", True),
        ]
        
        for email, name, should_be_active in accounts_data:
            self.service.get_or_create_account(email, name)
            if not should_be_active:
                self.service.deactivate_account(email)
        
        # Get active accounts only
        accounts = self.service.get_all_accounts(active_only=True)
        
        self.assertEqual(len(accounts), 2)
        active_emails = {acc.email_address for acc in accounts}
        self.assertEqual(active_emails, {"user1@gmail.com", "user3@gmail.com"})

    def test_get_all_accounts_include_inactive(self):
        """Test getting all accounts including inactive."""
        # Create multiple accounts
        accounts_data = [
            ("user1@gmail.com", "User 1", True),
            ("user2@gmail.com", "User 2", False),  # Will be deactivated
        ]
        
        for email, name, should_be_active in accounts_data:
            self.service.get_or_create_account(email, name)
            if not should_be_active:
                self.service.deactivate_account(email)
        
        # Get all accounts
        accounts = self.service.get_all_accounts(active_only=False)
        
        self.assertEqual(len(accounts), 2)
        all_emails = {acc.email_address for acc in accounts}
        self.assertEqual(all_emails, {"user1@gmail.com", "user2@gmail.com"})

    def test_deactivate_account_existing(self):
        """Test deactivating existing account."""
        # Create account
        self.service.get_or_create_account(self.test_email, "Test User")
        
        # Deactivate account
        result = self.service.deactivate_account(self.test_email)
        
        self.assertTrue(result)
        
        # Verify account is deactivated
        account = self.service.get_account_by_email(self.test_email)
        self.assertFalse(account.is_active)

    def test_deactivate_account_nonexistent(self):
        """Test deactivating non-existent account."""
        result = self.service.deactivate_account("nonexistent@gmail.com")
        self.assertFalse(result)

    def test_deactivate_account_invalid_email(self):
        """Test deactivating account with invalid email."""
        for invalid_email in self.invalid_emails:
            with self.assertRaises(ValueError):
                self.service.deactivate_account(invalid_email)

    @patch('services.account_category_service.logger')
    def test_error_logging(self, mock_logger):
        """Test that errors are properly logged."""
        # Test database error logging
        with patch.object(self.service, '_get_session') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            with self.assertRaises(Exception):
                self.service.get_account_by_email(self.test_email)
            
            mock_logger.error.assert_called()

    def test_session_management_owns_session(self):
        """Test proper session management when service owns session."""
        # Service should handle session lifecycle
        service = AccountCategoryService(db_path=self.db_path)
        
        # These operations should work without explicit session management
        account = service.get_or_create_account(self.test_email, "Test User")
        self.assertIsNotNone(account)
        
        retrieved = service.get_account_by_email(self.test_email)
        self.assertIsNotNone(retrieved)

    def test_session_management_provided_session(self):
        """Test proper session management when session is provided."""
        # Create service with provided session
        service = AccountCategoryService(db_session=self.session)
        
        # Operations should use provided session
        account = service.get_or_create_account(self.test_email, "Test User")
        self.assertIsNotNone(account)
        
        # Verify data is in the session
        retrieved = self.session.query(EmailAccount).filter_by(email_address=self.test_email).first()
        self.assertIsNotNone(retrieved)


if __name__ == "__main__":
    unittest.main()