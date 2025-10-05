"""
Fake factory implementation for creating FakeGmailFetcher instances in tests.
"""
from typing import Optional, Callable
from services.gmail_fetcher_factory_interface import GmailFetcherFactoryInterface
from services.gmail_fetcher_interface import GmailFetcherInterface
from tests.fake_gmail_fetcher import FakeGmailFetcher


class FakeGmailFetcherFactory(GmailFetcherFactoryInterface):
    """Fake factory for creating FakeGmailFetcher instances in tests."""

    def __init__(self, fetcher_provider: Optional[Callable[[], GmailFetcherInterface]] = None):
        """
        Initialize the fake factory.

        Args:
            fetcher_provider: Optional callable that returns a fetcher instance.
                            If None, creates a new FakeGmailFetcher each time.
        """
        self.fetcher_provider = fetcher_provider
        self.created_fetchers = []  # Track all created fetchers for testing

    def create_fetcher(
        self,
        email_address: str,
        app_password: str,
        api_token: str
    ) -> GmailFetcherInterface:
        """
        Create a FakeGmailFetcher instance.

        Args:
            email_address: Gmail email address (stored but not used)
            app_password: Gmail app-specific password (stored but not used)
            api_token: Control API token (stored but not used)

        Returns:
            FakeGmailFetcher instance (or custom fetcher from provider)
        """
        if self.fetcher_provider:
            fetcher = self.fetcher_provider()
        else:
            fetcher = FakeGmailFetcher()

        self.created_fetchers.append({
            'fetcher': fetcher,
            'email_address': email_address,
            'app_password': app_password,
            'api_token': api_token
        })
        return fetcher
