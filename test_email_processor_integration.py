#!/usr/bin/env python3
"""
Integration test script for AccountEmailProcessorService.

This script directly invokes the email processor for a specific Gmail account,
bypassing the API layer. It connects to MySQL, creates the account if needed,
and processes emails from the last N hours.

Usage:
    python test_email_processor_integration.py [--reprocess]

Options:
    --reprocess    Reprocess all emails, ignoring deduplication (skip previously seen emails check)
"""
import os
import sys
import argparse

# Set required environment variables BEFORE any imports
# MySQL connection settings (matching docker-compose.yml)
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("MYSQL_PORT", "3307")
os.environ.setdefault("MYSQL_DATABASE", "cat_emails")
os.environ.setdefault("MYSQL_USER", "cat_emails")
os.environ.setdefault("MYSQL_PASSWORD", "cat_emails_password")

# Required API keys (use existing .env values or defaults)
os.environ.setdefault("REQUESTYAI_API_KEY", "sk-XfUA7zpWQQKOa0pbc27aRYy/INsznmXksPmJidPYsJx2nXbYTHciNP1FTxp1gTQRk+BMOWS0g82S3VoTzzJinMdZg0I7Xsf9hPwJDaiNowI=")
os.environ.setdefault("REQUESTYAI_BASE_URL", "https://router.requesty.ai/v1")
os.environ.setdefault("CONTROL_TOKEN", "fXhS_j2zzsWOtEBnVz6w7egG65mNjxST-2ae62j3ZJI")

# Mailtrap configuration (from environment - use MAILTRAP_KEY)
os.environ.setdefault("MAILTRAP_KEY", "ed56366eab8188e73d6901428308bcde")

# Disable remote logging to avoid network calls during testing
os.environ.setdefault("DISABLE_REMOTE_LOGGING", "true")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MySQLDeduplicationFactory:
    """
    Custom deduplication factory that uses MySQL repository instead of SQLite.
    """
    def __init__(self, mysql_repository):
        self.mysql_repository = mysql_repository

    def create_deduplication_client(self, email_address: str):
        """Create a deduplication client using the MySQL repository."""
        from clients.gmail_deduplication_client import GmailDeduplicationClient
        # GmailDeduplicationClient needs a repository and a session
        # Get a new session from the repository's SessionFactory
        session = self.mysql_repository.SessionFactory()
        return GmailDeduplicationClient(
            repository=self.mysql_repository,
            account_email=email_address,
            session=session
        )


class NoOpDeduplicationClient:
    """
    A no-op deduplication client that always reports emails as not processed.
    Used when --reprocess flag is set to force reprocessing of all emails.
    """
    def __init__(self, account_email: str):
        self.account_email = account_email
        self.stats = {
            'checked': 0,
            'duplicates_found': 0,
            'new_emails': 0,
            'logged': 0,
            'errors': 0
        }
        logger.info(f"NoOpDeduplicationClient initialized for {account_email} (reprocess mode)")

    def is_email_processed(self, message_id: str) -> bool:
        """Always return False to force reprocessing."""
        self.stats['checked'] += 1
        self.stats['new_emails'] += 1
        return False

    def mark_email_as_processed(self, message_id: str):
        """No-op: don't actually mark as processed."""
        self.stats['logged'] += 1
        logger.debug(f"NoOp: Would mark {message_id} as processed (skipped)")

    def filter_new_emails(self, emails):
        """Return all emails as new."""
        self.stats['checked'] += len(emails)
        self.stats['new_emails'] += len(emails)
        logger.info(f"📊 NoOp Deduplication for {self.account_email}: All {len(emails)} emails treated as new")
        return emails

    def bulk_mark_as_processed(self, message_ids):
        """No-op: don't actually mark as processed."""
        self.stats['logged'] += len(message_ids)
        logger.info(f"NoOp: Would mark {len(message_ids)} emails as processed (skipped)")
        return len(message_ids), 0

    def get_stats(self):
        """Return statistics."""
        return self.stats.copy()


class NoOpDeduplicationFactory:
    """
    Factory that creates NoOpDeduplicationClient instances.
    Used when --reprocess flag is set.
    """
    def create_deduplication_client(self, email_address: str):
        """Create a no-op deduplication client."""
        return NoOpDeduplicationClient(email_address)


