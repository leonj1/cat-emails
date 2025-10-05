"""
Factory interface for creating EmailProcessorService instances.
"""
from abc import ABC, abstractmethod
from typing import Callable
from services.email_processor_service import EmailProcessorService
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
        categorize_fn: Callable[[str, str], str],
        logs_collector: LogsCollectorService
    ) -> EmailProcessorService:
        """
        Create an EmailProcessorService instance.

        Args:
            fetcher: GmailFetcherInterface implementation
            email_address: Email address being processed
            model: LLM model identifier
            categorize_fn: Function to categorize email content
            logs_collector: LogsCollectorService instance

        Returns:
            EmailProcessorService instance
        """
        pass
