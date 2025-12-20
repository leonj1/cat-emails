"""
Unit tests for GmailOAuthConnectionService.

Tests the OAuth 2.0 authentication flow for Gmail IMAP connections,
including token refresh, credential loading, and XOAUTH2 authentication.
"""
import base64
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch


class TestGmailOAuthConnectionServiceExists(unittest.TestCase):
    """Tests that the OAuth connection service class exists and is importable."""

    def test_service_class_exists(self):
        """Test that GmailOAuthConnectionService class exists."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        self.assertTrue(
            callable(GmailOAuthConnectionService),
            "GmailOAuthConnectionService should be a callable class"
        )

    def test_service_implements_interface(self):
        """Test that GmailOAuthConnectionService implements GmailConnectionInterface."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService
        from services.gmail_connection_interface import GmailConnectionInterface

        service = GmailOAuthConnectionService(
            email_address="test@gmail.com",
            client_id="test_client_id",
            client_secret="test_secret",
            refresh_token="test_refresh_token",
        )

        self.assertIsInstance(
            service,
            GmailConnectionInterface,
            "GmailOAuthConnectionService should implement GmailConnectionInterface"
        )

    def test_service_has_connect_method(self):
        """Test that GmailOAuthConnectionService has connect method."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        service = GmailOAuthConnectionService(
            email_address="test@gmail.com",
            client_id="test_client_id",
            client_secret="test_secret",
            refresh_token="test_refresh_token",
        )

        self.assertTrue(
            hasattr(service, 'connect'),
            "GmailOAuthConnectionService should have connect method"
        )
        self.assertTrue(
            callable(service.connect),
            "connect should be callable"
        )


class TestGmailOAuthConnectionServiceInit(unittest.TestCase):
    """Tests for GmailOAuthConnectionService initialization."""

    def test_init_with_direct_credentials(self):
        """Test initialization with directly provided credentials."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        service = GmailOAuthConnectionService(
            email_address="user@gmail.com",
            client_id="my_client_id",
            client_secret="my_client_secret",
            refresh_token="my_refresh_token",
        )

        self.assertEqual(service.email_address, "user@gmail.com")
        self.assertEqual(service.client_id, "my_client_id")
        self.assertEqual(service.client_secret, "my_client_secret")
        self.assertEqual(service.refresh_token, "my_refresh_token")

    def test_init_with_env_vars(self):
        """Test initialization with environment variables."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        with patch.dict(os.environ, {
            "GMAIL_OAUTH_CLIENT_ID": "env_client_id",
            "GMAIL_OAUTH_CLIENT_SECRET": "env_client_secret",
            "GMAIL_OAUTH_REFRESH_TOKEN": "env_refresh_token",
        }):
            service = GmailOAuthConnectionService(email_address="user@gmail.com")

            self.assertEqual(service.client_id, "env_client_id")
            self.assertEqual(service.client_secret, "env_client_secret")
            self.assertEqual(service.refresh_token, "env_refresh_token")

    def test_direct_credentials_override_env_vars(self):
        """Test that directly provided credentials override environment variables."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        with patch.dict(os.environ, {
            "GMAIL_OAUTH_CLIENT_ID": "env_client_id",
            "GMAIL_OAUTH_CLIENT_SECRET": "env_client_secret",
            "GMAIL_OAUTH_REFRESH_TOKEN": "env_refresh_token",
        }):
            service = GmailOAuthConnectionService(
                email_address="user@gmail.com",
                client_id="direct_client_id",
            )

            self.assertEqual(service.client_id, "direct_client_id")
            self.assertEqual(service.client_secret, "env_client_secret")


