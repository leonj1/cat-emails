"""
Unit tests for GmailConnectionFactory.

Tests the factory pattern for creating Gmail connection services
based on authentication method (IMAP vs OAuth 2.0).
"""
import os
import unittest
from unittest.mock import patch, MagicMock


class TestGmailAuthMethodConstants(unittest.TestCase):
    """Tests for GmailAuthMethod constants."""

    def test_auth_method_class_exists(self):
        """Test that GmailAuthMethod class exists."""
        from services.gmail_connection_factory import GmailAuthMethod

        self.assertTrue(hasattr(GmailAuthMethod, 'IMAP'))
        self.assertTrue(hasattr(GmailAuthMethod, 'OAUTH'))

    def test_imap_constant_value(self):
        """Test that IMAP constant has correct value."""
        from services.gmail_connection_factory import GmailAuthMethod

        self.assertEqual(GmailAuthMethod.IMAP, "imap")

    def test_oauth_constant_value(self):
        """Test that OAUTH constant has correct value."""
        from services.gmail_connection_factory import GmailAuthMethod

        self.assertEqual(GmailAuthMethod.OAUTH, "oauth")

    def test_all_methods_returns_list(self):
        """Test that all_methods returns list of valid methods."""
        from services.gmail_connection_factory import GmailAuthMethod

        methods = GmailAuthMethod.all_methods()

        self.assertIsInstance(methods, list)
        self.assertIn("imap", methods)
        self.assertIn("oauth", methods)
        self.assertEqual(len(methods), 2)


class TestGmailConnectionFactoryExists(unittest.TestCase):
    """Tests that the factory class exists and is importable."""

    def test_factory_class_exists(self):
        """Test that GmailConnectionFactory class exists."""
        from services.gmail_connection_factory import GmailConnectionFactory

        self.assertTrue(
            callable(GmailConnectionFactory.create_connection),
            "GmailConnectionFactory should have create_connection method"
        )

    def test_factory_has_get_auth_method(self):
        """Test that factory has get_auth_method method."""
        from services.gmail_connection_factory import GmailConnectionFactory

        self.assertTrue(
            hasattr(GmailConnectionFactory, 'get_auth_method'),
            "GmailConnectionFactory should have get_auth_method method"
        )


class TestGetAuthMethod(unittest.TestCase):
    """Tests for get_auth_method functionality."""

    def test_default_auth_method_is_imap(self):
        """Test that default authentication method is IMAP."""
        from services.gmail_connection_factory import GmailConnectionFactory

        # Clear env var if set
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GMAIL_AUTH_METHOD", None)

            method = GmailConnectionFactory.get_auth_method()

            self.assertEqual(
                method,
                "imap",
                "Default auth method should be 'imap'"
            )

    def test_imap_auth_method_from_env(self):
        """Test reading IMAP auth method from environment."""
        from services.gmail_connection_factory import GmailConnectionFactory

        with patch.dict(os.environ, {"GMAIL_AUTH_METHOD": "imap"}):
            method = GmailConnectionFactory.get_auth_method()

            self.assertEqual(method, "imap")

    def test_oauth_auth_method_from_env(self):
        """Test reading OAuth auth method from environment."""
        from services.gmail_connection_factory import GmailConnectionFactory

        with patch.dict(os.environ, {"GMAIL_AUTH_METHOD": "oauth"}):
            method = GmailConnectionFactory.get_auth_method()

            self.assertEqual(method, "oauth")

    def test_auth_method_case_insensitive(self):
        """Test that auth method is case insensitive."""
        from services.gmail_connection_factory import GmailConnectionFactory

        test_cases = ["OAUTH", "OAuth", "oAuth", "IMAP", "Imap", "ImAp"]

        for value in test_cases:
            with patch.dict(os.environ, {"GMAIL_AUTH_METHOD": value}):
                method = GmailConnectionFactory.get_auth_method()
                self.assertEqual(
                    method,
                    value.lower(),
                    f"'{value}' should be normalized to '{value.lower()}'"
                )

    def test_invalid_auth_method_defaults_to_imap(self):
        """Test that invalid auth method defaults to IMAP."""
        from services.gmail_connection_factory import GmailConnectionFactory

        with patch.dict(os.environ, {"GMAIL_AUTH_METHOD": "invalid_method"}):
            method = GmailConnectionFactory.get_auth_method()

            self.assertEqual(
                method,
                "imap",
                "Invalid auth method should default to 'imap'"
            )

    def test_whitespace_in_auth_method_is_stripped(self):
        """Test that whitespace in auth method is stripped."""
        from services.gmail_connection_factory import GmailConnectionFactory

        with patch.dict(os.environ, {"GMAIL_AUTH_METHOD": "  oauth  "}):
            method = GmailConnectionFactory.get_auth_method()

            self.assertEqual(method, "oauth")


