import os
import logging
from utils.logger import get_logger
from datetime import datetime
import pytz

from services.summary_sender_interface import SummarySenderInterface


class SummarySenderService(SummarySenderInterface):
    """Handles sending summaries and tracking last sent timestamps."""

    def __init__(self, summary_recipient: str, send_summary_fn) -> None:
        self.summary_recipient = summary_recipient
        self.send_summary_fn = send_summary_fn
        self.logger = get_logger(__name__)

        # Initialize last sent times far in the past (timezone-aware)
        self._last_morning_sent = datetime(2000, 1, 1, tzinfo=pytz.utc)
        self._last_evening_sent = datetime(2000, 1, 1, tzinfo=pytz.utc)
        self._last_weekly_sent = datetime(2000, 1, 1, tzinfo=pytz.utc)

    # Properties
    @property
    def last_morning_sent(self) -> datetime:
        return self._last_morning_sent

    @property
    def last_evening_sent(self) -> datetime:
        return self._last_evening_sent

    @property
    def last_weekly_sent(self) -> datetime:
        return self._last_weekly_sent

    # Core behavior
    def handle_scheduled_summary(self, report_type: str) -> bool:
        if not report_type:
            return False

        self.logger.info(f"Time to send {report_type} summary report")
        try:
            # Set environment variables for the summary script
            os.environ["GMAIL_EMAIL"] = self.summary_recipient
            os.environ["SUMMARY_RECIPIENT_EMAIL"] = self.summary_recipient

            # Send summary using provided function
            self.send_summary_fn()

            # Update last sent time
            now = datetime.now()
            if report_type == "morning":
                self._last_morning_sent = now
            elif report_type == "evening":
                self._last_evening_sent = now
            elif report_type == "weekly":
                self._last_weekly_sent = now

            self.logger.info(f"{report_type.capitalize()} summary sent successfully")
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to send {report_type} summary: {str(e)}", exc_info=True
            )
            self.logger.info("Service will continue running despite the error")
            return False

