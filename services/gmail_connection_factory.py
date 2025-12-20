"""
Factory for creating Gmail connection services based on authentication method.

Supports switching between IMAP (App Password) and OAuth 2.0 authentication
via the GMAIL_AUTH_METHOD environment variable.
"""
from __future__ import annotations

import os
from enum import Enum
from typing import Optional

from utils.logger import get_logger
from services.gmail_connection_interface import GmailConnectionInterface
from services.gmail_connection_service import GmailConnectionService
from services.gmail_oauth_connection_service import GmailOAuthConnectionService

logger = get_logger(__name__)


class GmailAuthMethod(str, Enum):
    """Supported Gmail authentication methods."""

    IMAP = "imap"
    OAUTH = "oauth"

    @classmethod
    def all_methods(cls) -> list[str]:
        """Return all supported authentication methods."""
        return [m.value for m in cls]


class GmailConnectionFactory:
    """
    Factory for creating Gmail connection services.

    The authentication method is determined by the GMAIL_AUTH_METHOD
    environment variable. Defaults to 'imap' if not specified.

    Environment variables:
        GMAIL_AUTH_METHOD: 'imap' (default) or 'oauth'

    For IMAP authentication:
        - GMAIL_EMAIL: Gmail email address
        - GMAIL_PASSWORD: Gmail App Password

    For OAuth authentication:
        - GMAIL_EMAIL: Gmail email address
        - GMAIL_OAUTH_CLIENT_ID: OAuth client ID
        - GMAIL_OAUTH_CLIENT_SECRET: OAuth client secret
        - GMAIL_OAUTH_REFRESH_TOKEN: OAuth refresh token
        - OR -
        - GMAIL_OAUTH_CREDENTIALS_FILE: Path to credentials.json
        - GMAIL_OAUTH_TOKEN_FILE: Path to token.json
    """

    DEFAULT_AUTH_METHOD = GmailAuthMethod.IMAP.value

    @classmethod
    def get_auth_method(cls) -> str:
        """
        Get the configured authentication method from environment.

        Returns:
            str: Authentication method ('imap' or 'oauth')
        """
        method = os.getenv("GMAIL_AUTH_METHOD", cls.DEFAULT_AUTH_METHOD).lower().strip()

        if method not in GmailAuthMethod.all_methods():
            logger.warning(
                f"Invalid GMAIL_AUTH_METHOD '{method}', "
                f"defaulting to '{cls.DEFAULT_AUTH_METHOD}'. "
                f"Valid options: {GmailAuthMethod.all_methods()}"
            )
            return cls.DEFAULT_AUTH_METHOD

        return method

    @classmethod
    def create_connection(
        cls,
        email_address: str,
        password: Optional[str] = None,
        imap_server: str = "imap.gmail.com",
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None,
        auth_method: Optional[str] = None,
    ) -> GmailConnectionInterface:
        """
        Create a Gmail connection service based on the authentication method.

        Args:
            email_address: Gmail email address
            password: Gmail App Password (for IMAP auth)
            imap_server: IMAP server hostname (for IMAP auth)
            client_id: OAuth client ID (for OAuth auth)
            client_secret: OAuth client secret (for OAuth auth)
            refresh_token: OAuth refresh token (for OAuth auth)
            credentials_file: Path to OAuth credentials.json (for OAuth auth)
            token_file: Path to OAuth token.json (for OAuth auth)
            auth_method: Override authentication method (optional)

        Returns:
            GmailConnectionInterface: Configured connection service

        Raises:
            ValueError: If required credentials are missing for the auth method
        """
        method = auth_method or cls.get_auth_method()
        logger.info(f"Creating Gmail connection using '{method}' authentication")

        if method == GmailAuthMethod.OAUTH.value:
            return cls._create_oauth_connection(
                email_address=email_address,
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                credentials_file=credentials_file,
                token_file=token_file,
            )
        else:
            return cls._create_imap_connection(
                email_address=email_address,
                password=password,
                imap_server=imap_server,
            )

    @classmethod
    def _create_imap_connection(
        cls,
        email_address: str,
        password: Optional[str],
        imap_server: str,
    ) -> GmailConnectionService:
        """Create an IMAP-based connection service."""
        password = password or os.getenv("GMAIL_PASSWORD", "")

        if not password:
            raise ValueError(
                "IMAP authentication requires a password. "
                "Set GMAIL_PASSWORD environment variable or provide password argument."
            )

        return GmailConnectionService(
            email_address=email_address,
            password=password,
            imap_server=imap_server,
        )

    @classmethod
    def _create_oauth_connection(
        cls,
        email_address: str,
        client_id: Optional[str],
        client_secret: Optional[str],
        refresh_token: Optional[str],
        credentials_file: Optional[str],
        token_file: Optional[str],
    ) -> GmailOAuthConnectionService:
        """Create an OAuth-based connection service."""
        return GmailOAuthConnectionService(
            email_address=email_address,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            credentials_file=credentials_file,
            token_file=token_file,
        )
