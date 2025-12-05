import os
import sys
from services.settings_service import SettingsService
from services.email_processing_interface import EmailProcessingConfigurationInterface

class EmailProcessingConfiguration(EmailProcessingConfigurationInterface):
    """Encapsulates configuration for the email processing service.
    Loads values from SettingsService and environment variables.
    """
    def __init__(self, settings_service: SettingsService, env=os.environ):
        # Core credentials
        self._email_address = env.get("GMAIL_EMAIL")
        self._app_password = env.get("GMAIL_PASSWORD")
        self._api_token = env.get("CONTROL_TOKEN")

        # Lookback hours: prefer dynamic settings, fall back to env HOURS if default
        hours = settings_service.get_lookback_hours()
        if hours == 2:  # If it's still default, allow env override
            hours = int(env.get("HOURS", "2"))
        self._hours = hours

        # General service configuration
        self._scan_interval = int(env.get("SCAN_INTERVAL", "2"))  # minutes
        self._enable_summaries = env.get("ENABLE_SUMMARIES", "true").lower() == "true"
        self._summary_recipient = env.get("SUMMARY_RECIPIENT_EMAIL", self._email_address)

        # Summary schedule configuration
        self._morning_hour = int(env.get("MORNING_HOUR", "5"))
        self._morning_minute = int(env.get("MORNING_MINUTE", "30"))
        self._evening_hour = int(env.get("EVENING_HOUR", "16"))
        self._evening_minute = int(env.get("EVENING_MINUTE", "30"))

    # Properties implementing the interface
    @property
    def email_address(self) -> str:
        return self._email_address

    @property
    def app_password(self) -> str:
        return self._app_password

    @property
    def api_token(self) -> str:
        return self._api_token

    @property
    def hours(self) -> int:
        return self._hours

    @property
    def scan_interval(self) -> int:
        return self._scan_interval

    @property
    def enable_summaries(self) -> bool:
        return self._enable_summaries

    @property
    def summary_recipient(self) -> str:
        return self._summary_recipient

    @property
    def morning_hour(self) -> int:
        return self._morning_hour

    @property
    def morning_minute(self) -> int:
        return self._morning_minute

    @property
    def evening_hour(self) -> int:
        return self._evening_hour

    @property
    def evening_minute(self) -> int:
        return self._evening_minute

    def validate_or_exit(self) -> None:
        """Validate required config and exit on failure (matches previous behavior)."""
        if not self._email_address or not self._app_password:
            raise SystemExit("GMAIL_EMAIL and GMAIL_PASSWORD environment variables are required")
        if not self._api_token:
            raise SystemExit("CONTROL_TOKEN environment variable is required")

