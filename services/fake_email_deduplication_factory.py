"""
Fake factory for creating email deduplication clients for testing.
"""
from services.email_deduplication_factory_interface import EmailDeduplicationFactoryInterface
from clients.email_deduplication_client_interface import EmailDeduplicationClientInterface
from services.fake_email_deduplication_client import FakeEmailDeduplicationClient


class FakeEmailDeduplicationFactory(EmailDeduplicationFactoryInterface):
    """Fake factory for creating email deduplication clients for testing."""

    def create_deduplication_client(self, email_address: str) -> EmailDeduplicationClientInterface:
        """
        Create a fake email deduplication client.

        Args:
            email_address: The email address to create a deduplication client for

        Returns:
            FakeEmailDeduplicationClient instance
        """
        return FakeEmailDeduplicationClient(email_address)
