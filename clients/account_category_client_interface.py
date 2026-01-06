"""
Interface for managing account and category statistics.
Defines the contract for account and email category tracking operations.
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Dict, Optional

from models.database import EmailAccount
from models.account_models import TopCategoriesResponse


class AccountCategoryClientInterface(ABC):
    """Interface for managing email accounts and category statistics."""

    @abstractmethod
    def get_or_create_account(self, email_address: str, display_name: Optional[str], app_password: Optional[str], auth_method: Optional[str], oauth_refresh_token: Optional[str]) -> EmailAccount:
        """
        Get existing account or create a new one.

        Args:
            email_address: Gmail email address
            display_name: Optional display name for the account
            app_password: Optional Gmail app-specific password for IMAP access
            auth_method: Optional authentication method ('oauth', 'imap', or None)
            oauth_refresh_token: OAuth refresh token (required if auth_method is 'oauth')

        Returns:
            EmailAccount object (existing or newly created)

        Raises:
            ValueError: If email address is invalid
        """
        pass

    @abstractmethod
    def get_account_by_email(self, email_address: str) -> Optional[EmailAccount]:
        """
        Retrieve an account by email address.

        Args:
            email_address: Gmail email address to look up

        Returns:
            EmailAccount if found, None otherwise

        Raises:
            ValueError: If email address is invalid or empty
        """
        pass

    @abstractmethod
    def update_account_last_scan(self, email_address: str) -> None:
        """
        Update the last_scan_at timestamp for an account.

        Args:
            email_address: Gmail email address

        Raises:
            ValueError: If email address is invalid
        """
        pass

    @abstractmethod
    def record_category_stats(self, email_address: str, stats_date: date,
                            category_stats: Dict[str, Dict[str, int]]) -> None:
        """
        Record daily category statistics for an account.

        Args:
            email_address: Gmail email address
            stats_date: Date for the statistics
            category_stats: Dictionary with format:
                {"Marketing": {"total": 10, "deleted": 8, "kept": 2, "archived": 0}}

        Raises:
            ValueError: If email address is invalid or data format is wrong
        """
        pass

    @abstractmethod
    def get_top_categories(self, email_address: str, days: int,
                          limit: int = 10, include_counts: bool = False) -> TopCategoriesResponse:
        """
        Get top categories for an account over specified days.

        Args:
            email_address: Gmail email address
            days: Number of days to look back from today (1-365)
            limit: Maximum number of categories to return (1-50)
            include_counts: Whether to include detailed breakdown counts

        Returns:
            TopCategoriesResponse with category statistics

        Raises:
            ValueError: If parameters are invalid or account not found
        """
        pass

    @abstractmethod
    def get_all_accounts(self, active_only: bool) -> List[EmailAccount]:
        """
        Get all accounts, optionally filtered by active status.

        Args:
            active_only: If True, only return active accounts

        Returns:
            List of EmailAccount objects
        """
        pass

    @abstractmethod
    def deactivate_account(self, email_address: str) -> bool:
        """
        Deactivate an account (soft delete).

        Args:
            email_address: Gmail email address

        Returns:
            True if account was deactivated, False if not found

        Raises:
            ValueError: If email address is invalid
        """
        pass
