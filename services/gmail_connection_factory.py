"""
Factory for creating Gmail connection services based on authentication method.

NEW: Account-based routing. Auth method is determined per account from database.
Supports both IMAP (App Password) and OAuth 2.0 authentication.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from utils.logger import get_logger
from services.gmail_connection_interface import GmailConnectionInterface
from services.gmail_connection_service import GmailConnectionService
from services.gmail_oauth_connection_service import GmailOAuthConnectionService
from services.oauth_token_service import OAuthTokenService
from repositories.database_repository_interface import DatabaseRepositoryInterface
from models.database import EmailAccount

logger = get_logger(__name__)


class GmailAuthMethod(str, Enum):
    """Supported Gmail authentication methods."""

    APP_PASSWORD = "app_password"
    OAUTH = "oauth"

    @classmethod
    def all_methods(cls) -> list[str]:
        """Return all supported authentication methods."""
        return [m.value for m in cls]


class GmailConnectionFactory:
    """
    Factory for creating Gmail connection services.

    NEW: Database-backed, account-based routing.
    The authentication method is determined by the account's auth_method field.

    Each account in the database has an auth_method column that specifies:
    - 'app_password': Use IMAP with app password
    - 'oauth': Use OAuth 2.0 with tokens from database
    """

    def __init__(self, repository: DatabaseRepositoryInterface):
        """
        Initialize factory with database repository.

        Args:
            repository: Database repository for loading account data
        """
        self.repository = repository
        self.token_service = OAuthTokenService(repository)

    def create_connection(self, account_id: int) -> GmailConnectionInterface:
        """
        Create a Gmail connection service based on account's auth_method.

        Args:
            account_id: Email account ID

        Returns:
            GmailConnectionInterface: Configured connection service

        Raises:
            ValueError: If account not found or auth method invalid
        """
        account = self.repository.get_by_id(EmailAccount, account_id)

        if not account:
            raise ValueError(f"Account {account_id} not found")

        if not account.is_active:
            raise ValueError(f"Account {account.email_address} is inactive")

        logger.info(
            f"Creating Gmail connection for {account.email_address} "
            f"using '{account.auth_method}' authentication"
        )

        if account.auth_method == GmailAuthMethod.OAUTH.value:
            return self._create_oauth_connection(account)
        elif account.auth_method == GmailAuthMethod.APP_PASSWORD.value:
            return self._create_imap_connection(account)
        else:
            raise ValueError(
                f"Unknown auth method '{account.auth_method}' for account {account.email_address}. "
                f"Valid options: {GmailAuthMethod.all_methods()}"
            )

    def _create_imap_connection(self, account: EmailAccount) -> GmailConnectionService:
        """
        Create an IMAP-based connection service.

        Args:
            account: Email account with app_password

        Returns:
            GmailConnectionService: IMAP connection service

        Raises:
            ValueError: If app_password is missing
        """
        if not account.app_password:
            raise ValueError(
                f"Account {account.email_address} has auth_method='app_password' "
                "but no app_password is set. Please update the account with a valid "
                "Gmail App Password or migrate to OAuth."
            )

        return GmailConnectionService(
            email_address=account.email_address,
            password=account.app_password,
            imap_server="imap.gmail.com",
        )

    def _create_oauth_connection(self, account: EmailAccount) -> GmailOAuthConnectionService:
        """
        Create an OAuth-based connection service.

        Args:
            account: Email account with OAuth tokens

        Returns:
            GmailOAuthConnectionService: OAuth connection service

        Raises:
            ValueError: If OAuth tokens are missing
        """
        if not account.oauth_refresh_token:
            raise ValueError(
                f"Account {account.email_address} has auth_method='oauth' "
                "but no OAuth refresh token is set. User must authorize via "
                "/api/oauth/authorize endpoint."
            )

        return GmailOAuthConnectionService(
            account_id=account.id,
            token_service=self.token_service,
            email_address=account.email_address,
        )
