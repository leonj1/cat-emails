import time
import logging
from utils.logger import get_logger
from typing import Any

from services.summary_sender_interface import SummarySenderInterface

from services.scan_cycle_interface import ScanCycleServiceInterface
from services.settings_service import SettingsService
from services.summary_schedule_service import SummaryScheduleService
from services.email_processing_config import EmailProcessingConfiguration
from services.gmail_fetcher_runner import GmailFetcherRunner


class ScanCycleService(ScanCycleServiceInterface):
    """Concrete implementation that runs a scan cycle and sends summaries when scheduled."""

    def __init__(
        self,
        settings_service: SettingsService,
        schedule_service: SummaryScheduleService,
        config: EmailProcessingConfiguration,
        gmail_fetcher: GmailFetcherRunner,
        summary_sender: SummarySenderInterface,
    ) -> None:
        self.settings_service = settings_service
        self.schedule_service = schedule_service
        self.config = config
        self.gmail_fetcher = gmail_fetcher
        self.summary_sender = summary_sender
        self.logger = get_logger(__name__)

    def execute_cycle(self, cycle_count: int, running: bool) -> None:
        self.logger.info(f"Starting scan cycle #{cycle_count}")

        try:
            # Get current lookback hours from settings (allows runtime configuration changes)
            current_hours = self.settings_service.get_lookback_hours()

            # Run the email fetcher
            start_time = time.time()
            self.gmail_fetcher.run(
                self.config.email_address,
                self.config.app_password,
                self.config.api_token,
                current_hours,
            )
            duration = time.time() - start_time

            # Convert duration to human-readable format
            minutes = int(duration // 60)
            seconds = int(duration % 60)

            if minutes > 0:
                self.logger.info(
                    f"Scan cycle #{cycle_count} completed successfully in {minutes} minutes and {seconds} seconds"
                )
            else:
                self.logger.info(
                    f"Scan cycle #{cycle_count} completed successfully in {seconds} seconds"
                )

        except Exception as e:
            self.logger.error(
                f"Error in scan cycle #{cycle_count}: {str(e)}", exc_info=True
            )
            self.logger.info("Service will continue running despite the error")


