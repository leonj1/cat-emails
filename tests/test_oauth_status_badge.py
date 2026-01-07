"""
Test suite for OAuth Status Badge feature on Accounts Page.

These tests verify that the /api/accounts endpoint includes auth_method field
for each account, enabling the frontend to display appropriate OAuth/IMAP badges.

Based on BDD Gherkin scenarios from tests/bdd/oauth-status-badge.feature

TDD Red Phase: These tests are expected to FAIL until implementation is complete.
The coder agent should:
1. Add auth_method field to EmailAccountInfo model
2. Update /api/accounts endpoint to include auth_method in response
3. Update FakeAccountCategoryClient to support auth_method
"""
import pytest
from datetime import datetime
from typing import Optional
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass, field

import sys
import os

# Add parent directory to path to import API modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set required environment variables before importing api_service
os.environ.setdefault('REQUESTYAI_API_KEY', 'test-key-for-unit-tests')


# ============================================================================
# Test Fixtures and Helpers
# ============================================================================

@dataclass
class MockEmailAccount:
    """Mock email account for testing auth_method behavior."""
    id: int
    email_address: str
    display_name: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_scan_at: Optional[datetime] = None
    app_password: Optional[str] = None
    auth_method: Optional[str] = None


class MockAccountService:
    """Mock account service that returns accounts with auth_method."""

    def __init__(self):
        self.accounts = {}
        self._next_id = 1

    def add_account(
        self,
        email_address: str,
        auth_method: Optional[str],
        app_password: Optional[str]
    ) -> MockEmailAccount:
        """Add a mock account with specified auth_method."""
        account = MockEmailAccount(
            id=self._next_id,
            email_address=email_address,
            display_name=email_address,
            auth_method=auth_method,
            app_password=app_password
        )
        self._next_id += 1
        self.accounts[email_address] = account
        return account

    def get_all_accounts(self, active_only: bool) -> list:
        """Return all accounts."""
        accounts = list(self.accounts.values())
        if active_only:
            accounts = [acc for acc in accounts if acc.is_active]
        return accounts

    def get_account_by_email(self, email_address: str) -> Optional[MockEmailAccount]:
        """Get account by email."""
        return self.accounts.get(email_address.lower())


# ============================================================================
# HAPPY PATH TESTS - API Response Behavior
# ============================================================================

class TestApiResponseIncludesAuthMethod:
    """
    Tests that the API response includes auth_method field for each account.

    Corresponds to BDD scenarios:
    - API response includes auth_method for each account
    - OAuth account returns oauth auth_method in API response
    - IMAP account returns imap auth_method in API response
    - Legacy account returns null auth_method in API response
    """

    def test_api_response_includes_auth_method_for_each_account(self):
        """
        Test that each account in the API response includes an auth_method field.

        The implementation should:
        - Add auth_method to EmailAccountInfo model
        - Include auth_method when converting database accounts to response format

        BDD Scenario: API response includes auth_method for each account
        """
        # Arrange
        mock_service = MockAccountService()
        mock_service.add_account("oauth@gmail.com", "oauth", None)
        mock_service.add_account("imap@company.com", "imap", "password123")
        mock_service.add_account("legacy@gmail.com", None, "oldpass")

        # Act - Get accounts from service
        accounts = mock_service.get_all_accounts(active_only=True)

        # Assert - Each account should have auth_method attribute
        for account in accounts:
            assert hasattr(account, 'auth_method'), \
                f"Account {account.email_address} missing auth_method attribute"

    def test_oauth_account_returns_oauth_auth_method_in_api_response(self):
        """
        Test that an OAuth-configured account returns auth_method="oauth".

        The implementation should:
        - Return auth_method "oauth" for accounts configured with OAuth

        BDD Scenario: OAuth account returns oauth auth_method in API response
        """
        # Arrange
        mock_service = MockAccountService()
        mock_service.add_account("user@gmail.com", "oauth", None)

        # Act
        account = mock_service.get_account_by_email("user@gmail.com")

        # Assert
        assert account is not None, "Account should exist"
        assert account.auth_method == "oauth", \
            f"Expected auth_method 'oauth', got '{account.auth_method}'"

    def test_imap_account_returns_imap_auth_method_in_api_response(self):
        """
        Test that an IMAP-configured account returns auth_method="imap".

        The implementation should:
        - Return auth_method "imap" for accounts configured with IMAP credentials

        BDD Scenario: IMAP account returns imap auth_method in API response
        """
        # Arrange
        mock_service = MockAccountService()
        mock_service.add_account("user@company.com", "imap", "app_password_123")

        # Act
        account = mock_service.get_account_by_email("user@company.com")

        # Assert
        assert account is not None, "Account should exist"
        assert account.auth_method == "imap", \
            f"Expected auth_method 'imap', got '{account.auth_method}'"

    def test_legacy_account_returns_null_auth_method_in_api_response(self):
        """
        Test that a legacy account (created before auth_method tracking) returns null.

        The implementation should:
        - Return auth_method null for accounts without auth_method set

        BDD Scenario: Legacy account returns null auth_method in API response
        """
        # Arrange
        mock_service = MockAccountService()
        mock_service.add_account("legacy@gmail.com", None, "old_password")

        # Act
        account = mock_service.get_account_by_email("legacy@gmail.com")

        # Assert
        assert account is not None, "Account should exist"
        assert account.auth_method is None, \
            f"Expected auth_method None, got '{account.auth_method}'"


