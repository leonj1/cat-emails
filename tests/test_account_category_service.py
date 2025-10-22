"""
Tests for AccountCategoryClient to ensure proper functionality and catch AttributeErrors.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from clients.account_category_client import AccountCategoryClient
from models.database import Base, EmailAccount, AccountCategoryStats


class TestAccountCategoryClient(unittest.TestCase):
    """Test cases for AccountCategoryClient."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        # Create test engine and session
        self.engine = create_engine(f'sqlite:///{self.temp_db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Initialize client with test session
        self.service = AccountCategoryClient(db_session=self.session)

        # Create test data
        self.test_email = "test@gmail.com"
        self.test_account = EmailAccount(
            email_address=self.test_email,
            created_at=datetime.now(),
            last_scan_at=datetime.now()
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.session.close()
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_get_account_by_email_exists(self):
        """Test get_account_by_email when account exists."""
        # Add test account to database
        self.session.add(self.test_account)
        self.session.commit()

        # Test retrieval
        account = self.service.get_account_by_email(self.test_email)

        self.assertIsNotNone(account)
        self.assertEqual(account.email_address, self.test_email)

    def test_get_account_by_email_not_exists(self):
        """Test get_account_by_email when account doesn't exist."""
        account = self.service.get_account_by_email("nonexistent@gmail.com")

        self.assertIsNone(account)

    def test_get_account_by_email_invalid_email(self):
        """Test get_account_by_email with invalid email format."""
        with self.assertRaises(ValueError) as context:
            self.service.get_account_by_email("invalid-email")

        self.assertIn("Invalid email address", str(context.exception))

    def test_get_account_by_email_empty_string(self):
        """Test get_account_by_email with empty string."""
        with self.assertRaises(ValueError) as context:
            self.service.get_account_by_email("")

        self.assertIn("Email address must be a non-empty string", str(context.exception))

    def test_get_account_by_email_none(self):
        """Test get_account_by_email with None value."""
        with self.assertRaises(ValueError) as context:
            self.service.get_account_by_email(None)

        self.assertIn("Email address must be a non-empty string", str(context.exception))

    def test_ensure_no_get_account_method(self):
        """Test that get_account method doesn't exist (to prevent regression)."""
        # This test ensures that the incorrect method name doesn't exist
        self.assertFalse(hasattr(self.service, 'get_account'),
                        "AccountCategoryClient should not have a 'get_account' method. Use 'get_account_by_email' instead.")

    def test_create_or_update_account(self):
        """Test get_or_create_account method."""
        # First creation
        account1 = self.service.get_or_create_account(self.test_email)
        self.assertIsNotNone(account1)
        self.assertEqual(account1.email_address, self.test_email)

        # Update existing
        account2 = self.service.get_or_create_account(self.test_email)
        self.assertIsNotNone(account2)
        self.assertEqual(account2.id, account1.id)  # Should be same account

    def test_update_account_last_scan(self):
        """Test updating account's last scan timestamp."""
        # Create account first
        self.session.add(self.test_account)
        self.session.commit()

        original_time = self.test_account.last_scan_at

        # Update last scan
        self.service.update_account_last_scan(self.test_email)

        # Refresh and check
        self.session.refresh(self.test_account)
        self.assertGreaterEqual(self.test_account.last_scan_at, original_time)

    def test_update_category_stats(self):
        """Test updating category statistics for an account."""
        # Create account first
        self.session.add(self.test_account)
        self.session.commit()

        # Record stats for today
        today = date.today()
        self.service.record_category_stats(
            email_address=self.test_email,
            stats_date=today,
            category_stats={
                "Marketing": {"total": 5, "deleted": 0, "kept": 5, "archived": 0}
            }
        )

        # Check stats were created
        stats = self.session.query(AccountCategoryStats).filter_by(
            account_id=self.test_account.id,
            category_name="Marketing",
            date=today
        ).first()

        self.assertIsNotNone(stats)
        self.assertEqual(stats.email_count, 5)
        self.assertEqual(stats.kept_count, 5)

        # Update again with new count (should replace, not increment)
        self.service.record_category_stats(
            email_address=self.test_email,
            stats_date=today,
            category_stats={
                "Marketing": {"total": 10, "deleted": 2, "kept": 8, "archived": 0}
            }
        )

        # Refresh and check updated values
        self.session.refresh(stats)
        self.assertEqual(stats.email_count, 10)  # Should replace, not be cumulative
        self.assertEqual(stats.deleted_count, 2)
        self.assertEqual(stats.kept_count, 8)

    def test_get_top_categories_with_data(self):
        """Test getting top categories when data exists."""
        # Create account and stats
        self.session.add(self.test_account)
        self.session.commit()

        # Add various category stats
        categories = [
            ("Marketing", 50),
            ("Advertising", 30),
            ("Personal", 20),
            ("Work-related", 10),
            ("Other", 5)
        ]

        for category, count in categories:
            stat = AccountCategoryStats(
                account_id=self.test_account.id,
                category_name=category,
                email_count=count,
                date=date.today()
            )
            self.session.add(stat)
        self.session.commit()

        # Get top categories
        response = self.service.get_top_categories(
            email_address=self.test_email,
            days=7,
            limit=3
        )

        self.assertIsNotNone(response)
        self.assertEqual(len(response.top_categories), 3)
        self.assertEqual(response.top_categories[0].category, "Marketing")
        self.assertEqual(response.top_categories[0].total_count, 50)

    def test_get_top_categories_no_data(self):
        """Test getting top categories when no data exists."""
        # Create account but no stats
        self.session.add(self.test_account)
        self.session.commit()

        response = self.service.get_top_categories(
            email_address=self.test_email,
            days=7,
            limit=5
        )

        self.assertIsNotNone(response)
        self.assertEqual(len(response.top_categories), 0)

    def test_list_accounts(self):
        """Test listing all accounts."""
        # Create multiple accounts
        accounts = [
            EmailAccount(email_address="user1@gmail.com", created_at=datetime.now()),
            EmailAccount(email_address="user2@gmail.com", created_at=datetime.now()),
            EmailAccount(email_address="user3@gmail.com", created_at=datetime.now())
        ]

        for account in accounts:
            self.session.add(account)
        self.session.commit()

        # List accounts using get_all_accounts method
        result = self.service.get_all_accounts(active_only=False)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)

        # Check that all accounts are returned
        emails = [acc.email_address for acc in result]
        self.assertIn("user1@gmail.com", emails)
        self.assertIn("user2@gmail.com", emails)
        self.assertIn("user3@gmail.com", emails)


class TestAccountCategoryClientIntegration(unittest.TestCase):
    """Integration tests for AccountCategoryClient with API service."""

    @patch('clients.account_category_client.init_database')
    @patch('clients.account_category_client.sessionmaker')
    def test_api_service_usage(self, mock_sessionmaker, mock_init_db):
        """Test that API service can properly use AccountCategoryClient."""
        # Mock database setup
        mock_session = MagicMock()
        mock_session_factory = MagicMock()

        # Configure the session factory to return our mock session when called
        mock_session_factory.return_value = mock_session

        # Configure sessionmaker to return our session factory
        mock_sessionmaker.return_value = mock_session_factory

        # Mock the database initialization
        mock_engine = MagicMock()
        mock_init_db.return_value = mock_engine

        # Create client
        service = AccountCategoryClient()

        # Test that the correct method exists and is callable
        self.assertTrue(hasattr(service, 'get_account_by_email'))
        self.assertTrue(callable(getattr(service, 'get_account_by_email')))

        # Ensure the old method name doesn't exist
        self.assertFalse(hasattr(service, 'get_account'))

        # Test method call
        mock_account = MagicMock(spec=EmailAccount)
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_account

        # Configure context manager behavior for the session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        result = service.get_account_by_email("test@gmail.com")

        # Verify the session factory was called to create a session
        mock_session_factory.assert_called()

        # Verify the call was made correctly on the session
        mock_session.query.assert_called_with(EmailAccount)
        mock_session.query.return_value.filter_by.assert_called_with(email_address="test@gmail.com")


if __name__ == '__main__':
    unittest.main()