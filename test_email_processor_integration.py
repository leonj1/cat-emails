#!/usr/bin/env python3
"""
Integration test script for AccountEmailProcessorService.

This script directly invokes the email processor for a specific Gmail account,
bypassing the API layer. It connects to MySQL, creates the account if needed,
and processes emails from the last N hours.

Usage:
    python test_email_processor_integration.py
"""
import os
import sys

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
os.environ.setdefault("CONTROL_API_TOKEN", "fXhS_j2zzsWOtEBnVz6w7egG65mNjxST-2ae62j3ZJI")

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


def main():
    """Run the email processor integration test."""
    # Test configuration
    EMAIL_ADDRESS = "leonj1@gmail.com"
    APP_PASSWORD = "ians rrxl nfpq yzsw"
    # Use 1 hour as requested; increase if you want to find more emails
    LOOKBACK_HOURS = 1

    logger.info("=" * 60)
    logger.info("Email Processor Integration Test")
    logger.info("=" * 60)
    logger.info(f"Email: {EMAIL_ADDRESS}")
    logger.info(f"Lookback hours: {LOOKBACK_HOURS}")
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

        # 5. Deduplication factory (using MySQL repository)
        logger.info("  - Initializing MySQLDeduplicationFactory...")
        deduplication_factory = MySQLDeduplicationFactory(settings_service.repository)

        # 6. Get API token and LLM model
        api_token = os.getenv("CONTROL_API_TOKEN", "")
        llm_model = os.getenv("LLM_MODEL", "vertex/google/gemini-2.5-flash")

        logger.info(f"  - API Token configured: {bool(api_token)}")
        logger.info(f"  - LLM Model: {llm_model}")

        # 7. Create the account email processor service
        logger.info("  - Initializing AccountEmailProcessorService...")
        processor_service = AccountEmailProcessorService(
            processing_status_manager=processing_status_manager,
            settings_service=settings_service,
            email_categorizer=email_categorizer,
            api_token=api_token,
            llm_model=llm_model,
            account_category_client=account_category_client,
            deduplication_factory=deduplication_factory
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