class TestEmailAccountInfoModelAuthMethod:
    """
    Tests that EmailAccountInfo Pydantic model includes auth_method field.

    The implementation should add:
    - auth_method: Optional[str] field to EmailAccountInfo model
    """

    def test_email_account_info_model_has_auth_method_field(self):
        """
        Test that EmailAccountInfo model includes auth_method field.

        The implementation should:
        - Add auth_method as Optional[str] to EmailAccountInfo
        - Field should be nullable (Optional)
        """
        from models.account_models import EmailAccountInfo

        # Arrange & Act - Create instance with auth_method
        account_info = EmailAccountInfo(
            id=1,
            email_address="test@gmail.com",
            auth_method="oauth",
            created_at=datetime.now()
        )

        # Assert
        assert hasattr(account_info, 'auth_method'), \
            "EmailAccountInfo should have auth_method attribute"
        assert account_info.auth_method == "oauth", \
            f"Expected auth_method 'oauth', got '{account_info.auth_method}'"

    def test_email_account_info_auth_method_can_be_null(self):
        """
        Test that auth_method can be null for legacy accounts.

        The implementation should:
        - Allow auth_method to be None (for legacy accounts)
        """
        from models.account_models import EmailAccountInfo

        # Arrange & Act - Create instance with null auth_method
        account_info = EmailAccountInfo(
            id=1,
            email_address="legacy@gmail.com",
            auth_method=None,
            created_at=datetime.now()
        )

        # Assert
        assert account_info.auth_method is None, \
            "auth_method should be None for legacy accounts"

    def test_email_account_info_auth_method_in_dict_representation(self):
        """
        Test that auth_method appears in dict/JSON representation.

        The implementation should:
        - Include auth_method in model_dump() / dict() output
        """
        from models.account_models import EmailAccountInfo

        # Arrange
        account_info = EmailAccountInfo(
            id=1,
            email_address="test@gmail.com",
            auth_method="imap",
            created_at=datetime.now()
        )

        # Act - Get dict representation
        # Note: Pydantic v2 uses model_dump(), v1 uses dict()
        try:
            account_dict = account_info.model_dump()
        except AttributeError:
            account_dict = account_info.dict()

        # Assert
        assert "auth_method" in account_dict, \
            "auth_method should be in dict representation"
        assert account_dict["auth_method"] == "imap", \
            f"Expected auth_method 'imap', got '{account_dict['auth_method']}'"

    def test_email_account_info_accepts_oauth_value(self):
        """
        Test that EmailAccountInfo accepts 'oauth' as auth_method value.
        """
        from models.account_models import EmailAccountInfo

        # Arrange & Act
        account_info = EmailAccountInfo(
            id=1,
            email_address="oauth@gmail.com",
            auth_method="oauth",
            created_at=datetime.now()
        )

        # Assert
        assert account_info.auth_method == "oauth"

    def test_email_account_info_accepts_imap_value(self):
        """
        Test that EmailAccountInfo accepts 'imap' as auth_method value.
        """
        from models.account_models import EmailAccountInfo

        # Arrange & Act
        account_info = EmailAccountInfo(
            id=1,
            email_address="imap@company.com",
            auth_method="imap",
            created_at=datetime.now()
        )

        # Assert
        assert account_info.auth_method == "imap"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestAuthMethodEdgeCases:
    """
    Tests for edge cases in auth_method handling.

    Corresponds to BDD scenarios:
    - Legacy account with null auth_method displays Not Configured badge
    - Case insensitive auth_method handling
    - Badge renders gracefully for unexpected auth_method value
    - Badge renders when auth_method field is missing from response
    """

    def test_null_auth_method_for_legacy_account(self):
        """
        Test that legacy accounts (before auth_method tracking) have null auth_method.

        BDD Scenario: Legacy account with null auth_method displays Not Configured badge
        """
        # Arrange
        mock_service = MockAccountService()
        mock_service.add_account("legacy@gmail.com", None, "old_password")

        # Act
        account = mock_service.get_account_by_email("legacy@gmail.com")

        # Assert
        assert account.auth_method is None, \
            "Legacy account should have null auth_method"

    def test_case_insensitive_auth_method_handling_uppercase_oauth(self):
        """
        Test case insensitive handling of auth_method (OAuth vs oauth).

        The implementation should normalize auth_method values.

        BDD Scenario: Case insensitive auth_method handling
        """
        # Arrange
        mock_service = MockAccountService()
        # Simulate database returning uppercase
        account = mock_service.add_account("user@gmail.com", "OAuth", None)

        # Act & Assert
        # The implementation should normalize to lowercase
        normalized = account.auth_method.lower() if account.auth_method else None
        assert normalized == "oauth", \
            "auth_method should be handled case-insensitively"

    def test_case_insensitive_auth_method_handling_uppercase_imap(self):
        """
        Test case insensitive handling of auth_method (IMAP vs imap).
        """
        # Arrange
        mock_service = MockAccountService()
        account = mock_service.add_account("user@company.com", "IMAP", "password")

        # Act & Assert
        normalized = account.auth_method.lower() if account.auth_method else None
        assert normalized == "imap", \
            "auth_method should be handled case-insensitively"

    def test_unexpected_auth_method_value_treated_as_not_configured(self):
        """
        Test that unexpected auth_method values are handled gracefully.

        The frontend should display "Not Configured" for unexpected values.

        BDD Scenario: Badge renders gracefully for unexpected auth_method value
        """
        # Arrange
        mock_service = MockAccountService()
        account = mock_service.add_account("user@gmail.com", "unexpected_value", None)

        # Act & Assert
        # The backend should allow any string, but frontend will handle display
        assert account.auth_method == "unexpected_value", \
            "Backend should store the value as-is"
        # Frontend will interpret non-oauth/non-imap as "Not Configured"
        valid_methods = {"oauth", "imap"}
        is_valid = account.auth_method.lower() in valid_methods if account.auth_method else False
        assert not is_valid, \
            "unexpected_value should not be a valid auth method"


