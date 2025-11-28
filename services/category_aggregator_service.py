"""
Category Aggregator Service.

This service aggregates email category counts in memory before persisting
them to the repository. It implements buffering to reduce database writes
and improve performance.

Thread-safe implementation using threading.Lock for concurrent access
from background processor and main application threads.
"""
from datetime import datetime, date
from typing import Dict, Tuple
import threading

from services.interfaces.category_aggregator_interface import ICategoryAggregator
from repositories.category_tally_repository_interface import ICategoryTallyRepository


class CategoryAggregator(ICategoryAggregator):
    """
    Thread-safe implementation of ICategoryAggregator that buffers category counts in memory.

    The aggregator maintains a buffer keyed by (email_address, date) tuples,
    with each entry containing a dictionary of category counts. When the total
    buffer size reaches the configured limit, it automatically flushes to the
    repository.

    Thread Safety:
        All buffer operations are protected by a threading.Lock to prevent
        race conditions during concurrent access from background processing
        and main application threads.

    Buffer structure:
        {
            ("user@example.com", date(2025, 11, 28)): {
                "Marketing": 5,
                "Personal": 3
            },
            ("other@example.com", date(2025, 11, 28)): {
                "Advertising": 10
            }
        }

    Total buffer size is the sum of ALL category counts across ALL buffer keys.
    """

    def __init__(self, repository: ICategoryTallyRepository, buffer_size: int):
        """
        Initialize the category aggregator.

        Args:
            repository: Repository for persisting category tallies
            buffer_size: Maximum total count across all buffered entries
                        before auto-flush triggers
        """
        self._repository = repository
        self._buffer_size = buffer_size
        self._buffer: Dict[Tuple[str, date], Dict[str, int]] = {}
        self._lock = threading.Lock()  # Thread synchronization for buffer operations

    def record_category(
        self,
        email_address: str,
        category: str,
        timestamp: datetime
    ) -> None:
        """
        Record a single email categorization event.

        Thread-safe: Protected by internal lock.

        Args:
            email_address: Email account address
            category: Category name for the email
            timestamp: When the email was categorized
        """
        with self._lock:
            tally_date = timestamp.date()
            key = (email_address, tally_date)

            # Initialize buffer entry if it doesn't exist
            if key not in self._buffer:
                self._buffer[key] = {}

            # Increment category count
            self._buffer[key][category] = self._buffer[key].get(category, 0) + 1

            # Check if we need to auto-flush
            if self._get_total_buffer_size() >= self._buffer_size:
                self._flush_internal()

    def record_batch(
        self,
        email_address: str,
        category_counts: Dict[str, int],
        timestamp: datetime
    ) -> None:
        """
        Record a batch of category counts at once.

        Thread-safe: Protected by internal lock.

        Args:
            email_address: Email account address
            category_counts: Dictionary of category names to counts
            timestamp: When these emails were categorized
        """
        with self._lock:
            tally_date = timestamp.date()
            key = (email_address, tally_date)

            # Initialize buffer entry if it doesn't exist
            if key not in self._buffer:
                self._buffer[key] = {}

            # Merge category counts
            for category, count in category_counts.items():
                self._buffer[key][category] = self._buffer[key].get(category, 0) + count

            # Check if we need to auto-flush
            if self._get_total_buffer_size() >= self._buffer_size:
                self._flush_internal()

    def flush(self) -> None:
        """
        Flush all buffered category counts to the repository (public method).

        Thread-safe: Acquires lock before flushing.

        For each buffered entry:
        1. Retrieve existing tally from repository to calculate correct total_emails
        2. Pass buffered counts to repository (repository will merge them)
        3. Pass total_emails calculated from what the final merged result will be
        4. Clear the buffer

        Note: The repository's save_daily_tally implements incremental merge semantics
        for category_counts but expects total_emails as the final absolute value.
        """
        with self._lock:
            self._flush_internal()

    def _flush_internal(self) -> None:
        """
        Internal flush implementation (called while lock is held).

        Must only be called when self._lock is already acquired.
        """
        # Empty flush is a no-op
        if not self._buffer:
            return

        # Process each buffered entry
        for (email_address, tally_date), category_counts in self._buffer.items():
            # Get existing tally to calculate what total_emails will be after merge
            existing_tally = self._repository.get_tally(email_address, tally_date)

            if existing_tally:
                # Calculate what the merged counts will be
                merged_counts = existing_tally.category_counts.copy()
                for category, count in category_counts.items():
                    merged_counts[category] = merged_counts.get(category, 0) + count
                # Total emails is the sum of the merged result
                total_emails = sum(merged_counts.values())
            else:
                # No existing tally, total will just be the buffered counts
                total_emails = sum(category_counts.values())

            # Pass buffered counts (repository will merge) and calculated total
            self._repository.save_daily_tally(
                email_address,
                tally_date,
                category_counts,
                total_emails
            )

        # Clear buffer after successful flush
        self._buffer.clear()

    def _get_total_buffer_size(self) -> int:
        """
        Calculate total buffer size as sum of all category counts.

        MUST be called while self._lock is held (internal helper).

        Returns:
            Total count across all buffered entries
        """
        total = 0
        for category_counts in self._buffer.values():
            total += sum(category_counts.values())
        return total

    # Helper methods for testing

    def get_buffer_count_for_account(self, email_address: str) -> int:
        """
        Get the total count of buffered items for a specific account.

        Thread-safe testing helper method.

        Args:
            email_address: Email account address

        Returns:
            Sum of all category counts for this account across all dates
        """
        with self._lock:
            total = 0
            for (buffered_email, _), category_counts in self._buffer.items():
                if buffered_email == email_address:
                    total += sum(category_counts.values())
            return total

    def get_buffer_contents(self) -> Dict[Tuple[str, date], Dict[str, int]]:
        """
        Get the current buffer contents.

        Thread-safe testing helper method.

        Returns:
            Copy of the buffer dictionary
        """
        with self._lock:
            # Return a copy to prevent external modification
            return {
                key: counts.copy()
                for key, counts in self._buffer.items()
            }

    def get_buffer_total_for_account_date(
        self,
        email_address: str,
        tally_date: date
    ) -> int:
        """
        Get the total count for a specific account and date in the buffer.

        Thread-safe testing helper method.

        Args:
            email_address: Email account address
            tally_date: Date to query

        Returns:
            Sum of all category counts for this account/date combination
        """
        with self._lock:
            key = (email_address, tally_date)
            if key not in self._buffer:
                return 0
            return sum(self._buffer[key].values())