def main():
    """Run the email processor integration test."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Email Processor Integration Test')
    parser.add_argument('--reprocess', action='store_true',
                        help='Reprocess all emails, ignoring deduplication')
    args = parser.parse_args()

    # Test configuration
    EMAIL_ADDRESS = "leonj1@gmail.com"
    APP_PASSWORD = "ians rrxl nfpq yzsw"
    # Use 1 hour as requested; increase if you want to find more emails
    LOOKBACK_HOURS = 1
    REPROCESS_MODE = args.reprocess

    logger.info("=" * 60)
    logger.info("Email Processor Integration Test")
    logger.info("=" * 60)
    logger.info(f"Email: {EMAIL_ADDRESS}")
    logger.info(f"Lookback hours: {LOOKBACK_HOURS}")
    logger.info(f"Reprocess mode: {REPROCESS_MODE}")
    logger.info(f"MySQL Host: {os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}")
    logger.info("=" * 60)

    try:
        # Import services after environment is set up
        logger.info("Importing services...")
        from services.settings_service import SettingsService
        from services.processing_status_manager import ProcessingStatusManager
        from services.email_categorizer_service import EmailCategorizerService
        from services.llm_service_factory import LLMServiceFactory
        # EmailDeduplicationFactory not used - using MySQLDeduplicationFactory instead
        from services.account_email_processor_service import AccountEmailProcessorService
        from clients.account_category_client import AccountCategoryClient

        # Domain recommendation services
        from services.blocking_recommendation_collector import BlockingRecommendationCollector
        from services.recommendation_email_formatter import RecommendationEmailFormatter
        from services.recommendation_email_notifier import RecommendationEmailNotifier
        from email_providers.mailtrap import MailtrapProvider, MailtrapConfig

        # Initialize dependencies
        logger.info("Initializing dependencies...")

        # 1. Settings service (connects to MySQL and creates tables)
        logger.info("  - Initializing SettingsService (MySQL connection)...")
        settings_service = SettingsService()
        logger.info(f"    MySQL connected: {settings_service.repository.is_connected()}")

        # 2. Processing status manager
        logger.info("  - Initializing ProcessingStatusManager...")
        processing_status_manager = ProcessingStatusManager()

        # 3. LLM service factory and email categorizer
        logger.info("  - Initializing LLMServiceFactory and EmailCategorizerService...")
        llm_factory = LLMServiceFactory()
        email_categorizer = EmailCategorizerService(llm_factory)

        # 4. Account category client (uses the same repository)
        logger.info("  - Initializing AccountCategoryClient...")
        account_category_client = AccountCategoryClient(repository=settings_service.repository)

        # 5. Deduplication factory (using MySQL repository or NoOp for reprocessing)
        if REPROCESS_MODE:
            logger.info("  - Initializing NoOpDeduplicationFactory (reprocess mode)...")
            deduplication_factory = NoOpDeduplicationFactory()
        else:
            logger.info("  - Initializing MySQLDeduplicationFactory...")
            deduplication_factory = MySQLDeduplicationFactory(settings_service.repository)

        # 6. Get API token and LLM model
        api_token = os.getenv("CONTROL_TOKEN", "")
        llm_model = os.getenv("LLM_MODEL", "vertex/google/gemini-2.5-flash")

        logger.info(f"  - API Token configured: {bool(api_token)}")
        logger.info(f"  - LLM Model: {llm_model}")

        # 7. Initialize Mailtrap email provider for recommendations
        logger.info("  - Initializing MailtrapProvider...")
        mailtrap_token = os.getenv("MAILTRAP_KEY")
        mailtrap_config = MailtrapConfig(api_token=mailtrap_token, sandbox=False)
        mailtrap_provider = MailtrapProvider(mailtrap_config)
        logger.info(f"    Mailtrap configured: {bool(mailtrap_token)}")

        # 8. Initialize blocking recommendation services
        logger.info("  - Initializing BlockingRecommendationCollector...")
        recommendation_collector = BlockingRecommendationCollector()

        logger.info("  - Initializing RecommendationEmailFormatter and Notifier...")
        recommendation_formatter = RecommendationEmailFormatter()
        recommendation_notifier = RecommendationEmailNotifier(
            email_provider=mailtrap_provider,
            formatter=recommendation_formatter
        )

        # 9. Create the account email processor service
        logger.info("  - Initializing AccountEmailProcessorService...")
        processor_service = AccountEmailProcessorService(
            processing_status_manager=processing_status_manager,
            settings_service=settings_service,
            email_categorizer=email_categorizer,
            api_token=api_token,
            llm_model=llm_model,
            account_category_client=account_category_client,
            deduplication_factory=deduplication_factory,
            blocking_recommendation_collector=recommendation_collector,
            recommendation_email_notifier=recommendation_notifier
        )

        logger.info("All dependencies initialized successfully!")
        logger.info("-" * 60)

        # Ensure the account exists in the database with the app password
        logger.info(f"Ensuring account exists: {EMAIL_ADDRESS}")
        account = account_category_client.get_or_create_account(
            email_address=EMAIL_ADDRESS,
            display_name="Test User",
            app_password=APP_PASSWORD
        )
        logger.info(f"Account ready: {account.email_address} (ID: {account.id})")

        # Override lookback hours for this test
        logger.info(f"Setting lookback hours to {LOOKBACK_HOURS}...")
        settings_service.set_lookback_hours(LOOKBACK_HOURS)

        # Process the account
        logger.info("-" * 60)
        logger.info(f"Starting email processing for {EMAIL_ADDRESS}...")
        logger.info("-" * 60)

        start_time = datetime.now()
        result = processor_service.process_account(EMAIL_ADDRESS)
        end_time = datetime.now()

        # Display results
        logger.info("=" * 60)
        logger.info("PROCESSING RESULTS")
        logger.info("=" * 60)

        if result.get("success"):
            logger.info(f"✅ SUCCESS")
            logger.info(f"   Account: {result.get('account')}")
            logger.info(f"   Emails found: {result.get('emails_found', 0)}")
            logger.info(f"   Emails processed: {result.get('emails_processed', 0)}")
            logger.info(f"   Emails categorized: {result.get('emails_categorized', 0)}")
            logger.info(f"   Emails labeled: {result.get('emails_labeled', 0)}")
            logger.info(f"   Processing time: {result.get('processing_time_seconds', 0):.2f}s")

            category_counts = result.get('category_counts', {})
            if category_counts:
                logger.info("   Category breakdown:")
                for category, stats in category_counts.items():
                    if isinstance(stats, dict):
                        logger.info(f"     - {category}: {stats.get('total', 0)} total, "
                                  f"{stats.get('deleted', 0)} deleted, {stats.get('kept', 0)} kept")
                    else:
                        logger.info(f"     - {category}: {stats}")

            # Display domain blocking recommendations
            recommendations = result.get('recommendations', [])
            if recommendations:
                logger.info("-" * 60)
                logger.info("DOMAIN BLOCKING RECOMMENDATIONS")
                logger.info("-" * 60)
                logger.info(f"   Total domains recommended: {len(recommendations)}")
                logger.info(f"   Total emails matched: {result.get('recommendations_total_matched', 0)}")
                for rec in recommendations[:10]:  # Show top 10
                    logger.info(f"     - {rec.get('domain', rec.domain if hasattr(rec, 'domain') else 'unknown')}: "
                              f"{rec.get('count', rec.count if hasattr(rec, 'count') else 0)} emails "
                              f"({rec.get('category', rec.category if hasattr(rec, 'category') else 'unknown')})")

            # Display notification result
            notification_result = result.get('notification_result')
            if notification_result:
                logger.info("-" * 60)
                logger.info("RECOMMENDATION EMAIL NOTIFICATION")
                logger.info("-" * 60)
                if hasattr(notification_result, 'success'):
                    if notification_result.success:
                        logger.info(f"   ✅ Email sent successfully to {notification_result.recipient}")
                        logger.info(f"   Recommendations included: {notification_result.recommendations_count}")
                    else:
                        logger.error(f"   ❌ Email failed: {notification_result.error_message}")
                else:
                    logger.info(f"   Result: {notification_result}")
        else:
            logger.error(f"❌ FAILED")
            logger.error(f"   Account: {result.get('account')}")
            logger.error(f"   Error: {result.get('error')}")

        logger.info(f"   Total execution time: {(end_time - start_time).total_seconds():.2f}s")
        logger.info("=" * 60)

        return 0 if result.get("success") else 1

    except Exception as e:
        logger.exception(f"Integration test failed with exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