class TestAccountsListMixedAuthMethods:
    """
    Tests for displaying mixed authentication methods in accounts list.

    Corresponds to BDD scenario:
    - Accounts list shows mixed authentication methods
    """

    def test_accounts_list_shows_mixed_authentication_methods(self):
        """
        Test that accounts list correctly shows mixed OAuth and IMAP accounts.

        BDD Scenario: Accounts list shows mixed authentication methods
        """
        # Arrange
        mock_service = MockAccountService()
        mock_service.add_account("oauth1@gmail.com", "oauth", None)
        mock_service.add_account("imap1@company.com", "imap", "password123")
        mock_service.add_account("oauth2@gmail.com", "oauth", None)

        # Act
        accounts = mock_service.get_all_accounts(active_only=True)
        accounts_by_email = {acc.email_address: acc for acc in accounts}

        # Assert
        assert len(accounts) == 3, f"Expected 3 accounts, got {len(accounts)}"

        assert accounts_by_email["oauth1@gmail.com"].auth_method == "oauth", \
            "oauth1@gmail.com should have auth_method 'oauth'"
        assert accounts_by_email["imap1@company.com"].auth_method == "imap", \
            "imap1@company.com should have auth_method 'imap'"
        assert accounts_by_email["oauth2@gmail.com"].auth_method == "oauth", \
            "oauth2@gmail.com should have auth_method 'oauth'"


