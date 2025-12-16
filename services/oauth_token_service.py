"""
OAuth Token Management Service

Handles OAuth 2.0 token storage, refresh, and revocation.
Integrates with database to persist tokens per email account.
"""
import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

from utils.logger import get_logger
from models.database import EmailAccount
from repositories.database_repository_interface import DatabaseRepositoryInterface

logger = get_logger(__name__)


class OAuthTokenService:
    """
    Service for managing OAuth 2.0 access and refresh tokens.

    Responsibilities:
    - Get valid access tokens (auto-refresh if expired)
    - Refresh access tokens using refresh_token
    - Update database with refreshed tokens
    - Revoke tokens on account deletion
    """

    TOKEN_URI = "https://oauth2.googleapis.com/token"
    REVOKE_URI = "https://oauth2.googleapis.com/revoke"
    TOKEN_EXPIRY_BUFFER_MINUTES = 5  # Refresh tokens 5 minutes before expiry

    def __init__(self, repository: DatabaseRepositoryInterface):
        """
        Initialize OAuth token service.

        Args:
            repository: Database repository for loading/saving account tokens
        """
        self.repository = repository
        self.client_id = os.getenv("OAUTH_CLIENT_ID")
        self.client_secret = os.getenv("OAUTH_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            logger.warning(
                "OAUTH_CLIENT_ID or OAUTH_CLIENT_SECRET not configured. "
                "OAuth token operations will fail."
            )

    def get_access_token(self, account_id: int) -> str:
        """
        Get a valid access token for an account, refreshing if necessary.

        Args:
            account_id: Email account ID

        Returns:
            str: Valid OAuth access token

        Raises:
            ValueError: If account not found or has no OAuth tokens
            Exception: If token refresh fails
        """
        account = self.repository.get_by_id(EmailAccount, account_id)

        if not account:
            raise ValueError(f"Account {account_id} not found")

        if account.auth_method != 'oauth':
            raise ValueError(
                f"Account {account.email_address} uses {account.auth_method} authentication, "
                "not OAuth. Use oauth auth_method for this account."
            )

        if not account.oauth_refresh_token:
            raise ValueError(
                f"Account {account.email_address} has no OAuth refresh token. "
                "Re-authorize the account via /api/oauth/authorize"
            )

        # Check if token expired or expires soon (within buffer)
        if self._is_token_expired(account):
            logger.info(
                f"Access token for {account.email_address} expired or expiring soon. Refreshing..."
            )
            return self._refresh_and_save(account)

        # Token still valid
        if account.oauth_access_token:
            return account.oauth_access_token

        # No access token but have refresh token - refresh immediately
        logger.info(f"No access token for {account.email_address}. Refreshing...")
        return self._refresh_and_save(account)

    def _is_token_expired(self, account: EmailAccount) -> bool:
        """
        Check if access token is expired or expiring soon.

        Args:
            account: Email account with OAuth tokens

        Returns:
            bool: True if token should be refreshed
        """
        if not account.oauth_token_expires_at:
            return True

        buffer = timedelta(minutes=self.TOKEN_EXPIRY_BUFFER_MINUTES)
        now = datetime.utcnow()
        expiry_with_buffer = account.oauth_token_expires_at - buffer

        return now >= expiry_with_buffer

    def _refresh_and_save(self, account: EmailAccount) -> str:
        """
        Refresh access token using refresh_token and save to database.

        Args:
            account: Email account with OAuth refresh_token

        Returns:
            str: New access token

        Raises:
            Exception: If token refresh fails
        """
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET must be configured "
                "in environment variables to refresh tokens"
            )

        # Validate URL scheme for security
        parsed_uri = urlparse(self.TOKEN_URI)
        if parsed_uri.scheme != "https":
            raise ValueError(
                f"Insecure URL scheme: {parsed_uri.scheme}. Only HTTPS is allowed."
            )

        # Prepare token refresh request
        data = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": account.oauth_refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")

        request = urllib.request.Request(
            self.TOKEN_URI,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))

            if "access_token" not in result:
                raise Exception(
                    f"OAuth token response missing 'access_token'. "
                    f"Response keys: {list(result.keys())}"
                )

            new_access_token = result["access_token"]
            expires_in = result.get("expires_in", 3600)  # Default 1 hour

            # Update account with new tokens
            account.oauth_access_token = new_access_token
            account.oauth_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            # Save new refresh token if provided (unlikely but possible)
            if "refresh_token" in result:
                account.oauth_refresh_token = result["refresh_token"]

            # Update scope and token type if provided
            if "scope" in result:
                account.oauth_scope = result["scope"]
            if "token_type" in result:
                account.oauth_token_type = result["token_type"]

            # Persist to database
            self.repository.update(account)

            logger.info(
                f"Successfully refreshed OAuth token for {account.email_address}. "
                f"Expires at: {account.oauth_token_expires_at}"
            )

            return new_access_token

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else "No error body"
            logger.exception(
                f"Failed to refresh OAuth token for {account.email_address}: "
                f"{e.code} - {error_body}"
            )
            raise Exception(
                f"OAuth token refresh failed: {e.code}. "
                "The refresh token may be revoked or expired. "
                "User must re-authorize via /api/oauth/authorize. "
                f"Details: {error_body}"
            ) from e
        except urllib.error.URLError as e:
            logger.exception(
                f"Network error refreshing OAuth token for {account.email_address}"
            )
            raise Exception(
                f"Network error during OAuth token refresh: {e}"
            ) from e
        except Exception as e:
            logger.exception(
                f"Unexpected error refreshing OAuth token for {account.email_address}"
            )
            raise

    def revoke_token(self, refresh_token: str) -> bool:
        """
        Revoke an OAuth refresh token with Google.

        This is called when deleting an account or when user explicitly revokes access.

        Args:
            refresh_token: OAuth refresh token to revoke

        Returns:
            bool: True if revocation successful, False otherwise
        """
        if not refresh_token:
            logger.warning("Attempted to revoke empty refresh token")
            return False

        try:
            # Prepare revocation request
            data = urllib.parse.urlencode({
                "token": refresh_token,
            }).encode("utf-8")

            request = urllib.request.Request(
                self.REVOKE_URI,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    logger.info("Successfully revoked OAuth token")
                    return True
                else:
                    logger.warning(f"Token revocation returned status {response.status}")
                    return False

        except urllib.error.HTTPError as e:
            # Token may already be revoked (returns 400)
            if e.code == 400:
                logger.info("Token already revoked or invalid")
                return True
            else:
                logger.exception(f"Failed to revoke OAuth token: {e.code}")
                return False
        except urllib.error.URLError as e:
            logger.exception(f"Network error revoking OAuth token: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error revoking OAuth token: {e}")
            return False

    def validate_credentials(self) -> bool:
        """
        Validate that OAuth client credentials are configured.

        Returns:
            bool: True if credentials are configured
        """
        return bool(self.client_id and self.client_secret)
