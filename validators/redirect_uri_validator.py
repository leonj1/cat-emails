"""
Redirect URI Validator for OAuth State Init Endpoint.

Validates redirect URIs according to the following rules:
- Required: non-empty
- Maximum length: 2048 characters
- Must be valid URL format
- Must use HTTPS (except localhost/127.0.0.1 for development)
"""

from typing import Optional, Tuple
from urllib.parse import urlparse


class RedirectUriValidator:
    """Validates OAuth redirect URIs for format and security requirements."""

    MAX_LENGTH = 2048

    def validate(self, uri: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Validate a redirect URI.

        Args:
            uri: The redirect URI to validate (may be None)

        Returns:
            Tuple of (error_code, error_message) if invalid
            Tuple of (None, None) if valid

        Error codes:
            - invalid_request: Missing URI (None)
            - invalid_redirect_uri: Format validation failed
        """
        # Check if URI is None (missing field)
        if uri is None:
            return "invalid_request", "Redirect URI is required"

        # Check if URI is empty or whitespace-only
        if not uri.strip():
            return "invalid_redirect_uri", "Redirect URI is required"

        # Check maximum length
        if len(uri) > self.MAX_LENGTH:
            return "invalid_redirect_uri", f"Redirect URI must not exceed {self.MAX_LENGTH} characters"

        # Parse and validate URL format
        try:
            parsed = urlparse(uri)

            # Check if scheme exists (if not, URL is invalid)
            if not parsed.scheme:
                return "invalid_redirect_uri", "Redirect URI must be a valid URL"

            # Check scheme (must be http or https)
            if parsed.scheme not in ('http', 'https'):
                return "invalid_redirect_uri", "Redirect URI must use HTTPS (or HTTP for localhost)"

            # Check for valid netloc (host) - must exist for http/https
            if not parsed.netloc:
                return "invalid_redirect_uri", "Redirect URI must be a valid URL"

        except Exception:
            return "invalid_redirect_uri", "Redirect URI must be a valid URL"

        # Check if HTTP is used with non-localhost domain
        if parsed.scheme == 'http':
            # Allow HTTP only for localhost and 127.0.0.1
            netloc_lower = parsed.netloc.lower()
            is_localhost = (
                netloc_lower.startswith('localhost') or
                netloc_lower.startswith('127.0.0.1')
            )
            if not is_localhost:
                return "invalid_redirect_uri", "Redirect URI must use HTTPS (or HTTP for localhost)"

        return None, None