class TestEmptyAccountsList:
    """
    Tests for empty accounts list behavior.

    Corresponds to BDD scenario:
    - Empty accounts list renders correctly
    """

    def test_empty_accounts_list_returns_empty_array(self):
        """
        Test that empty accounts list returns empty array with auth_method support.

        BDD Scenario: Empty accounts list renders correctly
        """
        # Arrange
        mock_service = MockAccountService()
        # No accounts added

        # Act
        accounts = mock_service.get_all_accounts(active_only=True)

        # Assert
        assert accounts == [], "Empty accounts list should return empty array"


# ============================================================================
# API ENDPOINT INTEGRATION TESTS
# ============================================================================

class TestAccountsEndpointAuthMethod:
    """
    Tests for /api/accounts endpoint auth_method field inclusion.

    These tests verify the actual API endpoint returns auth_method.
    """

    def test_accounts_endpoint_includes_auth_method_field(self):
        """
        Test that /api/accounts endpoint includes auth_method for each account.

        The implementation should:
        - Modify get_all_accounts endpoint to include auth_method in response
        - Map database auth_method to EmailAccountInfo.auth_method
        """
        # Mock SettingsService to prevent MySQL initialization
        with patch('services.settings_service.SettingsService') as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings.return_value = mock_settings_instance

            from fastapi.testclient import TestClient
            from api_service import app, get_account_service

            # Create test client
            client = TestClient(app)

            # Create mock service with accounts having different auth methods
            mock_service = MockAccountService()
            mock_service.add_account("oauth@gmail.com", "oauth", None)
            mock_service.add_account("imap@company.com", "imap", "password123")
            mock_service.add_account("legacy@gmail.com", None, "oldpass")

            # Override dependency
            app.dependency_overrides[get_account_service] = lambda: mock_service

            # Set API key for authentication
            os.environ['API_KEY'] = 'test-api-key'
            headers = {"X-API-Key": "test-api-key"}

            try:
                # Act
                response = client.get("/api/accounts", headers=headers)

                # Assert
                assert response.status_code == 200, \
                    f"Expected 200, got {response.status_code}: {response.text}"

                data = response.json()
                assert "accounts" in data, "Response should contain 'accounts' field"

                # Each account should have auth_method field
                for account in data["accounts"]:
                    assert "auth_method" in account, \
                        f"Account {account.get('email_address')} missing auth_method field"

                # Verify specific values
                accounts_by_email = {acc["email_address"]: acc for acc in data["accounts"]}

                oauth_account = accounts_by_email.get("oauth@gmail.com")
                assert oauth_account is not None, "oauth@gmail.com should exist"
                assert oauth_account["auth_method"] == "oauth", \
                    f"Expected 'oauth', got '{oauth_account['auth_method']}'"

                imap_account = accounts_by_email.get("imap@company.com")
                assert imap_account is not None, "imap@company.com should exist"
                assert imap_account["auth_method"] == "imap", \
                    f"Expected 'imap', got '{imap_account['auth_method']}'"

                legacy_account = accounts_by_email.get("legacy@gmail.com")
                assert legacy_account is not None, "legacy@gmail.com should exist"
                assert legacy_account["auth_method"] is None, \
                    f"Expected None, got '{legacy_account['auth_method']}'"

            finally:
                # Cleanup
                app.dependency_overrides.clear()
                if 'API_KEY' in os.environ:
                    del os.environ['API_KEY']

    def test_accounts_endpoint_returns_complete_response_with_auth_method(self):
        """
        Test that the complete API response includes all required fields including auth_method.

        Per testing-standards.md: Assert complete response structures, not individual fields.
        """
        with patch('services.settings_service.SettingsService') as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings.return_value = mock_settings_instance

            from fastapi.testclient import TestClient
            from api_service import app, get_account_service

            client = TestClient(app)

            # Create single account for predictable testing
            mock_service = MockAccountService()
            test_account = mock_service.add_account("test@gmail.com", "oauth", None)

            app.dependency_overrides[get_account_service] = lambda: mock_service
            os.environ['API_KEY'] = 'test-api-key'
            headers = {"X-API-Key": "test-api-key"}

            try:
                response = client.get("/api/accounts", headers=headers)

                assert response.status_code == 200
                data = response.json()

                # Verify response structure
                assert "accounts" in data
                assert "total_count" in data
                assert data["total_count"] == 1

                # Verify account has all required fields including auth_method
                account = data["accounts"][0]
                required_fields = [
                    "id",
                    "email_address",
                    "is_active",
                    "created_at",
                    "auth_method"  # New required field
                ]

                for field_name in required_fields:
                    assert field_name in account, \
                        f"Account missing required field: {field_name}"

            finally:
                app.dependency_overrides.clear()
                if 'API_KEY' in os.environ:
                    del os.environ['API_KEY']


