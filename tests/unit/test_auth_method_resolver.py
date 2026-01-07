"""
Tests for Auth Method Resolution Logic.

TDD Red Phase Tests - These tests define the expected behavior for the
AuthMethodResolver utility that determines authentication context based
on connection type.

Feature: Auth Method Resolution Logic
- Determines OAuth vs IMAP authentication based on connection_service presence
- Connection service present = OAuth (don't update auth_method/app_password)
- No connection service = IMAP (set auth_method='imap', preserve app_password)

The implementation should create:
1. AuthMethodContext dataclass with auth resolution results
2. AuthMethodResolver class with resolve() method
"""
import unittest
from typing import Optional, Protocol
from dataclasses import dataclass
from unittest.mock import MagicMock


class TestAuthMethodResolverImport(unittest.TestCase):
    """Tests that verify AuthMethodResolver module can be imported.

    These tests will fail until the implementation is created at:
    utils/auth_method_resolver.py
    """

    def test_auth_method_resolver_module_exists(self):
        """Test that auth_method_resolver module exists and is importable.

        The implementation should create utils/auth_method_resolver.py with:
        - AuthMethodContext dataclass
        - AuthMethodResolver class
        """
        from utils.auth_method_resolver import AuthMethodResolver

        self.assertIsNotNone(AuthMethodResolver)

    def test_auth_method_context_exists(self):
        """Test that AuthMethodContext dataclass exists and is importable.

        The implementation should define AuthMethodContext with fields:
        - has_connection_service: bool
        - is_oauth: bool
        - should_update_auth_method: bool
        - auth_method: Optional[str]
        - app_password: Optional[str]
        """
        from utils.auth_method_resolver import AuthMethodContext

        self.assertIsNotNone(AuthMethodContext)


class TestAuthMethodContextStructure(unittest.TestCase):
    """Tests that verify AuthMethodContext has the correct structure.

    AuthMethodContext should be a dataclass with these fields:
    - has_connection_service: bool - Whether a connection_service was provided
    - is_oauth: bool - Whether this is an OAuth authentication
    - should_update_auth_method: bool - Whether to update auth_method in DB
    - auth_method: Optional[str] - The auth_method value to set (or None)
    - app_password: Optional[str] - The app_password value to set (or None)
    """

    def test_context_has_connection_service_field(self):
        """Test that AuthMethodContext has has_connection_service field."""
        from utils.auth_method_resolver import AuthMethodContext

        # Create a minimal context to verify field exists
        context = AuthMethodContext(
            has_connection_service=True,
            is_oauth=True,
            should_update_auth_method=False,
            auth_method=None,
            app_password=None,
        )

        self.assertTrue(hasattr(context, 'has_connection_service'))
        self.assertIsInstance(context.has_connection_service, bool)

    def test_context_has_is_oauth_field(self):
        """Test that AuthMethodContext has is_oauth field."""
        from utils.auth_method_resolver import AuthMethodContext

        context = AuthMethodContext(
            has_connection_service=True,
            is_oauth=True,
            should_update_auth_method=False,
            auth_method=None,
            app_password=None,
        )

        self.assertTrue(hasattr(context, 'is_oauth'))
        self.assertIsInstance(context.is_oauth, bool)

    def test_context_has_should_update_auth_method_field(self):
        """Test that AuthMethodContext has should_update_auth_method field."""
        from utils.auth_method_resolver import AuthMethodContext

        context = AuthMethodContext(
            has_connection_service=True,
            is_oauth=True,
            should_update_auth_method=False,
            auth_method=None,
            app_password=None,
        )

        self.assertTrue(hasattr(context, 'should_update_auth_method'))
        self.assertIsInstance(context.should_update_auth_method, bool)

    def test_context_has_auth_method_field(self):
        """Test that AuthMethodContext has auth_method field."""
        from utils.auth_method_resolver import AuthMethodContext

        context = AuthMethodContext(
            has_connection_service=False,
            is_oauth=False,
            should_update_auth_method=True,
            auth_method="imap",
            app_password="password123",
        )

        self.assertTrue(hasattr(context, 'auth_method'))

    def test_context_has_app_password_field(self):
        """Test that AuthMethodContext has app_password field."""
        from utils.auth_method_resolver import AuthMethodContext

        context = AuthMethodContext(
            has_connection_service=False,
            is_oauth=False,
            should_update_auth_method=True,
            auth_method="imap",
            app_password="my-app-password",
        )

        self.assertTrue(hasattr(context, 'app_password'))