class TestCredentialsFileLoading(unittest.TestCase):
    """Tests for loading credentials from JSON files."""

    def test_load_credentials_from_installed_format(self):
        """Test loading credentials from Google's 'installed' app format."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        credentials_data = {
            "installed": {
                "client_id": "file_client_id",
                "client_secret": "file_client_secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(credentials_data, f)
            creds_file = f.name

        try:
            service = GmailOAuthConnectionService(
                email_address="user@gmail.com",
                credentials_file=creds_file,
                refresh_token="test_refresh",
            )

            self.assertEqual(service.client_id, "file_client_id")
            self.assertEqual(service.client_secret, "file_client_secret")
        finally:
            os.unlink(creds_file)

    def test_load_credentials_from_web_format(self):
        """Test loading credentials from Google's 'web' app format."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        credentials_data = {
            "web": {
                "client_id": "web_client_id",
                "client_secret": "web_client_secret",
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(credentials_data, f)
            creds_file = f.name

        try:
            service = GmailOAuthConnectionService(
                email_address="user@gmail.com",
                credentials_file=creds_file,
                refresh_token="test_refresh",
            )

            self.assertEqual(service.client_id, "web_client_id")
            self.assertEqual(service.client_secret, "web_client_secret")
        finally:
            os.unlink(creds_file)

    def test_load_token_from_file(self):
        """Test loading refresh token from token.json file."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        token_data = {
            "refresh_token": "file_refresh_token",
            "access_token": "file_access_token",
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(token_data, f)
            token_file = f.name

        try:
            service = GmailOAuthConnectionService(
                email_address="user@gmail.com",
                client_id="test_id",
                client_secret="test_secret",
                token_file=token_file,
            )

            self.assertEqual(service.refresh_token, "file_refresh_token")
        finally:
            os.unlink(token_file)

    def test_missing_credentials_file_logs_warning(self):
        """Test that missing credentials file logs a warning but doesn't crash."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        # Should not raise an exception
        service = GmailOAuthConnectionService(
            email_address="user@gmail.com",
            credentials_file="/nonexistent/path/credentials.json",
            refresh_token="test_refresh",
            client_id="fallback_id",
            client_secret="fallback_secret",
        )

        self.assertEqual(service.client_id, "fallback_id")


class TestCredentialValidation(unittest.TestCase):
    """Tests for credential validation."""

    def test_missing_client_id_raises_error_on_connect(self):
        """Test that missing client_id raises ValueError when connecting."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        with patch.dict(os.environ, {}, clear=True):
            service = GmailOAuthConnectionService(
                email_address="user@gmail.com",
                client_secret="secret",
                refresh_token="token",
            )

            with self.assertRaises(ValueError) as context:
                service._validate_credentials()

            self.assertIn("client_id", str(context.exception))

    def test_missing_client_secret_raises_error_on_connect(self):
        """Test that missing client_secret raises ValueError when connecting."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        with patch.dict(os.environ, {}, clear=True):
            service = GmailOAuthConnectionService(
                email_address="user@gmail.com",
                client_id="client_id",
                refresh_token="token",
            )

            with self.assertRaises(ValueError) as context:
                service._validate_credentials()

            self.assertIn("client_secret", str(context.exception))

    def test_missing_refresh_token_raises_error_on_connect(self):
        """Test that missing refresh_token raises ValueError when connecting."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        service = GmailOAuthConnectionService(
            email_address="user@gmail.com",
            client_id="client_id",
            client_secret="secret",
        )

        with self.assertRaises(ValueError) as context:
            service._validate_credentials()

        self.assertIn("refresh_token", str(context.exception))

    def test_all_credentials_present_passes_validation(self):
        """Test that complete credentials pass validation."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        service = GmailOAuthConnectionService(
            email_address="user@gmail.com",
            client_id="client_id",
            client_secret="secret",
            refresh_token="token",
        )

        # Should not raise
        service._validate_credentials()


