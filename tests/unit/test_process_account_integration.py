"""
Tests for integrating BlockingRecommendationCollector and RecommendationEmailNotifier
into AccountEmailProcessorService.process_account() (TDD Red Phase).

This module tests the integration of domain blocking recommendations into the main
email processing workflow. The integration adds:
1. BlockingRecommendationCollector injection via constructor
2. RecommendationEmailNotifier injection via constructor
3. Collection of domain recommendations during email processing
4. Sending notification emails after processing
5. Extended response with recommendation fields

Based on Gherkin scenarios from the Blocking Recommendations Email Notification feature.
These tests follow TDD Red phase - they will fail until implementation is complete.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date
from typing import Set, Dict, List, Optional
from collections import Counter

import uuid
import random
import string


# ============================================================================
# SECTION 1: Constructor Injection Tests
# ============================================================================

class TestAccountEmailProcessorServiceConstructorInjection(unittest.TestCase):
    """
    Tests for injecting BlockingRecommendationCollector and RecommendationEmailNotifier
    into AccountEmailProcessorService via constructor.

    Following strict architecture principles:
    - Dependencies passed as interfaces
    - No default values for constructor arguments
    - Constructor injection pattern
    """

    def setUp(self):
        """Set up test fixtures."""
        # Import dependencies
        from services.processing_status_manager import ProcessingStatusManager
        from services.fake_email_categorizer import FakeEmailCategorizer
        from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
        from tests.fake_account_category_client import FakeAccountCategoryClient

        # Create base mock dependencies
        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.api_token = str(uuid.uuid4())
        self.llm_model = "vertex/google/gemini-2.5-flash"
        self.account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

    def test_accepts_blocking_recommendation_collector_parameter(self):
        """
        Test that AccountEmailProcessorService constructor accepts
        a blocking_recommendation_collector parameter.

        The implementation should:
        - Accept an IBlockingRecommendationCollector instance
        - Store it for use during email processing
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.interfaces.blocking_recommendation_collector_interface import (
            IBlockingRecommendationCollector
        )

        # Arrange
        mock_collector = Mock(spec=IBlockingRecommendationCollector)
        mock_notifier = Mock()

        # Act
        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=mock_collector,
            recommendation_email_notifier=mock_notifier
        )

        # Assert
        self.assertIsNotNone(service)
        self.assertEqual(
            service.blocking_recommendation_collector,
            mock_collector,
            "Service should store the blocking_recommendation_collector"
        )

    def test_accepts_recommendation_email_notifier_parameter(self):
        """
        Test that AccountEmailProcessorService constructor accepts
        a recommendation_email_notifier parameter.

        The implementation should:
        - Accept an IRecommendationEmailNotifier instance
        - Store it for use after email processing
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.interfaces.recommendation_email_notifier_interface import (
            IRecommendationEmailNotifier
        )

        # Arrange
        mock_collector = Mock()
        mock_notifier = Mock(spec=IRecommendationEmailNotifier)

        # Act
        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=mock_collector,
            recommendation_email_notifier=mock_notifier
        )

        # Assert
        self.assertIsNotNone(service)
        self.assertEqual(
            service.recommendation_email_notifier,
            mock_notifier,
            "Service should store the recommendation_email_notifier"
        )


# ============================================================================
# SECTION 2: Collector Clear at Start of Processing
# ============================================================================

class TestCollectorClearedAtStartOfProcessing(unittest.TestCase):
    """
    Scenario: Collector is cleared between processing runs

    Given the blocked domains list is empty
    And account "user@gmail.com" was previously processed with recommendations
    When the process_account function runs again for "user@gmail.com"
    Then the recommendations should only reflect the current processing run
    And previous recommendations should not be carried over
    """

    def setUp(self):
        """Set up test fixtures."""
        

        from services.processing_status_manager import ProcessingStatusManager
        from services.fake_email_categorizer import FakeEmailCategorizer
        from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
        from tests.fake_account_category_client import FakeAccountCategoryClient
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.mock_settings_service.get_lookback_hours.return_value = 2
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.api_token = str(uuid.uuid4())
        self.llm_model = "vertex/google/gemini-2.5-flash"
        self.account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        # Create configured fake fetcher
        self.current_fetcher = FakeGmailFetcher()
        self.current_fetcher.summary_service = Mock()
        self.current_fetcher.summary_service.run_metrics = {'fetched': 0}
        self.current_fetcher.summary_service.db_service = None
        self.current_fetcher.account_service = self.account_category_client
        self.current_fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        self.test_email = "test@example.com"

    def test_collector_clear_called_at_start_of_process_account(self):
        """
        Test that collector.clear() is called at the start of process_account().

        This ensures previous recommendations don't carry over to new runs.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from models.domain_recommendation_models import NotificationResult

        # Arrange
        mock_collector = Mock()
        mock_collector.get_recommendations.return_value = []
        mock_collector.get_total_emails_matched.return_value = 0
        mock_collector.get_unique_domains_count.return_value = 0

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=False,
            recipient=self.test_email,
            recommendations_count=0,
            error_message=None
        )

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=mock_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: self.current_fetcher
        )

        # Setup account
        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        service.process_account(self.test_email)

        # Assert - clear() should be called before any processing
        mock_collector.clear.assert_called()

    def test_new_run_only_reflects_current_data(self):
        """
        Test that recommendations only reflect current processing run.

        Given account was previously processed with recommendations,
        when process_account runs again, the recommendations should
        only contain data from the current run.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import DomainRecommendation, NotificationResult

        # Arrange - Use real collector to test clearing behavior
        real_collector = BlockingRecommendationCollector()

        # Simulate previous run data
        real_collector.collect("old-spam.com", "Marketing", set())
        real_collector.collect("old-spam.com", "Marketing", set())
        initial_count = real_collector.get_total_emails_matched()
        self.assertEqual(initial_count, 2, "Precondition: collector should have previous data")

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=0,
            error_message=None
        )

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: self.current_fetcher
        )

        # Setup account with no emails
        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert - After processing with no emails, collector should be cleared
        # and not contain old data
        self.assertEqual(
            real_collector.get_total_emails_matched(),
            0,
            "Collector should be cleared, not contain old data"
        )


# ============================================================================
# SECTION 3: Domain Collection During Processing
# ============================================================================

class TestDomainCollectionDuringProcessing(unittest.TestCase):
    """
    Scenario: Generate recommendations for unblocked Marketing domain

    Given the blocked domains list is empty
    And the inbox contains emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "marketing-spam.com" with category "Marketing"
    """

    def setUp(self):
        """Set up test fixtures."""
        

        from services.processing_status_manager import ProcessingStatusManager
        from services.fake_email_categorizer import FakeEmailCategorizer
        from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
        from tests.fake_account_category_client import FakeAccountCategoryClient
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.mock_settings_service.get_lookback_hours.return_value = 2
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.api_token = str(uuid.uuid4())
        self.llm_model = "vertex/google/gemini-2.5-flash"
        self.account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        self.test_email = "user@gmail.com"

    def _create_configured_fake_fetcher(self, emails):
        """Helper to create a configured fake fetcher."""
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        for email in emails:
            fetcher.add_test_email(
                subject=email.get('Subject', 'Test'),
                body=email.get('Body', 'Test body'),
                sender=email.get('From', 'test@example.com'),
                message_id=email.get('Message-ID')
            )

        return fetcher

    def test_collector_collect_called_during_email_processing(self):
        """
        Test that collector.collect() is called for each email during processing.

        During the email processing loop, for each email that gets categorized,
        the collector should be called with the sender domain, category, and
        blocked domains set.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from models.domain_recommendation_models import NotificationResult

        # Arrange
        mock_collector = Mock()
        mock_collector.get_recommendations.return_value = []
        mock_collector.get_total_emails_matched.return_value = 0
        mock_collector.get_unique_domains_count.return_value = 0

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=0,
            error_message=None
        )

        test_emails = [
            {'Message-ID': str(uuid.uuid4()), 'Subject': 'Marketing email', 'From': 'newsletter@marketing-spam.com'},
        ]

        fetcher = self._create_configured_fake_fetcher(test_emails)

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=mock_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        service.process_account(self.test_email)

        # Assert - collector.collect() should be called for processed emails
        mock_collector.collect.assert_called()

    def test_collect_receives_correct_sender_domain(self):
        """
        Test that collector.collect() receives the correct sender domain.

        The domain should be extracted from the sender email address.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from models.domain_recommendation_models import NotificationResult

        # Arrange
        mock_collector = Mock()
        mock_collector.get_recommendations.return_value = []
        mock_collector.get_total_emails_matched.return_value = 0
        mock_collector.get_unique_domains_count.return_value = 0

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=0,
            error_message=None
        )

        test_emails = [
            {'Message-ID': str(uuid.uuid4()), 'Subject': 'Marketing email', 'From': 'newsletter@marketing-spam.com'},
        ]

        fetcher = self._create_configured_fake_fetcher(test_emails)

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=mock_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        service.process_account(self.test_email)

        # Assert - Check that collect was called with the correct domain
        collect_calls = mock_collector.collect.call_args_list
        self.assertTrue(
            len(collect_calls) > 0,
            "collector.collect should be called at least once"
        )

        # Check the first argument (sender_domain) contains the expected domain
        found_domain = False
        for call in collect_calls:
            args, kwargs = call
            sender_domain = args[0] if args else kwargs.get('sender_domain')
            if 'marketing-spam.com' in sender_domain.lower():
                found_domain = True
                break

        self.assertTrue(
            found_domain,
            f"collector.collect should be called with domain 'marketing-spam.com'. Calls: {collect_calls}"
        )


# ============================================================================
# SECTION 4: Multiple Domains with Different Categories
# ============================================================================

class TestMultipleDomainsWithDifferentCategories(unittest.TestCase):
    """
    Scenario: Multiple domains with different categories and counts

    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email                    | category      | count |
      | spam@marketing-spam.com         | Marketing     | 12    |
      | promo@ads-network.io            | Advertising   | 8     |
      | donate@pay-now.biz              | Wants-Money   | 3     |
      | news@legit-news.com             | Personal      | 5     |
    When the process_account function runs for "user@gmail.com"
    Then the response should include 3 domain recommendations
    And the "total_emails_matched" should be 23
    And domain "legit-news.com" should not be in recommendations
    """

    def setUp(self):
        """Set up test fixtures."""
        

        from services.processing_status_manager import ProcessingStatusManager
        from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
        from tests.fake_account_category_client import FakeAccountCategoryClient
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.mock_settings_service.get_lookback_hours.return_value = 2
        self.api_token = str(uuid.uuid4())
        self.llm_model = "vertex/google/gemini-2.5-flash"
        self.account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        self.test_email = "user@gmail.com"

    def _create_mock_categorizer_with_mapping(self, email_category_map: Dict[str, str]):
        """Create a mock categorizer that returns specific categories based on content keywords."""
        mock_categorizer = Mock()

        def categorize_side_effect(contents, model):
            # contents parameter contains cleaned email content (subject + body)
            contents_lower = contents.lower()

            # Direct keyword to domain/category mapping
            # Check in priority order to handle overlapping keywords
            if 'marketing' in contents_lower and 'marketing-spam.com' in email_category_map:
                return email_category_map['marketing-spam.com']
            elif ('ads' in contents_lower or 'advertising' in contents_lower) and 'ads-network.io' in email_category_map:
                return email_category_map['ads-network.io']
            elif ('donate' in contents_lower or 'money' in contents_lower) and 'pay-now.biz' in email_category_map:
                return email_category_map['pay-now.biz']
            elif 'news' in contents_lower and 'legit-news.com' in email_category_map:
                return email_category_map['legit-news.com']

            return "Unknown"

        mock_categorizer.categorize.side_effect = categorize_side_effect
        return mock_categorizer

    def test_response_includes_correct_number_of_recommendations(self):
        """
        Test that the response includes the correct number of domain recommendations.

        Only domains from qualifying categories (Marketing, Advertising, Wants-Money)
        should be included. Personal category should be excluded.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import DomainRecommendation, NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        # Arrange - Use real collector
        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=3,
            error_message=None
        )

        # Map sender patterns to categories
        email_category_map = {
            'marketing-spam.com': 'Marketing',
            'ads-network.io': 'Advertising',
            'pay-now.biz': 'Wants-Money',
            'legit-news.com': 'Personal'  # Non-qualifying category
        }
        mock_categorizer = self._create_mock_categorizer_with_mapping(email_category_map)

        # Create test emails - 12 Marketing, 8 Advertising, 3 Wants-Money, 5 Personal
        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        for i in range(12):
            fetcher.add_test_email(subject=f"Marketing {i}", body="spam", sender=f"spam{i}@marketing-spam.com")
        for i in range(8):
            fetcher.add_test_email(subject=f"Ads {i}", body="promo", sender=f"promo{i}@ads-network.io")
        for i in range(3):
            fetcher.add_test_email(subject=f"Donate {i}", body="money", sender=f"donate{i}@pay-now.biz")
        for i in range(5):
            fetcher.add_test_email(subject=f"News {i}", body="news", sender=f"news{i}@legit-news.com")

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=mock_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertIn(
            'recommended_domains_to_block',
            result,
            "Response should include 'recommended_domains_to_block' field"
        )

        recommendations = result['recommended_domains_to_block']
        self.assertEqual(
            len(recommendations),
            3,
            f"Should have 3 domain recommendations (Marketing, Advertising, Wants-Money), got {len(recommendations)}"
        )

    def test_total_emails_matched_is_sum_of_qualifying_categories(self):
        """
        Test that total_emails_matched is the sum of qualifying category emails only.

        Marketing (12) + Advertising (8) + Wants-Money (3) = 23
        Personal (5) should NOT be counted.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        # Arrange
        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=3,
            error_message=None
        )

        email_category_map = {
            'marketing-spam.com': 'Marketing',
            'ads-network.io': 'Advertising',
            'pay-now.biz': 'Wants-Money',
            'legit-news.com': 'Personal'
        }
        mock_categorizer = self._create_mock_categorizer_with_mapping(email_category_map)

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        for i in range(12):
            fetcher.add_test_email(subject=f"Marketing {i}", body="spam", sender=f"spam{i}@marketing-spam.com")
        for i in range(8):
            fetcher.add_test_email(subject=f"Ads {i}", body="promo", sender=f"promo{i}@ads-network.io")
        for i in range(3):
            fetcher.add_test_email(subject=f"Donate {i}", body="money", sender=f"donate{i}@pay-now.biz")
        for i in range(5):
            fetcher.add_test_email(subject=f"News {i}", body="news", sender=f"news{i}@legit-news.com")

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=mock_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertIn(
            'total_emails_matched',
            result,
            "Response should include 'total_emails_matched' field"
        )

        self.assertEqual(
            result['total_emails_matched'],
            23,
            f"total_emails_matched should be 23, got {result['total_emails_matched']}"
        )

    def test_non_qualifying_domain_not_in_recommendations(self):
        """
        Test that domains from non-qualifying categories are NOT in recommendations.

        'legit-news.com' with category 'Personal' should not appear.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        # Arrange
        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=3,
            error_message=None
        )

        email_category_map = {
            'marketing-spam.com': 'Marketing',
            'legit-news.com': 'Personal'
        }
        mock_categorizer = self._create_mock_categorizer_with_mapping(email_category_map)

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        fetcher.add_test_email(subject="Marketing", body="spam", sender="spam@marketing-spam.com")
        fetcher.add_test_email(subject="News", body="news", sender="news@legit-news.com")

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=mock_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        recommendations = result.get('recommended_domains_to_block', [])
        domains = [r['domain'] if isinstance(r, dict) else r.domain for r in recommendations]

        self.assertNotIn(
            'legit-news.com',
            domains,
            f"'legit-news.com' should NOT be in recommendations. Got: {domains}"
        )


