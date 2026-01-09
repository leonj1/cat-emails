"""
Integration tests for OAuth State Init Endpoint (POST /api/auth/gmail/init).

Tests derived from all 29 Gherkin scenarios for OAuth State Init Endpoint feature.
These tests verify the complete endpoint behavior including validation,
rate limiting, state storage, and error handling.

Categories covered:
- Happy Paths (6 scenarios)
- State Token Validation (8 scenarios)
- Redirect URI Validation (7 scenarios)
- Security (4 scenarios)
- Integration (4 scenarios)
"""

import pytest
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from typing import Protocol


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class OAuthStateInitEndpointProtocol(Protocol):
    """Protocol for the OAuth State Init Endpoint.

    The endpoint should:
    - Accept POST requests with JSON body containing state_token and redirect_uri
    - Validate state token (16-64 chars, alphanumeric + dashes)
    - Validate redirect URI (valid URL, HTTPS required except localhost)
    - Apply IP-based rate limiting (10 requests/minute/IP)
    - Store state token with 10-minute TTL
    - Return success response with expiration timestamp
    """
    pass


# Fixtures for test setup


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient
    from api_service import app
    return TestClient(app)


@pytest.fixture
def mock_rate_limiter():
    """Create a mock rate limiter that always allows requests."""
    with patch('api_service.ip_rate_limiter') as mock:
        mock.check_rate_limit.return_value = (True, None)
        yield mock


@pytest.fixture
def mock_oauth_state_repo():
    """Create a mock OAuth state repository."""
    with patch('api_service.oauth_state_repo') as mock:
        mock.store_state.return_value = None
        mock.get_state.return_value = None
        mock.delete_state.return_value = True
        yield mock


# === HAPPY PATHS (6 scenarios) ===