class TestOAuth2StringGeneration(unittest.TestCase):
    """Tests for XOAUTH2 string generation."""

    def test_generate_oauth2_string_format(self):
        """Test that XOAUTH2 string is generated in correct format."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        service = GmailOAuthConnectionService(
            email_address="user@gmail.com",
            client_id="test_id",
            client_secret="test_secret",
            refresh_token="test_token",
        )

        access_token = "ya29.test_access_token"
        oauth2_string = service._generate_oauth2_string(access_token)

        # Decode and verify format
        decoded = base64.b64decode(oauth2_string).decode("utf-8")
        expected = f"user=user@gmail.com\x01auth=Bearer {access_token}\x01\x01"

        self.assertEqual(decoded, expected)

    def test_oauth2_string_is_base64_encoded(self):
        """Test that XOAUTH2 string is properly base64 encoded."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService
        import binascii

        service = GmailOAuthConnectionService(
            email_address="test@example.com",
            client_id="test_id",
            client_secret="test_secret",
            refresh_token="test_token",
        )

        oauth2_string = service._generate_oauth2_string("access_token_123")

        # Should be valid base64
        try:
            decoded = base64.b64decode(oauth2_string)
            self.assertIsInstance(decoded, bytes)
        except (binascii.Error, ValueError) as e:
            self.fail(f"OAuth2 string should be valid base64: {e}")


