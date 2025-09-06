"""
Unit tests for account database models and data validation.
Provides comprehensive test coverage for database models, relationships, and constraints.
"""
import unittest
from unittest.mock import Mock, patch
import tempfile
import os
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError

from models.database import (
    Base, EmailAccount, AccountCategoryStats, 
    init_database, get_database_url, get_session
)
from models.account_models import (
    AccountCategoryStatsRequest, CategoryStats, DatePeriod,
    TopCategoriesResponse, EmailAccountInfo, AccountListResponse
)


class TestDatabaseModels(unittest.TestCase):
    """Test database model functionality and constraints."""

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
        
        # Test data
        self.test_email = "test@gmail.com"
        self.test_display_name = "Test User"
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.session.close()
        self.engine.dispose()
        
        # Remove temp database file
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_database_initialization(self):
        """Test that database initialization creates all tables."""
        # Verify all tables exist
        inspector = self.engine.inspect(self.engine)
        tables = inspector.get_table_names()
        
        expected_tables = {
            'email_accounts',
            'account_category_stats',
            'email_summaries',
            'category_summaries',
            'sender_summaries',
            'domain_summaries',
            'processing_runs'
        }
        
        self.assertTrue(expected_tables.issubset(set(tables)))

    def test_get_database_url(self):
        """Test database URL generation."""
        # Test with default path
        default_url = get_database_url()
        self.assertTrue(default_url.startswith("sqlite:///"))
        self.assertIn("summaries.db", default_url)
        
        # Test with custom path
        custom_path = "/custom/path/test.db"
        custom_url = get_database_url(custom_path)
        self.assertEqual(custom_url, f"sqlite:///{custom_path}")

    def test_get_session(self):
        """Test session creation."""
        session = get_session(self.engine)
        self.assertIsNotNone(session)
        
        # Verify session is functional
        result = session.execute(select(func.count()).select_from(EmailAccount))
        count = result.scalar()
        self.assertEqual(count, 0)  # Should be empty initially
        
        session.close()