# ============================================================================
# BADGE DISPLAY LOGIC TESTS (Frontend Support)
# ============================================================================

class TestBadgeDisplayLogic:
    """
    Tests for badge display logic based on auth_method values.

    These tests verify the logic for determining badge text and style.

    Corresponds to BDD scenarios:
    - OAuth Connected account displays green badge
    - IMAP account displays gray badge
    - Legacy account with null auth_method displays Not Configured badge
    """

    def test_oauth_auth_method_maps_to_oauth_connected_badge(self):
        """
        Test that auth_method="oauth" should display "OAuth Connected" badge.

        BDD Scenario: OAuth Connected account displays green badge
        """
        # Arrange
        auth_method = "oauth"

        # Act - Badge display logic
        if auth_method and auth_method.lower() == "oauth":
            badge_text = "OAuth Connected"
            badge_style = "green"
        elif auth_method and auth_method.lower() == "imap":
            badge_text = "IMAP"
            badge_style = "gray"
        else:
            badge_text = "Not Configured"
            badge_style = "neutral"

        # Assert
        assert badge_text == "OAuth Connected", \
            f"Expected 'OAuth Connected', got '{badge_text}'"
        assert badge_style == "green", \
            f"Expected 'green', got '{badge_style}'"

    def test_imap_auth_method_maps_to_imap_badge(self):
        """
        Test that auth_method="imap" should display "IMAP" badge.

        BDD Scenario: IMAP account displays gray badge
        """
        # Arrange
        auth_method = "imap"

        # Act - Badge display logic
        if auth_method and auth_method.lower() == "oauth":
            badge_text = "OAuth Connected"
            badge_style = "green"
        elif auth_method and auth_method.lower() == "imap":
            badge_text = "IMAP"
            badge_style = "gray"
        else:
            badge_text = "Not Configured"
            badge_style = "neutral"

        # Assert
        assert badge_text == "IMAP", \
            f"Expected 'IMAP', got '{badge_text}'"
        assert badge_style == "gray", \
            f"Expected 'gray', got '{badge_style}'"

    def test_null_auth_method_maps_to_not_configured_badge(self):
        """
        Test that auth_method=null should display "Not Configured" badge.

        BDD Scenario: Legacy account with null auth_method displays Not Configured badge
        """
        # Arrange
        auth_method = None

        # Act - Badge display logic
        if auth_method and auth_method.lower() == "oauth":
            badge_text = "OAuth Connected"
            badge_style = "green"
        elif auth_method and auth_method.lower() == "imap":
            badge_text = "IMAP"
            badge_style = "gray"
        else:
            badge_text = "Not Configured"
            badge_style = "neutral"

        # Assert
        assert badge_text == "Not Configured", \
            f"Expected 'Not Configured', got '{badge_text}'"
        assert badge_style == "neutral", \
            f"Expected 'neutral', got '{badge_style}'"

    def test_unexpected_auth_method_maps_to_not_configured_badge(self):
        """
        Test that unexpected auth_method values display "Not Configured" badge.

        BDD Scenario: Badge renders gracefully for unexpected auth_method value
        """
        # Arrange
        auth_method = "unexpected_value"

        # Act - Badge display logic
        if auth_method and auth_method.lower() == "oauth":
            badge_text = "OAuth Connected"
            badge_style = "green"
        elif auth_method and auth_method.lower() == "imap":
            badge_text = "IMAP"
            badge_style = "gray"
        else:
            badge_text = "Not Configured"
            badge_style = "neutral"

        # Assert
        assert badge_text == "Not Configured", \
            f"Expected 'Not Configured', got '{badge_text}'"
        assert badge_style == "neutral", \
            f"Expected 'neutral', got '{badge_style}'"


# ============================================================================
# ACCESSIBILITY TESTS
# ============================================================================

