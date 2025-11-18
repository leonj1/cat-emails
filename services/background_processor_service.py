import logging
from utils.logger import get_logger
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional
from services.background_processor_interface import BackgroundProcessorInterface
from clients.account_category_client import AccountCategoryClient

logger = get_logger(__name__)


class BackgroundProcessorService(BackgroundProcessorInterface):
    """Service for continuously processing Gmail accounts in the background."""

    def __init__(
        self,
        process_account_callback: Callable[[str], Dict],
        settings_service,
        scan_interval: int,
        background_enabled: bool
    ):
        """
        Initialize the background processor service.

        Args:
            process_account_callback: Function to process a single account's emails
            settings_service: Service for getting settings like lookback hours
            scan_interval: Seconds to wait between processing cycles
            background_enabled: Whether background processing is enabled
        """
        self.process_account_callback = process_account_callback
        self.settings_service = settings_service
        self.scan_interval = scan_interval
        self.background_enabled = background_enabled
        self.running = True
        self.next_execution_time: Optional[datetime] = None

        # Reuse repository from settings_service to maintain consistency
        # This uses the same database connection (MySQL if configured, else SQLite)
        self.repository = settings_service.repository
        try:
            if not self.repository.is_connected():
                self.repository.connect()
        except Exception as e:
            logger.error(f"Failed to connect to repository during BackgroundProcessorService initialization: {e}")
            raise RuntimeError(f"Repository connection failed: {e}") from e

    def should_continue(self) -> bool:
        """
        Check if the processor should continue running.

        Returns:
            bool: True if processor should continue, False to stop
        """
        return self.running

    def stop(self) -> None:
        """
        Signal the processor to stop running.
        """
        self.running = False

    def get_next_execution_time(self) -> Optional[datetime]:
        """
        Get the next scheduled execution time.

        Returns:
            Optional[datetime]: Next execution time or None if not scheduled
        """
        return self.next_execution_time

    def run(self) -> None:
        """
        Run the background processor loop.

        This method runs continuously until stopped,
        processing Gmail accounts at configured intervals.
        """
        logger.info("🚀 Background Gmail processor thread started")
        logger.info("⚙️  Configuration:")
        logger.info(f"   - Scan interval: {self.scan_interval} seconds")
        logger.info(f"   - Process emails from last: {self.settings_service.get_lookback_hours()} hours")
        logger.info(f"   - Background processing enabled: {self.background_enabled}")

        cycle_count = 0

        while self.running:
            try:
                cycle_count += 1
                logger.info(f"🔄 Starting background processing cycle #{cycle_count}")

                # Get list of active Gmail accounts from database
                try:
                    # Use the shared repository instance
                    service = AccountCategoryClient(repository=self.repository)
                    accounts = service.get_all_accounts()

                    if not accounts:
                        logger.info("📭 No Gmail accounts found in database to process")
                        logger.info("💡 Tip: Add accounts via POST /api/accounts endpoint")
                    else:
                        logger.info(f"👥 Found {len(accounts)} Gmail accounts to process")

                        # Process each account
                        total_processed = 0
                        total_errors = 0

                        for account in accounts:
                            if not self.running:
                                logger.info("🛑 Background processing stopped during account processing")
                                break

                            logger.info(f"🏃 Processing account: {account.email_address}")
                            result = self.process_account_callback(account.email_address)

                            if result["success"]:
                                total_processed += result.get("emails_processed", 0)
                            else:
                                total_errors += 1

                            # Small delay between accounts to prevent overwhelming Gmail API
                            time.sleep(5)

                        logger.info(f"📈 Cycle #{cycle_count} completed:")
                        logger.info(f"   - Accounts processed: {len(accounts)}")
                        logger.info(f"   - Total emails processed: {total_processed}")
                        logger.info(f"   - Errors: {total_errors}")

                except Exception as e:
                    logger.error(f"❌ Error in background processing cycle: {str(e)}")

                if self.running:
                    self.next_execution_time = datetime.now() + timedelta(seconds=self.scan_interval)
                    logger.info(f"💤 Sleeping {self.scan_interval} seconds. Next cycle at {self.next_execution_time.strftime('%H:%M:%S')}")

                    # Sleep in smaller intervals to allow for graceful shutdown
                    sleep_interval = 10  # Check for shutdown every 10 seconds
                    remaining_sleep = self.scan_interval

                    while remaining_sleep > 0 and self.running:
                        sleep_time = min(sleep_interval, remaining_sleep)
                        time.sleep(sleep_time)
                        remaining_sleep -= sleep_time

            except Exception as e:
                logger.error(f"💥 Fatal error in background processor: {str(e)}")
                logger.info("⏸️  Background processor will retry in 30 seconds...")
                time.sleep(30)

        logger.info("🏁 Background Gmail processor thread stopped")
