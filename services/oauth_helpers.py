"""
OAuth Helper Functions

Utility functions for OAuth 2.0 authorization flow:
- Token exchange (authorization code → tokens)
- ID token decoding (JWT parsing)
- Google OAuth URL building
"""
import os
import json
import base64
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


def exchange_authorization_code_for_tokens(
    authorization_code: str,
    redirect_uri: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> Dict[str, any]:
    """
    Exchange OAuth authorization code for access and refresh tokens.

    Args:
        authorization_code: Authorization code from OAuth callback
        redirect_uri: Redirect URI (must match the one used in authorize request)
        client_id: OAuth client ID (defaults to OAUTH_CLIENT_ID env var)
        client_secret: OAuth client secret (defaults to OAUTH_CLIENT_SECRET env var)

    Returns:
        dict: Token response from Google containing:
            - access_token: OAuth access token
            - refresh_token: OAuth refresh token (only on first authorization)
            - expires_in: Token lifetime in seconds
            - scope: Granted scopes
            - token_type: Token type (usually "Bearer")
            - id_token: JWT with user identity

    Raises:
        ValueError: If credentials not configured or code exchange fails
    """
    client_id = client_id or os.getenv("OAUTH_CLIENT_ID")
    client_secret = client_secret or os.getenv("OAUTH_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET must be configured "
            "in environment variables"
        )

    token_uri = "https://oauth2.googleapis.com/token"

    # Prepare token exchange request
    data = urllib.parse.urlencode({
        "code": authorization_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    request = urllib.request.Request(
        token_uri,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        logger.info("Successfully exchanged authorization code for tokens")
        return result

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No error body"
        logger.exception(f"Failed to exchange authorization code: {e.code} - {error_body}")
        raise ValueError(
            f"OAuth token exchange failed: {e.code}. "
            "The authorization code may be expired or invalid. "
            f"Details: {error_body}"
        ) from e
    except urllib.error.URLError as e:
        logger.exception("Network error during OAuth token exchange")
        raise ValueError(f"Network error during OAuth token exchange: {e}") from e


def decode_id_token(id_token: str) -> Dict[str, any]:
    """
    Decode Google OAuth ID token (JWT) to extract user information.

    Note: This is a simple base64 decode WITHOUT signature verification.
    For production, use a proper JWT library with signature verification.

    Args:
        id_token: JWT ID token from Google OAuth response

    Returns:
        dict: Decoded token payload containing:
            - sub: Google user ID (unique identifier)
            - email: User email address
            - email_verified: Whether email is verified
            - name: Full name (optional)
            - given_name: First name (optional)
            - family_name: Last name (optional)
            - picture: Profile picture URL (optional)

    Raises:
        ValueError: If token cannot be decoded
    """
    try:
        # JWT format: header.payload.signature
        parts = id_token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format. Expected 3 parts separated by dots.")

        # Decode payload (second part)
        payload_b64 = parts[1]

        # Add padding if needed (base64 requires padding to multiple of 4)
        padding = '=' * (4 - len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode('utf-8'))

        logger.debug(f"Successfully decoded ID token for user: {payload.get('email')}")
        return payload

    except Exception as e:
        logger.exception("Failed to decode ID token")
        raise ValueError(f"Failed to decode ID token: {e}") from e


def build_google_oauth_url(
    state: str,
    redirect_uri: str,
    client_id: Optional[str] = None,
    login_hint: Optional[str] = None,
    scopes: Optional[str] = None,
) -> str:
    """
    Build Google OAuth authorization URL.

    Args:
        state: State parameter for CSRF protection
        redirect_uri: Redirect URI for OAuth callback
        client_id: OAuth client ID (defaults to OAUTH_CLIENT_ID env var)
        login_hint: Email hint for Google login screen
        scopes: OAuth scopes (defaults to https://mail.google.com/)

    Returns:
        str: Complete Google OAuth authorization URL

    Raises:
        ValueError: If client_id not configured
    """
    client_id = client_id or os.getenv("OAUTH_CLIENT_ID")
    if not client_id:
        raise ValueError("OAUTH_CLIENT_ID must be configured")

    scopes = scopes or "https://mail.google.com/"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Force consent screen to ensure refresh token
        "state": state,
    }

    if login_hint:
        params["login_hint"] = login_hint

    query_string = urllib.parse.urlencode(params)
    oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"

    logger.debug(f"Built OAuth URL with state: {state[:20]}...")
    return oauth_url