class TestCreateConnectionIMAP(unittest.TestCase):
    """Tests for creating IMAP connections."""

    def test_create_imap_connection_returns_correct_type(self):
        """Test that IMAP auth method returns GmailConnectionService."""
        from services.gmail_connection_factory import GmailConnectionFactory
        from services.gmail_connection_service import GmailConnectionService

        with patch.dict(os.environ, {"GMAIL_AUTH_METHOD": "imap"}):
            connection = GmailConnectionFactory.create_connection(
                email_address="test@gmail.com",
                password="test_password",
            )

            self.assertIsInstance(
                connection,
                GmailConnectionService,
                "IMAP auth should return GmailConnectionService"
            )

    def test_create_imap_connection_with_explicit_method(self):
        """Test creating IMAP connection with explicit auth_method parameter."""
        from services.gmail_connection_factory import GmailConnectionFactory
        from services.gmail_connection_service import GmailConnectionService

        connection = GmailConnectionFactory.create_connection(
            email_address="test@gmail.com",
            password="test_password",
            auth_method="imap",
        )

        self.assertIsInstance(connection, GmailConnectionService)

    def test_create_imap_connection_passes_credentials(self):
        """Test that IMAP connection receives correct credentials."""
        from services.gmail_connection_factory import GmailConnectionFactory

        connection = GmailConnectionFactory.create_connection(
            email_address="user@gmail.com",
            password="my_app_password",
            imap_server="custom.imap.server",
            auth_method="imap",
        )

        self.assertEqual(connection.email_address, "user@gmail.com")
        self.assertEqual(connection.password, "my_app_password")
        self.assertEqual(connection.imap_server, "custom.imap.server")

    def test_create_imap_connection_uses_env_password(self):
        """Test that IMAP connection falls back to env var for password."""
        from services.gmail_connection_factory import GmailConnectionFactory

        with patch.dict(os.environ, {"GMAIL_PASSWORD": "env_password"}):
            connection = GmailConnectionFactory.create_connection(
                email_address="user@gmail.com",
                auth_method="imap",
            )

            self.assertEqual(connection.password, "env_password")

    def test_create_imap_connection_missing_password_raises_error(self):
        """Test that missing password raises ValueError."""
        from services.gmail_connection_factory import GmailConnectionFactory

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GMAIL_PASSWORD", None)

            with self.assertRaises(ValueError) as context:
                GmailConnectionFactory.create_connection(
                    email_address="user@gmail.com",
                    auth_method="imap",
                )

            self.assertIn("password", str(context.exception).lower())


class TestCreateConnectionOAuth(unittest.TestCase):
    """Tests for creating OAuth connections."""

    def test_create_oauth_connection_returns_correct_type(self):
        """Test that OAuth auth method returns GmailOAuthConnectionService."""
        from services.gmail_connection_factory import GmailConnectionFactory
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        with patch.dict(os.environ, {
            "GMAIL_AUTH_METHOD": "oauth",
            "GMAIL_OAUTH_CLIENT_ID": "test_id",
            "GMAIL_OAUTH_CLIENT_SECRET": "test_secret",
            "GMAIL_OAUTH_REFRESH_TOKEN": "test_token",
        }):
            connection = GmailConnectionFactory.create_connection(
                email_address="test@gmail.com",
            )

            self.assertIsInstance(
                connection,
                GmailOAuthConnectionService,
                "OAuth auth should return GmailOAuthConnectionService"
            )

    def test_create_oauth_connection_with_explicit_method(self):
        """Test creating OAuth connection with explicit auth_method parameter."""
        from services.gmail_connection_factory import GmailConnectionFactory
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        connection = GmailConnectionFactory.create_connection(
            email_address="test@gmail.com",
            client_id="test_id",
            client_secret="test_secret",
            refresh_token="test_token",
            auth_method="oauth",
        )

        self.assertIsInstance(connection, GmailOAuthConnectionService)

    def test_create_oauth_connection_passes_credentials(self):
        """Test that OAuth connection receives correct credentials."""
        from services.gmail_connection_factory import GmailConnectionFactory

        connection = GmailConnectionFactory.create_connection(
            email_address="user@gmail.com",
            client_id="my_client_id",
            client_secret="my_client_secret",
            refresh_token="my_refresh_token",
            auth_method="oauth",
        )

        self.assertEqual(connection.email_address, "user@gmail.com")
        self.assertEqual(connection.client_id, "my_client_id")
        self.assertEqual(connection.client_secret, "my_client_secret")
        self.assertEqual(connection.refresh_token, "my_refresh_token")

    def test_create_oauth_connection_with_file_paths(self):
        """Test creating OAuth connection with file paths."""
        from services.gmail_connection_factory import GmailConnectionFactory

        connection = GmailConnectionFactory.create_connection(
            email_address="user@gmail.com",
            credentials_file="/path/to/credentials.json",
            token_file="/path/to/token.json",
            auth_method="oauth",
        )

        self.assertEqual(connection.credentials_file, "/path/to/credentials.json")
        self.assertEqual(connection.token_file, "/path/to/token.json")


