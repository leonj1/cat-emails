"""
Tests for AccountEmailProcessorService to ensure proper email processing workflow.
"""
import unittest
from unittest.mock import Mock, MagicMock
from datetime import datetime, date
from faker import Faker

from services.account_email_processor_service import AccountEmailProcessorService
from services.processing_status_manager import ProcessingStatusManager, ProcessingState
from services.fake_email_categorizer import FakeEmailCategorizer
from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
from tests.fake_account_category_client import FakeAccountCategoryClient, FakeEmailAccount
from tests.fake_gmail_fetcher import FakeGmailFetcher


class TestAccountEmailProcessorService(unittest.TestCase):
    """Test cases for AccountEmailProcessorService."""

    def setUp(self):
        """Set up test fixtures."""
        # Initialize Faker
        fake = Faker()

        # Create mock dependencies
        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")

        self.api_token = fake.uuid4()
        self.llm_model = "vertex/google/gemini-2.5-flash"

        # Initialize fake account category client (no database needed!)
        self.account_category_client = FakeAccountCategoryClient()

        # Initialize factory
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        # Create default fake fetcher with required attributes
        # (tests can override by setting self.current_fetcher before calling process_account)
        from collections import Counter
        self.current_fetcher = FakeGmailFetcher()
        self.current_fetcher.summary_service = Mock()
        self.current_fetcher.summary_service.run_metrics = {'fetched': 0}
        self.current_fetcher.summary_service.db_service = None  # Disable database checks in tests
        self.current_fetcher.account_service = self.account_category_client
        self.current_fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        # Initialize service with fetcher creation callback
        self.service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            create_gmail_fetcher=lambda email, pwd, token: self.current_fetcher
        )

        # Test data
        self.test_email = fake.email()
        self.test_password = fake.password(length=16)

    def _create_configured_fake_fetcher(self, emails=None, stats=None):
        """Helper to create and configure a fake fetcher with required attributes."""
        from collections import Counter
        fetcher = FakeGmailFetcher()

        # Add mock summary_service (required by AccountEmailProcessorService)
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None  # Disable database checks in tests

        # Add mock account_service (optional, used for recording stats)
        fetcher.account_service = self.account_category_client

        # Add stats attribute (required for result reporting)
        # Must include 'categories' key like the real GmailFetcher
        default_stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}
        if stats:
            # Merge provided stats with defaults (ensure 'categories' exists)
            default_stats.update(stats)
            if 'categories' not in default_stats:
                default_stats['categories'] = Counter()
        fetcher.stats = default_stats

        # Pre-populate with test emails if provided
        if emails:
            for email in emails:
                fetcher.add_test_email(
                    subject=email.get('Subject', 'Test'),
                    body=email.get('Body', 'Test body'),
                    sender=email.get('From', 'test@example.com'),
                    message_id=email.get('Message-ID')
                )

        return fetcher

    def test_initialization(self):
        """Test service initialization with all dependencies."""
        self.assertIsNotNone(self.service)
        self.assertEqual(self.service.api_token, self.api_token)
        self.assertEqual(self.service.llm_model, self.llm_model)
        self.assertEqual(self.service.processing_status_manager, self.mock_processing_status_manager)
        self.assertEqual(self.service.settings_service, self.mock_settings_service)
        self.assertEqual(self.service.email_categorizer, self.fake_email_categorizer)

    def test_process_account_already_processing(self):
        """Test process_account when another account is already being processed."""
        # Setup: Make start_processing raise ValueError
        fake = Faker()
        another_email = fake.email()
        self.mock_processing_status_manager.start_processing.side_effect = ValueError(
            f"Processing already active for {another_email}"
        )

        # Execute
        result = self.service.process_account(self.test_email)

        # Verify
        self.assertFalse(result['success'])
        self.assertIn('Processing already in progress', result['error'])
        self.assertEqual(result['account'], self.test_email)
        self.assertIn('timestamp', result)

    def test_process_account_not_found(self):
        """Test process_account when account doesn't exist in database."""
        # Execute - account doesn't exist in fake client
        result = self.service.process_account(self.test_email)

        # Verify
        self.assertFalse(result['success'])
        self.assertIn('not found in database', result['error'])
        self.assertEqual(result['account'], self.test_email)

        # Verify status manager calls
        self.mock_processing_status_manager.update_status.assert_called()
        self.mock_processing_status_manager.complete_processing.assert_called()

    def test_process_account_no_password(self):
        """Test process_account when account has no app password configured."""
        # Setup - create account without app password
        account = self.account_category_client.get_or_create_account(self.test_email, None, None, None)
        account.app_password = None

        # Execute
        result = self.service.process_account(self.test_email)

        # Verify
        self.assertFalse(result['success'])
        self.assertIn('No app password configured', result['error'])
        self.assertEqual(result['account'], self.test_email)

        # Verify status manager calls
        self.mock_processing_status_manager.update_status.assert_called_with(
            ProcessingState.ERROR,
            unittest.mock.ANY,
            error_message=unittest.mock.ANY
        )
        self.mock_processing_status_manager.complete_processing.assert_called()

    def test_process_account_success(self):
        """Test successful email processing workflow."""
        # Setup account with app password
        account = self.account_category_client.get_or_create_account(self.test_email, None, None, None)
        account.app_password = self.test_password

        # Setup settings
        self.mock_settings_service.get_lookback_hours.return_value = 2

        # Setup test emails
        fake = Faker()
        msg_id_1 = fake.uuid4()
        msg_id_2 = fake.uuid4()
        test_emails = [
            {'Message-ID': msg_id_1, 'Subject': fake.sentence(), 'From': fake.email()},
            {'Message-ID': msg_id_2, 'Subject': fake.sentence(), 'From': fake.email()}
        ]

        # Create configured fake fetcher
        self.current_fetcher = self._create_configured_fake_fetcher(
            emails=test_emails,
            stats={'deleted': 5, 'kept': 10}
        )

        # Execute (EmailProcessorService will be created automatically inside process_account)
        result = self.service.process_account(self.test_email)

        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['account'], self.test_email)
        self.assertEqual(result['emails_found'], 2)
        self.assertEqual(result['emails_processed'], 2)
        self.assertIn('processing_time_seconds', result)
        self.assertIn('timestamp', result)

        # Verify fetcher was used (disconnect happens in finally block)
        # The fake fetcher should have been disconnected after processing
        self.assertFalse(self.current_fetcher.connected)

        # Verify status updates
        self.mock_processing_status_manager.start_processing.assert_called_once_with(self.test_email)
        self.assertTrue(self.mock_processing_status_manager.update_status.called)
        self.mock_processing_status_manager.complete_processing.assert_called_once()

    def test_process_account_fetcher_exception(self):
        """Test process_account when fetcher raises an exception."""
        # Setup account with app password
        account = self.account_category_client.get_or_create_account(self.test_email, None, None, None)
        account.app_password = self.test_password

        # Setup settings
        self.mock_settings_service.get_lookback_hours.return_value = 2

        # Setup fetcher that raises exception on connect
        self.current_fetcher = Mock()
        self.current_fetcher.connect.side_effect = Exception("IMAP connection failed")
        self.current_fetcher.summary_service = Mock()

        # Execute
        result = self.service.process_account(self.test_email)

        # Verify
        self.assertFalse(result['success'])
        self.assertIn('IMAP connection failed', result['error'])
        self.assertEqual(result['account'], self.test_email)

        # Verify status manager was updated with error
        error_call = None
        for call_args in self.mock_processing_status_manager.update_status.call_args_list:
            if call_args[0][0] == ProcessingState.ERROR:
                error_call = call_args
                break

        self.assertIsNotNone(error_call, "Status manager should have been updated with ERROR state")
        self.mock_processing_status_manager.complete_processing.assert_called()

    def test_process_account_no_new_emails(self):
        """Test process_account when no new emails are found."""
        # Setup account with app password
        account = self.account_category_client.get_or_create_account(self.test_email, None, None, None)
        account.app_password = self.test_password

        # Setup settings
        self.mock_settings_service.get_lookback_hours.return_value = 2

        # Create configured fake fetcher with no emails
        self.current_fetcher = self._create_configured_fake_fetcher(
            emails=[],  # No emails
            stats={'deleted': 0, 'kept': 0}
        )

        # Execute (EmailProcessorService will be created automatically inside process_account)
        result = self.service.process_account(self.test_email)

        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['emails_found'], 0)
        self.assertEqual(result['emails_processed'], 0)

    def test_process_account_logs_collector_integration(self):
        """Test that LogsCollectorService is properly disabled during tests."""
        # Execute - LogsCollectorService will be disabled (no api_url)
        # Account doesn't exist in fake client
        result = self.service.process_account(self.test_email)

        # Verify the process completed without errors from logging
        self.assertFalse(result['success'])
        self.assertIn('not found in database', result['error'])

    def test_process_account_category_stats_recording(self):
        """Test that category statistics are recorded after processing."""
        # Setup account with app password
        account = self.account_category_client.get_or_create_account(self.test_email, None, None, None)
        account.app_password = self.test_password

        # Setup settings
        self.mock_settings_service.get_lookback_hours.return_value = 2

        # Setup emails
        fake = Faker()
        msg_id_1 = fake.uuid4()
        msg_id_2 = fake.uuid4()
        msg_id_3 = fake.uuid4()
        test_emails = [
            {'Message-ID': msg_id_1, 'Subject': fake.sentence(), 'From': fake.email()},
            {'Message-ID': msg_id_2, 'Subject': fake.sentence(), 'From': fake.email()},
            {'Message-ID': msg_id_3, 'Subject': fake.sentence(), 'From': fake.email()}
        ]

        # Create configured fake fetcher
        self.current_fetcher = self._create_configured_fake_fetcher(
            emails=test_emails,
            stats={'deleted': 2, 'kept': 3}
        )

        # Execute (EmailProcessorService will be created automatically inside process_account)
        # The fake categorizer will categorize all emails as "Marketing" by default
        result = self.service.process_account(self.test_email)

        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['emails_found'], 3, f"Expected 3 emails but found {result.get('emails_found')}")
        self.assertEqual(result['emails_processed'], 3, f"Expected to process 3 emails but processed {result.get('emails_processed')}")

        # Verify category stats were recorded in the fake client
        self.assertIn(self.test_email.lower(), self.account_category_client.category_stats)
        recorded_stats = self.account_category_client.category_stats[self.test_email.lower()]
        self.assertEqual(len(recorded_stats), 1)
        # With 3 emails all categorized as "Marketing" by FakeEmailCategorizer
        self.assertIn('Marketing', recorded_stats[0]['stats'])
        self.assertIsInstance(recorded_stats[0]['date'], date)

        # Verify last scan was updated
        updated_account = self.account_category_client.get_account_by_email(self.test_email)
        self.assertIsNotNone(updated_account.last_scan_at)


