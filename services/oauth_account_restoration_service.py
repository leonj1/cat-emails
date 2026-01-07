"""
OAuth Account Restoration Service.

This service identifies and restores OAuth accounts that were corrupted by the auth_method bug.
The bug caused accounts with OAuth refresh tokens to have their auth_method incorrectly
set to 'imap' instead of 'oauth'.

Corrupted accounts have:
- auth_method = 'imap' (case-insensitive)
- oauth_refresh_token IS NOT NULL AND NOT EMPTY (after trimming whitespace)

Usage:
    from services.oauth_account_restoration_service import OAuthAccountRestorationService

    service = OAuthAccountRestorationService(repository=my_repository)

    # Scan for corrupted accounts
    corrupted = service.scan_corrupted_accounts()

    # Restore corrupted accounts
    count = service.restore_corrupted_accounts()
"""

from typing import List, Dict, Protocol
from utils.logger import get_logger


class DatabaseRepositoryProtocol(Protocol):
    """Protocol for database repository interface."""

    def get_all_accounts(self) -> List:
        """Get all email accounts."""
        ...

    def update_account_auth_method(self, email_address: str, auth_method: str) -> bool:
        """Update the auth_method for an account."""
        ...


class OAuthAccountRestorationService:
    """Service for identifying and restoring corrupted OAuth accounts."""

    def __init__(self, repository: DatabaseRepositoryProtocol):
        """
        Initialize the OAuth Account Restoration Service.

        Args:
            repository: Database repository for account access
        """
        self.repository = repository
        self.logger = get_logger(__name__)
        self.logger.info("OAuth Account Restoration Service initialized")

    def is_account_corrupted(self, account) -> bool:
        """
        Check if a single account is corrupted.

        An account is corrupted if ALL conditions are true:
        - auth_method is 'imap' (case-insensitive)
        - oauth_refresh_token IS NOT NULL
        - oauth_refresh_token is NOT empty string (after trimming whitespace)

        An account is NOT corrupted if ANY condition is true:
        - auth_method is 'oauth'
        - oauth_refresh_token is None
        - oauth_refresh_token is empty string or whitespace-only
        - auth_method is None

        Args:
            account: Email account object with auth_method and oauth_refresh_token attributes

        Returns:
            True if account is corrupted, False otherwise
        """
        # Check if auth_method is None
        if account.auth_method is None:
            return False

        # Check if oauth_refresh_token is None or empty/whitespace
        if account.oauth_refresh_token is None:
            return False

        token = str(account.oauth_refresh_token).strip()
        if not token:
            return False

        # Check if auth_method is 'imap' (case-insensitive)
        auth_method = str(account.auth_method).strip().lower()
        if auth_method != 'imap':
            return False

        # All conditions met - account is corrupted
        return True

    def scan_corrupted_accounts(self) -> List[Dict]:
        """
        Scan for corrupted OAuth accounts.

        Returns a list of dictionaries with:
        - email: The account email address
        - reason: Description of why it's corrupted

        Returns:
            List of corrupted account details

        Raises:
            Exception: If database scan fails
        """
        try:
            self.logger.info("Starting scan for corrupted OAuth accounts")

            all_accounts = self.repository.get_all_accounts()
            corrupted_accounts = []

            for account in all_accounts:
                if self.is_account_corrupted(account):
                    corrupted_accounts.append({
                        'email': account.email_address,
                        'reason': 'has oauth_refresh_token but auth_method is imap'
                    })

            self.logger.info(f"Scan complete. Found {len(corrupted_accounts)} corrupted accounts")
            return corrupted_accounts

        except Exception as e:
            self.logger.error(f"Error scanning for corrupted accounts: {str(e)}")
            raise

    def restore_corrupted_accounts(self) -> int:
        """
        Restore corrupted OAuth accounts by setting auth_method='oauth'.

        This operation is idempotent - running it multiple times will only
        restore accounts that are currently corrupted. Already-restored
        accounts will not be modified.

        Returns:
            Number of accounts restored

        Raises:
            Exception: If database error occurs during restoration
        """
        try:
            self.logger.info("Starting OAuth account restoration process")

            all_accounts = self.repository.get_all_accounts()
            restored_count = 0

            for account in all_accounts:
                if self.is_account_corrupted(account):
                    try:
                        # Log the restoration
                        self.logger.info(
                            f"Restoring account: {account.email_address} "
                            f"(old_method=imap, new_method=oauth)"
                        )

                        # Update the account
                        success = self.repository.update_account_auth_method(
                            account.email_address,
                            'oauth'
                        )

                        if success:
                            restored_count += 1
                        else:
                            self.logger.warning(
                                f"Failed to restore account {account.email_address}: "
                                f"update_account_auth_method returned False"
                            )

                    except Exception as e:
                        self.logger.error(
                            f"Database error restoring account {account.email_address}: {str(e)}"
                        )
                        raise Exception(
                            f"Database error during restoration for {account.email_address}: {str(e)}"
                        )

            self.logger.info(f"Restoration complete. Total accounts restored: {restored_count}")
            return restored_count

        except Exception as e:
            self.logger.error(f"Error during OAuth account restoration: {str(e)}")
            raise