class TestEmailAccountModel(unittest.TestCase):
    """Test EmailAccount database model."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.engine = init_database(self.db_path)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.session.close()
        self.engine.dispose()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_email_account_creation(self):
        """Test creating EmailAccount with all fields."""
        now = datetime.utcnow()
        
        account = EmailAccount(
            email_address="test@gmail.com",
            display_name="Test User",
            is_active=True,
            last_scan_at=now,
            created_at=now,
            updated_at=now
        )
        
        self.session.add(account)
        self.session.commit()
        
        # Verify account was created
        retrieved = self.session.query(EmailAccount).filter_by(email_address="test@gmail.com").first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.email_address, "test@gmail.com")
        self.assertEqual(retrieved.display_name, "Test User")
        self.assertTrue(retrieved.is_active)
        self.assertEqual(retrieved.last_scan_at, now)

    def test_email_account_defaults(self):
        """Test EmailAccount default values."""
        account = EmailAccount(email_address="test@gmail.com")
        
        self.session.add(account)
        self.session.commit()
        
        # Verify defaults
        retrieved = self.session.query(EmailAccount).filter_by(email_address="test@gmail.com").first()
        self.assertTrue(retrieved.is_active)  # Default True
        self.assertIsNotNone(retrieved.created_at)  # Auto-generated
        self.assertIsNotNone(retrieved.updated_at)  # Auto-generated
        self.assertIsNone(retrieved.display_name)  # Optional
        self.assertIsNone(retrieved.last_scan_at)  # Optional

    def test_email_account_unique_constraint(self):
        """Test that email addresses must be unique."""
        # Create first account
        account1 = EmailAccount(email_address="test@gmail.com", display_name="User 1")
        self.session.add(account1)
        self.session.commit()
        
        # Try to create second account with same email
        account2 = EmailAccount(email_address="test@gmail.com", display_name="User 2")
        self.session.add(account2)
        
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_email_account_required_fields(self):
        """Test that required fields are enforced."""
        # Email address is required
        account = EmailAccount(display_name="Test User")
        self.session.add(account)
        
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_email_account_indexes(self):
        """Test that database indexes exist."""
        # This test verifies that the indexes are created
        # We check the table structure
        inspector = self.engine.inspect(self.engine)
        indexes = inspector.get_indexes('email_accounts')
        
        index_names = [idx['name'] for idx in indexes]
        
        # Verify that our custom index exists
        self.assertIn('idx_email_active', index_names)

    def test_email_account_relationships(self):
        """Test EmailAccount relationships with other models."""
        # Create account
        account = EmailAccount(email_address="test@gmail.com")
        self.session.add(account)
        self.session.commit()
        
        # Create related category stats
        stats = AccountCategoryStats(
            account_id=account.id,
            date=date.today(),
            category_name="Marketing",
            email_count=10,
            deleted_count=5,
            kept_count=5,
            archived_count=0
        )
        self.session.add(stats)
        self.session.commit()
        
        # Test relationship access
        retrieved_account = self.session.query(EmailAccount).filter_by(email_address="test@gmail.com").first()
        self.assertEqual(len(retrieved_account.category_stats), 1)
        self.assertEqual(retrieved_account.category_stats[0].category_name, "Marketing")

    def test_email_account_cascade_delete(self):
        """Test that deleting account cascades to related records."""
        # Create account with category stats
        account = EmailAccount(email_address="test@gmail.com")
        self.session.add(account)
        self.session.flush()  # Get account.id
        
        stats = AccountCategoryStats(
            account_id=account.id,
            date=date.today(),
            category_name="Marketing",
            email_count=10
        )
        self.session.add(stats)
        self.session.commit()
        
        # Verify both exist
        self.assertEqual(self.session.query(EmailAccount).count(), 1)
        self.assertEqual(self.session.query(AccountCategoryStats).count(), 1)
        
        # Delete account
        self.session.delete(account)
        self.session.commit()
        
        # Verify cascade deletion
        self.assertEqual(self.session.query(EmailAccount).count(), 0)
        self.assertEqual(self.session.query(AccountCategoryStats).count(), 0)


class TestAccountCategoryStatsModel(unittest.TestCase):
    """Test AccountCategoryStats database model."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.engine = init_database(self.db_path)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Create test account
        self.account = EmailAccount(email_address="test@gmail.com")
        self.session.add(self.account)
        self.session.commit()
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.session.close()
        self.engine.dispose()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_account_category_stats_creation(self):
        """Test creating AccountCategoryStats with all fields."""
        now = datetime.utcnow()
        today = date.today()
        
        stats = AccountCategoryStats(
            account_id=self.account.id,
            date=today,
            category_name="Marketing",
            email_count=15,
            deleted_count=10,
            archived_count=2,
            kept_count=3,
            created_at=now,
            updated_at=now
        )
        
        self.session.add(stats)
        self.session.commit()
        
        # Verify creation
        retrieved = self.session.query(AccountCategoryStats).filter_by(
            account_id=self.account.id,
            category_name="Marketing"
        ).first()
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.email_count, 15)
        self.assertEqual(retrieved.deleted_count, 10)
        self.assertEqual(retrieved.archived_count, 2)
        self.assertEqual(retrieved.kept_count, 3)
        self.assertEqual(retrieved.date, today)

    def test_account_category_stats_defaults(self):
        """Test AccountCategoryStats default values."""
        stats = AccountCategoryStats(
            account_id=self.account.id,
            date=date.today(),
            category_name="Marketing"
        )
        
        self.session.add(stats)
        self.session.commit()
        
        # Verify defaults
        retrieved = self.session.query(AccountCategoryStats).first()
        self.assertEqual(retrieved.email_count, 0)
        self.assertEqual(retrieved.deleted_count, 0)
        self.assertEqual(retrieved.archived_count, 0)
        self.assertEqual(retrieved.kept_count, 0)
        self.assertIsNotNone(retrieved.created_at)
        self.assertIsNotNone(retrieved.updated_at)

    def test_account_category_stats_unique_constraint(self):
        """Test unique constraint on account_id, date, category_name."""
        today = date.today()
        
        # Create first stats record
        stats1 = AccountCategoryStats(
            account_id=self.account.id,
            date=today,
            category_name="Marketing",
            email_count=10
        )
        self.session.add(stats1)
        self.session.commit()
        
        # Try to create duplicate
        stats2 = AccountCategoryStats(
            account_id=self.account.id,
            date=today,
            category_name="Marketing",
            email_count=20
        )
        self.session.add(stats2)
        
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_account_category_stats_foreign_key(self):
        """Test foreign key constraint to EmailAccount."""
        # Try to create stats with invalid account_id
        stats = AccountCategoryStats(
            account_id=99999,  # Non-existent account
            date=date.today(),
            category_name="Marketing",
            email_count=10
        )
        self.session.add(stats)
        
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_account_category_stats_required_fields(self):
        """Test that required fields are enforced."""
        # Missing account_id
        with self.assertRaises(TypeError):
            AccountCategoryStats(
                date=date.today(),
                category_name="Marketing"
            )

    def test_account_category_stats_indexes(self):
        """Test that database indexes exist."""
        inspector = self.engine.inspect(self.engine)
        indexes = inspector.get_indexes('account_category_stats')
        
        index_names = [idx['name'] for idx in indexes]
        
        # Verify custom indexes exist
        expected_indexes = ['idx_account_date', 'idx_account_category', 'idx_date_category']
        for expected in expected_indexes:
            self.assertIn(expected, index_names)

    def test_account_category_stats_relationship(self):
        """Test relationship back to EmailAccount."""
        stats = AccountCategoryStats(
            account_id=self.account.id,
            date=date.today(),
            category_name="Marketing",
            email_count=10
        )
        self.session.add(stats)
        self.session.commit()
        
        # Test relationship access
        retrieved_stats = self.session.query(AccountCategoryStats).first()
        self.assertIsNotNone(retrieved_stats.email_account)
        self.assertEqual(retrieved_stats.email_account.email_address, "test@gmail.com")

    def test_account_category_stats_date_range_queries(self):
        """Test querying stats by date ranges."""
        base_date = date.today()
        
        # Create stats for multiple days
        for i in range(5):
            stats_date = base_date - timedelta(days=i)
            stats = AccountCategoryStats(
                account_id=self.account.id,
                date=stats_date,
                category_name=f"Category_{i}",
                email_count=10 + i
            )
            self.session.add(stats)
        
        self.session.commit()
        
        # Query for last 3 days
        three_days_ago = base_date - timedelta(days=2)
        recent_stats = self.session.query(AccountCategoryStats).filter(
            AccountCategoryStats.account_id == self.account.id,
            AccountCategoryStats.date >= three_days_ago
        ).all()
        
        self.assertEqual(len(recent_stats), 3)

    def test_account_category_stats_aggregation_queries(self):
        """Test aggregation queries on stats."""
        today = date.today()
        
        # Create multiple stats for same day
        categories = [
            ("Marketing", 20, 15, 5),
            ("Personal", 10, 0, 10),
            ("Work", 15, 5, 10)
        ]
        
        for cat_name, total, deleted, kept in categories:
            stats = AccountCategoryStats(
                account_id=self.account.id,
                date=today,
                category_name=cat_name,
                email_count=total,
                deleted_count=deleted,
                kept_count=kept
            )
            self.session.add(stats)
        
        self.session.commit()
        
        # Test aggregation
        total_emails = self.session.query(
            func.sum(AccountCategoryStats.email_count)
        ).filter(
            AccountCategoryStats.account_id == self.account.id,
            AccountCategoryStats.date == today
        ).scalar()
        
        self.assertEqual(total_emails, 45)  # 20 + 10 + 15


