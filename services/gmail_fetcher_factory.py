"""
Factory implementation for creating GmailFetcher instances.
"""
from services.gmail_fetcher_factory_interface import GmailFetcherFactoryInterface
from services.gmail_fetcher_interface import GmailFetcherInterface
from services.gmail_fetcher_service import GmailFetcher


class GmailFetcherFactory(GmailFetcherFactoryInterface):
    """Factory for creating GmailFetcher instances."""

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
            GmailFetcher instance
        """
        return GmailFetcher(email_address, app_password, api_token)
