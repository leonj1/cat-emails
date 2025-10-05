"""
Interface for creating email deduplication clients.
"""
from abc import ABC, abstractmethod
from clients.email_deduplication_client_interface import EmailDeduplicationClientInterface


class EmailDeduplicationFactoryInterface(ABC):
    """Interface for factories that create email deduplication clients."""

    @abstractmethod
    def create_deduplication_client(self, email_address: str) -> EmailDeduplicationClientInterface:
        """
        Create an email deduplication client for the specified email address.

        Args:
            email_address: The email address to create a deduplication client for

        Returns:
            EmailDeduplicationClientInterface implementation
        """
        pass
