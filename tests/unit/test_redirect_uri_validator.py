"""
Unit tests for Redirect URI Validator.

Tests derived from Gherkin scenarios for OAuth State Init Endpoint feature.
These tests define the expected behavior for redirect URI validation.

Scenarios covered:
- Valid HTTPS redirect URI is accepted
- HTTP localhost redirect URI is accepted for development
- HTTP 127.0.0.1 redirect URI is accepted for development
- Empty redirect URI is rejected
- Missing redirect URI is rejected (None)
- Invalid URL format is rejected
- Malformed URL is rejected
- HTTP non-localhost redirect URI is rejected
- FTP scheme redirect URI is rejected
- Redirect URI exceeding maximum length (2048) is rejected
"""

import pytest
from typing import Protocol, Tuple, Optional


class RedirectUriValidatorProtocol(Protocol):
    """Protocol for redirect URI validation.

    The implementation should:
    - Accept valid HTTPS URLs
    - Accept HTTP URLs only for localhost and 127.0.0.1
    - Reject non-HTTP/HTTPS schemes
    - Reject URLs exceeding 2048 characters
    - Reject malformed URLs
    - Return (error_code, error_message) tuple for failures
    - Return (None, None) for valid URIs
    """

    def validate(self, uri: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Validate a redirect URI.

        Args:
            uri: The redirect URI to validate (may be None)

        Returns:
            Tuple of (error_code, error_message) if invalid
            Tuple of (None, None) if valid
        """
        ...


class TestRedirectUriValidatorHappyPath:
    """Tests for valid redirect URIs - should all return (None, None)."""

    def test_valid_https_redirect_uri(self):
        """
        Valid HTTPS redirect URI should be accepted.

        Given a valid redirect URI "https://myapp.example.com/oauth/callback"
        When validating the redirect URI
        Then validation should succeed with no errors
        """
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "https://myapp.example.com/oauth/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None, f"Expected no error code, got '{error_code}'"
        assert error_message is None, f"Expected no error message, got '{error_message}'"

    def test_http_localhost_redirect_uri_accepted(self):
        """
        Scenario: HTTP localhost redirect URI is accepted for development

        Given a redirect URI "http://localhost:3000/oauth/callback"
        When validating the redirect URI
        Then validation should succeed with no errors
        """
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "http://localhost:3000/oauth/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None, f"Expected no error code, got '{error_code}'"
        assert error_message is None, f"Expected no error message, got '{error_message}'"

    def test_http_127_0_0_1_redirect_uri_accepted(self):
        """
        Scenario: HTTP 127.0.0.1 redirect URI is accepted for development

        Given a redirect URI "http://127.0.0.1:8080/oauth/callback"
        When validating the redirect URI
        Then validation should succeed with no errors
        """
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "http://127.0.0.1:8080/oauth/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None, f"Expected no error code, got '{error_code}'"
        assert error_message is None, f"Expected no error message, got '{error_message}'"

    def test_https_localhost_redirect_uri_accepted(self):
        """HTTPS localhost should also be accepted."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "https://localhost:3000/oauth/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_https_127_0_0_1_redirect_uri_accepted(self):
        """HTTPS 127.0.0.1 should also be accepted."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "https://127.0.0.1:8080/oauth/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_http_localhost_without_port_accepted(self):
        """HTTP localhost without port should be accepted."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "http://localhost/oauth/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_valid_https_uri_with_query_params(self):
        """Valid HTTPS URI with query parameters should be accepted."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "https://myapp.example.com/oauth/callback?param=value"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_valid_https_uri_with_fragment(self):
        """Valid HTTPS URI with fragment should be accepted."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "https://myapp.example.com/oauth/callback#section"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None
        assert error_message is None


class TestRedirectUriValidatorEmptyAndMissing:
    """Tests for empty and missing redirect URIs."""

    def test_empty_redirect_uri_rejected(self):
        """
        Scenario: Empty redirect URI is rejected

        Given an empty redirect URI ""
        When validating the redirect URI
        Then validation should fail with error code "invalid_redirect_uri"
        And error message "Redirect URI is required"
        """
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = ""

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri", f"Expected 'invalid_redirect_uri', got '{error_code}'"
        assert error_message == "Redirect URI is required", f"Unexpected message: {error_message}"

    def test_missing_redirect_uri_rejected(self):
        """
        Scenario: Missing redirect URI field is rejected

        Given a request body without a redirect_uri field (None)
        When validating the redirect URI
        Then validation should fail with error code "invalid_request"
        And error message "Redirect URI is required"
        """
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = None

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_request", f"Expected 'invalid_request', got '{error_code}'"
        assert error_message == "Redirect URI is required", f"Unexpected message: {error_message}"

    def test_whitespace_only_redirect_uri_rejected(self):
        """Redirect URI containing only whitespace should be rejected."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "   "

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri"
        assert error_message == "Redirect URI is required"


class TestRedirectUriValidatorUrlFormat:
    """Tests for URL format validation."""

    def test_invalid_url_format_rejected(self):
        """
        Scenario: Invalid URL format is rejected

        Given a redirect URI "not-a-valid-url"
        When validating the redirect URI
        Then validation should fail with error code "invalid_redirect_uri"
        And error message "Redirect URI must be a valid URL"
        """
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "not-a-valid-url"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri", f"Expected 'invalid_redirect_uri', got '{error_code}'"
        assert error_message == "Redirect URI must be a valid URL", f"Unexpected message: {error_message}"

    def test_malformed_url_rejected(self):
        """
        Scenario: Malformed URL is rejected

        Given a redirect URI "https://[invalid"
        When validating the redirect URI
        Then validation should fail with error code "invalid_redirect_uri"
        And error message "Redirect URI must be a valid URL"
        """
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "https://[invalid"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri", f"Expected 'invalid_redirect_uri', got '{error_code}'"
        assert error_message == "Redirect URI must be a valid URL", f"Unexpected message: {error_message}"

    def test_url_without_scheme_rejected(self):
        """URL without scheme should be rejected."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "myapp.example.com/oauth/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri"
        assert error_message == "Redirect URI must be a valid URL"

    def test_url_without_host_rejected(self):
        """URL without host should be rejected."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "https:///path/only"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri"
        assert error_message == "Redirect URI must be a valid URL"


class TestRedirectUriValidatorSchemeValidation:
    """Tests for URL scheme validation."""

    def test_http_non_localhost_rejected(self):
        """
        Scenario: HTTP non-localhost redirect URI is rejected

        Given a redirect URI "http://myapp.example.com/oauth/callback"
        When validating the redirect URI
        Then validation should fail with error code "invalid_redirect_uri"
        And error message "Redirect URI must use HTTPS (or HTTP for localhost)"
        """
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "http://myapp.example.com/oauth/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri", f"Expected 'invalid_redirect_uri', got '{error_code}'"
        assert error_message == "Redirect URI must use HTTPS (or HTTP for localhost)", f"Unexpected message: {error_message}"

    def test_ftp_scheme_rejected(self):
        """
        Scenario: FTP scheme redirect URI is rejected

        Given a redirect URI "ftp://myapp.example.com/oauth/callback"
        When validating the redirect URI
        Then validation should fail with error code "invalid_redirect_uri"
        And error message "Redirect URI must use HTTPS (or HTTP for localhost)"
        """
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "ftp://myapp.example.com/oauth/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri", f"Expected 'invalid_redirect_uri', got '{error_code}'"
        assert error_message == "Redirect URI must use HTTPS (or HTTP for localhost)", f"Unexpected message: {error_message}"

    def test_file_scheme_rejected(self):
        """File scheme should be rejected."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "file:///path/to/file"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri"
        assert error_message == "Redirect URI must use HTTPS (or HTTP for localhost)"

    def test_javascript_scheme_rejected(self):
        """JavaScript scheme should be rejected."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "javascript:alert('xss')"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri"
        # Could be either "must be a valid URL" or "must use HTTPS" depending on implementation

    def test_data_scheme_rejected(self):
        """Data scheme should be rejected."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "data:text/html,<script>alert('xss')</script>"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri"


class TestRedirectUriValidatorLengthValidation:
    """Tests for redirect URI length validation."""

    def test_redirect_uri_exceeding_max_length_rejected(self):
        """
        Scenario: Redirect URI exceeding maximum length is rejected

        Given a redirect URI that exceeds 2048 characters
        When validating the redirect URI
        Then validation should fail with error code "invalid_redirect_uri"
        And error message "Redirect URI must not exceed 2048 characters"
        """
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        # Create a URI that exceeds 2048 characters
        base_uri = "https://myapp.example.com/oauth/callback?data="
        padding = "a" * (2049 - len(base_uri))
        uri = base_uri + padding

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert len(uri) > 2048, f"Test URI should exceed 2048 chars, got {len(uri)}"
        assert error_code == "invalid_redirect_uri", f"Expected 'invalid_redirect_uri', got '{error_code}'"
        assert error_message == "Redirect URI must not exceed 2048 characters", f"Unexpected message: {error_message}"

    def test_redirect_uri_at_max_length_accepted(self):
        """Redirect URI at exactly 2048 characters should be accepted."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        # Create a URI that is exactly 2048 characters
        base_uri = "https://myapp.example.com/oauth/callback?data="
        padding = "a" * (2048 - len(base_uri))
        uri = base_uri + padding

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert len(uri) == 2048, f"Test URI should be exactly 2048 chars, got {len(uri)}"
        assert error_code is None, f"Expected no error code, got '{error_code}'"
        assert error_message is None, f"Expected no error message, got '{error_message}'"

    def test_redirect_uri_one_over_max_length_rejected(self):
        """Redirect URI at 2049 characters should be rejected."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        base_uri = "https://myapp.example.com/oauth/callback?data="
        padding = "a" * (2049 - len(base_uri))
        uri = base_uri + padding

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert len(uri) == 2049, f"Test URI should be 2049 chars, got {len(uri)}"
        assert error_code == "invalid_redirect_uri"
        assert error_message == "Redirect URI must not exceed 2048 characters"


class TestRedirectUriValidatorLocalhostVariants:
    """Tests for localhost variant handling."""

    def test_http_localhost_lowercase_accepted(self):
        """http://localhost should be accepted."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "http://localhost:3000/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_http_localhost_uppercase_accepted(self):
        """http://LOCALHOST should be accepted (case insensitive)."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "http://LOCALHOST:3000/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_http_localhost_mixed_case_accepted(self):
        """http://LocalHost should be accepted (case insensitive)."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "http://LocalHost:3000/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_http_127_0_0_1_any_port_accepted(self):
        """http://127.0.0.1 with any port should be accepted."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()

        # Test various ports
        for port in [80, 443, 3000, 8080, 9000]:
            uri = f"http://127.0.0.1:{port}/callback"

            # Act
            error_code, error_message = validator.validate(uri)

            # Assert
            assert error_code is None, f"Port {port} should be accepted"
            assert error_message is None

    def test_http_localhost_subdomain_rejected(self):
        """http://subdomain.localhost should be rejected (not true localhost)."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "http://subdomain.localhost:3000/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri"
        assert error_message == "Redirect URI must use HTTPS (or HTTP for localhost)"


class TestRedirectUriValidatorEdgeCases:
    """Edge case tests for redirect URI validation."""

    def test_valid_uri_with_numeric_port(self):
        """Valid URI with numeric port should be accepted."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "https://myapp.example.com:8443/oauth/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_valid_uri_with_ipv4_and_https(self):
        """Valid HTTPS URI with IPv4 address should be accepted."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "https://192.168.1.1/oauth/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_http_non_localhost_ipv4_rejected(self):
        """HTTP with non-localhost IPv4 should be rejected."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "http://192.168.1.1/oauth/callback"

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code == "invalid_redirect_uri"
        assert error_message == "Redirect URI must use HTTPS (or HTTP for localhost)"

    def test_valid_uri_with_unicode_domain(self):
        """Valid URI with unicode domain (IDN) should be handled."""
        from validators.redirect_uri_validator import RedirectUriValidator

        # Arrange
        validator = RedirectUriValidator()
        uri = "https://xn--nxasmq5b.example.com/callback"  # Punycode

        # Act
        error_code, error_message = validator.validate(uri)

        # Assert
        assert error_code is None
        assert error_message is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
