"""
Factory interface for creating EmailProcessorService instances.
"""
from abc import ABC, abstractmethod
from services.email_processor_service import EmailProcessorService
from services.email_categorizer_interface import EmailCategorizerInterface
from services.gmail_fetcher_interface import GmailFetcherInterface
from services.logs_collector_service import LogsCollectorService


class EmailProcessorFactoryInterface(ABC):
    """Interface for creating EmailProcessorService instances with runtime parameters."""

    @abstractmethod
    def create_processor(
        self,
        fetcher: GmailFetcherInterface,
        email_address: str,
        model: str,
        email_categorizer: EmailCategorizerInterface,
        logs_collector: LogsCollectorService
    ) -> EmailProcessorService:
        """
        Create an EmailProcessorService instance.

        Args:
            fetcher: GmailFetcherInterface implementation
            email_address: Email address being processed
            model: LLM model identifier
            email_categorizer: Email categorizer implementation
            logs_collector: LogsCollectorService instance

        Returns:
            EmailProcessorService instance
        """
        pass
