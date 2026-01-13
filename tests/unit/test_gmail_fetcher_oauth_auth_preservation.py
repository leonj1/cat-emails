"""
Tests for Gmail OAuth Auth Method Preservation.

TDD Red Phase Tests - These tests define the expected behavior for the
Gmail OAuth authentication method preservation feature.

Feature: Gmail OAuth Auth Method Preservation
- When connection_service is provided (OAuth): do NOT update auth_method
- When connection_service is NOT provided (IMAP): set auth_method='imap'

Bug Fix: Line 78 in gmail_fetcher_service.py currently always sets
auth_method='imap', corrupting OAuth accounts.

The fix should:
1. Use AuthMethodResolver to determine if OAuth or IMAP
2. Pass auth_method=None when OAuth (don't update)
3. Pass auth_method='imap' only when IMAP
"""
import unittest
from typing import Optional, Protocol
from unittest.mock import MagicMock, Mock, patch, PropertyMock


class AccountServiceProtocol(Protocol):
    """Protocol for account service to ensure mock compliance."""

    def get_or_create_account(
        self,
        email_address: str,
        display_name: Optional[str],
        app_password: Optional[str],
        auth_method: Optional[str],
        oauth_refresh_token: Optional[str],
    ) -> object:
        """Get or create an account."""
        ...


