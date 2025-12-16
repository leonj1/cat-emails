"""
Gmail OAuth 2.0 connection service using XOAUTH2 for IMAP authentication.

This service allows users to authenticate via OAuth 2.0 instead of App Passwords.
It uses the Gmail API OAuth flow but connects via IMAP using XOAUTH2.
"""
from __future__ import annotations

import base64
import imaplib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import ClassVar, Optional
from urllib.parse import urlparse

from utils.logger import get_logger
from services.gmail_connection_interface import GmailConnectionInterface

logger = get_logger(__name__)


class GmailOAuthConnectionService(GmailConnectionInterface):
    """
    Gmail connection service using OAuth 2.0 authentication.

    Requires OAuth credentials from Google Cloud Console:
    - Client ID and Client Secret (from credentials.json)
    - Refresh token (obtained through initial OAuth consent flow)

    Environment variables:
    - GMAIL_OAUTH_CLIENT_ID: OAuth client ID
    - GMAIL_OAUTH_CLIENT_SECRET: OAuth client secret
    - GMAIL_OAUTH_REFRESH_TOKEN: OAuth refresh token for the user
    - GMAIL_OAUTH_CREDENTIALS_FILE: Path to credentials.json (alternative)
    - GMAIL_OAUTH_TOKEN_FILE: Path to token.json (alternative)
    """

    TOKEN_URI = "https://oauth2.googleapis.com/token"
    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    SCOPES: ClassVar[list[str]] = [
        "https://mail.google.com/",
    ]

    def __init__(
        self,
        email_address: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None,
    ):
        """
        Initialize OAuth connection service.

        Args:
            email_address: Gmail address to authenticate
            client_id: OAuth client ID (or use env var GMAIL_OAUTH_CLIENT_ID)
            client_secret: OAuth client secret (or use env var GMAIL_OAUTH_CLIENT_SECRET)
            refresh_token: OAuth refresh token (or use env var GMAIL_OAUTH_REFRESH_TOKEN)
            credentials_file: Path to credentials.json from Google Cloud Console
            token_file: Path to token.json with stored refresh token
        """
        self.email_address = email_address
        self.client_id = client_id or os.getenv("GMAIL_OAUTH_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GMAIL_OAUTH_CLIENT_SECRET")
        self.refresh_token = refresh_token or os.getenv("GMAIL_OAUTH_REFRESH_TOKEN")
        self.credentials_file = credentials_file or os.getenv("GMAIL_OAUTH_CREDENTIALS_FILE")
        self.token_file = token_file or os.getenv("GMAIL_OAUTH_TOKEN_FILE")
        self._access_token: Optional[str] = None

        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load OAuth credentials from files if not provided directly."""
        if self.credentials_file and not (self.client_id and self.client_secret):
            self._load_credentials_file()

        if self.token_file and not self.refresh_token:
            self._load_token_file()

    def _load_credentials_file(self) -> None:
        """Load client_id and client_secret from credentials.json."""
        creds_path = Path(self.credentials_file)
        if not creds_path.exists():
            logger.warning(f"Credentials file not found: {self.credentials_file}")
            return

        try:
            with open(creds_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            installed = data.get("installed") or data.get("web", {})
            self.client_id = self.client_id or installed.get("client_id")
            self.client_secret = self.client_secret or installed.get("client_secret")
            logger.info("Loaded OAuth credentials from file")
        except json.JSONDecodeError:
            logger.exception("Failed to parse credentials file")

    def _load_token_file(self) -> None:
        """Load refresh_token from token.json."""
        token_path = Path(self.token_file)
        if not token_path.exists():
            logger.warning(f"Token file not found: {self.token_file}")
            return

        try:
            with open(token_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.refresh_token = self.refresh_token or data.get("refresh_token")
            self._access_token = data.get("access_token")
            logger.info("Loaded OAuth token from file")
        except json.JSONDecodeError:
            logger.exception("Failed to parse token file")

    def _validate_credentials(self) -> None:
        """Validate that all required credentials are present."""
        missing = []
        if not self.client_id:
            missing.append("client_id (GMAIL_OAUTH_CLIENT_ID)")
        if not self.client_secret:
            missing.append("client_secret (GMAIL_OAUTH_CLIENT_SECRET)")
        if not self.refresh_token:
            missing.append("refresh_token (GMAIL_OAUTH_REFRESH_TOKEN)")

        if missing:
            raise ValueError(
                f"Missing OAuth credentials: {', '.join(missing)}. "
                "Provide them via constructor arguments, environment variables, "
                "or credentials/token files."
            )

    def _refresh_access_token(self) -> str:
        """
        Refresh the OAuth access token using the refresh token.

        Returns:
            str: Fresh access token
        """
        import urllib.request
        import urllib.parse

        self._validate_credentials()

        # Validate URL scheme for security
        parsed_uri = urlparse(self.TOKEN_URI)
        if parsed_uri.scheme != "https":
            raise ValueError(f"Insecure URL scheme: {parsed_uri.scheme}. Only HTTPS is allowed.")

        data = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
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

            self._access_token = result["access_token"]
            logger.info("Successfully refreshed OAuth access token")

            if self.token_file and "refresh_token" in result:
                self._save_token_file(result)

            return self._access_token
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.exception(f"Failed to refresh OAuth token: {e.code} - {error_body}")
            raise Exception(
                f"OAuth token refresh failed: {e.code}. "
                "Ensure your refresh_token is valid and not revoked. "
                f"Details: {error_body}"
            ) from e
        except urllib.error.URLError as e:
            logger.exception("Network error refreshing OAuth token")
            raise Exception(f"Network error during OAuth token refresh: {e}") from e

    def _save_token_file(self, token_data: dict) -> None:
        """Save updated token data to token file using atomic write."""
        if not self.token_file:
            return

        try:
            token_path = Path(self.token_file)
            existing = {}
            if token_path.exists():
                with open(token_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)

            existing.update(token_data)

            # Atomic write to prevent corruption from concurrent access
            fd, tmp_path = tempfile.mkstemp(dir=token_path.parent, suffix=".json")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(existing, f, indent=2)
                shutil.move(tmp_path, token_path)
            except Exception:
                os.unlink(tmp_path)
                raise

            logger.debug("Saved updated OAuth token to file")
        except Exception as e:
            logger.warning(f"Failed to save token file: {e}")

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

        Returns:
            imaplib.IMAP4: An authenticated IMAP4_SSL connection object.
        """
        access_token = self._refresh_access_token()

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
                        "4) The email address doesn't match the OAuth grant."
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
