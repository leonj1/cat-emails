"""
Factory for creating Gmail deduplication clients.
"""
from services.email_deduplication_factory_interface import EmailDeduplicationFactoryInterface
from clients.email_deduplication_client_interface import EmailDeduplicationClientInterface
from clients.gmail_deduplication_client import GmailDeduplicationClient
from models.database import init_database, get_session
from repositories.sqlalchemy_repository import SQLAlchemyRepository


class EmailDeduplicationFactory(EmailDeduplicationFactoryInterface):
    """Factory for creating Gmail deduplication clients."""

    def create_deduplication_client(self, email_address: str) -> EmailDeduplicationClientInterface:
        """
        Create a Gmail deduplication client for the specified email address.

        Args:
            email_address: The email address to create a deduplication client for

        Returns:
            GmailDeduplicationClient instance
        """
        engine = init_database()
        session = get_session(engine)
        repository = SQLAlchemyRepository(session)
        return GmailDeduplicationClient(repository, email_address, session)