class TestTokenRefresh(unittest.TestCase):
    """Tests for OAuth token refresh functionality."""

    @patch('urllib.request.urlopen')
    def test_refresh_access_token_success(self, mock_urlopen):
        """Test successful token refresh."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        # Mock successful token response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "access_token": "new_access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        service = GmailOAuthConnectionService(
            email_address="user@gmail.com",
            client_id="test_client_id",
            client_secret="test_client_secret",
            refresh_token="test_refresh_token",
        )

        access_token = service._refresh_access_token()

        self.assertEqual(access_token, "new_access_token")
        self.assertEqual(service._access_token, "new_access_token")

    @patch('urllib.request.urlopen')
    def test_refresh_token_request_contains_correct_params(self, mock_urlopen):
        """Test that token refresh request contains correct parameters."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService
        import urllib.parse

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "access_token": "new_token",
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        service = GmailOAuthConnectionService(
            email_address="user@gmail.com",
            client_id="my_client_id",
            client_secret="my_client_secret",
            refresh_token="my_refresh_token",
        )

        service._refresh_access_token()

        # Verify the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]

        self.assertEqual(request.full_url, "https://oauth2.googleapis.com/token")

        # Parse the request data
        request_data = urllib.parse.parse_qs(request.data.decode("utf-8"))

        self.assertEqual(request_data["client_id"][0], "my_client_id")
        self.assertEqual(request_data["client_secret"][0], "my_client_secret")
        self.assertEqual(request_data["refresh_token"][0], "my_refresh_token")
        self.assertEqual(request_data["grant_type"][0], "refresh_token")

    @patch('urllib.request.urlopen')
    def test_refresh_token_failure_raises_exception(self, mock_urlopen):
        """Test that token refresh failure raises an exception."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService
        import urllib.error

        # Mock HTTP error response
        mock_error = urllib.error.HTTPError(
            url="https://oauth2.googleapis.com/token",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=MagicMock(read=lambda: b'{"error": "invalid_grant"}'),
        )
        mock_urlopen.side_effect = mock_error

        service = GmailOAuthConnectionService(
            email_address="user@gmail.com",
            client_id="test_client_id",
            client_secret="test_client_secret",
            refresh_token="invalid_refresh_token",
        )

        with self.assertRaises(Exception) as context:
            service._refresh_access_token()

        self.assertIn("OAuth token refresh failed", str(context.exception))


class TestConnect(unittest.TestCase):
    """Tests for the connect method."""

    @patch('services.gmail_oauth_connection_service.GmailOAuthConnectionService._refresh_access_token')
    @patch('imaplib.IMAP4_SSL')
    def test_connect_returns_imap_connection(self, mock_imap, mock_refresh):
        """Test that connect returns an IMAP4 connection object."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        mock_refresh.return_value = "test_access_token"

        mock_conn = MagicMock()
        mock_conn.authenticate.return_value = ("OK", [b"Success"])
        mock_imap.return_value = mock_conn

        service = GmailOAuthConnectionService(
            email_address="user@gmail.com",
            client_id="test_id",
            client_secret="test_secret",
            refresh_token="test_token",
        )

        result = service.connect()

        self.assertEqual(result, mock_conn)

    @patch('services.gmail_oauth_connection_service.GmailOAuthConnectionService._refresh_access_token')
    @patch('imaplib.IMAP4_SSL')
    def test_connect_uses_xoauth2_authentication(self, mock_imap, mock_refresh):
        """Test that connect uses XOAUTH2 authentication mechanism."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        mock_refresh.return_value = "test_access_token"

        mock_conn = MagicMock()
        mock_conn.authenticate.return_value = ("OK", [b"Success"])
        mock_imap.return_value = mock_conn

        service = GmailOAuthConnectionService(
            email_address="user@gmail.com",
            client_id="test_id",
            client_secret="test_secret",
            refresh_token="test_token",
        )

        service.connect()

        # Verify XOAUTH2 was used
        mock_conn.authenticate.assert_called_once()
        call_args = mock_conn.authenticate.call_args
        self.assertEqual(call_args[0][0], "XOAUTH2")

    @patch('services.gmail_oauth_connection_service.GmailOAuthConnectionService._refresh_access_token')
    @patch('imaplib.IMAP4_SSL')
    def test_connect_uses_correct_server_and_port(self, mock_imap, mock_refresh):
        """Test that connect uses correct IMAP server and port."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        mock_refresh.return_value = "test_access_token"

        mock_conn = MagicMock()
        mock_conn.authenticate.return_value = ("OK", [b"Success"])
        mock_imap.return_value = mock_conn

        service = GmailOAuthConnectionService(
            email_address="user@gmail.com",
            client_id="test_id",
            client_secret="test_secret",
            refresh_token="test_token",
        )

        service.connect()

        mock_imap.assert_called_once_with("imap.gmail.com", 993)

    @patch('services.gmail_oauth_connection_service.GmailOAuthConnectionService._refresh_access_token')
    @patch('imaplib.IMAP4_SSL')
    def test_connect_authentication_failure_raises_exception(self, mock_imap, mock_refresh):
        """Test that authentication failure raises an exception."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService
        import imaplib

        mock_refresh.return_value = "test_access_token"

        mock_conn = MagicMock()
        mock_conn.authenticate.side_effect = imaplib.IMAP4.error("Invalid credentials")
        mock_imap.return_value = mock_conn

        service = GmailOAuthConnectionService(
            email_address="user@gmail.com",
            client_id="test_id",
            client_secret="test_secret",
            refresh_token="test_token",
        )

        with self.assertRaises(Exception) as context:
            service.connect()

        self.assertIn("OAuth authentication failed", str(context.exception))


class TestConstants(unittest.TestCase):
    """Tests for service constants."""

    def test_token_uri_is_google_oauth(self):
        """Test that TOKEN_URI points to Google's OAuth endpoint."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        self.assertEqual(
            GmailOAuthConnectionService.TOKEN_URI,
            "https://oauth2.googleapis.com/token"
        )

    def test_imap_server_is_gmail(self):
        """Test that IMAP_SERVER is Gmail's IMAP server."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        self.assertEqual(
            GmailOAuthConnectionService.IMAP_SERVER,
            "imap.gmail.com"
        )

    def test_imap_port_is_993(self):
        """Test that IMAP_PORT is 993 (IMAPS)."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        self.assertEqual(
            GmailOAuthConnectionService.IMAP_PORT,
            993
        )

    def test_scopes_include_gmail_full_access(self):
        """Test that SCOPES include full Gmail access."""
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        self.assertIn(
            "https://mail.google.com/",
            GmailOAuthConnectionService.SCOPES
        )


if __name__ == '__main__':
    unittest.main()
