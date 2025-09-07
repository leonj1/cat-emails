import logging
import os
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
        # Also import function to discover default model used for categorization
        try:
            from gmail_fetcher import categorize_email_with_resilient_client as _cat_fn  # type: ignore
            _defaults = getattr(_cat_fn, "__defaults__", None) or ()
            default_model = _defaults[0] if len(_defaults) >= 1 else "unknown"
        except Exception:
            default_model = "unknown"

        # Derive provider and base URL consistent with gmail_fetcher._make_llm_categorizer
        provider = "requestyai"
        base_url = os.environ.get("REQUESTYAI_BASE_URL", "https://api.requesty.ai/openai/v1")

        self.logger.info(
            "LLM configuration: provider=%s, model=%s, base_url=%s",
            provider,
            default_model,
            base_url or "(default SDK)",
        )

        self.logger.debug(
            "Running GmailFetcherRunner with email=%s, hours=%s", email_address, hours
        )
        return gmail_fetcher_main(email_address, app_password, api_token, hours)
