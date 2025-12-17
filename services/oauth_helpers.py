"""
OAuth Helper Functions

Utility functions for OAuth 2.0 authorization flow:
- Token exchange (authorization code → tokens)
- ID token decoding and verification (JWT with signature validation)
- Google OAuth URL building
"""
import os
import urllib.parse
from typing import Any, Dict, Optional

import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from utils.logger import get_logger

logger = get_logger(__name__)

# Google OAuth 2.0 endpoints
GOOGLE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Default OAuth scopes for Gmail
DEFAULT_GMAIL_SCOPE = "https://mail.google.com/"


def exchange_authorization_code_for_tokens(
    authorization_code: str,
    redirect_uri: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> Dict[str, Any]:
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

    # Prepare token exchange request
    payload = {
        "code": authorization_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    try:
        response = requests.post(
            GOOGLE_TOKEN_URL,
            data=payload,
            timeout=30,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        result = response.json()

        # Validate required fields in response
        required_fields = ["access_token", "expires_in", "token_type"]
        missing_fields = [field for field in required_fields if field not in result]
        if missing_fields:
            raise ValueError(
                f"Token response missing required fields: {', '.join(missing_fields)}"
            )

        logger.info("Successfully exchanged authorization code for tokens")
        return result

    except requests.exceptions.HTTPError as e:
        error_detail = e.response.text if e.response else "No error details"
        logger.exception(
            f"Failed to exchange authorization code: {e.response.status_code if e.response else 'Unknown'} - {error_detail}"
        )
        raise ValueError(
            f"OAuth token exchange failed: {e.response.status_code if e.response else 'Unknown'}. "
            "The authorization code may be expired or invalid. "
            f"Details: {error_detail}"
        ) from e
    except requests.exceptions.RequestException as e:
        logger.exception("Network error during OAuth token exchange")
        raise ValueError(f"Network error during OAuth token exchange: {e}") from e


def decode_and_verify_id_token(
    token: str,
    client_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Decode and verify Google OAuth ID token with signature verification.

    This function uses Google's official library to verify:
    - Token signature using Google's public certificates
    - Token expiration
    - Audience claim (matches client_id)
    - Issuer claim (Google)

    Args:
        token: JWT ID token from Google OAuth response
        client_id: OAuth client ID for audience validation (defaults to OAUTH_CLIENT_ID env var)

    Returns:
        dict: Verified token payload containing:
            - sub: Google user ID (unique identifier)
            - email: User email address
            - email_verified: Whether email is verified
            - name: Full name (optional)
            - given_name: First name (optional)
            - family_name: Last name (optional)
            - picture: Profile picture URL (optional)

    Raises:
        ValueError: If token verification fails (invalid signature, expired, wrong audience)
    """
    client_id = client_id or os.getenv("OAUTH_CLIENT_ID")
    if not client_id:
        raise ValueError("OAUTH_CLIENT_ID must be configured for ID token verification")

    try:
        # Verify token signature and claims using Google's library
        payload = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id
        )

        logger.info(f"Successfully verified ID token for user: {payload.get('email')}")
        return payload

    except ValueError as e:
        logger.exception("ID token verification failed")
        raise ValueError(f"Invalid or expired ID token: {e}") from e


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
        state: State parameter for CSRF protection (cannot be empty)
        redirect_uri: Redirect URI for OAuth callback (must be http/https)
        client_id: OAuth client ID (defaults to OAUTH_CLIENT_ID env var)
        login_hint: Email hint for Google login screen
        scopes: OAuth scopes (defaults to https://mail.google.com/)

    Returns:
        str: Complete Google OAuth authorization URL

    Raises:
        ValueError: If required parameters missing or invalid
    """
    client_id = client_id or os.getenv("OAUTH_CLIENT_ID")
    if not client_id:
        raise ValueError("OAUTH_CLIENT_ID must be configured")

    # Validate state parameter
    if not state or not state.strip():
        raise ValueError("State parameter cannot be empty")

    # Validate redirect_uri scheme
    parsed_uri = urllib.parse.urlparse(redirect_uri)
    if parsed_uri.scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid redirect_uri scheme: {parsed_uri.scheme}. Must be http or https."
        )

    # For production, enforce HTTPS
    if parsed_uri.scheme != "https":
        logger.warning(f"redirect_uri uses HTTP instead of HTTPS: {redirect_uri}")

    # Use default scope if not provided
    scopes = scopes or DEFAULT_GMAIL_SCOPE

    # Validate scopes is non-empty
    if not scopes or not scopes.strip():
        raise ValueError("Scopes parameter cannot be empty")

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
    oauth_url = f"{GOOGLE_OAUTH_AUTH_URL}?{query_string}"

    logger.debug(f"Built OAuth URL with state: {state[:20]}...")
    return oauth_url
