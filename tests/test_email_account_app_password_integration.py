#!/usr/bin/env python3
"""
Integration test to verify EmailAccount has app_password attribute.

This test would have caught the AttributeError: 'EmailAccount' object has no attribute 'app_password'
by using the real AccountCategoryClient with real database models instead of mocks.
"""
import unittest
import tempfile
import os
from faker import Faker

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import init_database, get_session, EmailAccount
from clients.account_category_client import AccountCategoryClient
from services.account_email_processor_service import AccountEmailProcessorService
from services.processing_status_manager import ProcessingStatusManager
from services.settings_service import SettingsService
from services.logs_collector_service import LogsCollectorService
from services.email_deduplication_factory import EmailDeduplicationFactory
from unittest.mock import Mock


class TestEmailAccountAppPasswordIntegration(unittest.TestCase):
    """Integration tests for EmailAccount app_password field."""

    def setUp(self):
        """Set up test database and services."""
        self.fake = Faker()

        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        # Initialize database
        self.engine = init_database(self.temp_db_path)
        self.session = get_session(self.engine)

        # Create real AccountCategoryClient with the session
        # Pass the session directly so it uses the same session for all operations
        self.real_client = AccountCategoryClient(db_session=self.session)

    def tearDown(self):
        """Clean up test database."""
        self.session.close()
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_email_account_has_app_password_attribute(self):
        """Test that EmailAccount from real database has app_password attribute."""
        # Generate random test email
        test_email = self.fake.email()
        test_password = self.fake.password()

        # Create account using real client
        account = self.real_client.get_or_create_account(test_email)

        # This should NOT raise AttributeError
        # Set the app_password
        account.app_password = test_password

        # Save to database
        self.session.add(account)
        self.session.commit()

        # Retrieve and verify
        retrieved = self.real_client.get_account_by_email(test_email)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.app_password, test_password)
        self.assertEqual(retrieved.email_address, test_email)

    def test_account_email_processor_can_access_app_password(self):
        """Test that AccountEmailProcessorService can access app_password from real account."""
        # Generate random test data
        test_email = self.fake.email()
        test_password = self.fake.password()
        api_token = self.fake.uuid4()

        # Create account with app_password
        account = self.real_client.get_or_create_account(test_email)
        account.app_password = test_password
        self.session.add(account)
        self.session.commit()

        # Create service with real AccountCategoryClient
        processing_status_manager = ProcessingStatusManager()
        settings_service = SettingsService()
        email_categorizer = Mock(return_value="Marketing")
        logs_collector = LogsCollectorService()
        deduplication_factory = EmailDeduplicationFactory()

        # Create fake fetcher that will be used
        fake_fetcher = Mock()
        fake_fetcher.connect = Mock()
        fake_fetcher.disconnect = Mock()
        fake_fetcher.get_recent_emails = Mock(return_value=[])
        fake_fetcher.summary_service = Mock()
        fake_fetcher.summary_service.clear_tracked_data = Mock()
        fake_fetcher.summary_service.start_processing_run = Mock()
        fake_fetcher.summary_service.complete_processing_run = Mock()
        fake_fetcher.summary_service.run_metrics = {'fetched': 0}
        fake_fetcher.stats = {'deleted': 0, 'kept': 0}
        fake_fetcher.account_service = None

        def create_fake_fetcher(email, password, token):
            # Verify that password is accessible
            self.assertEqual(password, test_password)
            return fake_fetcher

        service = AccountEmailProcessorService(
            processing_status_manager=processing_status_manager,
            settings_service=settings_service,
            email_categorizer=email_categorizer,
            api_token=api_token,
            llm_model="test-model",
            account_category_client=self.real_client,
            deduplication_factory=deduplication_factory,
            logs_collector=logs_collector,
            create_gmail_fetcher=create_fake_fetcher
        )

        # This should work without AttributeError
        result = service.process_account(test_email)

        # Verify it processed successfully
        self.assertTrue(result['success'])
        self.assertEqual(result['account'], test_email)

    def test_account_without_app_password_returns_error(self):
        """Test that account without app_password returns appropriate error."""
        # Generate random test email
        test_email = self.fake.email()
        api_token = self.fake.uuid4()

        # Create account WITHOUT app_password
        account = self.real_client.get_or_create_account(test_email)
        # Don't set app_password - it should be None
        self.session.add(account)
        self.session.commit()

        # Create service
        processing_status_manager = ProcessingStatusManager()
        settings_service = SettingsService()
        email_categorizer = Mock(return_value="Marketing")
        logs_collector = LogsCollectorService()
        deduplication_factory = EmailDeduplicationFactory()

        service = AccountEmailProcessorService(
            processing_status_manager=processing_status_manager,
            settings_service=settings_service,
            email_categorizer=email_categorizer,
            api_token=api_token,
            llm_model="test-model",
            account_category_client=self.real_client,
            deduplication_factory=deduplication_factory,
            logs_collector=logs_collector
        )

        # Process should fail with appropriate error
        result = service.process_account(test_email)

        self.assertFalse(result['success'])
        self.assertIn('No app password configured', result['error'])


if __name__ == '__main__':
    unittest.main()