# ============================================================================
# SECTION 5: Response Fields
# ============================================================================

class TestResponseIncludesRecommendationSummary(unittest.TestCase):
    """
    Scenario: Response includes complete recommendation summary

    Given the blocked domains list is empty
    And the inbox contains 10 emails from "spam@example.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the response should include:
      | field                          | expected_value |
      | recommended_domains_to_block   | list           |
      | total_emails_matched           | 10             |
      | unique_domains_count           | 1              |
      | notification_sent              | true           |
      | notification_error             | null           |
    """

    def setUp(self):
        """Set up test fixtures."""
        

        from services.processing_status_manager import ProcessingStatusManager
        from services.fake_email_categorizer import FakeEmailCategorizer
        from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
        from tests.fake_account_category_client import FakeAccountCategoryClient
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.mock_settings_service.get_lookback_hours.return_value = 2
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.api_token = str(uuid.uuid4())
        self.llm_model = "vertex/google/gemini-2.5-flash"
        self.account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        self.test_email = "user@gmail.com"

    def test_response_includes_recommended_domains_to_block(self):
        """
        Test that response includes 'recommended_domains_to_block' field.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        # Arrange
        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=1,
            error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        for i in range(10):
            fetcher.add_test_email(subject=f"Spam {i}", body="spam", sender="spam@example.com")

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertIn(
            'recommended_domains_to_block',
            result,
            "Response should include 'recommended_domains_to_block' field"
        )
        self.assertIsInstance(
            result['recommended_domains_to_block'],
            list,
            "'recommended_domains_to_block' should be a list"
        )

    def test_response_includes_total_emails_matched(self):
        """
        Test that response includes 'total_emails_matched' field.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        # Arrange
        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=1,
            error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        for i in range(10):
            fetcher.add_test_email(subject=f"Spam {i}", body="spam", sender="spam@example.com")

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertIn(
            'total_emails_matched',
            result,
            "Response should include 'total_emails_matched' field"
        )
        self.assertEqual(
            result['total_emails_matched'],
            10,
            f"'total_emails_matched' should be 10, got {result.get('total_emails_matched')}"
        )

    def test_response_includes_unique_domains_count(self):
        """
        Test that response includes 'unique_domains_count' field.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        # Arrange
        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=1,
            error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        for i in range(10):
            fetcher.add_test_email(subject=f"Spam {i}", body="spam", sender="spam@example.com")

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertIn(
            'unique_domains_count',
            result,
            "Response should include 'unique_domains_count' field"
        )
        self.assertEqual(
            result['unique_domains_count'],
            1,
            f"'unique_domains_count' should be 1, got {result.get('unique_domains_count')}"
        )

    def test_response_includes_notification_sent(self):
        """
        Test that response includes 'notification_sent' field.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        # Arrange
        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=1,
            error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        for i in range(10):
            fetcher.add_test_email(subject=f"Spam {i}", body="spam", sender="spam@example.com")

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertIn(
            'notification_sent',
            result,
            "Response should include 'notification_sent' field"
        )
        self.assertTrue(
            result['notification_sent'],
            "'notification_sent' should be True when notification succeeds"
        )

    def test_response_includes_notification_error_null_on_success(self):
        """
        Test that response includes 'notification_error' field as null on success.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        # Arrange
        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=1,
            error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        for i in range(10):
            fetcher.add_test_email(subject=f"Spam {i}", body="spam", sender="spam@example.com")

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertIn(
            'notification_error',
            result,
            "Response should include 'notification_error' field"
        )
        self.assertIsNone(
            result['notification_error'],
            f"'notification_error' should be None on success, got {result.get('notification_error')}"
        )


# ============================================================================
# SECTION 6: Email Notification Failure Handling
# ============================================================================

class TestEmailNotificationFailureHandling(unittest.TestCase):
    """
    Scenario: Email notification failure does not break main processing

    Given the blocked domains list is empty
    And the inbox contains emails from "spam@marketing.com" categorized as "Marketing"
    And the email notification service is failing
    When the process_account function runs for "user@gmail.com"
    Then the processing should complete successfully
    And the response "success" should be true
    And "notification_sent" should be false
    And "notification_error" should contain the failure reason
    And the recommendations should still be included in the response
    """

    def setUp(self):
        """Set up test fixtures."""
        

        from services.processing_status_manager import ProcessingStatusManager
        from services.fake_email_categorizer import FakeEmailCategorizer
        from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
        from tests.fake_account_category_client import FakeAccountCategoryClient
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.mock_settings_service.get_lookback_hours.return_value = 2
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.api_token = str(uuid.uuid4())
        self.llm_model = "vertex/google/gemini-2.5-flash"
        self.account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        self.test_email = "user@gmail.com"

    def test_processing_succeeds_when_notification_fails(self):
        """
        Test that processing completes successfully even when notification fails.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        # Arrange
        real_collector = BlockingRecommendationCollector()

        # Simulate failing notifier
        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=False,
            recipient=self.test_email,
            recommendations_count=1,
            error_message="Connection refused"
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        fetcher.add_test_email(subject="Spam", body="spam", sender="spam@marketing.com")

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertTrue(
            result['success'],
            "Processing should succeed even when notification fails"
        )

    def test_notification_sent_false_when_notification_fails(self):
        """
        Test that 'notification_sent' is false when notification fails.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        # Arrange
        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=False,
            recipient=self.test_email,
            recommendations_count=1,
            error_message="Connection refused"
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        fetcher.add_test_email(subject="Spam", body="spam", sender="spam@marketing.com")

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertFalse(
            result['notification_sent'],
            "'notification_sent' should be False when notification fails"
        )

    def test_notification_error_contains_failure_reason(self):
        """
        Test that 'notification_error' contains the failure reason.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        # Arrange
        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=False,
            recipient=self.test_email,
            recommendations_count=1,
            error_message="Connection refused"
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        fetcher.add_test_email(subject="Spam", body="spam", sender="spam@marketing.com")

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertIn(
            "Connection refused",
            result['notification_error'],
            f"'notification_error' should contain 'Connection refused', got {result.get('notification_error')}"
        )

    def test_recommendations_still_included_when_notification_fails(self):
        """
        Test that recommendations are still included in response when notification fails.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        # Arrange
        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=False,
            recipient=self.test_email,
            recommendations_count=1,
            error_message="Connection refused"
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        fetcher.add_test_email(subject="Spam", body="spam", sender="spam@marketing.com")

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertIn(
            'recommended_domains_to_block',
            result,
            "Recommendations should still be included when notification fails"
        )
        self.assertGreater(
            len(result['recommended_domains_to_block']),
            0,
            "Recommendations list should not be empty"
        )


# ============================================================================
# SECTION 7: Response Maintains Existing Fields
# ============================================================================

class TestResponseMaintainsExistingFields(unittest.TestCase):
    """
    Scenario: Response maintains existing fields

    Given the blocked domains list is empty
    And the inbox contains 10 emails with 3 categorized as "Marketing" from unblocked domains
    When the process_account function runs for "user@gmail.com"
    Then the response should include all existing fields:
      | field                  |
      | account                |
      | emails_found           |
      | emails_processed       |
      | emails_categorized     |
      | processing_time_seconds|
      | timestamp              |
      | success                |
    And the response should also include new recommendation fields
    """

    def setUp(self):
        """Set up test fixtures."""
        

        from services.processing_status_manager import ProcessingStatusManager
        from services.fake_email_categorizer import FakeEmailCategorizer
        from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
        from tests.fake_account_category_client import FakeAccountCategoryClient

        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.mock_settings_service.get_lookback_hours.return_value = 2
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.api_token = str(uuid.uuid4())
        self.llm_model = "vertex/google/gemini-2.5-flash"
        self.account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        self.test_email = "user@gmail.com"

    def test_response_includes_account_field(self):
        """Test that response includes 'account' field."""
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        real_collector = BlockingRecommendationCollector()
        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True, recipient=self.test_email, recommendations_count=0, error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        result = service.process_account(self.test_email)

        self.assertIn('account', result, "Response should include 'account' field")
        self.assertEqual(result['account'], self.test_email)

    def test_response_includes_emails_found_field(self):
        """Test that response includes 'emails_found' field."""
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        real_collector = BlockingRecommendationCollector()
        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True, recipient=self.test_email, recommendations_count=0, error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        result = service.process_account(self.test_email)

        self.assertIn('emails_found', result, "Response should include 'emails_found' field")

    def test_response_includes_emails_processed_field(self):
        """Test that response includes 'emails_processed' field."""
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        real_collector = BlockingRecommendationCollector()
        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True, recipient=self.test_email, recommendations_count=0, error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        result = service.process_account(self.test_email)

        self.assertIn('emails_processed', result, "Response should include 'emails_processed' field")

    def test_response_includes_processing_time_seconds_field(self):
        """Test that response includes 'processing_time_seconds' field."""
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        real_collector = BlockingRecommendationCollector()
        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True, recipient=self.test_email, recommendations_count=0, error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        result = service.process_account(self.test_email)

        self.assertIn('processing_time_seconds', result, "Response should include 'processing_time_seconds' field")

    def test_response_includes_timestamp_field(self):
        """Test that response includes 'timestamp' field."""
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        real_collector = BlockingRecommendationCollector()
        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True, recipient=self.test_email, recommendations_count=0, error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        result = service.process_account(self.test_email)

        self.assertIn('timestamp', result, "Response should include 'timestamp' field")

    def test_response_includes_success_field(self):
        """Test that response includes 'success' field."""
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        real_collector = BlockingRecommendationCollector()
        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True, recipient=self.test_email, recommendations_count=0, error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        result = service.process_account(self.test_email)

        self.assertIn('success', result, "Response should include 'success' field")


# ============================================================================
# SECTION 8: No Recommendations When Inbox is Empty
# ============================================================================

class TestNoRecommendationsWhenInboxEmpty(unittest.TestCase):
    """
    Scenario: No recommendations when inbox is empty

    Given the blocked domains list is empty
    And the inbox is empty
    When the process_account function runs for "user@gmail.com"
    Then the "recommended_domains_to_block" should be an empty list
    And no notification email should be sent
    And the processing should complete successfully
    """

    def setUp(self):
        """Set up test fixtures."""
        

        from services.processing_status_manager import ProcessingStatusManager
        from services.fake_email_categorizer import FakeEmailCategorizer
        from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
        from tests.fake_account_category_client import FakeAccountCategoryClient

        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.mock_settings_service.get_lookback_hours.return_value = 2
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.api_token = str(uuid.uuid4())
        self.llm_model = "vertex/google/gemini-2.5-flash"
        self.account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        self.test_email = "user@gmail.com"

    def test_empty_inbox_returns_empty_recommendations_list(self):
        """
        Test that empty inbox returns empty 'recommended_domains_to_block' list.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=False,
            recipient=self.test_email,
            recommendations_count=0,
            error_message=None
        )

        # Empty fetcher - no emails
        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertIn('recommended_domains_to_block', result)
        self.assertEqual(
            result['recommended_domains_to_block'],
            [],
            f"'recommended_domains_to_block' should be empty list, got {result['recommended_domains_to_block']}"
        )

    def test_no_notification_sent_when_inbox_empty(self):
        """
        Test that no notification email is sent when inbox is empty.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=False,
            recipient=self.test_email,
            recommendations_count=0,
            error_message=None
        )

        # Empty fetcher - no emails
        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert - notification_sent should be false when no recommendations
        self.assertFalse(
            result.get('notification_sent', True),
            "'notification_sent' should be False when inbox is empty"
        )

    def test_processing_succeeds_when_inbox_empty(self):
        """
        Test that processing completes successfully when inbox is empty.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=False,
            recipient=self.test_email,
            recommendations_count=0,
            error_message=None
        )

        # Empty fetcher - no emails
        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert
        self.assertTrue(
            result['success'],
            "Processing should succeed even when inbox is empty"
        )


