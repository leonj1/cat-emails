"""
Category Tally Repository Interface.

This interface defines the contract for persisting and retrieving email category tallies.
It follows the Repository Pattern to decouple business logic from data access.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date

from models.category_tally_models import (
    DailyCategoryTally,
    AggregatedCategoryTally
)


class ICategoryTallyRepository(ABC):
    """
    Abstract interface for category tally repository operations.

    This interface defines methods for:
    - Saving daily tallies (with upsert semantics)
    - Retrieving tallies by date or date range
    - Aggregating tallies across date ranges
    - Deleting old tallies
    """

    @abstractmethod
    def save_daily_tally(
        self,
        email_address: str,
        tally_date: date,
        category_counts: dict,
        total_emails: int
    ) -> DailyCategoryTally:
        """
        Save or update a daily category tally for an account.

        This method implements upsert semantics: if a tally exists for the
        given email_address and tally_date, it will be updated; otherwise,
        a new tally will be created.

        Args:
            email_address: Email account address
            tally_date: Date for this tally
            category_counts: Dictionary of category names to counts
            total_emails: Total emails across all categories

        Returns:
            The saved DailyCategoryTally with id populated

        Raises:
            ValueError: If parameters are invalid
        """
        pass

    @abstractmethod
    def get_tally(
        self,
        email_address: str,
        tally_date: date
    ) -> Optional[DailyCategoryTally]:
        """
        Retrieve a single daily tally for a specific account and date.

        Args:
            email_address: Email account address
            tally_date: Date to retrieve tally for

        Returns:
            DailyCategoryTally if found, None otherwise
        """
        pass

    @abstractmethod
    def get_tallies_for_period(
        self,
        email_address: str,
        start_date: date,
        end_date: date
    ) -> List[DailyCategoryTally]:
        """
        Retrieve all daily tallies for an account within a date range.

        Args:
            email_address: Email account address
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of DailyCategoryTally objects (empty list if none found)
        """
        pass

    @abstractmethod
    def get_aggregated_tallies(
        self,
        email_address: str,
        start_date: date,
        end_date: date
    ) -> AggregatedCategoryTally:
        """
        Get aggregated statistics across a date range for an account.

        This method calculates:
        - Total emails across all days and categories
        - Number of days with data
        - Per-category totals, percentages, and daily averages

        Args:
            email_address: Email account address
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            AggregatedCategoryTally with calculated statistics
        """
        pass

    @abstractmethod
    def delete_tallies_before(
        self,
        email_address: str,
        cutoff_date: date
    ) -> int:
        """
        Delete all tallies for an account before a cutoff date.

        This is useful for data retention/cleanup policies.

        Args:
            email_address: Email account address
            cutoff_date: Delete tallies before this date (exclusive)

        Returns:
            Number of tallies deleted
        """
        pass
