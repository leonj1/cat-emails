"""
TDD Test: emails_reviewed count is incremented when emails are processed.

This test verifies that when AccountEmailProcessorService.process_account()
processes emails, it correctly calls increment_reviewed() on the
ProcessingStatusManager for each email processed.

ROOT CAUSE IDENTIFIED:
- services/account_email_processor_service.py:232 - processor.process_email(msg)
  is called but increment_reviewed() is never called
- The increment_reviewed() method exists in ProcessingStatusManager (lines 263-279)
  but is never invoked during email processing

EXPECTED FIX LOCATION:
- services/account_email_processor_service.py, around line 232-233
- After processor.process_email(msg) is called, add:
    self.processing_status_manager.increment_reviewed()

TEST APPROACH (TDD Red-Green):
1. This test will FAIL initially (Red phase) because increment_reviewed() is not called
2. After implementing the fix, this test will PASS (Green phase)
"""
import unittest
from unittest.mock import Mock, MagicMock, call
from collections import Counter
from faker import Faker

from services.account_email_processor_service import AccountEmailProcessorService
from services.processing_status_manager import ProcessingStatusManager, ProcessingState
from services.fake_email_categorizer import FakeEmailCategorizer
from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
from tests.fake_account_category_client import FakeAccountCategoryClient
from tests.fake_gmail_fetcher import FakeGmailFetcher


class TestEmailsReviewedCountIntegration(unittest.TestCase):
    """
    Test that emails_reviewed count is correctly incremented during processing.

    BDD Scenario:
        Given an account with emails to process
        When the AccountEmailProcessorService processes the emails
        Then increment_reviewed() should be called once per email processed
        And the final emails_reviewed count should match the number of emails processed
    """

    def setUp(self):
        """Set up test fixtures."""
        self.fake = Faker()

        # Create mock processing status manager to track increment_reviewed calls
        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.fake_account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        # Create fake fetcher
        self.current_fetcher = FakeGmailFetcher()
        self.current_fetcher.summary_service = Mock()
        self.current_fetcher.summary_service.run_metrics = {'fetched': 0}
        self.current_fetcher.summary_service.db_service = None
        self.current_fetcher.account_service = self.fake_account_category_client
        self.current_fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        # Create service under test
        self.service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.fake.uuid4(),
            llm_model="test-model",
            account_category_client=self.fake_account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            create_gmail_fetcher=lambda email, pwd, token: self.current_fetcher
        )

    def _create_configured_fake_fetcher(self, emails=None, stats=None):
        """Helper to create and configure a fake fetcher with required attributes."""
        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.fake_account_category_client

        default_stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}
        if stats:
            default_stats.update(stats)
            if 'categories' not in default_stats:
                default_stats['categories'] = Counter()
        fetcher.stats = default_stats

        if emails:
            for email in emails:
                fetcher.add_test_email(
                    subject=email.get('Subject', 'Test'),
                    body=email.get('Body', 'Test body'),
                    sender=email.get('From', 'test@example.com'),
                    message_id=email.get('Message-ID')
                )

        return fetcher

    def test_increment_reviewed_called_for_single_email(self):
        """
        Test that increment_reviewed is called when processing a single email.

        Given: An account with 1 email to process
        When: process_account() is called
        Then: increment_reviewed() should be called exactly 1 time
        """
        # Setup account
        test_email = self.fake.email()
        account = self.fake_account_category_client.get_or_create_account(test_email, None, None, None, None)
        account.app_password = self.fake.password(length=16)

        # Setup settings
        self.mock_settings_service.get_lookback_hours.return_value = 2

        # Setup 1 test email
        test_emails = [
            {'Message-ID': self.fake.uuid4(), 'Subject': 'Test Email', 'From': self.fake.email()}
        ]
        self.current_fetcher = self._create_configured_fake_fetcher(emails=test_emails)

        # Execute
        result = self.service.process_account(test_email)

        # Verify success
        self.assertTrue(result['success'], f"Processing failed: {result.get('error')}")
        self.assertEqual(result['emails_processed'], 1)

        # Verify increment_reviewed was called exactly 1 time
        self.mock_processing_status_manager.increment_reviewed.assert_called()
        self.assertEqual(
            self.mock_processing_status_manager.increment_reviewed.call_count,
            1,
            "increment_reviewed() should be called once per email processed"
        )

    def test_increment_reviewed_called_for_multiple_emails(self):
        """
        Test that increment_reviewed is called once for each email processed.

        Given: An account with 5 emails to process
        When: process_account() is called
        Then: increment_reviewed() should be called exactly 5 times
        """
        # Setup account
        test_email = self.fake.email()
        account = self.fake_account_category_client.get_or_create_account(test_email, None, None, None, None)
        account.app_password = self.fake.password(length=16)

        # Setup settings
        self.mock_settings_service.get_lookback_hours.return_value = 2

        # Setup 5 test emails
        num_emails = 5
        test_emails = [
            {'Message-ID': self.fake.uuid4(), 'Subject': f'Test Email {i}', 'From': self.fake.email()}
            for i in range(num_emails)
        ]
        self.current_fetcher = self._create_configured_fake_fetcher(emails=test_emails)

        # Execute
        result = self.service.process_account(test_email)

        # Verify success
        self.assertTrue(result['success'], f"Processing failed: {result.get('error')}")
        self.assertEqual(result['emails_processed'], num_emails)

        # Verify increment_reviewed was called exactly num_emails times
        self.assertEqual(
            self.mock_processing_status_manager.increment_reviewed.call_count,
            num_emails,
            f"increment_reviewed() should be called {num_emails} times for {num_emails} emails"
        )

    def test_increment_reviewed_not_called_when_no_emails(self):
        """
        Test that increment_reviewed is not called when there are no emails to process.

        Given: An account with 0 emails to process
        When: process_account() is called
        Then: increment_reviewed() should NOT be called
        """
        # Setup account
        test_email = self.fake.email()
        account = self.fake_account_category_client.get_or_create_account(test_email, None, None, None, None)
        account.app_password = self.fake.password(length=16)

        # Setup settings
        self.mock_settings_service.get_lookback_hours.return_value = 2

        # Setup 0 test emails
        self.current_fetcher = self._create_configured_fake_fetcher(emails=[])

        # Execute
        result = self.service.process_account(test_email)

        # Verify success
        self.assertTrue(result['success'], f"Processing failed: {result.get('error')}")
        self.assertEqual(result['emails_processed'], 0)

        # Verify increment_reviewed was NOT called
        self.mock_processing_status_manager.increment_reviewed.assert_not_called()


