#!/usr/bin/env python3
"""
Gmail Fetcher Service - Continuous email processing service
Runs gmail_fetcher.main() function at regular intervals
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime, time as datetime_time
import pytz

from send_emails import main as send_summary_main
from services.settings_service import SettingsService
from services.summary_schedule_service import SummaryScheduleService
from services.email_processing_config import EmailProcessingConfiguration
from services.scan_cycle_service import ScanCycleService
from services.summary_sender_service import SummarySenderService
from services.gmail_fetcher_runner import GmailFetcherRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# Global flag for graceful shutdown
running = True

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    running = False


def run_service():
    """Main service loop"""
    # Initialize settings service and configuration
    settings_service = SettingsService()
    config = EmailProcessingConfiguration(settings_service)
    schedule_service = SummaryScheduleService()
    summary_sender = SummarySenderService(
        summary_recipient=config.summary_recipient,
        send_summary_fn=send_summary_main,
    )

    scan_cycle_service = ScanCycleService(
        settings_service,
        schedule_service,
        config,
        GmailFetcherRunner(),
        summary_sender,
    )

    # Validate configuration
    config.validate_or_exit()

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Gmail Fetcher Service starting...")
    logger.info(f"Configuration:")
    logger.info(f"  - Email: {config.email_address}")
    logger.info(f"  - Hours to scan: {config.hours} (dynamically updated from settings)")
    logger.info(f"  - Scan interval: {config.scan_interval} minutes")
    logger.info(f"  - Summaries enabled: {config.enable_summaries}")
    if config.enable_summaries:
        logger.info(f"  - Summary recipient: {config.summary_recipient}")
        logger.info(f"  - Morning summary: {config.morning_hour:02d}:{config.morning_minute:02d} ET")
        logger.info(f"  - Evening summary: {config.evening_hour:02d}:{config.evening_minute:02d} ET")


    # Main service loop
    cycle_count = 0
    while running:
        cycle_count += 1
        scan_cycle_service.execute_cycle(cycle_count, running)

        # Check if we should send a summary (moved from ScanCycleService)
        if running and config.enable_summaries:
            report_type = schedule_service.should_send_summary(
                summary_sender.last_morning_sent,
                summary_sender.last_evening_sent,
                summary_sender.last_weekly_sent,
                config.morning_hour,
                config.morning_minute,
                config.evening_hour,
                config.evening_minute,
            )
            if report_type:
                summary_sender.handle_scheduled_summary(report_type)

        if running:
            # Calculate next run time
            next_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Next scan will run in {config.scan_interval} minutes at approximately {next_run}")

            # Sleep in small intervals to allow for quick shutdown
            sleep_seconds = config.scan_interval * 60
            sleep_interval = 5  # Check for shutdown every 5 seconds

            for _ in range(0, sleep_seconds, sleep_interval):
                if not running:
                    break
                time.sleep(min(sleep_interval, sleep_seconds))

    logger.info("Gmail Fetcher Service shutting down gracefully")

if __name__ == "__main__":
    run_service()