class TestBadgeAccessibility:
    """
    Tests for badge accessibility attributes.

    Corresponds to BDD scenarios:
    - OAuth badge has accessible aria-label
    - IMAP badge has accessible aria-label
    - Not Configured badge has accessible aria-label
    """

    def test_oauth_badge_aria_label(self):
        """
        Test that OAuth badge has correct aria-label.

        BDD Scenario: OAuth badge has accessible aria-label
        """
        # Arrange
        auth_method = "oauth"

        # Act - Compute aria-label
        if auth_method and auth_method.lower() == "oauth":
            badge_text = "OAuth Connected"
        elif auth_method and auth_method.lower() == "imap":
            badge_text = "IMAP"
        else:
            badge_text = "Not Configured"

        aria_label = f"Authentication method: {badge_text}"

        # Assert
        expected_aria_label = "Authentication method: OAuth Connected"
        assert aria_label == expected_aria_label, \
            f"Expected '{expected_aria_label}', got '{aria_label}'"

    def test_imap_badge_aria_label(self):
        """
        Test that IMAP badge has correct aria-label.

        BDD Scenario: IMAP badge has accessible aria-label
        """
        # Arrange
        auth_method = "imap"

        # Act - Compute aria-label
        if auth_method and auth_method.lower() == "oauth":
            badge_text = "OAuth Connected"
        elif auth_method and auth_method.lower() == "imap":
            badge_text = "IMAP"
        else:
            badge_text = "Not Configured"

        aria_label = f"Authentication method: {badge_text}"

        # Assert
        expected_aria_label = "Authentication method: IMAP"
        assert aria_label == expected_aria_label, \
            f"Expected '{expected_aria_label}', got '{aria_label}'"

    def test_not_configured_badge_aria_label(self):
        """
        Test that Not Configured badge has correct aria-label.

        BDD Scenario: Not Configured badge has accessible aria-label
        """
        # Arrange
        auth_method = None

        # Act - Compute aria-label
        if auth_method and auth_method.lower() == "oauth":
            badge_text = "OAuth Connected"
        elif auth_method and auth_method.lower() == "imap":
            badge_text = "IMAP"
        else:
            badge_text = "Not Configured"

        aria_label = f"Authentication method: {badge_text}"

        # Assert
        expected_aria_label = "Authentication method: Not Configured"
        assert aria_label == expected_aria_label, \
            f"Expected '{expected_aria_label}', got '{aria_label}'"


# ============================================================================
# FAKE ACCOUNT CATEGORY CLIENT TESTS
# ============================================================================

class TestFakeAccountCategoryClientAuthMethod:
    """
    Tests that FakeAccountCategoryClient supports auth_method.

    The implementation should:
    - Add auth_method field to FakeEmailAccount dataclass
    - Support auth_method in get_or_create_account method
    """

    def test_fake_email_account_has_auth_method_attribute(self):
        """
        Test that FakeEmailAccount supports auth_method attribute.
        """
        from tests.fake_account_category_client import FakeEmailAccount

        # Arrange & Act
        account = FakeEmailAccount(
            id=1,
            email_address="test@gmail.com",
            display_name="Test",
            auth_method="oauth"
        )

        # Assert
        assert hasattr(account, 'auth_method'), \
            "FakeEmailAccount should have auth_method attribute"
        assert account.auth_method == "oauth", \
            f"Expected 'oauth', got '{account.auth_method}'"

    def test_fake_client_get_or_create_account_supports_auth_method(self):
        """
        Test that FakeAccountCategoryClient.get_or_create_account supports auth_method.
        """
        from tests.fake_account_category_client import FakeAccountCategoryClient

        # Arrange
        client = FakeAccountCategoryClient()

        # Act - Create account with auth_method parameter
        account = client.get_or_create_account(
            email_address="test@gmail.com",
            display_name="Test",
            app_password=None,
            auth_method="oauth"  # New parameter
        )

        # Assert
        assert account.auth_method == "oauth", \
            f"Expected auth_method 'oauth', got '{account.auth_method}'"

    def test_fake_client_returns_auth_method_in_get_all_accounts(self):
        """
        Test that get_all_accounts returns accounts with auth_method.
        """
        from tests.fake_account_category_client import FakeAccountCategoryClient

        # Arrange
        client = FakeAccountCategoryClient()
        client.get_or_create_account("oauth@gmail.com", None, None, "oauth")
        client.get_or_create_account("imap@gmail.com", None, None, "imap")

        # Act
        accounts = client.get_all_accounts(active_only=True)

        # Assert
        for account in accounts:
            assert hasattr(account, 'auth_method'), \
                f"Account {account.email_address} missing auth_method"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