class TestAuthMethodResolverStructure(unittest.TestCase):
    """Tests that verify AuthMethodResolver has the correct methods."""

    def test_resolver_has_resolve_method(self):
        """Test that AuthMethodResolver has a resolve class method.

        The resolve method should accept:
        - connection_service: Optional[Any] - The OAuth connection service or None
        - app_password: Optional[str] - The app password for IMAP auth

        And return an AuthMethodContext with the resolution result.
        """
        from utils.auth_method_resolver import AuthMethodResolver

        self.assertTrue(
            hasattr(AuthMethodResolver, 'resolve'),
            "AuthMethodResolver should have a 'resolve' method"
        )
        self.assertTrue(
            callable(AuthMethodResolver.resolve),
            "resolve should be callable"
        )


class TestConnectionServicePresentIndicatesOAuth(unittest.TestCase):
    """Tests for Scenario: Connection service present indicates OAuth authentication.

    Given a connection service is provided
    When the auth method is resolved
    Then the result should indicate OAuth authentication
    And auth_method should be null (not overwritten)
    And app_password should be null (not overwritten)
    """

    def test_connection_service_present_indicates_oauth(self):
        """Test that presence of connection_service indicates OAuth auth.

        When a connection_service object is provided (not None), the resolver
        should identify this as OAuth authentication.
        """
        from utils.auth_method_resolver import AuthMethodResolver, AuthMethodContext

        # Arrange: Create a mock connection service
        mock_connection_service = MagicMock()

        # Act: Resolve the auth method
        result = AuthMethodResolver.resolve(
            connection_service=mock_connection_service,
            app_password=None,
        )

        # Assert: Result indicates OAuth
        self.assertIsInstance(result, AuthMethodContext)
        self.assertTrue(result.is_oauth, "Result should indicate OAuth authentication")
        self.assertTrue(result.has_connection_service, "Should report connection service present")

    def test_oauth_auth_method_is_null(self):
        """Test that auth_method is None when OAuth (don't overwrite existing).

        For OAuth accounts, we don't want to update the auth_method field
        in the database, so it should be None (meaning "don't update").
        """
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        mock_connection_service = MagicMock()

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=mock_connection_service,
            app_password=None,
        )

        # Assert: auth_method is None (don't update)
        self.assertIsNone(
            result.auth_method,
            "auth_method should be None for OAuth (don't overwrite existing value)"
        )

    def test_oauth_app_password_is_null(self):
        """Test that app_password is None when OAuth (don't overwrite existing).

        For OAuth accounts, we don't want to update the app_password field
        in the database, so it should be None (meaning "don't update").
        """
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        mock_connection_service = MagicMock()

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=mock_connection_service,
            app_password=None,
        )

        # Assert: app_password is None (don't update)
        self.assertIsNone(
            result.app_password,
            "app_password should be None for OAuth (don't overwrite existing value)"
        )

    def test_oauth_should_not_update_auth_method(self):
        """Test that should_update_auth_method is False for OAuth.

        OAuth accounts should not have their auth_method updated during
        registration to avoid the bug where OAuth gets overwritten to IMAP.
        """
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        mock_connection_service = MagicMock()

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=mock_connection_service,
            app_password=None,
        )

        # Assert
        self.assertFalse(
            result.should_update_auth_method,
            "should_update_auth_method should be False for OAuth"
        )


