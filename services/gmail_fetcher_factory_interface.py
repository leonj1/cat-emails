"""
Factory interface for creating GmailFetcher instances.
"""
from abc import ABC, abstractmethod
from services.gmail_fetcher_interface import GmailFetcherInterface


class GmailFetcherFactoryInterface(ABC):
    """Interface for creating GmailFetcher instances with runtime parameters."""

    @abstractmethod
    def create_fetcher(
        self,
        email_address: str,
        app_password: str,
        api_token: str
    ) -> GmailFetcherInterface:
        """
        Create a GmailFetcher instance.

        Args:
            email_address: Gmail email address
            app_password: Gmail app-specific password
            api_token: Control API token for domain service

        Returns:
            GmailFetcherInterface implementation
        """
        pass
