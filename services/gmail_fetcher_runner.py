import logging
from typing import Any


class GmailFetcherRunner:
    """Project-specific concrete runner for executing the Gmail fetch cycle.

    This wraps the existing gmail_fetcher.main(...) function in a concrete class
    so service layers can depend on a project-defined type rather than a raw Callable.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def run(self, email_address: str, app_password: str, api_token: str, hours: int) -> Any:
        """Execute one Gmail fetch run.

        Args:
            email_address: Gmail account email
            app_password: Gmail App Password
            api_token: Control API token
            hours: Lookback window in hours
        """
        # Local import to avoid circulars at import time
        from gmail_fetcher import main as gmail_fetcher_main

        self.logger.debug(
            "Running GmailFetcherRunner with email=%s, hours=%s", email_address, hours
        )
        return gmail_fetcher_main(email_address, app_password, api_token, hours)

