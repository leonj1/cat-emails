"""
Unit tests for OAuthFlowService.

Tests the OAuth 2.0 consent flow for multi-user Gmail API authorization,
including authorization URL generation, token exchange, and revocation.
"""
import json
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


class TestOAuthFlowServiceExists(unittest.TestCase):
    """Tests that the OAuth flow service class exists and is importable."""

    def test_service_class_exists(self):
        """Test that OAuthFlowService class exists."""
        from services.oauth_flow_service import OAuthFlowService

        self.assertTrue(
            callable(OAuthFlowService),
            "OAuthFlowService should be a callable class"
        )

    def test_service_has_required_methods(self):
        """Test that OAuthFlowService has all required methods."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_secret",
        )

        required_methods = [
            'generate_state_token',
            'generate_authorization_url',
            'exchange_code_for_tokens',
            'refresh_access_token',
            'revoke_token',
            'calculate_token_expiry',
            'parse_scopes',
        ]

        for method in required_methods:
            self.assertTrue(
                hasattr(service, method),
                f"OAuthFlowService should have {method} method"
            )
            self.assertTrue(
                callable(getattr(service, method)),
                f"{method} should be callable"
            )


class TestOAuthFlowServiceInit(unittest.TestCase):
    """Tests for OAuthFlowService initialization."""

    def test_init_with_direct_credentials(self):
        """Test initialization with directly provided credentials."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="my_client_id",
            client_secret="my_client_secret",
        )

        self.assertEqual(service.client_id, "my_client_id")
        self.assertEqual(service.client_secret, "my_client_secret")

    def test_init_with_env_vars(self):
        """Test initialization with environment variables."""
        from services.oauth_flow_service import OAuthFlowService

        with patch.dict(os.environ, {
            "GMAIL_OAUTH_CLIENT_ID": "env_client_id",
            "GMAIL_OAUTH_CLIENT_SECRET": "env_client_secret",
        }):
            service = OAuthFlowService()

            self.assertEqual(service.client_id, "env_client_id")
            self.assertEqual(service.client_secret, "env_client_secret")

    def test_direct_credentials_override_env_vars(self):
        """Test that directly provided credentials override environment variables."""
        from services.oauth_flow_service import OAuthFlowService

        with patch.dict(os.environ, {
            "GMAIL_OAUTH_CLIENT_ID": "env_client_id",
            "GMAIL_OAUTH_CLIENT_SECRET": "env_client_secret",
        }):
            service = OAuthFlowService(client_id="direct_client_id")

            self.assertEqual(service.client_id, "direct_client_id")
            self.assertEqual(service.client_secret, "env_client_secret")