class TestAccountModels(unittest.TestCase):
    """Test Pydantic models for account management."""

    def test_account_category_stats_request_valid(self):
        """Test valid AccountCategoryStatsRequest."""
        request = AccountCategoryStatsRequest(
            days=7,
            limit=10,
            include_counts=True
        )
        
        self.assertEqual(request.days, 7)
        self.assertEqual(request.limit, 10)
        self.assertTrue(request.include_counts)

    def test_account_category_stats_request_defaults(self):
        """Test AccountCategoryStatsRequest defaults."""
        request = AccountCategoryStatsRequest(days=7)
        
        self.assertEqual(request.days, 7)
        self.assertEqual(request.limit, 10)  # Default
        self.assertFalse(request.include_counts)  # Default

    def test_account_category_stats_request_validation(self):
        """Test AccountCategoryStatsRequest validation."""
        # Days too low
        with self.assertRaises(ValidationError):
            AccountCategoryStatsRequest(days=0)
        
        # Days too high
        with self.assertRaises(ValidationError):
            AccountCategoryStatsRequest(days=366)
        
        # Limit too low
        with self.assertRaises(ValidationError):
            AccountCategoryStatsRequest(days=7, limit=0)
        
        # Limit too high
        with self.assertRaises(ValidationError):
            AccountCategoryStatsRequest(days=7, limit=51)

    def test_category_stats_valid(self):
        """Test valid CategoryStats model."""
        stats = CategoryStats(
            category="Marketing",
            total_count=100,
            percentage=45.67,
            kept_count=30,
            deleted_count=60,
            archived_count=10
        )
        
        self.assertEqual(stats.category, "Marketing")
        self.assertEqual(stats.total_count, 100)
        self.assertEqual(stats.percentage, 45.67)
        self.assertEqual(stats.kept_count, 30)

    def test_category_stats_percentage_rounding(self):
        """Test that percentage is rounded to 2 decimal places."""
        stats = CategoryStats(
            category="Marketing",
            total_count=100,
            percentage=45.6789123
        )
        
        self.assertEqual(stats.percentage, 45.68)

    def test_category_stats_validation(self):
        """Test CategoryStats validation."""
        # Negative total_count
        with self.assertRaises(ValidationError):
            CategoryStats(
                category="Marketing",
                total_count=-1,
                percentage=50.0
            )
        
        # Percentage over 100
        with self.assertRaises(ValidationError):
            CategoryStats(
                category="Marketing",
                total_count=100,
                percentage=150.0
            )
        
        # Negative percentage
        with self.assertRaises(ValidationError):
            CategoryStats(
                category="Marketing",
                total_count=100,
                percentage=-10.0
            )

    def test_date_period_valid(self):
        """Test valid DatePeriod model."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 7)
        
        period = DatePeriod(
            start_date=start,
            end_date=end,
            days=7
        )
        
        self.assertEqual(period.start_date, start)
        self.assertEqual(period.end_date, end)
        self.assertEqual(period.days, 7)

    def test_date_period_validation_order(self):
        """Test DatePeriod date order validation."""
        start = date(2024, 1, 7)
        end = date(2024, 1, 1)  # Before start
        
        with self.assertRaises(ValidationError):
            DatePeriod(
                start_date=start,
                end_date=end,
                days=7
            )

    def test_date_period_validation_days_mismatch(self):
        """Test DatePeriod days field validation."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 7)  # 7 days difference
        
        # Wrong days count
        with self.assertRaises(ValidationError):
            DatePeriod(
                start_date=start,
                end_date=end,
                days=5  # Should be 7
            )

    def test_top_categories_response_valid(self):
        """Test valid TopCategoriesResponse model."""
        period = DatePeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            days=7
        )
        
        categories = [
            CategoryStats(category="Marketing", total_count=100, percentage=60.0),
            CategoryStats(category="Personal", total_count=67, percentage=40.0)
        ]
        
        response = TopCategoriesResponse(
            email_address="test@gmail.com",
            period=period,
            total_emails=167,
            top_categories=categories
        )
        
        self.assertEqual(response.email_address, "test@gmail.com")
        self.assertEqual(response.total_emails, 167)
        self.assertEqual(len(response.top_categories), 2)

    def test_top_categories_response_order_validation(self):
        """Test TopCategoriesResponse category order validation."""
        period = DatePeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            days=7
        )
        
        # Categories not in descending order
        categories = [
            CategoryStats(category="Personal", total_count=50, percentage=40.0),
            CategoryStats(category="Marketing", total_count=100, percentage=60.0)  # Higher count should be first
        ]
        
        with self.assertRaises(ValidationError):
            TopCategoriesResponse(
                email_address="test@gmail.com",
                period=period,
                total_emails=150,
                top_categories=categories
            )

    def test_email_account_info_valid(self):
        """Test valid EmailAccountInfo model."""
        info = EmailAccountInfo(
            id=1,
            email_address="test@gmail.com",
            display_name="Test User",
            is_active=True,
            last_scan_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        
        self.assertEqual(info.id, 1)
        self.assertEqual(info.email_address, "test@gmail.com")
        self.assertTrue(info.is_active)

    def test_email_account_info_validation(self):
        """Test EmailAccountInfo validation."""
        # Invalid ID (must be > 0)
        with self.assertRaises(ValidationError):
            EmailAccountInfo(
                id=0,
                email_address="test@gmail.com",
                created_at=datetime.utcnow()
            )

    def test_account_list_response_valid(self):
        """Test valid AccountListResponse model."""
        accounts = [
            EmailAccountInfo(
                id=1,
                email_address="user1@gmail.com",
                created_at=datetime.utcnow()
            ),
            EmailAccountInfo(
                id=2,
                email_address="user2@gmail.com",
                created_at=datetime.utcnow()
            )
        ]
        
        response = AccountListResponse(
            accounts=accounts,
            total_count=2
        )
        
        self.assertEqual(len(response.accounts), 2)
        self.assertEqual(response.total_count, 2)

    def test_account_list_response_count_validation(self):
        """Test AccountListResponse count validation."""
        accounts = [
            EmailAccountInfo(
                id=1,
                email_address="user1@gmail.com",
                created_at=datetime.utcnow()
            )
        ]
        
        # Mismatched count
        with self.assertRaises(ValidationError):
            AccountListResponse(
                accounts=accounts,
                total_count=2  # Should be 1
            )

    def test_model_serialization(self):
        """Test that models can be serialized to JSON."""
        stats = CategoryStats(
            category="Marketing",
            total_count=100,
            percentage=45.67
        )
        
        # Should be able to convert to dict
        data = stats.model_dump()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["category"], "Marketing")
        
        # Should be able to recreate from dict
        recreated = CategoryStats(**data)
        self.assertEqual(recreated.category, stats.category)
        self.assertEqual(recreated.total_count, stats.total_count)


if __name__ == "__main__":
    unittest.main()