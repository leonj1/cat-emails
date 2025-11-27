"""
Integration test to verify that tracked categories are properly recorded when processing emails.

This test uses repository-based persistence and fake classes for Gmail interaction,
ensuring that category statistics are correctly stored and retrieved.
"""
import os
import tempfile
import unittest
from datetime import datetime, date
from typing import Dict

# Database models and initialization
from models.database import Base, init_database
from clients.account_category_client import AccountCategoryClient

# Services and interfaces
from services.account_email_processor_service import AccountEmailProcessorService
from services.processing_status_manager import ProcessingStatusManager
from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
from services.settings_service import SettingsService
from services.logs_collector_service import LogsCollectorService
from repositories.sqlalchemy_repository import SQLAlchemyRepository

# Fake implementations for testing
from tests.fake_gmail_fetcher import FakeGmailFetcher
from services.fake_email_categorizer import FakeEmailCategorizer


class TestTrackedCategoriesIntegration(unittest.TestCase):
    """Test that email processing correctly tracks categories in the database."""

    def setUp(self):
        """Set up test environment with SQLite database and fake services."""
        # Create a temporary database file for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        # Initialize database with schema
        self.engine = init_database(self.db_path)
        
        # Create SQLite repository explicitly
        self.repository = SQLAlchemyRepository(self.db_path)
        
        # Create real account category client with injected repository
        self.account_category_client = AccountCategoryClient(repository=self.repository)
        
        # Create test email account
        self.test_email = "test@example.com"
        self.test_password = "test-app-password"
        
        # Create account in database
        self.account = self.account_category_client.get_or_create_account(
            email_address=self.test_email,
            display_name="Test Account",
            app_password=self.test_password
        )
        
        # Set up fake services
        self.processing_status_manager = ProcessingStatusManager()
        # Inject repository into SettingsService
        self.settings_service = SettingsService(repository=self.repository)
        self.deduplication_factory = FakeEmailDeduplicationFactory()
        self.logs_collector = LogsCollectorService()
        
        # Create fake email categorizer that returns valid SimpleEmailCategory values
        # Valid categories are: "Advertising", "Marketing", "Wants-Money", and "Other"
        self.email_categorizer = FakeEmailCategorizer(default_category="Other")

        # Set up category mappings based on test email subjects/content
        self.email_categorizer.set_category_mapping("invoice", "Wants-Money")
        self.email_categorizer.set_category_mapping("payment", "Wants-Money")
        self.email_categorizer.set_category_mapping("subscription", "Marketing")
        self.email_categorizer.set_category_mapping("order", "Marketing")
        self.email_categorizer.set_category_mapping("discount", "Advertising")
        self.email_categorizer.set_category_mapping("sale", "Advertising")
        
        # Create factory function for fake Gmail fetcher
        def create_fake_fetcher(email_address: str, app_password: str, api_token: str) -> FakeGmailFetcher:
            """Create and configure a fake Gmail fetcher with test emails."""
            fetcher = FakeGmailFetcher()
            
            # Add required attributes for compatibility with the processor
            from services.email_summary_service import EmailSummaryService
            from clients.account_category_client import AccountCategoryClient
            fetcher.summary_service = EmailSummaryService(gmail_email=email_address)
            fetcher.account_service = self.account_category_client  # Use the test's account client
            from collections import Counter
            fetcher.stats = {
                'deleted': 0,
                'kept': 0,
                'categories': Counter()
            }
            
            # Pre-populate with test emails
            fetcher.add_test_email(
                subject="Invoice Payment Due",
                body="Your invoice for $500 is due by the end of the month.",
                sender="billing@company.com"
            )
            
            fetcher.add_test_email(
                subject="Meeting Schedule Update",
                body="The quarterly meeting has been rescheduled to next Tuesday.",
                sender="admin@workplace.com"
            )
            
            fetcher.add_test_email(
                subject="Project Status Report",
                body="Please find attached the weekly project status report.",
                sender="pm@workplace.com"
            )
            
            fetcher.add_test_email(
                subject="Hello from your friend",
                body="Just wanted to check in and see how you're doing!",
                sender="friend@personal.com"
            )
            
            fetcher.add_test_email(
                subject="Subscription Renewal Notice",
                body="Your subscription will renew automatically next month.",
                sender="service@subscriptions.com"
            )
            
            fetcher.add_test_email(
                subject="Order Confirmation",
                body="Your order #12345 has been confirmed and will ship soon.",
                sender="orders@ecommerce.com"
            )
            
            fetcher.add_test_email(
                subject="Account Statement",
                body="Your monthly account statement is now available.",
                sender="statements@bank.com"
            )
            
            fetcher.add_test_email(
                subject="Team Announcement",
                body="Important announcement regarding the upcoming team restructure.",
                sender="hr@company.com"
            )
            
            return fetcher
        
        # Create the processor service with all dependencies
        self.processor_service = AccountEmailProcessorService(
            processing_status_manager=self.processing_status_manager,
            settings_service=self.settings_service,
            email_categorizer=self.email_categorizer,
            api_token="test-api-token",
            llm_model="test-model",
            account_category_client=self.account_category_client,
            deduplication_factory=self.deduplication_factory,
            logs_collector=self.logs_collector,
            create_gmail_fetcher=create_fake_fetcher
        )

    def tearDown(self):
        """Clean up test database."""
        # Close any open connections
        if hasattr(self, 'engine'):
            self.engine.dispose()
        
        # Remove temporary database file
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_tracked_categories_are_recorded(self):
        """
        Test that processing emails results in non-zero tracked categories.
        
        This test verifies the core issue: after processing emails for an account,
        the tracked categories should not be zero.
        """
        # Process emails for the test account
        result = self.processor_service.process_account(self.test_email)
        
        # Verify processing was successful
        self.assertTrue(result.get('success', False), f"Processing failed: {result.get('error')}")
        
        # Check that emails were processed
        self.assertIn('emails_processed', result)
        self.assertGreater(result['emails_processed'], 0, "No emails were processed")
        
        # Get top categories for the account (last 7 days)
        top_categories_response = self.account_category_client.get_top_categories(
            email_address=self.test_email,
            days=7,
            limit=10,
            include_counts=True
        )
        
        # MAIN ASSERTION: Tracked categories should not be zero
        self.assertIsNotNone(top_categories_response)
        self.assertGreater(
            len(top_categories_response.top_categories), 
            0, 
            "No tracked categories found after processing emails"
        )
        
        # Verify total emails matches what was processed
        self.assertEqual(
            top_categories_response.total_emails,
            result['emails_processed'],
            f"Total tracked emails ({top_categories_response.total_emails}) doesn't match processed count ({result['emails_processed']})"
        )
        
        # Verify category details
        for category_stat in top_categories_response.top_categories:
            self.assertIsNotNone(category_stat.category)
            self.assertGreater(category_stat.total_count, 0, f"Category {category_stat.category} has zero count")
            self.assertGreater(category_stat.percentage, 0.0, f"Category {category_stat.category} has zero percentage")
        
        # Log the results for debugging
        print(f"\n✅ Successfully tracked {len(top_categories_response.top_categories)} categories:")
        for cat in top_categories_response.top_categories:
            print(f"  - {cat.category}: {cat.total_count} emails ({cat.percentage}%)")
        print(f"Total emails tracked: {top_categories_response.total_emails}")

    def test_category_stats_persist_in_database(self):
        """
        Test that category statistics are actually persisted in the database
        and can be retrieved in subsequent queries.
        """
        # Process emails
        result = self.processor_service.process_account(self.test_email)
        self.assertTrue(result.get('success', False))
        
        # Get stats immediately after processing
        initial_response = self.account_category_client.get_top_categories(
            email_address=self.test_email,
            days=1,
            limit=10,
            include_counts=True
        )
        
        initial_category_count = len(initial_response.top_categories)
        initial_total_emails = initial_response.total_emails
        
        # Create a new client instance to ensure we're reading from DB, not cache
        # Use a fresh repository instance for the same DB path
        new_repo = SQLAlchemyRepository(self.db_path)
        new_client = AccountCategoryClient(repository=new_repo)
        
        # Get stats with new client instance
        persisted_response = new_client.get_top_categories(
            email_address=self.test_email,
            days=1,
            limit=10,
            include_counts=True
        )
        
        # Verify data was persisted
        self.assertEqual(
            len(persisted_response.top_categories),
            initial_category_count,
            "Category count doesn't match after creating new client"
        )
        
        self.assertEqual(
            persisted_response.total_emails,
            initial_total_emails,
            "Total emails count doesn't match after creating new client"
        )
        
        # Verify individual categories match
        initial_categories = {cat.category: cat.total_count for cat in initial_response.top_categories}
        persisted_categories = {cat.category: cat.total_count for cat in persisted_response.top_categories}
        
        self.assertEqual(
            initial_categories,
            persisted_categories,
            "Category details don't match after persistence"
        )

    def test_multiple_processing_runs_accumulate_stats(self):
        """
        Test that running processing multiple times accumulates statistics correctly.
        """
        # First processing run
        first_result = self.processor_service.process_account(self.test_email)
        self.assertTrue(first_result.get('success', False))
        first_email_count = first_result['emails_processed']
        
        # Get initial stats
        initial_stats = self.account_category_client.get_top_categories(
            email_address=self.test_email,
            days=1,
            limit=50
        )
        
        # Reset the fake fetcher with new emails for second run
        # Note: In a real scenario, this would be new emails arriving
        # For this test, we'll process again (the deduplication should prevent double-counting)
        
        # Second processing run
        second_result = self.processor_service.process_account(self.test_email)
        
        # Get updated stats
        updated_stats = self.account_category_client.get_top_categories(
            email_address=self.test_email,
            days=1,
            limit=50
        )
        
        # Due to deduplication, total should remain the same if processing same emails
        # But categories should still be tracked
        self.assertGreater(len(updated_stats.top_categories), 0, "Categories lost after second run")
        
        print(f"\n📊 Stats after multiple runs:")
        print(f"  Initial emails: {initial_stats.total_emails}")
        print(f"  After second run: {updated_stats.total_emails}")
        print(f"  Categories tracked: {len(updated_stats.top_categories)}")


if __name__ == '__main__':
    unittest.main()