class TestNoConnectionServiceIndicatesIMAP(unittest.TestCase):
    """Tests for Scenario: No connection service indicates IMAP authentication.

    Given no connection service is provided
    And an app password "my-app-password" is available
    When the auth method is resolved
    Then the result should indicate IMAP authentication
    And auth_method should be "imap"
    And app_password should be "my-app-password"
    """

    def test_no_connection_service_indicates_imap(self):
        """Test that absence of connection_service indicates IMAP auth."""
        from utils.auth_method_resolver import AuthMethodResolver, AuthMethodContext

        # Arrange: No connection service
        app_password = "my-app-password"

        # Act: Resolve the auth method
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password=app_password,
        )

        # Assert: Result indicates IMAP
        self.assertIsInstance(result, AuthMethodContext)
        self.assertFalse(result.is_oauth, "Result should NOT indicate OAuth authentication")
        self.assertFalse(result.has_connection_service, "Should report no connection service")

    def test_imap_auth_method_is_imap(self):
        """Test that auth_method is 'imap' when no connection service."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        app_password = "my-app-password"

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password=app_password,
        )

        # Assert: auth_method is "imap"
        self.assertEqual(
            result.auth_method,
            "imap",
            "auth_method should be 'imap' when no connection service"
        )

    def test_imap_app_password_is_preserved(self):
        """Test that app_password is preserved when IMAP."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        app_password = "my-app-password"

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password=app_password,
        )

        # Assert: app_password is preserved
        self.assertEqual(
            result.app_password,
            "my-app-password",
            "app_password should be preserved for IMAP authentication"
        )

    def test_imap_should_update_auth_method(self):
        """Test that should_update_auth_method is True for IMAP."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        app_password = "my-app-password"

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password=app_password,
        )

        # Assert
        self.assertTrue(
            result.should_update_auth_method,
            "should_update_auth_method should be True for IMAP"
        )


class TestAuthContextIdentifiesOAuth(unittest.TestCase):
    """Tests for Scenario: Auth context correctly identifies OAuth connection.

    Given a connection service object exists
    When the auth method context is created
    Then the context should report has_connection_service as true
    And the context should report is_oauth as true
    And the context should report should_update_auth_method as false
    """

    def test_oauth_context_has_connection_service_true(self):
        """Test that OAuth context reports has_connection_service as True."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        mock_connection_service = MagicMock()

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=mock_connection_service,
            app_password=None,
        )

        # Assert
        self.assertTrue(
            result.has_connection_service,
            "has_connection_service should be True when connection_service is provided"
        )

    def test_oauth_context_is_oauth_true(self):
        """Test that OAuth context reports is_oauth as True."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        mock_connection_service = MagicMock()

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=mock_connection_service,
            app_password=None,
        )

        # Assert
        self.assertTrue(
            result.is_oauth,
            "is_oauth should be True when connection_service is provided"
        )

    def test_oauth_context_should_update_auth_method_false(self):
        """Test that OAuth context reports should_update_auth_method as False."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        mock_connection_service = MagicMock()

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=mock_connection_service,
            app_password=None,
        )

        # Assert
        self.assertFalse(
            result.should_update_auth_method,
            "should_update_auth_method should be False for OAuth"
        )


