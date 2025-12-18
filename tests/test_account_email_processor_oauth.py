"""
Tests for OAuth support in AccountEmailProcessorService.

Tests that the processor correctly handles OAuth-authenticated accounts.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

# Set mock API key before any imports that may trigger api_service loading
os.environ.setdefault('REQUESTYAI_API_KEY', 'test_api_key_for_unit_test')


class TestAccountEmailProcessorOAuthSupport(unittest.TestCase):
    """Test cases for OAuth support in AccountEmailProcessorService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_status_manager = MagicMock()
        self.mock_settings_service = MagicMock()
        self.mock_settings_service.get_lookback_hours.return_value = 24
        self.mock_email_categorizer = MagicMock()
        self.mock_account_client = MagicMock()
        self.mock_dedup_factory = MagicMock()

    def _create_processor(self, create_gmail_fetcher=None):
        """Create a processor instance for testing."""
        from services.account_email_processor_service import AccountEmailProcessorService

        return AccountEmailProcessorService(
            processing_status_manager=self.mock_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.mock_email_categorizer,
            api_token="test_api_token",
            llm_model="test_model",
            account_category_client=self.mock_account_client,
            deduplication_factory=self.mock_dedup_factory,
            create_gmail_fetcher=create_gmail_fetcher,
        )

    def test_process_account_detects_oauth_auth_method(self):
        """Test that processor detects OAuth auth method from account.

        This test verifies the processor's OAuth detection logic by testing:
        1. The processor correctly identifies auth_method='oauth'
        2. The processor uses GmailConnectionFactory.create_connection with OAuth params
        """
        # Create mock OAuth account
        mock_account = MagicMock()
        mock_account.auth_method = 'oauth'
        mock_account.oauth_refresh_token = 'test_refresh_token'
        mock_account.app_password = None

        self.mock_account_client.get_account_by_email.return_value = mock_account

        # Mock the fetcher creation to verify OAuth path
        mock_fetcher = MagicMock()
        mock_fetcher.summary_service = MagicMock()
        mock_fetcher.account_service = MagicMock()
        mock_fetcher.get_blocked_domains.return_value = set()
        mock_fetcher.connection_service = None  # Will be replaced with OAuth connection

        fetcher_calls = []

        def mock_create_fetcher(email, password, api_token, connection_service=None):
            fetcher_calls.append({'email': email, 'password': password, 'connection_service': connection_service})
            return mock_fetcher

        processor = self._create_processor(create_gmail_fetcher=mock_create_fetcher)

        # Mock connection factory - patch before it's imported in process_account
        with patch('services.gmail_connection_factory.GmailConnectionFactory') as mock_factory:
            mock_connection = MagicMock()
            mock_factory.create_connection.return_value = mock_connection

            # Should not raise for missing app_password when using OAuth
            result = processor.process_account("oauth_user@gmail.com")

            # Verify processing succeeded
            self.assertIsNotNone(result)
            self.assertTrue(result.get('success', False), "Processing should succeed for OAuth account")

            # Verify the fetcher was created with refresh_token as password (OAuth flow)
            self.assertEqual(len(fetcher_calls), 1)
            self.assertEqual(fetcher_calls[0]['email'], "oauth_user@gmail.com")
            self.assertEqual(fetcher_calls[0]['password'], 'test_refresh_token')

            # Verify OAuth connection was created via factory
            mock_factory.create_connection.assert_called_once_with(
                email_address="oauth_user@gmail.com",
                auth_method='oauth',
                refresh_token='test_refresh_token',
            )

    def test_process_account_imap_fallback(self):
        """Test that processor uses IMAP for non-OAuth accounts."""
        # Create mock IMAP account
        mock_account = MagicMock()
        mock_account.auth_method = 'imap'
        mock_account.app_password = 'test_app_password'
        mock_account.oauth_refresh_token = None

        self.mock_account_client.get_account_by_email.return_value = mock_account

        mock_fetcher = MagicMock()
        mock_fetcher.summary_service = MagicMock()
        mock_fetcher.account_service = MagicMock()
        mock_fetcher.get_blocked_domains.return_value = set()

        fetcher_calls = []

        def mock_create_fetcher(email, password, api_token):
            fetcher_calls.append((email, password, api_token))
            return mock_fetcher

        processor = self._create_processor(create_gmail_fetcher=mock_create_fetcher)

        processor.process_account("imap_user@gmail.com")

        # Verify IMAP fetcher was created with password
        self.assertEqual(len(fetcher_calls), 1)
        self.assertEqual(fetcher_calls[0][0], "imap_user@gmail.com")
        self.assertEqual(fetcher_calls[0][1], "test_app_password")

    def test_process_account_missing_oauth_token_returns_error(self):
        """Test that missing OAuth refresh token returns error."""
        # Create mock OAuth account without refresh token
        mock_account = MagicMock()
        mock_account.auth_method = 'oauth'
        mock_account.oauth_refresh_token = None
        mock_account.app_password = None

        self.mock_account_client.get_account_by_email.return_value = mock_account

        processor = self._create_processor()

        result = processor.process_account("oauth_user@gmail.com")

        self.assertFalse(result['success'])
        self.assertIn('No OAuth refresh token', result['error'])

    def test_process_account_missing_app_password_returns_error(self):
        """Test that missing app password for IMAP returns error."""
        # Create mock IMAP account without password
        mock_account = MagicMock()
        mock_account.auth_method = 'imap'
        mock_account.app_password = None
        mock_account.oauth_refresh_token = None

        self.mock_account_client.get_account_by_email.return_value = mock_account

        processor = self._create_processor()

        result = processor.process_account("imap_user@gmail.com")

        self.assertFalse(result['success'])
        self.assertIn('No app password', result['error'])

    def test_process_account_default_auth_method_is_imap(self):
        """Test that accounts without auth_method default to IMAP."""
        # Create mock account without auth_method attribute
        mock_account = MagicMock(spec=['email_address', 'app_password'])
        mock_account.email_address = "old_user@gmail.com"
        mock_account.app_password = "old_password"
        # auth_method attribute doesn't exist, getattr should return 'imap'

        self.mock_account_client.get_account_by_email.return_value = mock_account

        mock_fetcher = MagicMock()
        mock_fetcher.summary_service = MagicMock()
        mock_fetcher.account_service = MagicMock()
        mock_fetcher.get_blocked_domains.return_value = set()

        fetcher_calls = []

        def mock_create_fetcher(email, password, api_token):
            fetcher_calls.append((email, password, api_token))
            return mock_fetcher

        processor = self._create_processor(create_gmail_fetcher=mock_create_fetcher)

        processor.process_account("old_user@gmail.com")

        # Should use IMAP flow (password-based)
        self.assertEqual(len(fetcher_calls), 1)
        self.assertEqual(fetcher_calls[0][1], "old_password")

    def test_process_account_none_auth_method_treated_as_imap(self):
        """Test that None auth_method is treated as IMAP."""
        mock_account = MagicMock()
        mock_account.auth_method = None
        mock_account.app_password = "test_password"

        self.mock_account_client.get_account_by_email.return_value = mock_account

        mock_fetcher = MagicMock()
        mock_fetcher.summary_service = MagicMock()
        mock_fetcher.account_service = MagicMock()
        mock_fetcher.get_blocked_domains.return_value = set()

        fetcher_calls = []

        def mock_create_fetcher(email, password, api_token):
            fetcher_calls.append((email, password, api_token))
            return mock_fetcher

        processor = self._create_processor(create_gmail_fetcher=mock_create_fetcher)

        processor.process_account("user@gmail.com")

        # Should use IMAP flow
        self.assertEqual(len(fetcher_calls), 1)


class TestProcessorOAuthConnectionFactory(unittest.TestCase):
    """Tests for OAuth connection factory integration."""

    def test_gmail_connection_factory_supports_oauth(self):
        """Test that GmailConnectionFactory supports OAuth auth method."""
        from services.gmail_connection_factory import GmailConnectionFactory, GmailAuthMethod

        self.assertIn('oauth', GmailAuthMethod.all_methods())

    def test_gmail_connection_factory_create_oauth_connection(self):
        """Test that factory can create OAuth connection with parameters."""
        from services.gmail_connection_factory import GmailConnectionFactory

        with patch('services.gmail_connection_factory.GmailOAuthConnectionService') as mock_oauth:
            mock_oauth.return_value = MagicMock()

            connection = GmailConnectionFactory.create_connection(
                email_address="user@gmail.com",
                auth_method="oauth",
                refresh_token="test_refresh_token",
            )

            # Verify connection was created
            self.assertIsNotNone(connection)

            mock_oauth.assert_called_once()
            call_kwargs = mock_oauth.call_args[1]
            self.assertEqual(call_kwargs['email_address'], "user@gmail.com")
            self.assertEqual(call_kwargs['refresh_token'], "test_refresh_token")


if __name__ == '__main__':
    unittest.main()
