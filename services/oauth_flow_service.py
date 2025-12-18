"""
OAuth 2.0 flow service for Gmail API authorization.

Handles the OAuth consent flow for multi-user email access:
- Generating authorization URLs
- Exchanging authorization codes for tokens
- Refreshing access tokens
- Revoking access
"""
from __future__ import annotations

import json
import os
import secrets
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class OAuthFlowService:
    """
    Service for managing OAuth 2.0 consent flow.

    Uses application-level OAuth credentials (client_id, client_secret)
    to enable per-user authorization.
    """

    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

    REQUIRED_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.labels",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize OAuth flow service.

        Args:
            client_id: OAuth client ID (or use env var GMAIL_OAUTH_CLIENT_ID)
            client_secret: OAuth client secret (or use env var GMAIL_OAUTH_CLIENT_SECRET)
        """
        self.client_id = client_id or os.getenv("GMAIL_OAUTH_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GMAIL_OAUTH_CLIENT_SECRET")

    def _validate_credentials(self) -> None:
        """Validate that application credentials are configured."""
        missing = []
        if not self.client_id:
            missing.append("client_id (GMAIL_OAUTH_CLIENT_ID)")
        if not self.client_secret:
            missing.append("client_secret (GMAIL_OAUTH_CLIENT_SECRET)")

        if missing:
            raise ValueError(
                f"Missing OAuth application credentials: {', '.join(missing)}. "
                "Configure them via constructor arguments or environment variables."
            )

    def generate_state_token(self) -> str:
        """Generate a cryptographically secure state token for CSRF protection."""
        return secrets.token_urlsafe(32)

    def generate_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        login_hint: Optional[str] = None,
    ) -> str:
        """
        Generate the Google OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect to after consent
            state: CSRF protection state token
            login_hint: Optional email address to pre-fill

        Returns:
            str: Full authorization URL to redirect user to
        """
        self._validate_credentials()

        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.REQUIRED_SCOPES),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        if login_hint:
            params["login_hint"] = login_hint

        query_string = urllib.parse.urlencode(params)
        return f"{self.GOOGLE_AUTH_URL}?{query_string}"

    def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
    ) -> dict:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect_uri used in authorization request

        Returns:
            dict: Token response containing:
                - access_token: Short-lived access token
                - refresh_token: Long-lived refresh token
                - expires_in: Seconds until access token expires
                - scope: Granted scopes
                - token_type: Token type (Bearer)
        """
        self._validate_credentials()

        data = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }).encode("utf-8")

        request = urllib.request.Request(
            self.GOOGLE_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))

            if "access_token" not in result:
                raise ValueError(
                    f"Token response missing 'access_token'. Keys: {list(result.keys())}"
                )

            if "refresh_token" not in result:
                logger.warning(
                    "Token response missing 'refresh_token'. "
                    "User may have previously granted access. "
                    "Consider prompting for re-consent with prompt=consent."
                )

            logger.info("Successfully exchanged authorization code for tokens")
            return result

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.exception(f"Token exchange failed: {e.code} - {error_body}")
            raise ValueError(
                f"Failed to exchange authorization code: {e.code}. {error_body}"
            ) from e
        except urllib.error.URLError as e:
            logger.exception("Network error during token exchange")
            raise ValueError(f"Network error during token exchange: {e}") from e

    def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token: Long-lived refresh token

        Returns:
            dict: Token response containing:
                - access_token: New short-lived access token
                - expires_in: Seconds until access token expires
                - scope: Granted scopes
                - token_type: Token type (Bearer)
        """
        self._validate_credentials()

        data = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")

        request = urllib.request.Request(
            self.GOOGLE_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))

            if "access_token" not in result:
                raise ValueError(
                    f"Token response missing 'access_token'. Keys: {list(result.keys())}"
                )

            logger.info("Successfully refreshed access token")
            return result

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.exception(f"Token refresh failed: {e.code} - {error_body}")
            raise ValueError(
                f"Failed to refresh access token: {e.code}. "
                "The refresh token may be expired or revoked. "
                f"Details: {error_body}"
            ) from e
        except urllib.error.URLError as e:
            logger.exception("Network error during token refresh")
            raise ValueError(f"Network error during token refresh: {e}") from e

    def revoke_token(self, token: str) -> bool:
        """
        Revoke an OAuth token (access or refresh token).

        Args:
            token: Token to revoke (access_token or refresh_token)

        Returns:
            bool: True if revocation succeeded
        """
        data = urllib.parse.urlencode({"token": token}).encode("utf-8")

        request = urllib.request.Request(
            self.GOOGLE_REVOKE_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status == 200:
                    logger.info("Successfully revoked OAuth token")
                    return True
                else:
                    logger.warning(f"Token revocation returned status {response.status}")
                    return False

        except urllib.error.HTTPError as e:
            if e.code == 400:
                logger.info("Token already revoked or invalid")
                return True
            error_body = e.read().decode("utf-8")
            logger.exception(f"Token revocation failed: {e.code} - {error_body}")
            return False
        except urllib.error.URLError:
            logger.exception("Network error during token revocation")
            return False

    def calculate_token_expiry(self, expires_in: int) -> datetime:
        """
        Calculate the absolute expiry time from expires_in seconds.

        Args:
            expires_in: Seconds until token expires

        Returns:
            datetime: Absolute expiry timestamp
        """
        return datetime.utcnow() + timedelta(seconds=expires_in)

    def parse_scopes(self, scope_string: str) -> list[str]:
        """
        Parse scope string into list of scopes.

        Args:
            scope_string: Space-separated scope string

        Returns:
            list[str]: List of individual scopes
        """
        return scope_string.split() if scope_string else []
