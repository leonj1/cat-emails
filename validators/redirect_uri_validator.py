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
        # Note: urlparse() doesn't typically raise exceptions, so no try/except needed
        parsed = urlparse(uri)

        # Check if scheme exists (if not, URL is invalid)
        if not parsed.scheme:
            return "invalid_redirect_uri", "Redirect URI must be a valid URL"

        # Check scheme (must be http or https)
        if parsed.scheme not in ("http", "https"):
            return "invalid_redirect_uri", "Redirect URI must use HTTPS (or HTTP for localhost)"

        # Require a real hostname (netloc alone can be misleading, e.g. "https://:80/path")
        if not parsed.netloc or not parsed.hostname:
            return "invalid_redirect_uri", "Redirect URI must be a valid URL"

        # Reject userinfo (username/password) and fragments (commonly invalid for OAuth redirect URIs)
        if parsed.username or parsed.password or parsed.fragment:
            return "invalid_redirect_uri", "Redirect URI must be a valid URL"

        # Check if HTTP is used with non-localhost domain
        if parsed.scheme == "http":
            # Allow HTTP only for exact localhost, 127.0.0.1, and ::1 (IPv6 localhost)
            # Extract hostname without port for exact matching
            hostname = parsed.hostname.lower()  # Already validated above, safe to access
            is_localhost = hostname in {"localhost", "127.0.0.1", "::1"}
            if not is_localhost:
                return "invalid_redirect_uri", "Redirect URI must use HTTPS (or HTTP for localhost)"

        return None, None
