"""
Factory implementation for creating EmailProcessorService instances.
"""
from services.email_processor_factory_interface import EmailProcessorFactoryInterface
from services.email_processor_service import EmailProcessorService
from services.email_categorizer_interface import EmailCategorizerInterface
from services.gmail_fetcher_interface import GmailFetcherInterface
from services.logs_collector_service import LogsCollectorService


class EmailProcessorFactory(EmailProcessorFactoryInterface):
    """Factory for creating EmailProcessorService instances."""

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
        return EmailProcessorService(
            fetcher=fetcher,
            email_address=email_address,
            model=model,
            email_categorizer=email_categorizer,
            logs_collector=logs_collector
        )