class TestGmailFetcherOAuthAuthMethodNotOverwritten(unittest.TestCase):
    """Tests for Scenario: OAuth account authentication method is not overwritten during processing.

    Given an account "oauth-user@gmail.com" is connected via OAuth
    And the account has auth_method "oauth"
    When the Gmail fetcher is created with a connection service for "oauth-user@gmail.com"
    Then the account service should not update the auth_method
    And the account "oauth-user@gmail.com" should still have auth_method "oauth"
    """

    def setUp(self):
        """Set up test fixtures with mocks."""
        # Mock AccountCategoryClient
        self.mock_account_client = MagicMock()
        self.mock_account_client.get_or_create_account = MagicMock()

        # Mock existing OAuth account
        self.mock_oauth_account = MagicMock()
        self.mock_oauth_account.email_address = "oauth-user@gmail.com"
        self.mock_oauth_account.auth_method = "oauth"
        self.mock_oauth_account.oauth_refresh_token = "existing-refresh-token"

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_oauth_account_auth_method_not_overwritten(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test that OAuth account auth_method is NOT updated when connection_service is provided.

        When a GmailFetcher is created with a connection_service (OAuth mode),
        the call to get_or_create_account should pass auth_method=None,
        NOT auth_method='imap'.

        This is the core fix for the bug at line 78.
        """
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange: Set up mock account service
        mock_account_service = MagicMock()
        mock_account_service.get_or_create_account.return_value = self.mock_oauth_account
        mock_account_client_class.return_value = mock_account_service

        # Set up mock connection service (indicates OAuth)
        mock_connection_service = MagicMock()

        # Act: Create GmailFetcher with connection_service (OAuth mode)
        fetcher = GmailFetcher(
            email_address="oauth-user@gmail.com",
            app_password="",  # OAuth doesn't use app password
            api_token="test-api-token",
            connection_service=mock_connection_service,
        )

        # Assert: get_or_create_account was called with auth_method=None
        mock_account_service.get_or_create_account.assert_called_once()
        call_args = mock_account_service.get_or_create_account.call_args

        # The auth_method argument should be None (don't update existing OAuth auth)
        # Arguments are: email_address, display_name, app_password, auth_method, oauth_refresh_token
        actual_auth_method = call_args[0][3]  # 4th positional argument

        self.assertIsNone(
            actual_auth_method,
            f"auth_method should be None when OAuth (connection_service provided), "
            f"but got '{actual_auth_method}'. This corrupts OAuth accounts to IMAP."
        )

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_oauth_account_app_password_not_overwritten(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test that app_password is NOT updated when connection_service is provided.

        For OAuth accounts, the app_password should also be passed as None
        to avoid overwriting any existing value.
        """
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange
        mock_account_service = MagicMock()
        mock_account_service.get_or_create_account.return_value = self.mock_oauth_account
        mock_account_client_class.return_value = mock_account_service

        mock_connection_service = MagicMock()

        # Act: Create GmailFetcher with connection_service (OAuth mode)
        fetcher = GmailFetcher(
            email_address="oauth-user@gmail.com",
            app_password="",
            api_token="test-api-token",
            connection_service=mock_connection_service,
        )

        # Assert: get_or_create_account was called with app_password=None
        call_args = mock_account_service.get_or_create_account.call_args
        # Arguments: email_address, display_name, app_password, auth_method, oauth_refresh_token
        actual_app_password = call_args[0][2]  # 3rd positional argument

        self.assertIsNone(
            actual_app_password,
            f"app_password should be None when OAuth to avoid overwriting existing values, "
            f"but got '{actual_app_password}'."
        )


class TestGmailFetcherIMAPAuthMethodSetCorrectly(unittest.TestCase):
    """Tests for Scenario: IMAP account authentication method is set correctly during processing.

    Given an account "imap-user@gmail.com" is configured for IMAP
    When the Gmail fetcher is created without a connection service for "imap-user@gmail.com"
    And an app password "test-app-password" is provided
    Then the account service should set auth_method to "imap"
    And the account should have the app_password stored
    """

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_imap_account_auth_method_set_to_imap(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test that IMAP account auth_method IS set to 'imap' when no connection_service.

        When a GmailFetcher is created WITHOUT a connection_service (IMAP mode),
        the call to get_or_create_account should pass auth_method='imap'.
        """
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange
        mock_account_service = MagicMock()
        mock_imap_account = MagicMock()
        mock_imap_account.email_address = "imap-user@gmail.com"
        mock_account_service.get_or_create_account.return_value = mock_imap_account
        mock_account_client_class.return_value = mock_account_service

        # Act: Create GmailFetcher WITHOUT connection_service (IMAP mode)
        fetcher = GmailFetcher(
            email_address="imap-user@gmail.com",
            app_password="test-app-password",
            api_token="test-api-token",
            connection_service=None,  # No connection service = IMAP mode
        )

        # Assert: get_or_create_account was called with auth_method='imap'
        call_args = mock_account_service.get_or_create_account.call_args
        # Arguments: email_address, display_name, app_password, auth_method, oauth_refresh_token
        actual_auth_method = call_args[0][3]

        self.assertEqual(
            actual_auth_method,
            "imap",
            f"auth_method should be 'imap' when no connection_service, "
            f"but got '{actual_auth_method}'."
        )

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_imap_account_app_password_stored(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test that IMAP account has app_password stored correctly.

        When creating an IMAP account, the app_password should be passed to
        get_or_create_account to be stored in the database.
        """
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange
        mock_account_service = MagicMock()
        mock_account_service.get_or_create_account.return_value = MagicMock()
        mock_account_client_class.return_value = mock_account_service

        # Act
        fetcher = GmailFetcher(
            email_address="imap-user@gmail.com",
            app_password="test-app-password",
            api_token="test-api-token",
            connection_service=None,
        )

        # Assert
        call_args = mock_account_service.get_or_create_account.call_args
        actual_app_password = call_args[0][2]

        self.assertEqual(
            actual_app_password,
            "test-app-password",
            f"app_password should be 'test-app-password', but got '{actual_app_password}'."
        )


class TestOAuthAccountRemainsAfterMultipleProcessingRuns(unittest.TestCase):
    """Tests for Scenario: OAuth account remains functional after multiple processing runs.

    Given an account "oauth-user@gmail.com" is connected via OAuth
    And the account has auth_method "oauth"
    When the Gmail fetcher processes emails for "oauth-user@gmail.com" with OAuth connection
    And the Gmail fetcher processes emails for "oauth-user@gmail.com" with OAuth connection again
    Then the account "oauth-user@gmail.com" should still have auth_method "oauth"
    And the account should remain functional
    """

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_oauth_account_survives_multiple_fetcher_creations(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test that OAuth auth_method is preserved across multiple GmailFetcher instances.

        Creating multiple GmailFetcher instances for the same OAuth account
        should never pass auth_method='imap' to get_or_create_account.
        """
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange
        mock_account_service = MagicMock()
        mock_oauth_account = MagicMock()
        mock_oauth_account.auth_method = "oauth"
        mock_account_service.get_or_create_account.return_value = mock_oauth_account
        mock_account_client_class.return_value = mock_account_service

        mock_connection_service = MagicMock()

        # Act: Create GmailFetcher twice (simulating multiple processing runs)
        fetcher1 = GmailFetcher(
            email_address="oauth-user@gmail.com",
            app_password="",
            api_token="test-api-token",
            connection_service=mock_connection_service,
        )

        fetcher2 = GmailFetcher(
            email_address="oauth-user@gmail.com",
            app_password="",
            api_token="test-api-token",
            connection_service=mock_connection_service,
        )

        # Assert: Both calls should have auth_method=None
        self.assertEqual(
            mock_account_service.get_or_create_account.call_count,
            2,
            "get_or_create_account should have been called twice"
        )

        for call_index, call in enumerate(mock_account_service.get_or_create_account.call_args_list):
            actual_auth_method = call[0][3]
            self.assertIsNone(
                actual_auth_method,
                f"Call {call_index + 1}: auth_method should be None for OAuth, "
                f"but got '{actual_auth_method}'."
            )


class TestNewIMAPAccountCreatedWithCorrectAuthMethod(unittest.TestCase):
    """Tests for Scenario: New IMAP account is created with correct auth method.

    Given no account exists for "new-imap@gmail.com"
    When the Gmail fetcher is created without a connection service for "new-imap@gmail.com"
    And an app password "new-app-password" is provided
    Then a new account should be created for "new-imap@gmail.com"
    And the new account should have auth_method "imap"
    And the new account should have the app_password stored
    """

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_new_imap_account_created_with_correct_values(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test that new IMAP accounts are created with auth_method='imap' and app_password."""
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange
        mock_account_service = MagicMock()
        new_account = MagicMock()
        new_account.email_address = "new-imap@gmail.com"
        new_account.auth_method = "imap"
        new_account.app_password = "new-app-password"
        mock_account_service.get_or_create_account.return_value = new_account
        mock_account_client_class.return_value = mock_account_service

        # Act
        fetcher = GmailFetcher(
            email_address="new-imap@gmail.com",
            app_password="new-app-password",
            api_token="test-api-token",
            connection_service=None,
        )

        # Assert
        call_args = mock_account_service.get_or_create_account.call_args

        # Verify all arguments
        actual_email = call_args[0][0]
        actual_app_password = call_args[0][2]
        actual_auth_method = call_args[0][3]

        self.assertEqual(actual_email, "new-imap@gmail.com")
        self.assertEqual(actual_app_password, "new-app-password")
        self.assertEqual(actual_auth_method, "imap")


class TestExistingOAuthAccountNotModified(unittest.TestCase):
    """Tests for Scenario: Existing OAuth account is not modified when processing with OAuth.

    Given an account "existing-oauth@gmail.com" exists with:
      | auth_method          | oauth                    |
      | oauth_refresh_token  | existing-refresh-token   |
    When the Gmail fetcher is created with a connection service for "existing-oauth@gmail.com"
    Then the account "existing-oauth@gmail.com" should retain:
      | auth_method          | oauth                    |
      | oauth_refresh_token  | existing-refresh-token   |
    """

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_existing_oauth_account_fields_preserved(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test that existing OAuth account's auth_method and refresh_token are preserved.

        When get_or_create_account is called with auth_method=None,
        it should NOT update the existing auth_method field.
        """
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange
        mock_account_service = MagicMock()
        existing_account = MagicMock()
        existing_account.email_address = "existing-oauth@gmail.com"
        existing_account.auth_method = "oauth"
        existing_account.oauth_refresh_token = "existing-refresh-token"
        mock_account_service.get_or_create_account.return_value = existing_account
        mock_account_client_class.return_value = mock_account_service

        mock_connection_service = MagicMock()

        # Act
        fetcher = GmailFetcher(
            email_address="existing-oauth@gmail.com",
            app_password="",
            api_token="test-api-token",
            connection_service=mock_connection_service,
        )

        # Assert: get_or_create_account called with None auth_method and None oauth_refresh_token
        call_args = mock_account_service.get_or_create_account.call_args
        actual_auth_method = call_args[0][3]
        actual_refresh_token = call_args[0][4]

        self.assertIsNone(
            actual_auth_method,
            f"auth_method should be None to preserve existing value, got '{actual_auth_method}'"
        )
        self.assertIsNone(
            actual_refresh_token,
            f"oauth_refresh_token should be None to preserve existing value, got '{actual_refresh_token}'"
        )


class TestHybridAccountTreatedAsOAuth(unittest.TestCase):
    """Tests for Scenario: Account with both OAuth token and app password is treated as OAuth.

    Given an account "hybrid@gmail.com" has:
      | auth_method          | oauth                    |
      | oauth_refresh_token  | valid-token              |
      | app_password         | legacy-password          |
    When the Gmail fetcher is created with a connection service for "hybrid@gmail.com"
    Then the account should be treated as an OAuth account
    And the auth_method should remain "oauth"
    """

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_hybrid_account_oauth_takes_precedence(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test that connection_service presence means OAuth, regardless of app_password.

        The presence of connection_service is the sole determinant of OAuth mode.
        Even if app_password is also provided, OAuth should take precedence.
        """
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange
        mock_account_service = MagicMock()
        hybrid_account = MagicMock()
        hybrid_account.email_address = "hybrid@gmail.com"
        hybrid_account.auth_method = "oauth"
        hybrid_account.oauth_refresh_token = "valid-token"
        hybrid_account.app_password = "legacy-password"
        mock_account_service.get_or_create_account.return_value = hybrid_account
        mock_account_client_class.return_value = mock_account_service

        mock_connection_service = MagicMock()

        # Act: Create fetcher with BOTH connection_service and app_password
        fetcher = GmailFetcher(
            email_address="hybrid@gmail.com",
            app_password="legacy-password",  # Legacy password also provided
            api_token="test-api-token",
            connection_service=mock_connection_service,  # OAuth mode
        )

        # Assert: OAuth takes precedence - auth_method should be None
        call_args = mock_account_service.get_or_create_account.call_args
        actual_auth_method = call_args[0][3]

        self.assertIsNone(
            actual_auth_method,
            f"When connection_service is provided, auth_method should be None "
            f"even if app_password is also provided. Got '{actual_auth_method}'."
        )


class TestAccountServiceFailureHandledGracefully(unittest.TestCase):
    """Tests for Scenario: Account service failure does not crash Gmail fetcher initialization.

    Given the account service is temporarily unavailable
    When the Gmail fetcher is created for "any-user@gmail.com"
    Then the Gmail fetcher should initialize successfully
    And a warning should be logged about account tracking being disabled
    And email processing should continue without account tracking
    """

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_account_service_failure_does_not_crash_fetcher(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test that GmailFetcher initializes even if AccountCategoryClient fails."""
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange: AccountCategoryClient constructor raises exception
        mock_account_client_class.side_effect = Exception("Database connection failed")

        # Act: Should not raise - should handle gracefully
        # If this raises, the test fails automatically
        _ = GmailFetcher(
            email_address="any-user@gmail.com",
            app_password="test-password",
            api_token="test-api-token",
            connection_service=None,
        )
        # If we reach here, initialization succeeded (graceful degradation)

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_account_service_failure_sets_service_to_none(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test that account_service is None when AccountCategoryClient fails."""
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange
        mock_account_client_class.side_effect = Exception("Database unavailable")

        # Act
        fetcher = GmailFetcher(
            email_address="any-user@gmail.com",
            app_password="test-password",
            api_token="test-api-token",
            connection_service=None,
        )

        # Assert
        self.assertIsNone(
            fetcher.account_service,
            "account_service should be None when initialization fails"
        )

    @patch('services.gmail_fetcher_service.logger')
    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_account_service_failure_logs_warning(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class,
        mock_logger
    ):
        """Test that a warning is logged when account service fails."""
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange
        mock_account_client_class.side_effect = Exception("Connection refused")

        # Act
        fetcher = GmailFetcher(
            email_address="any-user@gmail.com",
            app_password="test-password",
            api_token="test-api-token",
            connection_service=None,
        )

        # Assert: Warning about account tracking was logged
        warning_logged = False
        for call in mock_logger.warning.call_args_list:
            if "account" in str(call).lower() and "tracking" in str(call).lower():
                warning_logged = True
                break

        self.assertTrue(
            warning_logged,
            "A warning about account tracking being disabled should be logged"
        )


class TestInvalidConnectionServiceHandledGracefully(unittest.TestCase):
    """Tests for Scenario: Invalid connection service is handled gracefully.

    Given an account "user@gmail.com" is configured for OAuth
    When the Gmail fetcher is created with an invalid connection service
    Then the system should handle the error gracefully
    And an appropriate error should be logged
    """

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_fetcher_initializes_with_invalid_connection_service(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test that GmailFetcher initializes even with an invalid connection service.

        The invalid connection service should be stored, and errors will only
        occur when connect() is called.
        """
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange
        mock_account_service = MagicMock()
        mock_account_service.get_or_create_account.return_value = MagicMock()
        mock_account_client_class.return_value = mock_account_service

        # Invalid connection service that will fail when connect() is called
        invalid_connection_service = MagicMock()
        invalid_connection_service.connect.side_effect = Exception("Invalid OAuth token")

        # Act: Initialization should succeed
        try:
            fetcher = GmailFetcher(
                email_address="user@gmail.com",
                app_password="",
                api_token="test-api-token",
                connection_service=invalid_connection_service,
            )
            initialization_succeeded = True
        except Exception:
            initialization_succeeded = False

        # Assert
        self.assertTrue(
            initialization_succeeded,
            "GmailFetcher initialization should succeed even with invalid connection service"
        )

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_connection_with_invalid_service_raises_error(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test that connect() raises when connection service is invalid."""
        from services.gmail_fetcher_service import GmailFetcher

        # Arrange
        mock_account_service = MagicMock()
        mock_account_service.get_or_create_account.return_value = MagicMock()
        mock_account_client_class.return_value = mock_account_service

        invalid_connection_service = MagicMock()
        invalid_connection_service.connect.side_effect = Exception("Invalid OAuth credentials")

        fetcher = GmailFetcher(
            email_address="user@gmail.com",
            app_password="",
            api_token="test-api-token",
            connection_service=invalid_connection_service,
        )

        # Act & Assert: connect() should raise
        with self.assertRaises(Exception) as context:
            fetcher.connect()

        self.assertIn(
            "Invalid OAuth",
            str(context.exception),
            "Error message should indicate OAuth credential issue"
        )


class TestAuthMethodResolverIntegration(unittest.TestCase):
    """Tests that verify GmailFetcher uses AuthMethodResolver correctly.

    These tests verify the integration between GmailFetcher and
    AuthMethodResolver for determining auth_method values.
    """

    def test_auth_method_resolver_available(self):
        """Test that AuthMethodResolver can be imported."""
        from utils.auth_method_resolver import AuthMethodResolver, AuthMethodContext

        self.assertIsNotNone(AuthMethodResolver)
        self.assertIsNotNone(AuthMethodContext)

    def test_auth_method_resolver_oauth_detection(self):
        """Test that AuthMethodResolver correctly identifies OAuth mode."""
        from utils.auth_method_resolver import AuthMethodResolver

        mock_connection_service = MagicMock()

        context = AuthMethodResolver.resolve(
            connection_service=mock_connection_service,
            app_password=None,
        )

        self.assertTrue(context.is_oauth)
        self.assertIsNone(context.auth_method)
        self.assertFalse(context.should_update_auth_method)

    def test_auth_method_resolver_imap_detection(self):
        """Test that AuthMethodResolver correctly identifies IMAP mode."""
        from utils.auth_method_resolver import AuthMethodResolver

        context = AuthMethodResolver.resolve(
            connection_service=None,
            app_password="test-password",
        )

        self.assertFalse(context.is_oauth)
        self.assertEqual(context.auth_method, "imap")
        self.assertTrue(context.should_update_auth_method)


class TestGmailFetcherCallsGetOrCreateAccountCorrectly(unittest.TestCase):
    """Tests that verify the exact arguments passed to get_or_create_account.

    These tests ensure the fix at line 78 passes the correct arguments
    based on whether OAuth or IMAP mode is detected.
    """

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_oauth_mode_passes_correct_arguments(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test exact arguments for OAuth mode (connection_service provided)."""
        from services.gmail_fetcher_service import GmailFetcher

        mock_account_service = MagicMock()
        mock_account_service.get_or_create_account.return_value = MagicMock()
        mock_account_client_class.return_value = mock_account_service

        mock_connection_service = MagicMock()

        fetcher = GmailFetcher(
            email_address="oauth@gmail.com",
            app_password="ignored-password",
            api_token="test-api-token",
            connection_service=mock_connection_service,
        )

        # Verify exact call arguments
        call_args = mock_account_service.get_or_create_account.call_args
        args = call_args[0]

        expected_args = (
            "oauth@gmail.com",  # email_address
            None,               # display_name
            None,               # app_password (None for OAuth)
            None,               # auth_method (None = don't update)
            None,               # oauth_refresh_token (None = don't update)
        )

        self.assertEqual(
            args,
            expected_args,
            f"OAuth mode args mismatch.\nExpected: {expected_args}\nActual: {args}"
        )

    @patch('services.gmail_fetcher_service.AccountCategoryClient')
    @patch('services.gmail_fetcher_service.DomainService')
    @patch('services.gmail_fetcher_service.EmailSummaryService')
    @patch('services.gmail_fetcher_service.GmailConnectionService')
    def test_imap_mode_passes_correct_arguments(
        self,
        mock_connection_class,
        mock_summary_class,
        mock_domain_class,
        mock_account_client_class
    ):
        """Test exact arguments for IMAP mode (no connection_service)."""
        from services.gmail_fetcher_service import GmailFetcher

        mock_account_service = MagicMock()
        mock_account_service.get_or_create_account.return_value = MagicMock()
        mock_account_client_class.return_value = mock_account_service

        fetcher = GmailFetcher(
            email_address="imap@gmail.com",
            app_password="my-app-password",
            api_token="test-api-token",
            connection_service=None,
        )

        # Verify exact call arguments
        call_args = mock_account_service.get_or_create_account.call_args
        args = call_args[0]

        expected_args = (
            "imap@gmail.com",    # email_address
            None,                # display_name
            "my-app-password",   # app_password (stored for IMAP)
            "imap",              # auth_method = 'imap'
            None,                # oauth_refresh_token
        )

        self.assertEqual(
            args,
            expected_args,
            f"IMAP mode args mismatch.\nExpected: {expected_args}\nActual: {args}"
        )


if __name__ == '__main__':
    unittest.main()