class TestAuthMethodOverride(unittest.TestCase):
    """Tests for auth_method parameter overriding environment variable."""

    def test_explicit_oauth_overrides_env_imap(self):
        """Test that explicit oauth overrides env var set to imap."""
        from services.gmail_connection_factory import GmailConnectionFactory
        from services.gmail_oauth_connection_service import GmailOAuthConnectionService

        with patch.dict(os.environ, {"GMAIL_AUTH_METHOD": "imap"}):
            connection = GmailConnectionFactory.create_connection(
                email_address="test@gmail.com",
                client_id="test_id",
                client_secret="test_secret",
                refresh_token="test_token",
                auth_method="oauth",
            )

            self.assertIsInstance(connection, GmailOAuthConnectionService)

    def test_explicit_imap_overrides_env_oauth(self):
        """Test that explicit imap overrides env var set to oauth."""
        from services.gmail_connection_factory import GmailConnectionFactory
        from services.gmail_connection_service import GmailConnectionService

        with patch.dict(os.environ, {"GMAIL_AUTH_METHOD": "oauth"}):
            connection = GmailConnectionFactory.create_connection(
                email_address="test@gmail.com",
                password="test_password",
                auth_method="imap",
            )

            self.assertIsInstance(connection, GmailConnectionService)


class TestDefaultAuthMethod(unittest.TestCase):
    """Tests for default authentication method constant."""

    def test_default_auth_method_is_imap(self):
        """Test that DEFAULT_AUTH_METHOD is 'imap'."""
        from services.gmail_connection_factory import GmailConnectionFactory

        self.assertEqual(
            GmailConnectionFactory.DEFAULT_AUTH_METHOD,
            "imap",
            "DEFAULT_AUTH_METHOD should be 'imap'"
        )


class TestInterfaceCompliance(unittest.TestCase):
    """Tests that created connections implement the interface."""

    def test_imap_connection_implements_interface(self):
        """Test that IMAP connection implements GmailConnectionInterface."""
        from services.gmail_connection_factory import GmailConnectionFactory
        from services.gmail_connection_interface import GmailConnectionInterface

        connection = GmailConnectionFactory.create_connection(
            email_address="test@gmail.com",
            password="test_password",
            auth_method="imap",
        )

        self.assertIsInstance(connection, GmailConnectionInterface)

    def test_oauth_connection_implements_interface(self):
        """Test that OAuth connection implements GmailConnectionInterface."""
        from services.gmail_connection_factory import GmailConnectionFactory
        from services.gmail_connection_interface import GmailConnectionInterface

        connection = GmailConnectionFactory.create_connection(
            email_address="test@gmail.com",
            client_id="test_id",
            client_secret="test_secret",
            refresh_token="test_token",
            auth_method="oauth",
        )

        self.assertIsInstance(connection, GmailConnectionInterface)

    def test_both_connections_have_connect_method(self):
        """Test that both connection types have connect method."""
        from services.gmail_connection_factory import GmailConnectionFactory

        imap_conn = GmailConnectionFactory.create_connection(
            email_address="test@gmail.com",
            password="test_password",
            auth_method="imap",
        )

        oauth_conn = GmailConnectionFactory.create_connection(
            email_address="test@gmail.com",
            client_id="test_id",
            client_secret="test_secret",
            refresh_token="test_token",
            auth_method="oauth",
        )

        self.assertTrue(hasattr(imap_conn, 'connect'))
        self.assertTrue(callable(imap_conn.connect))
        self.assertTrue(hasattr(oauth_conn, 'connect'))
        self.assertTrue(callable(oauth_conn.connect))


if __name__ == '__main__':
    unittest.main()