class TestAccountEmailProcessorServiceStatusUpdates(unittest.TestCase):
    """Test cases for status update progression in AccountEmailProcessorService."""

    def setUp(self):
        """Set up test fixtures."""
        fake = Faker()

        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.fake_account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        # Create default fake fetcher with required attributes
        # (tests can override by setting self.current_fetcher before calling process_account)
        from collections import Counter
        self.current_fetcher = FakeGmailFetcher()
        self.current_fetcher.summary_service = Mock()
        self.current_fetcher.summary_service.run_metrics = {'fetched': 0}
        self.current_fetcher.summary_service.db_service = None  # Disable database checks in tests
        self.current_fetcher.account_service = self.fake_account_category_client
        self.current_fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        self.service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=fake.uuid4(),
            llm_model=fake.word(),
            account_category_client=self.fake_account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            create_gmail_fetcher=lambda email, pwd, token: self.current_fetcher
        )

    def test_status_progression_through_processing_states(self):
        """Test that status updates progress through expected states."""
        # Setup
        fake = Faker()
        test_email = fake.email()
        account = self.fake_account_category_client.get_or_create_account(test_email, None, None, None)
        account.app_password = fake.password(length=16)
        self.mock_settings_service.get_lookback_hours.return_value = 2

        # Setup fetcher with no emails
        from collections import Counter
        self.current_fetcher = FakeGmailFetcher()
        self.current_fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}
        self.current_fetcher.summary_service = Mock()
        self.current_fetcher.summary_service.run_metrics = {'fetched': 0}
        self.current_fetcher.summary_service.db_service = None  # Disable database checks in tests
        self.current_fetcher.account_service = self.fake_account_category_client

        # Execute (EmailProcessorService will be created automatically inside process_account)
        self.service.process_account(test_email)

        # Verify status progression
        update_calls = self.mock_processing_status_manager.update_status.call_args_list
        states_used = [call[0][0] for call in update_calls]

        # Should have CONNECTING, FETCHING, PROCESSING, and COMPLETED states
        self.assertIn(ProcessingState.CONNECTING, states_used)
        self.assertIn(ProcessingState.FETCHING, states_used)
        self.assertIn(ProcessingState.PROCESSING, states_used)
        self.assertIn(ProcessingState.COMPLETED, states_used)


if __name__ == '__main__':
    unittest.main()