# ============================================================================
# SECTION 9: Notification Subject
# ============================================================================

class TestNotificationEmailSubject(unittest.TestCase):
    """
    Scenario: Generate recommendations for unblocked Marketing domain

    And a notification email should be sent to "user@gmail.com"
    And the notification email subject should be "Domains recommended to be blocked"
    """

    def setUp(self):
        """Set up test fixtures."""
        

        from services.processing_status_manager import ProcessingStatusManager
        from services.fake_email_categorizer import FakeEmailCategorizer
        from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
        from tests.fake_account_category_client import FakeAccountCategoryClient

        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.mock_settings_service.get_lookback_hours.return_value = 2
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.api_token = str(uuid.uuid4())
        self.llm_model = "vertex/google/gemini-2.5-flash"
        self.account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        self.test_email = "user@gmail.com"

    def test_notifier_send_recommendations_called_with_correct_recipient(self):
        """
        Test that send_recommendations is called with the correct recipient email.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=1,
            error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        fetcher.add_test_email(
            subject="Marketing email",
            body="spam",
            sender="newsletter@marketing-spam.com"
        )

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        service.process_account(self.test_email)

        # Assert
        mock_notifier.send_recommendations.assert_called()
        call_args = mock_notifier.send_recommendations.call_args
        recipient_arg = call_args[0][0] if call_args[0] else call_args[1].get('recipient_email')

        self.assertEqual(
            recipient_arg,
            self.test_email,
            f"send_recommendations should be called with recipient '{self.test_email}', got '{recipient_arg}'"
        )


# ============================================================================
# SECTION 10: Complete Response Structure Test
# ============================================================================

class TestCompleteResponseStructure(unittest.TestCase):
    """
    Test that the complete response structure is correct.

    This test verifies all expected fields are present and have correct types.
    """

    def setUp(self):
        """Set up test fixtures."""
        

        from services.processing_status_manager import ProcessingStatusManager
        from services.fake_email_categorizer import FakeEmailCategorizer
        from services.fake_email_deduplication_factory import FakeEmailDeduplicationFactory
        from tests.fake_account_category_client import FakeAccountCategoryClient

        self.mock_processing_status_manager = Mock(spec=ProcessingStatusManager)
        self.mock_settings_service = Mock()
        self.mock_settings_service.get_lookback_hours.return_value = 2
        self.fake_email_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.api_token = str(uuid.uuid4())
        self.llm_model = "vertex/google/gemini-2.5-flash"
        self.account_category_client = FakeAccountCategoryClient()
        self.fake_deduplication_factory = FakeEmailDeduplicationFactory()

        self.test_email = "user@gmail.com"

    def test_complete_successful_response_structure(self):
        """
        Test that a successful response includes all required fields with correct types.
        """
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from models.domain_recommendation_models import NotificationResult
        from tests.fake_gmail_fetcher import FakeGmailFetcher

        real_collector = BlockingRecommendationCollector()

        mock_notifier = Mock()
        mock_notifier.send_recommendations.return_value = NotificationResult(
            success=True,
            recipient=self.test_email,
            recommendations_count=1,
            error_message=None
        )

        fetcher = FakeGmailFetcher()
        fetcher.summary_service = Mock()
        fetcher.summary_service.run_metrics = {'fetched': 0}
        fetcher.summary_service.db_service = None
        fetcher.account_service = self.account_category_client
        fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': Counter()}

        fetcher.add_test_email(
            subject="Marketing email",
            body="spam",
            sender="newsletter@marketing-spam.com"
        )

        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.fake_email_categorizer,
            api_token=self.api_token,
            llm_model=self.llm_model,
            account_category_client=self.account_category_client,
            deduplication_factory=self.fake_deduplication_factory,
            blocking_recommendation_collector=real_collector,
            recommendation_email_notifier=mock_notifier,
            create_gmail_fetcher=lambda email, pwd, token: fetcher
        )

        account = self.account_category_client.get_or_create_account(self.test_email)
        account.app_password = "testpassword1234"

        # Act
        result = service.process_account(self.test_email)

        # Assert - Complete response structure
        expected_fields = {
            'account': str,
            'emails_found': int,
            'emails_processed': int,
            'processing_time_seconds': (int, float),
            'timestamp': str,
            'success': bool,
            'recommended_domains_to_block': list,
            'total_emails_matched': int,
            'unique_domains_count': int,
            'notification_sent': bool,
            'notification_error': (str, type(None)),
        }

        for field, expected_type in expected_fields.items():
            self.assertIn(
                field,
                result,
                f"Response should include '{field}' field"
            )
            self.assertIsInstance(
                result[field],
                expected_type,
                f"'{field}' should be of type {expected_type}, got {type(result[field])}"
            )


if __name__ == '__main__':
    unittest.main()