class TestAuthContextIdentifiesIMAP(unittest.TestCase):
    """Tests for Scenario: Auth context correctly identifies IMAP connection.

    Given no connection service object exists
    And an app password is available
    When the auth method context is created
    Then the context should report has_connection_service as false
    And the context should report is_oauth as false
    And the context should report should_update_auth_method as true
    """

    def test_imap_context_has_connection_service_false(self):
        """Test that IMAP context reports has_connection_service as False."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        app_password = "test-password"

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password=app_password,
        )

        # Assert
        self.assertFalse(
            result.has_connection_service,
            "has_connection_service should be False when connection_service is None"
        )

    def test_imap_context_is_oauth_false(self):
        """Test that IMAP context reports is_oauth as False."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        app_password = "test-password"

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password=app_password,
        )

        # Assert
        self.assertFalse(
            result.is_oauth,
            "is_oauth should be False when connection_service is None"
        )

    def test_imap_context_should_update_auth_method_true(self):
        """Test that IMAP context reports should_update_auth_method as True."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        app_password = "test-password"

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password=app_password,
        )

        # Assert
        self.assertTrue(
            result.should_update_auth_method,
            "should_update_auth_method should be True for IMAP"
        )


class TestNullAppPasswordWithIMAP(unittest.TestCase):
    """Tests for Scenario: Null app password with IMAP still sets auth method.

    Given no connection service is provided
    And app password is null
    When the auth method is resolved
    Then auth_method should be "imap"
    And app_password should be null
    """

    def test_null_app_password_sets_auth_method_to_imap(self):
        """Test that null app_password still results in auth_method='imap'.

        Even when app_password is None, if there's no connection_service,
        this is still an IMAP registration (just without a password stored).
        """
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange: No connection service, no app password
        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password=None,
        )

        # Assert: auth_method is still "imap"
        self.assertEqual(
            result.auth_method,
            "imap",
            "auth_method should be 'imap' even when app_password is None"
        )

    def test_null_app_password_preserved_as_null(self):
        """Test that null app_password is preserved as null in result."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange: No connection service, no app password
        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password=None,
        )

        # Assert: app_password is None
        self.assertIsNone(
            result.app_password,
            "app_password should be None when provided as None"
        )

    def test_null_app_password_context_indicates_imap(self):
        """Test that null app_password context correctly indicates IMAP."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password=None,
        )

        # Assert: Context indicates IMAP, not OAuth
        self.assertFalse(result.is_oauth)
        self.assertFalse(result.has_connection_service)
        self.assertTrue(result.should_update_auth_method)


class TestEmptyAppPasswordWithIMAP(unittest.TestCase):
    """Tests for Scenario: Empty app password with IMAP still sets auth method.

    Given no connection service is provided
    And app password is empty string
    When the auth method is resolved
    Then auth_method should be "imap"
    And app_password should be empty string
    """

    def test_empty_app_password_sets_auth_method_to_imap(self):
        """Test that empty string app_password still results in auth_method='imap'.

        Even when app_password is "", if there's no connection_service,
        this is still an IMAP registration.
        """
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange: No connection service, empty app password
        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password="",
        )

        # Assert: auth_method is still "imap"
        self.assertEqual(
            result.auth_method,
            "imap",
            "auth_method should be 'imap' even when app_password is empty string"
        )

    def test_empty_app_password_preserved_as_empty_string(self):
        """Test that empty string app_password is preserved in result."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange: No connection service, empty app password
        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password="",
        )

        # Assert: app_password is empty string
        self.assertEqual(
            result.app_password,
            "",
            "app_password should be empty string when provided as empty string"
        )

    def test_empty_app_password_context_indicates_imap(self):
        """Test that empty app_password context correctly indicates IMAP."""
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange
        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password="",
        )

        # Assert: Context indicates IMAP, not OAuth
        self.assertFalse(result.is_oauth)
        self.assertFalse(result.has_connection_service)
        self.assertTrue(result.should_update_auth_method)


class TestConnectionServiceIsSoleDeterminant(unittest.TestCase):
    """Additional tests to verify connection_service presence is the sole
    determinant of OAuth vs IMAP mode.

    Edge Cases:
    - Connection service presence is the sole determinant of OAuth vs IMAP
    """

    def test_connection_service_with_app_password_still_oauth(self):
        """Test that OAuth is detected even if app_password is also provided.

        The presence of connection_service should override any app_password value.
        """
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange: Both connection service AND app password provided
        mock_connection_service = MagicMock()
        app_password = "some-password"

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=mock_connection_service,
            app_password=app_password,
        )

        # Assert: OAuth takes precedence
        self.assertTrue(result.is_oauth)
        self.assertTrue(result.has_connection_service)
        self.assertFalse(result.should_update_auth_method)
        # auth_method and app_password should be None (don't update)
        self.assertIsNone(result.auth_method)
        self.assertIsNone(result.app_password)

    def test_no_connection_service_without_app_password_still_imap(self):
        """Test that IMAP is detected even without app_password.

        The absence of connection_service indicates IMAP regardless of
        whether app_password is provided.
        """
        from utils.auth_method_resolver import AuthMethodResolver

        # Arrange: No connection service, no app password
        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password=None,
        )

        # Assert: IMAP is indicated
        self.assertFalse(result.is_oauth)
        self.assertFalse(result.has_connection_service)
        self.assertTrue(result.should_update_auth_method)
        self.assertEqual(result.auth_method, "imap")


