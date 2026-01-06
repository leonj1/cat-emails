"""
Fake implementation of AccountCategoryClientInterface for testing.

This fake client is designed for use in unit tests and provides an in-memory
implementation that doesn't require a database. It implements all methods from
AccountCategoryClientInterface and can be used as a drop-in replacement in tests.

Usage:
    from tests.fake_account_category_client import FakeAccountCategoryClient

    client = FakeAccountCategoryClient()
    account = client.get_or_create_account("test@example.com")
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from clients.account_category_client_interface import AccountCategoryClientInterface
from models.account_models import TopCategoriesResponse, CategoryStats, DatePeriod


@dataclass
class FakeEmailAccount:
    """Simple data class to represent an email account for testing."""
    id: int
    email_address: str
    display_name: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_scan_at: Optional[datetime] = None
    app_password: Optional[str] = None
    auth_method: Optional[str] = None


class FakeAccountCategoryClient(AccountCategoryClientInterface):
    """
    Fake implementation of account category client for testing.

    This implementation stores data in memory and doesn't persist to any database.
    """

    def __init__(self):
        """Initialize the fake account category client."""
        self.accounts: Dict[str, FakeEmailAccount] = {}
        self.category_stats: Dict[str, List[Dict]] = {}  # email -> list of stats
        self._next_id = 1

    def get_or_create_account(self, email_address: str, display_name: Optional[str], app_password: Optional[str], auth_method: Optional[str], oauth_refresh_token: Optional[str]) -> FakeEmailAccount:
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
        if not email_address or not email_address.strip():
            raise ValueError("Email address cannot be empty")

        email_address = email_address.strip().lower()

        if email_address in self.accounts:
            # Return existing account without modifying it
            return self.accounts[email_address]

        # Create new account
        account = FakeEmailAccount(
            id=self._next_id,
            email_address=email_address,
            display_name=display_name or email_address,
            app_password=app_password,
            auth_method=auth_method,
            is_active=True,
            created_at=datetime.utcnow(),
            last_scan_at=None
        )
        self._next_id += 1
        self.accounts[email_address] = account
        return account

    def get_account_by_email(self, email_address: str) -> Optional[FakeEmailAccount]:
        """
        Retrieve an account by email address.

        Args:
            email_address: Gmail email address to look up

        Returns:
            EmailAccount if found, None otherwise

        Raises:
            ValueError: If email address is invalid or empty
        """
        if not email_address or not email_address.strip():
            raise ValueError("Email address cannot be empty")

        email_address = email_address.strip().lower()
        return self.accounts.get(email_address)

    def update_account_last_scan(self, email_address: str) -> None:
        """
        Update the last_scan_at timestamp for an account.

        Args:
            email_address: Gmail email address

        Raises:
            ValueError: If email address is invalid
        """
        if not email_address or not email_address.strip():
            raise ValueError("Email address cannot be empty")

        email_address = email_address.strip().lower()
        account = self.accounts.get(email_address)

        if account:
            account.last_scan_at = datetime.utcnow()

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
        if not email_address or not email_address.strip():
            raise ValueError("Email address cannot be empty")

        email_address = email_address.strip().lower()

        if email_address not in self.category_stats:
            self.category_stats[email_address] = []

        # Store the stats
        self.category_stats[email_address].append({
            'date': stats_date,
            'stats': category_stats
        })

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
        if not email_address or not email_address.strip():
            raise ValueError("Email address cannot be empty")

        if days < 1 or days > 365:
            raise ValueError("Days must be between 1 and 365")

        if limit < 1 or limit > 50:
            raise ValueError("Limit must be between 1 and 50")

        email_address = email_address.strip().lower()

        if email_address not in self.accounts:
            raise ValueError(f"Account not found: {email_address}")

        # Aggregate category stats
        category_totals: Dict[str, Dict[str, int]] = {}
        stats_list = self.category_stats.get(email_address, [])

        for stat_entry in stats_list:
            for category, counts in stat_entry['stats'].items():
                if category not in category_totals:
                    category_totals[category] = {
                        'total': 0,
                        'deleted': 0,
                        'kept': 0,
                        'archived': 0
                    }

                # If counts is just an integer (count of emails), convert it
                if isinstance(counts, int):
                    category_totals[category]['total'] += counts
                else:
                    category_totals[category]['total'] += counts.get('total', counts.get('count', 0))
                    category_totals[category]['deleted'] += counts.get('deleted', 0)
                    category_totals[category]['kept'] += counts.get('kept', 0)
                    category_totals[category]['archived'] += counts.get('archived', 0)

        # Sort by total and limit
        sorted_categories = sorted(
            category_totals.items(),
            key=lambda x: x[1]['total'],
            reverse=True
        )[:limit]

        # Calculate total emails
        total_emails = sum(counts['total'] for _, counts in sorted_categories)

        # Build category stats
        top_categories = []
        for category, counts in sorted_categories:
            percentage = (counts['total'] / total_emails * 100) if total_emails > 0 else 0.0

            category_stat = CategoryStats(
                category=category,
                total_count=counts['total'],
                percentage=round(percentage, 2)
            )

            if include_counts:
                category_stat.kept_count = counts['kept']
                category_stat.deleted_count = counts['deleted']
                category_stat.archived_count = counts['archived']

            top_categories.append(category_stat)

        # Create date period
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)

        period = DatePeriod(
            start_date=start_date,
            end_date=end_date,
            days=days
        )

        return TopCategoriesResponse(
            email_address=email_address,
            period=period,
            total_emails=total_emails,
            top_categories=top_categories
        )

    def get_all_accounts(self, active_only: bool) -> List[FakeEmailAccount]:
        """
        Get all accounts, optionally filtered by active status.

        Args:
            active_only: If True, only return active accounts (default: True)

        Returns:
            List of EmailAccount objects
        """
        accounts = list(self.accounts.values())

        if active_only:
            accounts = [acc for acc in accounts if acc.is_active]

        return accounts

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
        if not email_address or not email_address.strip():
            raise ValueError("Email address cannot be empty")

        email_address = email_address.strip().lower()
        account = self.accounts.get(email_address)

        if account:
            account.is_active = False
            return True

        return False