class TestStateTokenGeneration(unittest.TestCase):
    """Tests for state token generation."""

    def test_generate_state_token_returns_string(self):
        """Test that generate_state_token returns a string."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_id",
            client_secret="test_secret",
        )

        state = service.generate_state_token()

        self.assertIsInstance(state, str)
        self.assertTrue(len(state) > 0)

    def test_generate_state_token_is_unique(self):
        """Test that generate_state_token produces unique values."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_id",
            client_secret="test_secret",
        )

        states = [service.generate_state_token() for _ in range(100)]
        unique_states = set(states)

        self.assertEqual(len(states), len(unique_states))

    def test_generate_state_token_sufficient_length(self):
        """Test that state token has sufficient entropy."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_id",
            client_secret="test_secret",
        )

        state = service.generate_state_token()

        # Should be at least 32 characters for security
        self.assertGreaterEqual(len(state), 32)


class TestAuthorizationUrlGeneration(unittest.TestCase):
    """Tests for authorization URL generation."""

    def test_generate_authorization_url_contains_base_url(self):
        """Test that authorization URL contains Google's OAuth endpoint."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_secret",
        )

        url = service.generate_authorization_url(
            redirect_uri="https://example.com/callback",
            state="test_state",
        )

        self.assertIn("https://accounts.google.com/o/oauth2/v2/auth", url)

    def test_generate_authorization_url_contains_client_id(self):
        """Test that authorization URL contains client_id parameter."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_secret",
        )

        url = service.generate_authorization_url(
            redirect_uri="https://example.com/callback",
            state="test_state",
        )

        self.assertIn("client_id=test_client_id", url)

    def test_generate_authorization_url_contains_redirect_uri(self):
        """Test that authorization URL contains redirect_uri parameter."""
        from services.oauth_flow_service import OAuthFlowService
        from urllib.parse import quote

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_secret",
        )

        redirect_uri = "https://example.com/callback"
        url = service.generate_authorization_url(
            redirect_uri=redirect_uri,
            state="test_state",
        )

        self.assertIn(f"redirect_uri={quote(redirect_uri, safe='')}", url)

    def test_generate_authorization_url_contains_state(self):
        """Test that authorization URL contains state parameter."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_secret",
        )

        url = service.generate_authorization_url(
            redirect_uri="https://example.com/callback",
            state="my_unique_state",
        )

        self.assertIn("state=my_unique_state", url)

    def test_generate_authorization_url_contains_required_scopes(self):
        """Test that authorization URL contains required Gmail scopes."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_secret",
        )

        url = service.generate_authorization_url(
            redirect_uri="https://example.com/callback",
            state="test_state",
        )

        # URL-encoded scopes should be present
        self.assertIn("scope=", url)
        self.assertIn("gmail.readonly", url)

    def test_generate_authorization_url_requests_offline_access(self):
        """Test that authorization URL requests offline access for refresh token."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_secret",
        )

        url = service.generate_authorization_url(
            redirect_uri="https://example.com/callback",
            state="test_state",
        )

        self.assertIn("access_type=offline", url)

    def test_generate_authorization_url_with_login_hint(self):
        """Test that authorization URL includes login_hint when provided."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_secret",
        )

        url = service.generate_authorization_url(
            redirect_uri="https://example.com/callback",
            state="test_state",
            login_hint="user@gmail.com",
        )

        self.assertIn("login_hint=user%40gmail.com", url)

    def test_generate_authorization_url_missing_credentials_raises_error(self):
        """Test that missing credentials raise ValueError."""
        from services.oauth_flow_service import OAuthFlowService

        with patch.dict(os.environ, {}, clear=True):
            service = OAuthFlowService()

            with self.assertRaises(ValueError) as context:
                service.generate_authorization_url(
                    redirect_uri="https://example.com/callback",
                    state="test_state",
                )

            self.assertIn("Missing OAuth", str(context.exception))


class TestTokenExchange(unittest.TestCase):
    """Tests for authorization code exchange."""

    @patch('urllib.request.urlopen')
    def test_exchange_code_for_tokens_success(self, mock_urlopen):
        """Test successful token exchange."""
        from services.oauth_flow_service import OAuthFlowService

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/gmail.readonly",
            "token_type": "Bearer",
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        result = service.exchange_code_for_tokens(
            code="authorization_code",
            redirect_uri="https://example.com/callback",
        )

        self.assertEqual(result["access_token"], "new_access_token")
        self.assertEqual(result["refresh_token"], "new_refresh_token")
        self.assertEqual(result["expires_in"], 3600)

    @patch('urllib.request.urlopen')
    def test_exchange_code_request_contains_correct_params(self, mock_urlopen):
        """Test that token exchange request contains correct parameters."""
        from services.oauth_flow_service import OAuthFlowService
        import urllib.parse

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "access_token": "token",
            "refresh_token": "refresh",
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        service = OAuthFlowService(
            client_id="my_client_id",
            client_secret="my_client_secret",
        )

        service.exchange_code_for_tokens(
            code="auth_code_123",
            redirect_uri="https://example.com/callback",
        )

        call_args = mock_urlopen.call_args
        request = call_args[0][0]

        self.assertEqual(request.full_url, "https://oauth2.googleapis.com/token")

        request_data = urllib.parse.parse_qs(request.data.decode("utf-8"))

        self.assertEqual(request_data["client_id"][0], "my_client_id")
        self.assertEqual(request_data["client_secret"][0], "my_client_secret")
        self.assertEqual(request_data["code"][0], "auth_code_123")
        self.assertEqual(request_data["grant_type"][0], "authorization_code")

    @patch('urllib.request.urlopen')
    def test_exchange_code_failure_raises_exception(self, mock_urlopen):
        """Test that token exchange failure raises an exception."""
        from services.oauth_flow_service import OAuthFlowService
        import urllib.error

        mock_error = urllib.error.HTTPError(
            url="https://oauth2.googleapis.com/token",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=MagicMock(read=lambda: b'{"error": "invalid_grant"}'),
        )
        mock_urlopen.side_effect = mock_error

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        with self.assertRaises(ValueError) as context:
            service.exchange_code_for_tokens(
                code="invalid_code",
                redirect_uri="https://example.com/callback",
            )

        self.assertIn("Failed to exchange", str(context.exception))


class TestTokenRefresh(unittest.TestCase):
    """Tests for access token refresh."""

    @patch('urllib.request.urlopen')
    def test_refresh_access_token_success(self, mock_urlopen):
        """Test successful token refresh."""
        from services.oauth_flow_service import OAuthFlowService

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "access_token": "refreshed_access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        result = service.refresh_access_token("my_refresh_token")

        self.assertEqual(result["access_token"], "refreshed_access_token")


class TestTokenRevocation(unittest.TestCase):
    """Tests for token revocation."""

    @patch('urllib.request.urlopen')
    def test_revoke_token_success(self, mock_urlopen):
        """Test successful token revocation."""
        from services.oauth_flow_service import OAuthFlowService

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        result = service.revoke_token("token_to_revoke")

        self.assertTrue(result)

    @patch('urllib.request.urlopen')
    def test_revoke_token_already_revoked_returns_true(self, mock_urlopen):
        """Test that revoking already-revoked token returns True."""
        from services.oauth_flow_service import OAuthFlowService
        import urllib.error

        mock_error = urllib.error.HTTPError(
            url="https://oauth2.googleapis.com/revoke",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=MagicMock(read=lambda: b'{"error": "invalid_token"}'),
        )
        mock_urlopen.side_effect = mock_error

        service = OAuthFlowService(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        result = service.revoke_token("already_revoked_token")

        # 400 error for invalid token should return True
        self.assertTrue(result)


class TestHelperMethods(unittest.TestCase):
    """Tests for helper methods."""

    def test_calculate_token_expiry(self):
        """Test token expiry calculation."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_id",
            client_secret="test_secret",
        )

        before = datetime.utcnow()
        expiry = service.calculate_token_expiry(3600)
        after = datetime.utcnow()

        expected_min = before + timedelta(seconds=3600)
        expected_max = after + timedelta(seconds=3600)

        self.assertGreaterEqual(expiry, expected_min)
        self.assertLessEqual(expiry, expected_max)

    def test_parse_scopes_space_separated(self):
        """Test parsing space-separated scopes."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_id",
            client_secret="test_secret",
        )

        scopes = service.parse_scopes(
            "https://www.googleapis.com/auth/gmail.readonly "
            "https://www.googleapis.com/auth/gmail.labels"
        )

        self.assertEqual(len(scopes), 2)
        self.assertIn("https://www.googleapis.com/auth/gmail.readonly", scopes)
        self.assertIn("https://www.googleapis.com/auth/gmail.labels", scopes)

    def test_parse_scopes_empty_string(self):
        """Test parsing empty scope string."""
        from services.oauth_flow_service import OAuthFlowService

        service = OAuthFlowService(
            client_id="test_id",
            client_secret="test_secret",
        )

        scopes = service.parse_scopes("")

        self.assertEqual(scopes, [])


class TestConstants(unittest.TestCase):
    """Tests for service constants."""

    def test_google_auth_url(self):
        """Test that GOOGLE_AUTH_URL is correct."""
        from services.oauth_flow_service import OAuthFlowService

        self.assertEqual(
            OAuthFlowService.GOOGLE_AUTH_URL,
            "https://accounts.google.com/o/oauth2/v2/auth"
        )

    def test_google_token_url(self):
        """Test that GOOGLE_TOKEN_URL is correct."""
        from services.oauth_flow_service import OAuthFlowService

        self.assertEqual(
            OAuthFlowService.GOOGLE_TOKEN_URL,
            "https://oauth2.googleapis.com/token"
        )

    def test_required_scopes_include_gmail_permissions(self):
        """Test that REQUIRED_SCOPES include necessary Gmail permissions."""
        from services.oauth_flow_service import OAuthFlowService

        scopes = OAuthFlowService.REQUIRED_SCOPES

        self.assertIn("https://www.googleapis.com/auth/gmail.readonly", scopes)
        self.assertIn("https://www.googleapis.com/auth/gmail.labels", scopes)
        self.assertIn("https://www.googleapis.com/auth/gmail.modify", scopes)


if __name__ == '__main__':
    unittest.main()