class TestEmailsReviewedCountEndToEnd(unittest.TestCase):
    """
    End-to-end test using real ProcessingStatusManager to verify emails_reviewed count.

    This test uses the actual ProcessingStatusManager (not a mock) to verify that
    the emails_reviewed count is correctly tracked in the processing history.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.fake = Faker()

        # Use REAL ProcessingStatusManager (not a mock)
        self.processing_status_manager = ProcessingStatusManager(max_history=10)
        self.mock_settings_service = Mock()
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.fake_account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        # Create fake fetcher
        self.current_fetcher = FakeGmailFetcher()
        self.current_fetcher.summary_service = Mock()
        self.current_fetcher.summary_service.run_metrics = {'fetched': 0}
        self.current_fetcher.summary_service.db_service = None
        self.current_fetcher.account_service = self.fake_account_category_client
        self.current_fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        # Create service under test with REAL ProcessingStatusManager
        self.service = AccountEmailProcessorService(
            processing_status_manager=self.processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.fake.uuid4(),
            llm_model="test-model",
            account_category_client=self.fake_account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            create_gmail_fetcher=lambda email, pwd, token: self.current_fetcher
        )

    def _create_configured_fake_fetcher(self, emails=None, stats=None):
        """Helper to create and configure a fake fetcher with required attributes."""
        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.fake_account_category_client

        default_stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}
        if stats:
            default_stats.update(stats)
            if 'categories' not in default_stats:
                default_stats['categories'] = Counter()
        fetcher.stats = default_stats

        if emails:
            for email in emails:
                fetcher.add_test_email(
                    subject=email.get('Subject', 'Test'),
                    body=email.get('Body', 'Test body'),
                    sender=email.get('From', 'test@example.com'),
                    message_id=email.get('Message-ID')
                )

        return fetcher

    def test_emails_reviewed_count_in_processing_history(self):
        """
        Test that emails_reviewed count is correctly recorded in processing history.

        Given: An account with 3 emails to process
        When: process_account() is called and completes successfully
        Then: The processing history should show emails_reviewed = 3

        This is the key test that validates the fix for the bug where
        /api/processing/history shows emails_reviewed = 0 even when emails
        were processed.
        """
        # Setup account
        test_email = self.fake.email()
        account = self.fake_account_category_client.get_or_create_account(test_email, None, None, None, None)
        account.app_password = self.fake.password(length=16)

        # Setup settings
        self.mock_settings_service.get_lookback_hours.return_value = 2

        # Setup 3 test emails
        num_emails = 3
        test_emails = [
            {'Message-ID': self.fake.uuid4(), 'Subject': f'Test Email {i}', 'From': self.fake.email()}
            for i in range(num_emails)
        ]
        self.current_fetcher = self._create_configured_fake_fetcher(emails=test_emails)

        # Execute
        result = self.service.process_account(test_email)

        # Verify success
        self.assertTrue(result['success'], f"Processing failed: {result.get('error')}")
        self.assertEqual(result['emails_processed'], num_emails)

        # Get processing history (returns list of dicts, most recent first)
        history = self.processing_status_manager.get_recent_runs()

        # Verify history exists
        self.assertGreater(len(history), 0, "Processing history should not be empty")

        # Get the most recent processing run
        latest_run = history[0]

        # Verify emails_reviewed count matches the number of emails processed
        emails_reviewed = latest_run.get('emails_reviewed', 0)
        self.assertEqual(
            emails_reviewed,
            num_emails,
            f"emails_reviewed should be {num_emails} but got {emails_reviewed}. "
            f"This indicates increment_reviewed() is not being called during email processing."
        )


if __name__ == '__main__':
    unittest.main()
