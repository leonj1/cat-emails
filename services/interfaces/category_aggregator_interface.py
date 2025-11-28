"""
Category Aggregator Interface.

This interface defines the contract for aggregating email category counts
before persisting them to the repository. It implements buffering to reduce
database writes and improve performance.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict


class ICategoryAggregator(ABC):
    """
    Abstract interface for category aggregator operations.

    This interface defines methods for:
    - Recording individual category events
    - Recording batches of category counts
    - Flushing buffered data to the repository
    """

    @abstractmethod
    def record_category(
        self,
        email_address: str,
        category: str,
        timestamp: datetime
    ) -> None:
        """
        Record a single email categorization event.

        Args:
            email_address: Email account address
            category: Category name for the email
            timestamp: When the email was categorized

        Note:
            This method buffers the categorization. Call flush() to persist.
        """
        pass

    @abstractmethod
    def record_batch(
        self,
        email_address: str,
        category_counts: Dict[str, int],
        timestamp: datetime
    ) -> None:
        """
        Record a batch of category counts at once.

        Args:
            email_address: Email account address
            category_counts: Dictionary of category names to counts
            timestamp: When these emails were categorized

        Note:
            This method buffers the counts. Call flush() to persist.
        """
        pass

    @abstractmethod
    def flush(self) -> None:
        """
        Flush all buffered category counts to the repository.

        This method retrieves existing tallies from the repository,
        merges the buffered counts with existing counts, and saves
        the merged results back to the repository.

        After flushing, the buffer is cleared.
        """
        pass