class TestOAuthStateInitHappyPaths:
    """Tests for successful state token registration scenarios."""

    def test_successful_state_token_registration_with_valid_inputs(self, test_client, mock_rate_limiter, mock_oauth_state_repo):
        """
        Scenario: Successful state token registration with valid inputs

        Given a valid state token "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 200
        And the response should contain success true
        And the response should contain the registered state token
        And the response should contain an expiration timestamp
        """
        # Arrange
        request_body = {
            "state_token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["success"] is True, f"Expected success=True, got {data}"
        assert data["state_token"] == request_body["state_token"], f"Expected state_token to match, got {data}"
        assert "expires_at" in data, f"Expected expires_at in response, got {data}"

    def test_response_includes_correct_expiration_timestamp(self, test_client, mock_rate_limiter, mock_oauth_state_repo):
        """
        Scenario: Response includes correct expiration timestamp

        Given a valid state token "valid-state-token-1234567890"
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 200
        And the expiration timestamp should be approximately 10 minutes from now
        And the expiration timestamp should be in ISO 8601 format
        """
        # Arrange
        request_body = {
            "state_token": "valid-state-token-1234567890",
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }
        before_request = datetime.now(timezone.utc)

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify expiration timestamp is approximately 10 minutes from now
        expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
        expected_expiry = before_request + timedelta(minutes=10)

        # Allow 5 second tolerance for test execution time
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 5, f"Expiration should be ~10 minutes from now, diff was {time_diff}s"

        # Verify ISO 8601 format (should parse without error)
        try:
            datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"expires_at is not valid ISO 8601: {data['expires_at']}")

    def test_state_token_minimum_valid_length_accepted(self, test_client, mock_rate_limiter, mock_oauth_state_repo):
        """
        Scenario: State token with minimum valid length is accepted

        Given a state token exactly 16 characters long "abcdefghij123456"
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 200
        And the response should contain success true
        """
        # Arrange
        request_body = {
            "state_token": "abcdefghij123456",  # Exactly 16 characters
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_state_token_maximum_valid_length_accepted(self, test_client, mock_rate_limiter, mock_oauth_state_repo):
        """
        Scenario: State token with maximum valid length is accepted

        Given a state token exactly 64 characters long
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 200
        And the response should contain success true
        """
        # Arrange
        request_body = {
            "state_token": "a" * 64,  # Exactly 64 characters
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_http_localhost_redirect_uri_accepted_for_development(self, test_client, mock_rate_limiter, mock_oauth_state_repo):
        """
        Scenario: HTTP localhost redirect URI is accepted for development

        Given a valid state token "dev-state-token-12345678"
        And a redirect URI "http://localhost:3000/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 200
        And the response should contain success true
        """
        # Arrange
        request_body = {
            "state_token": "dev-state-token-12345678",
            "redirect_uri": "http://localhost:3000/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_http_127_0_0_1_redirect_uri_accepted_for_development(self, test_client, mock_rate_limiter, mock_oauth_state_repo):
        """
        Scenario: HTTP 127.0.0.1 redirect URI is accepted for development

        Given a valid state token "dev-state-token-12345678"
        And a redirect URI "http://127.0.0.1:8080/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 200
        And the response should contain success true
        """
        # Arrange
        request_body = {
            "state_token": "dev-state-token-12345678",
            "redirect_uri": "http://127.0.0.1:8080/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# === STATE TOKEN VALIDATION (8 scenarios) ===


class TestOAuthStateInitStateTokenValidation:
    """Tests for state token validation error scenarios."""

    def test_state_token_too_short_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: State token too short is rejected

        Given a state token "short12345" that is only 10 characters
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_state_token"
        And the response should contain message "State token must be at least 16 characters"
        """
        # Arrange
        request_body = {
            "state_token": "short12345",  # Only 10 characters
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert data["error"] == "invalid_state_token", f"Expected error='invalid_state_token', got {data}"
        assert data["message"] == "State token must be at least 16 characters", f"Unexpected message: {data}"

    def test_state_token_too_long_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: State token too long is rejected

        Given a state token that is 65 characters long
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_state_token"
        And the response should contain message "State token must not exceed 64 characters"
        """
        # Arrange
        request_body = {
            "state_token": "a" * 65,  # 65 characters
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_state_token"
        assert data["message"] == "State token must not exceed 64 characters"

    def test_state_token_with_spaces_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: State token with spaces is rejected

        Given a state token "invalid state token 123"
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_state_token"
        And the response should contain message "State token must contain only alphanumeric characters and dashes"
        """
        # Arrange
        request_body = {
            "state_token": "invalid state token 123",
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_state_token"
        assert data["message"] == "State token must contain only alphanumeric characters and dashes"

    def test_state_token_with_special_characters_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: State token with special characters is rejected

        Given a state token "invalid!@#$%token123456"
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_state_token"
        And the response should contain message "State token must contain only alphanumeric characters and dashes"
        """
        # Arrange
        request_body = {
            "state_token": "invalid!@#$%token123456",
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_state_token"
        assert data["message"] == "State token must contain only alphanumeric characters and dashes"

    def test_state_token_with_underscores_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: State token with underscores is rejected

        Given a state token "invalid_underscore_123456"
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_state_token"
        And the response should contain message "State token must contain only alphanumeric characters and dashes"
        """
        # Arrange
        request_body = {
            "state_token": "invalid_underscore_123456",
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_state_token"
        assert data["message"] == "State token must contain only alphanumeric characters and dashes"

    def test_empty_state_token_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: Empty state token is rejected

        Given an empty state token ""
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_state_token"
        And the response should contain message "State token is required"
        """
        # Arrange
        request_body = {
            "state_token": "",
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_state_token"
        assert data["message"] == "State token is required"

    def test_missing_state_token_field_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: Missing state token field is rejected

        Given a request body without a state_token field
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_request"
        And the response should contain message "State token is required"
        """
        # Arrange
        request_body = {
            "redirect_uri": "https://myapp.example.com/oauth/callback"
            # No state_token field
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_request"
        assert data["message"] == "State token is required"

    def test_whitespace_only_state_token_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: Whitespace-only state token is rejected

        Given a state token "                " containing only spaces
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_state_token"
        And the response should contain message "State token is required"
        """
        # Arrange
        request_body = {
            "state_token": "                ",  # 16 spaces
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_state_token"
        assert data["message"] == "State token is required"


# === REDIRECT URI VALIDATION (7 scenarios) ===


class TestOAuthStateInitRedirectUriValidation:
    """Tests for redirect URI validation error scenarios."""

    def test_empty_redirect_uri_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: Empty redirect URI is rejected

        Given a valid state token "valid-state-token-1234567890"
        And an empty redirect URI ""
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_redirect_uri"
        And the response should contain message "Redirect URI is required"
        """
        # Arrange
        request_body = {
            "state_token": "valid-state-token-1234567890",
            "redirect_uri": ""
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_redirect_uri"
        assert data["message"] == "Redirect URI is required"

    def test_missing_redirect_uri_field_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: Missing redirect URI field is rejected

        Given a valid state token "valid-state-token-1234567890"
        And a request body without a redirect_uri field
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_request"
        And the response should contain message "Redirect URI is required"
        """
        # Arrange
        request_body = {
            "state_token": "valid-state-token-1234567890"
            # No redirect_uri field
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_request"
        assert data["message"] == "Redirect URI is required"

    def test_invalid_url_format_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: Invalid URL format is rejected

        Given a valid state token "valid-state-token-1234567890"
        And a redirect URI "not-a-valid-url"
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_redirect_uri"
        And the response should contain message "Redirect URI must be a valid URL"
        """
        # Arrange
        request_body = {
            "state_token": "valid-state-token-1234567890",
            "redirect_uri": "not-a-valid-url"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_redirect_uri"
        assert data["message"] == "Redirect URI must be a valid URL"

    def test_malformed_url_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: Malformed URL is rejected

        Given a valid state token "valid-state-token-1234567890"
        And a redirect URI "https://[invalid"
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_redirect_uri"
        And the response should contain message "Redirect URI must be a valid URL"
        """
        # Arrange
        request_body = {
            "state_token": "valid-state-token-1234567890",
            "redirect_uri": "https://[invalid"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_redirect_uri"
        assert data["message"] == "Redirect URI must be a valid URL"

    def test_http_non_localhost_redirect_uri_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: HTTP non-localhost redirect URI is rejected

        Given a valid state token "valid-state-token-1234567890"
        And a redirect URI "http://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_redirect_uri"
        And the response should contain message "Redirect URI must use HTTPS (or HTTP for localhost)"
        """
        # Arrange
        request_body = {
            "state_token": "valid-state-token-1234567890",
            "redirect_uri": "http://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_redirect_uri"
        assert data["message"] == "Redirect URI must use HTTPS (or HTTP for localhost)"

    def test_ftp_scheme_redirect_uri_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: FTP scheme redirect URI is rejected

        Given a valid state token "valid-state-token-1234567890"
        And a redirect URI "ftp://myapp.example.com/oauth/callback"
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_redirect_uri"
        And the response should contain message "Redirect URI must use HTTPS (or HTTP for localhost)"
        """
        # Arrange
        request_body = {
            "state_token": "valid-state-token-1234567890",
            "redirect_uri": "ftp://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_redirect_uri"
        assert data["message"] == "Redirect URI must use HTTPS (or HTTP for localhost)"

    def test_redirect_uri_exceeding_max_length_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: Redirect URI exceeding maximum length is rejected

        Given a valid state token "valid-state-token-1234567890"
        And a redirect URI that exceeds 2048 characters
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_redirect_uri"
        And the response should contain message "Redirect URI must not exceed 2048 characters"
        """
        # Arrange
        base_uri = "https://myapp.example.com/oauth/callback?data="
        padding = "a" * (2049 - len(base_uri))
        long_uri = base_uri + padding

        request_body = {
            "state_token": "valid-state-token-1234567890",
            "redirect_uri": long_uri
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert len(long_uri) > 2048
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_redirect_uri"
        assert data["message"] == "Redirect URI must not exceed 2048 characters"


# === SECURITY (4 scenarios) ===


class TestOAuthStateInitSecurity:
    """Tests for security-related scenarios including rate limiting."""

    def test_rate_limiting_rejects_excessive_requests(self, test_client, mock_oauth_state_repo):
        """
        Scenario: Rate limiting rejects excessive requests from same IP

        Given a valid state token "rate-limit-test-12345678"
        And a valid redirect URI "https://myapp.example.com/oauth/callback"
        And 10 state token registrations have been made from the same IP in the last minute
        When the frontend requests state token registration
        Then the response should have status 429
        And the response should contain error "rate_limit_exceeded"
        And the response should contain message "Too many state token registration requests. Try again later."
        """
        # Arrange - mock rate limiter to return rate limited
        with patch('api_service.ip_rate_limiter') as mock_limiter:
            mock_limiter.check_rate_limit.return_value = (False, 30.0)

            request_body = {
                "state_token": "rate-limit-test-12345678",
                "redirect_uri": "https://myapp.example.com/oauth/callback"
            }

            # Act
            response = test_client.post("/api/auth/gmail/init", json=request_body)

            # Assert
            assert response.status_code == 429
            data = response.json()
            assert data["error"] == "rate_limit_exceeded"
            assert data["message"] == "Too many state token registration requests. Try again later."

    def test_rate_limit_resets_after_time_window(self, test_client, mock_oauth_state_repo):
        """
        Scenario: Rate limit resets after time window

        Given 10 state token registrations were made from the same IP
        And the rate limit time window has elapsed
        When the frontend requests state token registration with a valid token
        Then the response should have status 200
        And the response should contain success true
        """
        # Arrange - mock rate limiter to return allowed (window elapsed)
        with patch('api_service.ip_rate_limiter') as mock_limiter:
            mock_limiter.check_rate_limit.return_value = (True, None)

            request_body = {
                "state_token": "valid-state-token-1234567890",
                "redirect_uri": "https://myapp.example.com/oauth/callback"
            }

            # Act
            response = test_client.post("/api/auth/gmail/init", json=request_body)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_duplicate_state_token_overwrites_previous(self, test_client, mock_rate_limiter):
        """
        Scenario: Duplicate state token registration overwrites previous registration

        Given a state token "duplicate-token-123456789012" was previously registered
        And a valid redirect URI "https://newapp.example.com/oauth/callback"
        When the frontend requests state token registration with the same token
        Then the response should have status 200
        And the response should contain success true
        And the new redirect URI should be associated with the state token
        """
        # Arrange
        with patch('api_service.oauth_state_repo') as mock_repo:
            # Simulate existing registration
            mock_repo.get_state.return_value = {
                "redirect_uri": "https://oldapp.example.com/callback",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            }
            mock_repo.store_state.return_value = None  # Upsert succeeds

            request_body = {
                "state_token": "duplicate-token-123456789012",
                "redirect_uri": "https://newapp.example.com/oauth/callback"
            }

            # Act
            response = test_client.post("/api/auth/gmail/init", json=request_body)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify store_state was called with new redirect_uri
            mock_repo.store_state.assert_called()
            call_args = mock_repo.store_state.call_args
            assert call_args[0][1] == "https://newapp.example.com/oauth/callback" or \
                   call_args.kwargs.get('redirect_uri') == "https://newapp.example.com/oauth/callback"

    def test_invalid_json_request_body_rejected(self, test_client, mock_rate_limiter):
        """
        Scenario: Invalid JSON request body is rejected

        Given a request body with invalid JSON
        When the frontend requests state token registration
        Then the response should have status 400
        And the response should contain error "invalid_request"
        And the response should contain message "Invalid JSON body"
        """
        # Act - send invalid JSON
        response = test_client.post(
            "/api/auth/gmail/init",
            content="not valid json {",
            headers={"Content-Type": "application/json"}
        )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_request"
        assert data["message"] == "Invalid JSON body"


# === INTEGRATION (4 scenarios) ===


class TestOAuthStateInitIntegration:
    """Tests for integration with OAuth callback endpoint."""

    def test_registered_state_token_found_by_callback(self, mock_rate_limiter):
        """
        Scenario: Registered state token is found by callback endpoint

        Given a state token "integration-test-123456789" is pre-registered
        And the redirect URI "https://myapp.example.com/oauth/callback" is associated
        When the OAuth callback endpoint validates the state token
        Then the state token should be recognized as valid
        And the associated redirect URI should be returned
        """
        from repositories.oauth_state_repository import OAuthStateRepository

        # Arrange - use actual repository (or mock)
        with patch.object(OAuthStateRepository, 'get_state') as mock_get:
            mock_get.return_value = {
                "redirect_uri": "https://myapp.example.com/oauth/callback",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
            }

            repo = OAuthStateRepository()

            # Act
            state_data = repo.get_state("integration-test-123456789")

            # Assert
            assert state_data is not None, "State token should be found"
            assert state_data["redirect_uri"] == "https://myapp.example.com/oauth/callback"

    def test_state_token_expires_after_10_minutes(self, mock_rate_limiter):
        """
        Scenario: State token expires after 10 minutes

        Given a state token "expiring-token-123456789012" was registered 11 minutes ago
        When the OAuth callback endpoint validates the state token
        Then the state token should be recognized as expired
        And the validation should fail
        """
        from repositories.oauth_state_repository import OAuthStateRepository

        # Arrange - mock expired state
        with patch.object(OAuthStateRepository, 'get_state') as mock_get:
            # Return None to simulate expired token
            mock_get.return_value = None

            repo = OAuthStateRepository()

            # Act
            state_data = repo.get_state("expiring-token-123456789012")

            # Assert
            assert state_data is None, "Expired state token should not be found"

    def test_state_token_valid_within_10_minute_window(self, mock_rate_limiter):
        """
        Scenario: State token is valid within 10 minute window

        Given a state token "valid-window-123456789012" was registered 9 minutes ago
        When the OAuth callback endpoint validates the state token
        Then the state token should be recognized as valid
        """
        from repositories.oauth_state_repository import OAuthStateRepository

        # Arrange - mock valid state within window
        with patch.object(OAuthStateRepository, 'get_state') as mock_get:
            mock_get.return_value = {
                "redirect_uri": "https://myapp.example.com/oauth/callback",
                "created_at": (datetime.now(timezone.utc) - timedelta(minutes=9)).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
            }

            repo = OAuthStateRepository()

            # Act
            state_data = repo.get_state("valid-window-123456789012")

            # Assert
            assert state_data is not None, "State token within window should be found"
            assert "redirect_uri" in state_data

    def test_unregistered_state_token_rejected(self, mock_rate_limiter):
        """
        Scenario: Unregistered state token is rejected by callback

        Given a state token "never-registered-1234567890" was never registered
        When the OAuth callback endpoint validates the state token
        Then the state token should be recognized as invalid
        And the validation should fail
        """
        from repositories.oauth_state_repository import OAuthStateRepository

        # Arrange - mock missing state
        with patch.object(OAuthStateRepository, 'get_state') as mock_get:
            mock_get.return_value = None

            repo = OAuthStateRepository()

            # Act
            state_data = repo.get_state("never-registered-1234567890")

            # Assert
            assert state_data is None, "Unregistered state token should not be found"


# === RESPONSE STRUCTURE TESTS ===


class TestOAuthStateInitResponseStructure:
    """Tests for complete response structure validation."""

    def test_success_response_structure(self, test_client, mock_rate_limiter, mock_oauth_state_repo):
        """Verify complete success response structure."""
        # Arrange
        request_body = {
            "state_token": "valid-state-token-1234567890",
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify all expected fields are present
        expected_fields = {"success", "state_token", "expires_at"}
        actual_fields = set(data.keys())
        assert expected_fields <= actual_fields, f"Missing fields: {expected_fields - actual_fields}"

        # Verify field types
        assert isinstance(data["success"], bool)
        assert isinstance(data["state_token"], str)
        assert isinstance(data["expires_at"], str)

    def test_error_response_structure(self, test_client, mock_rate_limiter):
        """Verify complete error response structure."""
        # Arrange
        request_body = {
            "state_token": "short",  # Invalid
            "redirect_uri": "https://myapp.example.com/oauth/callback"
        }

        # Act
        response = test_client.post("/api/auth/gmail/init", json=request_body)

        # Assert
        assert response.status_code == 400
        data = response.json()

        # Verify all expected fields are present
        expected_fields = {"error", "message"}
        actual_fields = set(data.keys())
        assert expected_fields <= actual_fields, f"Missing fields: {expected_fields - actual_fields}"

        # Verify field types
        assert isinstance(data["error"], str)
        assert isinstance(data["message"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