class TestAuthMethodResolverCompleteContext(unittest.TestCase):
    """Tests that verify the complete AuthMethodContext structure."""

    def test_oauth_context_complete_structure(self):
        """Test complete OAuth context structure matches expected format."""
        from utils.auth_method_resolver import AuthMethodResolver, AuthMethodContext

        # Arrange
        mock_connection_service = MagicMock()

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=mock_connection_service,
            app_password=None,
        )

        # Assert complete structure
        expected = AuthMethodContext(
            has_connection_service=True,
            is_oauth=True,
            should_update_auth_method=False,
            auth_method=None,
            app_password=None,
        )

        self.assertEqual(result.has_connection_service, expected.has_connection_service)
        self.assertEqual(result.is_oauth, expected.is_oauth)
        self.assertEqual(result.should_update_auth_method, expected.should_update_auth_method)
        self.assertEqual(result.auth_method, expected.auth_method)
        self.assertEqual(result.app_password, expected.app_password)

    def test_imap_context_complete_structure(self):
        """Test complete IMAP context structure matches expected format."""
        from utils.auth_method_resolver import AuthMethodResolver, AuthMethodContext

        # Arrange
        app_password = "test-password-123"

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password=app_password,
        )

        # Assert complete structure
        expected = AuthMethodContext(
            has_connection_service=False,
            is_oauth=False,
            should_update_auth_method=True,
            auth_method="imap",
            app_password="test-password-123",
        )

        self.assertEqual(result.has_connection_service, expected.has_connection_service)
        self.assertEqual(result.is_oauth, expected.is_oauth)
        self.assertEqual(result.should_update_auth_method, expected.should_update_auth_method)
        self.assertEqual(result.auth_method, expected.auth_method)
        self.assertEqual(result.app_password, expected.app_password)


class TestAuthMethodResolverTypeHints(unittest.TestCase):
    """Tests to verify proper type hints are implemented."""

    def test_resolve_returns_auth_method_context(self):
        """Test that resolve() returns an AuthMethodContext instance."""
        from utils.auth_method_resolver import AuthMethodResolver, AuthMethodContext

        # Act
        result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password="password",
        )

        # Assert
        self.assertIsInstance(result, AuthMethodContext)

    def test_context_auth_method_is_optional_string(self):
        """Test that auth_method can be None or str."""
        from utils.auth_method_resolver import AuthMethodResolver

        # OAuth case - should be None
        oauth_result = AuthMethodResolver.resolve(
            connection_service=MagicMock(),
            app_password=None,
        )
        self.assertIsNone(oauth_result.auth_method)

        # IMAP case - should be str
        imap_result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password="password",
        )
        self.assertIsInstance(imap_result.auth_method, str)

    def test_context_app_password_is_optional_string(self):
        """Test that app_password can be None, empty str, or str."""
        from utils.auth_method_resolver import AuthMethodResolver

        # OAuth case - should be None
        oauth_result = AuthMethodResolver.resolve(
            connection_service=MagicMock(),
            app_password=None,
        )
        self.assertIsNone(oauth_result.app_password)

        # IMAP with password - should be str
        imap_result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password="password",
        )
        self.assertEqual(imap_result.app_password, "password")

        # IMAP with empty password - should be empty str
        empty_result = AuthMethodResolver.resolve(
            connection_service=None,
            app_password="",
        )
        self.assertEqual(empty_result.app_password, "")


if __name__ == '__main__':
    unittest.main()
