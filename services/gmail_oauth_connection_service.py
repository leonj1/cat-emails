"""
Gmail OAuth 2.0 connection service using XOAUTH2 for IMAP authentication.

This service allows users to authenticate via OAuth 2.0 instead of App Passwords.
Tokens are loaded from the database per email account.
"""
from __future__ import annotations

import base64
import imaplib
import os
from typing import ClassVar, Optional

from utils.logger import get_logger
from services.gmail_connection_interface import GmailConnectionInterface
from services.oauth_token_service import OAuthTokenService

logger = get_logger(__name__)


class GmailOAuthConnectionService(GmailConnectionInterface):
    """
    Gmail connection service using OAuth 2.0 authentication.

    NEW: Database-backed token management.
    Tokens are stored per account in the database and automatically refreshed.

    Environment variables (shared OAuth app):
    - OAUTH_CLIENT_ID: OAuth client ID from Google Cloud Console
    - OAUTH_CLIENT_SECRET: OAuth client secret from Google Cloud Console
    """

    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    SCOPES: ClassVar[list[str]] = [
        "https://mail.google.com/",
    ]

    def __init__(
        self,
        account_id: int,
        token_service: OAuthTokenService,
        email_address: str,
    ):
        """
        Initialize OAuth connection service with database-backed tokens.

        Args:
            account_id: Email account ID (for loading tokens from database)
            token_service: OAuth token service for token refresh
            email_address: Gmail address to authenticate (for XOAUTH2 string)
        """
        self.account_id = account_id
        self.token_service = token_service
        self.email_address = email_address
        self.client_id = os.getenv("OAUTH_CLIENT_ID")
        self.client_secret = os.getenv("OAUTH_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            logger.warning(
                "OAUTH_CLIENT_ID or OAUTH_CLIENT_SECRET not configured. "
                "OAuth authentication will fail."
            )


    def _generate_oauth2_string(self, access_token: str) -> str:
        """
        Generate the XOAUTH2 authentication string.

        Args:
            access_token: OAuth 2.0 access token

        Returns:
            str: Base64-encoded XOAUTH2 string
        """
        auth_string = f"user={self.email_address}\x01auth=Bearer {access_token}\x01\x01"
        return base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    def connect(self) -> imaplib.IMAP4:
        """
        Establish connection to Gmail IMAP server using OAuth 2.0.

        Tokens are loaded from database and automatically refreshed if expired.

        Returns:
            imaplib.IMAP4: An authenticated IMAP4_SSL connection object.

        Raises:
            Exception: If authentication fails or tokens are invalid
        """
        # Get fresh access token from database (auto-refreshes if expired)
        try:
            access_token = self.token_service.get_access_token(self.account_id)
        except ValueError as e:
            logger.error(f"Failed to get access token for account {self.account_id}: {e}")
            raise Exception(
                f"OAuth token not available for account. "
                "User must re-authorize via /api/oauth/authorize"
            ) from e

        logger.info(f"Connecting to Gmail IMAP via OAuth for {self.email_address}")

        try:
            conn = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)

            auth_string = self._generate_oauth2_string(access_token)

            try:
                typ, data = conn.authenticate("XOAUTH2", lambda _: auth_string.encode())
                if typ != "OK":
                    raise imaplib.IMAP4.error(f"XOAUTH2 authentication failed: {data!r}")

                logger.info("Successfully connected to Gmail IMAP via OAuth 2.0")
                return conn

            except imaplib.IMAP4.error as auth_err:
                error_msg = str(auth_err)

                if "Invalid credentials" in error_msg:
                    guidance = (
                        "OAuth authentication failed. This may indicate: "
                        "1) The access token expired (will auto-refresh on next attempt), "
                        "2) The refresh token was revoked, "
                        "3) The OAuth app permissions were changed, or "
                        "4) The email address doesn't match the OAuth grant. "
                        "User should re-authorize via /api/oauth/authorize"
                    )
                else:
                    guidance = (
                        "XOAUTH2 authentication failed. Ensure the OAuth credentials "
                        "are correctly configured and the user has granted access."
                    )

                logger.exception(f"Gmail OAuth authentication failed: {error_msg}. {guidance}")
                raise Exception(f"Gmail OAuth authentication failed: {error_msg}. {guidance}") from auth_err

        except (imaplib.IMAP4.error, OSError):
            logger.exception(f"Gmail OAuth connection error for {self.email_address}")
            raise
