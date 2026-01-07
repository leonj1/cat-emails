"""
Tests for OAuth Account Restoration Service.

TDD Red Phase Tests - These tests define the expected behavior for restoring
OAuth accounts that were corrupted by the auth method bug.

Feature: Corrupted OAuth Account Restoration
- Scan for corrupted accounts (auth_method='imap' AND oauth_refresh_token IS NOT NULL AND NOT EMPTY)
- Restore corrupted accounts by setting auth_method='oauth'
- Return count of restored accounts
- Support idempotent execution

The corruption bug caused accounts with OAuth refresh tokens to have their
auth_method incorrectly set to 'imap' instead of 'oauth'.

Implementation should create:
- services/oauth_account_restoration_service.py
- sql/V11__restore_corrupted_oauth_accounts.sql
"""
import unittest
from typing import Protocol, List, Optional, Dict
from datetime import datetime, timezone
from dataclasses import dataclass
from unittest.mock import MagicMock, Mock, patch, call


# ============================================================================
# Protocol Definitions for Type Safety
# ============================================================================

@dataclass
class MockEmailAccount:
    """Mock EmailAccount for testing without database dependency."""
    id: int
    email_address: str
    auth_method: Optional[str]
    oauth_refresh_token: Optional[str]
    app_password: Optional[str]
    updated_at: Optional[datetime]

    @classmethod
    def create_corrupted(
        cls,
        email: str,
        token: str,
        account_id: int
    ) -> "MockEmailAccount":
        """Factory for creating a corrupted OAuth account."""
        return cls(
            id=account_id,
            email_address=email,
            auth_method="imap",
            oauth_refresh_token=token,
            app_password=None,
            updated_at=datetime.now(timezone.utc)
        )

    @classmethod
    def create_healthy_oauth(
        cls,
        email: str,
        token: str,
        account_id: int
    ) -> "MockEmailAccount":
        """Factory for creating a healthy OAuth account."""
        return cls(
            id=account_id,
            email_address=email,
            auth_method="oauth",
            oauth_refresh_token=token,
            app_password=None,
            updated_at=datetime.now(timezone.utc)
        )

    @classmethod
    def create_true_imap(
        cls,
        email: str,
        password: str,
        account_id: int
    ) -> "MockEmailAccount":
        """Factory for creating a true IMAP account."""
        return cls(
            id=account_id,
            email_address=email,
            auth_method="imap",
            oauth_refresh_token=None,
            app_password=password,
            updated_at=datetime.now(timezone.utc)
        )


class DatabaseRepositoryProtocol(Protocol):
    """Protocol for database repository interface."""

    def get_all_accounts(self) -> List[MockEmailAccount]:
        """Get all email accounts."""
        ...

    def update_account_auth_method(
        self,
        email_address: str,
        auth_method: str
    ) -> bool:
        """Update the auth_method for an account."""
        ...


# ============================================================================
# Test: Module Import and Structure
# ============================================================================

class TestOAuthAccountRestorationServiceImport(unittest.TestCase):
    """Tests that verify the service module can be imported.

    These tests will fail until the implementation is created at:
    services/oauth_account_restoration_service.py
    """

    def test_service_module_exists(self):
        """Test that oauth_account_restoration_service module exists.

        The implementation should create:
        services/oauth_account_restoration_service.py

        With class OAuthAccountRestorationService
        """
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        self.assertIsNotNone(OAuthAccountRestorationService)

    def test_service_has_scan_corrupted_accounts_method(self):
        """Test that service has scan_corrupted_accounts method."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        self.assertTrue(
            hasattr(OAuthAccountRestorationService, 'scan_corrupted_accounts'),
            "Service should have 'scan_corrupted_accounts' method"
        )

    def test_service_has_restore_corrupted_accounts_method(self):
        """Test that service has restore_corrupted_accounts method."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        self.assertTrue(
            hasattr(OAuthAccountRestorationService, 'restore_corrupted_accounts'),
            "Service should have 'restore_corrupted_accounts' method"
        )

    def test_service_has_is_account_corrupted_method(self):
        """Test that service has is_account_corrupted method."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        self.assertTrue(
            hasattr(OAuthAccountRestorationService, 'is_account_corrupted'),
            "Service should have 'is_account_corrupted' method"
        )


# ============================================================================
# Test: Corrupted Account Identification
# ============================================================================

class TestCorruptedOAuthAccountIsIdentified(unittest.TestCase):
    """Tests for Scenario: Corrupted OAuth account is identified.

    Given an account "corrupted@gmail.com" has:
      | auth_method          | imap                     |
      | oauth_refresh_token  | valid-refresh-token      |
    When the system scans for corrupted accounts
    Then the account "corrupted@gmail.com" should be identified as corrupted
    And the reason should be "has oauth_refresh_token but auth_method is imap"
    """

    def test_corrupted_account_detected_by_is_account_corrupted(self):
        """Test that is_account_corrupted returns True for corrupted accounts.

        A corrupted account has:
        - auth_method = 'imap'
        - oauth_refresh_token is not None and not empty string
        """
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange: Create mock repository
        mock_repository = MagicMock()
        service = OAuthAccountRestorationService(repository=mock_repository)

        # Create corrupted account
        corrupted_account = MockEmailAccount.create_corrupted(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )

        # Act
        is_corrupted = service.is_account_corrupted(corrupted_account)

        # Assert
        self.assertTrue(
            is_corrupted,
            "Account with auth_method='imap' and oauth_refresh_token='valid-refresh-token' "
            "should be identified as corrupted"
        )

    def test_scan_corrupted_accounts_finds_corrupted_account(self):
        """Test that scan_corrupted_accounts finds the corrupted account."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        corrupted_account = MockEmailAccount.create_corrupted(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [corrupted_account]

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        corrupted_accounts = service.scan_corrupted_accounts()

        # Assert
        self.assertEqual(len(corrupted_accounts), 1)
        self.assertEqual(
            corrupted_accounts[0]["email"],
            "corrupted@gmail.com"
        )

    def test_scan_corrupted_accounts_includes_reason(self):
        """Test that scan result includes reason for corruption."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        corrupted_account = MockEmailAccount.create_corrupted(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [corrupted_account]

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        corrupted_accounts = service.scan_corrupted_accounts()

        # Assert
        self.assertEqual(len(corrupted_accounts), 1)
        self.assertIn(
            "reason",
            corrupted_accounts[0],
            "Scan result should include 'reason' field"
        )
        self.assertIn(
            "oauth_refresh_token",
            corrupted_accounts[0]["reason"].lower(),
            "Reason should mention oauth_refresh_token"
        )
        self.assertIn(
            "imap",
            corrupted_accounts[0]["reason"].lower(),
            "Reason should mention imap auth_method"
        )


# ============================================================================
# Test: Corrupted Account Restoration
# ============================================================================

class TestCorruptedOAuthAccountIsRestored(unittest.TestCase):
    """Tests for Scenario: Corrupted OAuth account is restored to correct auth method.

    Given an account "corrupted@gmail.com" has:
      | auth_method          | imap                     |
      | oauth_refresh_token  | valid-refresh-token      |
    When the restoration process runs
    Then the account "corrupted@gmail.com" should have auth_method "oauth"
    And a log entry should record the restoration
    """

    def test_restore_corrupted_accounts_sets_auth_method_to_oauth(self):
        """Test that restoration changes auth_method from 'imap' to 'oauth'."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        corrupted_account = MockEmailAccount.create_corrupted(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [corrupted_account]
        mock_repository.update_account_auth_method.return_value = True

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        restored_count = service.restore_corrupted_accounts()

        # Assert: update_account_auth_method was called with correct args
        mock_repository.update_account_auth_method.assert_called_once_with(
            "corrupted@gmail.com",
            "oauth"
        )
        self.assertEqual(restored_count, 1)

    @patch('services.oauth_account_restoration_service.get_logger')
    def test_restore_corrupted_accounts_logs_restoration(self, mock_get_logger):
        """Test that restoration logs each account restored."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_repository = MagicMock()
        corrupted_account = MockEmailAccount.create_corrupted(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [corrupted_account]
        mock_repository.update_account_auth_method.return_value = True

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        service.restore_corrupted_accounts()

        # Assert: Logging was called
        log_calls = mock_logger.info.call_args_list
        logged_text = " ".join(str(call) for call in log_calls)

        self.assertTrue(
            len(log_calls) > 0,
            "Restoration should log information"
        )
        # Log should include the email being restored
        self.assertIn(
            "corrupted@gmail.com",
            logged_text,
            "Log should include the restored email address"
        )


# ============================================================================
# Test: Multiple Corrupted Accounts Restoration
# ============================================================================

class TestMultipleCorruptedAccountsRestored(unittest.TestCase):
    """Tests for Scenario: Multiple corrupted accounts are restored in one migration.

    Given the following corrupted accounts exist:
      | email                | auth_method | oauth_refresh_token |
      | user1@gmail.com      | imap        | token-1             |
      | user2@gmail.com      | imap        | token-2             |
      | user3@gmail.com      | imap        | token-3             |
    When the restoration process runs
    Then all three accounts should have auth_method "oauth"
    And the restoration count should be 3
    """

    def test_multiple_corrupted_accounts_all_restored(self):
        """Test that multiple corrupted accounts are all restored."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        corrupted_accounts = [
            MockEmailAccount.create_corrupted("user1@gmail.com", "token-1", 1),
            MockEmailAccount.create_corrupted("user2@gmail.com", "token-2", 2),
            MockEmailAccount.create_corrupted("user3@gmail.com", "token-3", 3),
        ]
        mock_repository.get_all_accounts.return_value = corrupted_accounts
        mock_repository.update_account_auth_method.return_value = True

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        restored_count = service.restore_corrupted_accounts()

        # Assert: All three accounts were updated
        self.assertEqual(restored_count, 3)
        self.assertEqual(
            mock_repository.update_account_auth_method.call_count,
            3
        )

    def test_multiple_corrupted_accounts_each_updated_correctly(self):
        """Test that each corrupted account is updated with correct auth_method."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        corrupted_accounts = [
            MockEmailAccount.create_corrupted("user1@gmail.com", "token-1", 1),
            MockEmailAccount.create_corrupted("user2@gmail.com", "token-2", 2),
            MockEmailAccount.create_corrupted("user3@gmail.com", "token-3", 3),
        ]
        mock_repository.get_all_accounts.return_value = corrupted_accounts
        mock_repository.update_account_auth_method.return_value = True

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        service.restore_corrupted_accounts()

        # Assert: Each call was made with correct arguments
        expected_calls = [
            call("user1@gmail.com", "oauth"),
            call("user2@gmail.com", "oauth"),
            call("user3@gmail.com", "oauth"),
        ]
        mock_repository.update_account_auth_method.assert_has_calls(
            expected_calls,
            any_order=True
        )


# ============================================================================
# Test: Already Correct OAuth Account Not Modified
# ============================================================================

class TestHealthyOAuthAccountNotModified(unittest.TestCase):
    """Tests for Scenario: Already correct OAuth account is not modified.

    Given an account "healthy@gmail.com" has:
      | auth_method          | oauth                    |
      | oauth_refresh_token  | valid-refresh-token      |
    When the restoration process runs
    Then the account "healthy@gmail.com" should not be modified
    And the restoration count for this account should be 0
    """

    def test_healthy_oauth_account_not_identified_as_corrupted(self):
        """Test that healthy OAuth account is NOT identified as corrupted."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        service = OAuthAccountRestorationService(repository=mock_repository)

        healthy_account = MockEmailAccount.create_healthy_oauth(
            email="healthy@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )

        # Act
        is_corrupted = service.is_account_corrupted(healthy_account)

        # Assert
        self.assertFalse(
            is_corrupted,
            "Account with auth_method='oauth' should NOT be identified as corrupted"
        )

    def test_healthy_oauth_account_not_in_scan_results(self):
        """Test that healthy OAuth account does not appear in scan results."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        healthy_account = MockEmailAccount.create_healthy_oauth(
            email="healthy@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [healthy_account]

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        corrupted_accounts = service.scan_corrupted_accounts()

        # Assert
        self.assertEqual(len(corrupted_accounts), 0)

    def test_healthy_oauth_account_not_updated_during_restoration(self):
        """Test that healthy OAuth account is not updated during restoration."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        healthy_account = MockEmailAccount.create_healthy_oauth(
            email="healthy@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [healthy_account]

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        restored_count = service.restore_corrupted_accounts()

        # Assert
        self.assertEqual(restored_count, 0)
        mock_repository.update_account_auth_method.assert_not_called()


# ============================================================================
# Test: True IMAP Account Not Modified
# ============================================================================

class TestTrueIMAPAccountNotModified(unittest.TestCase):
    """Tests for Scenario: True IMAP account without OAuth token is not modified.

    Given an account "true-imap@gmail.com" has:
      | auth_method          | imap                     |
      | oauth_refresh_token  | null                     |
      | app_password         | valid-app-password       |
    When the restoration process runs
    Then the account "true-imap@gmail.com" should still have auth_method "imap"
    And the account should not be flagged as corrupted
    """

    def test_true_imap_account_not_identified_as_corrupted(self):
        """Test that true IMAP account (no oauth token) is NOT corrupted."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        service = OAuthAccountRestorationService(repository=mock_repository)

        true_imap_account = MockEmailAccount.create_true_imap(
            email="true-imap@gmail.com",
            password="valid-app-password",
            account_id=1
        )

        # Act
        is_corrupted = service.is_account_corrupted(true_imap_account)

        # Assert
        self.assertFalse(
            is_corrupted,
            "True IMAP account (no oauth_refresh_token) should NOT be corrupted"
        )

    def test_true_imap_account_not_in_scan_results(self):
        """Test that true IMAP account does not appear in scan results."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        true_imap_account = MockEmailAccount.create_true_imap(
            email="true-imap@gmail.com",
            password="valid-app-password",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [true_imap_account]

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        corrupted_accounts = service.scan_corrupted_accounts()

        # Assert
        self.assertEqual(len(corrupted_accounts), 0)

    def test_true_imap_account_not_updated_during_restoration(self):
        """Test that true IMAP account is not updated during restoration."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        true_imap_account = MockEmailAccount.create_true_imap(
            email="true-imap@gmail.com",
            password="valid-app-password",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [true_imap_account]

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        restored_count = service.restore_corrupted_accounts()

        # Assert
        self.assertEqual(restored_count, 0)
        mock_repository.update_account_auth_method.assert_not_called()


# ============================================================================
# Test: Empty OAuth Refresh Token Not Modified
# ============================================================================

class TestEmptyOAuthRefreshTokenNotModified(unittest.TestCase):
    """Tests for Scenario: Account with empty oauth_refresh_token is not modified.

    Given an account "empty-token@gmail.com" has:
      | auth_method          | imap                     |
      | oauth_refresh_token  | empty string             |
    When the restoration process runs
    Then the account "empty-token@gmail.com" should still have auth_method "imap"
    """

    def test_empty_token_account_not_identified_as_corrupted(self):
        """Test that account with empty oauth_refresh_token is NOT corrupted."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        service = OAuthAccountRestorationService(repository=mock_repository)

        empty_token_account = MockEmailAccount(
            id=1,
            email_address="empty-token@gmail.com",
            auth_method="imap",
            oauth_refresh_token="",  # Empty string
            app_password=None,
            updated_at=datetime.now(timezone.utc)
        )

        # Act
        is_corrupted = service.is_account_corrupted(empty_token_account)

        # Assert
        self.assertFalse(
            is_corrupted,
            "Account with empty oauth_refresh_token should NOT be corrupted"
        )

    def test_empty_token_account_not_in_scan_results(self):
        """Test that empty token account does not appear in scan results."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        empty_token_account = MockEmailAccount(
            id=1,
            email_address="empty-token@gmail.com",
            auth_method="imap",
            oauth_refresh_token="",
            app_password=None,
            updated_at=datetime.now(timezone.utc)
        )
        mock_repository.get_all_accounts.return_value = [empty_token_account]

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        corrupted_accounts = service.scan_corrupted_accounts()

        # Assert
        self.assertEqual(len(corrupted_accounts), 0)

    def test_empty_token_account_not_updated_during_restoration(self):
        """Test that empty token account is not updated during restoration."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        empty_token_account = MockEmailAccount(
            id=1,
            email_address="empty-token@gmail.com",
            auth_method="imap",
            oauth_refresh_token="",
            app_password=None,
            updated_at=datetime.now(timezone.utc)
        )
        mock_repository.get_all_accounts.return_value = [empty_token_account]

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        restored_count = service.restore_corrupted_accounts()

        # Assert
        self.assertEqual(restored_count, 0)
        mock_repository.update_account_auth_method.assert_not_called()


# ============================================================================
# Test: Idempotent Restoration
# ============================================================================

class TestRestorationIsIdempotent(unittest.TestCase):
    """Tests for Scenario: Restoration is idempotent - running twice has no additional effect.

    Given an account "corrupted@gmail.com" has:
      | auth_method          | imap                     |
      | oauth_refresh_token  | valid-refresh-token      |
    When the restoration process runs
    And the restoration process runs again
    Then the account "corrupted@gmail.com" should have auth_method "oauth"
    And the second run should report 0 accounts restored
    """

    def test_first_run_restores_corrupted_account(self):
        """Test that first run restores the corrupted account."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        corrupted_account = MockEmailAccount.create_corrupted(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [corrupted_account]
        mock_repository.update_account_auth_method.return_value = True

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        first_run_count = service.restore_corrupted_accounts()

        # Assert
        self.assertEqual(first_run_count, 1)

    def test_second_run_reports_zero_accounts_restored(self):
        """Test that second run reports 0 accounts restored."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()

        # First run: corrupted account
        corrupted_account = MockEmailAccount.create_corrupted(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )

        # After first run: account is now healthy
        healthy_account = MockEmailAccount.create_healthy_oauth(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )

        # First call returns corrupted, second call returns healthy
        mock_repository.get_all_accounts.side_effect = [
            [corrupted_account],
            [healthy_account]
        ]
        mock_repository.update_account_auth_method.return_value = True

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act: First run
        first_run_count = service.restore_corrupted_accounts()

        # Act: Second run
        second_run_count = service.restore_corrupted_accounts()

        # Assert
        self.assertEqual(first_run_count, 1)
        self.assertEqual(
            second_run_count,
            0,
            "Second run should report 0 accounts restored"
        )


# ============================================================================
# Test: Legacy Account with Null Auth Method
# ============================================================================

class TestLegacyAccountNotModified(unittest.TestCase):
    """Tests for Scenario: Legacy account with null auth_method and no OAuth token is not modified.

    Given an account "legacy@gmail.com" has:
      | auth_method          | null                     |
      | oauth_refresh_token  | null                     |
    When the restoration process runs
    Then the account "legacy@gmail.com" should not be modified
    """

    def test_legacy_account_not_identified_as_corrupted(self):
        """Test that legacy account with null auth_method is NOT corrupted."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        service = OAuthAccountRestorationService(repository=mock_repository)

        legacy_account = MockEmailAccount(
            id=1,
            email_address="legacy@gmail.com",
            auth_method=None,  # Null auth_method
            oauth_refresh_token=None,  # Null oauth_refresh_token
            app_password=None,
            updated_at=datetime.now(timezone.utc)
        )

        # Act
        is_corrupted = service.is_account_corrupted(legacy_account)

        # Assert
        self.assertFalse(
            is_corrupted,
            "Legacy account with null auth_method should NOT be corrupted"
        )

    def test_legacy_account_not_in_scan_results(self):
        """Test that legacy account does not appear in scan results."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        legacy_account = MockEmailAccount(
            id=1,
            email_address="legacy@gmail.com",
            auth_method=None,
            oauth_refresh_token=None,
            app_password=None,
            updated_at=datetime.now(timezone.utc)
        )
        mock_repository.get_all_accounts.return_value = [legacy_account]

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        corrupted_accounts = service.scan_corrupted_accounts()

        # Assert
        self.assertEqual(len(corrupted_accounts), 0)

    def test_legacy_account_not_updated_during_restoration(self):
        """Test that legacy account is not updated during restoration."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        legacy_account = MockEmailAccount(
            id=1,
            email_address="legacy@gmail.com",
            auth_method=None,
            oauth_refresh_token=None,
            app_password=None,
            updated_at=datetime.now(timezone.utc)
        )
        mock_repository.get_all_accounts.return_value = [legacy_account]

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        restored_count = service.restore_corrupted_accounts()

        # Assert
        self.assertEqual(restored_count, 0)
        mock_repository.update_account_auth_method.assert_not_called()


# ============================================================================
# Test: Database Error Handling
# ============================================================================

class TestDatabaseErrorHandling(unittest.TestCase):
    """Tests for Scenario: Database error during restoration is handled gracefully.

    Given corrupted accounts exist in the database
    And the database becomes unavailable during restoration
    When the restoration process runs
    Then an error should be logged
    And the restoration should be rolled back
    And no accounts should be partially modified
    """

    @patch('services.oauth_account_restoration_service.get_logger')
    def test_database_error_is_logged(self, mock_get_logger):
        """Test that database errors are logged."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_repository = MagicMock()
        corrupted_account = MockEmailAccount.create_corrupted(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [corrupted_account]
        mock_repository.update_account_auth_method.side_effect = Exception(
            "Database connection lost"
        )

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        try:
            service.restore_corrupted_accounts()
        except Exception:
            pass  # We expect an exception

        # Assert: Error was logged
        error_logged = False
        for log_call in mock_logger.error.call_args_list:
            if "database" in str(log_call).lower() or "error" in str(log_call).lower():
                error_logged = True
                break

        self.assertTrue(
            error_logged,
            "Database errors should be logged"
        )

    def test_database_error_raises_exception(self):
        """Test that database errors raise an exception for rollback."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        corrupted_account = MockEmailAccount.create_corrupted(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [corrupted_account]
        mock_repository.update_account_auth_method.side_effect = Exception(
            "Database connection lost"
        )

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act & Assert: Should raise exception
        with self.assertRaises(Exception) as context:
            service.restore_corrupted_accounts()

        self.assertIn(
            "Database",
            str(context.exception),
            "Exception should indicate database error"
        )

    def test_database_scan_error_raises_exception(self):
        """Test that database errors during scan raise an exception."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        mock_repository.get_all_accounts.side_effect = Exception(
            "Database unavailable"
        )

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act & Assert: Should raise exception
        with self.assertRaises(Exception):
            service.scan_corrupted_accounts()


# ============================================================================
# Test: Audit Logging
# ============================================================================

class TestRestorationAuditLogging(unittest.TestCase):
    """Tests for Scenario: Restoration logs detailed information for audit.

    Given an account "corrupted@gmail.com" has:
      | auth_method          | imap                     |
      | oauth_refresh_token  | valid-refresh-token      |
    When the restoration process runs
    Then the log should include:
      | field        | value                    |
      | email        | corrupted@gmail.com      |
      | old_method   | imap                     |
      | new_method   | oauth                    |
      | timestamp    | restoration time         |
    """

    @patch('services.oauth_account_restoration_service.get_logger')
    def test_restoration_logs_email_address(self, mock_get_logger):
        """Test that restoration logs the email address."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_repository = MagicMock()
        corrupted_account = MockEmailAccount.create_corrupted(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [corrupted_account]
        mock_repository.update_account_auth_method.return_value = True

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        service.restore_corrupted_accounts()

        # Assert: Email was logged
        log_calls = " ".join(str(c) for c in mock_logger.info.call_args_list)
        self.assertIn(
            "corrupted@gmail.com",
            log_calls,
            "Log should include the email address"
        )

    @patch('services.oauth_account_restoration_service.get_logger')
    def test_restoration_logs_old_auth_method(self, mock_get_logger):
        """Test that restoration logs the old auth method."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_repository = MagicMock()
        corrupted_account = MockEmailAccount.create_corrupted(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [corrupted_account]
        mock_repository.update_account_auth_method.return_value = True

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        service.restore_corrupted_accounts()

        # Assert: Old method was logged
        log_calls = " ".join(str(c) for c in mock_logger.info.call_args_list)
        self.assertIn(
            "imap",
            log_calls.lower(),
            "Log should include the old auth_method 'imap'"
        )

    @patch('services.oauth_account_restoration_service.get_logger')
    def test_restoration_logs_new_auth_method(self, mock_get_logger):
        """Test that restoration logs the new auth method."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_repository = MagicMock()
        corrupted_account = MockEmailAccount.create_corrupted(
            email="corrupted@gmail.com",
            token="valid-refresh-token",
            account_id=1
        )
        mock_repository.get_all_accounts.return_value = [corrupted_account]
        mock_repository.update_account_auth_method.return_value = True

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        service.restore_corrupted_accounts()

        # Assert: New method was logged
        log_calls = " ".join(str(c) for c in mock_logger.info.call_args_list)
        self.assertIn(
            "oauth",
            log_calls.lower(),
            "Log should include the new auth_method 'oauth'"
        )

    @patch('services.oauth_account_restoration_service.get_logger')
    def test_restoration_logs_total_count(self, mock_get_logger):
        """Test that restoration logs the total restoration count."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_repository = MagicMock()
        corrupted_accounts = [
            MockEmailAccount.create_corrupted("user1@gmail.com", "token-1", 1),
            MockEmailAccount.create_corrupted("user2@gmail.com", "token-2", 2),
            MockEmailAccount.create_corrupted("user3@gmail.com", "token-3", 3),
        ]
        mock_repository.get_all_accounts.return_value = corrupted_accounts
        mock_repository.update_account_auth_method.return_value = True

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        service.restore_corrupted_accounts()

        # Assert: Total count was logged
        log_calls = " ".join(str(c) for c in mock_logger.info.call_args_list)
        self.assertIn(
            "3",
            log_calls,
            "Log should include the total count of restored accounts"
        )


# ============================================================================
# Test: Mixed Account Types
# ============================================================================

class TestMixedAccountTypes(unittest.TestCase):
    """Tests for mixed account types - only corrupted accounts should be restored."""

    def test_only_corrupted_accounts_restored_in_mixed_list(self):
        """Test that only corrupted accounts are restored when mixed with healthy ones."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        mixed_accounts = [
            MockEmailAccount.create_corrupted("corrupted1@gmail.com", "token-1", 1),
            MockEmailAccount.create_healthy_oauth("healthy@gmail.com", "token-2", 2),
            MockEmailAccount.create_true_imap("imap@gmail.com", "password", 3),
            MockEmailAccount.create_corrupted("corrupted2@gmail.com", "token-4", 4),
            MockEmailAccount(
                id=5,
                email_address="empty@gmail.com",
                auth_method="imap",
                oauth_refresh_token="",  # Empty
                app_password=None,
                updated_at=datetime.now(timezone.utc)
            ),
            MockEmailAccount(
                id=6,
                email_address="legacy@gmail.com",
                auth_method=None,  # Null
                oauth_refresh_token=None,
                app_password=None,
                updated_at=datetime.now(timezone.utc)
            ),
        ]
        mock_repository.get_all_accounts.return_value = mixed_accounts
        mock_repository.update_account_auth_method.return_value = True

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        restored_count = service.restore_corrupted_accounts()

        # Assert: Only 2 corrupted accounts should be restored
        self.assertEqual(restored_count, 2)
        self.assertEqual(
            mock_repository.update_account_auth_method.call_count,
            2
        )

        # Verify correct accounts were updated
        updated_emails = [
            call[0][0]
            for call in mock_repository.update_account_auth_method.call_args_list
        ]
        self.assertIn("corrupted1@gmail.com", updated_emails)
        self.assertIn("corrupted2@gmail.com", updated_emails)
        self.assertNotIn("healthy@gmail.com", updated_emails)
        self.assertNotIn("imap@gmail.com", updated_emails)
        self.assertNotIn("empty@gmail.com", updated_emails)
        self.assertNotIn("legacy@gmail.com", updated_emails)

    def test_scan_finds_only_corrupted_accounts_in_mixed_list(self):
        """Test that scan only finds corrupted accounts in mixed list."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        mixed_accounts = [
            MockEmailAccount.create_corrupted("corrupted@gmail.com", "token-1", 1),
            MockEmailAccount.create_healthy_oauth("healthy@gmail.com", "token-2", 2),
            MockEmailAccount.create_true_imap("imap@gmail.com", "password", 3),
        ]
        mock_repository.get_all_accounts.return_value = mixed_accounts

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        corrupted_accounts = service.scan_corrupted_accounts()

        # Assert
        self.assertEqual(len(corrupted_accounts), 1)
        self.assertEqual(
            corrupted_accounts[0]["email"],
            "corrupted@gmail.com"
        )


# ============================================================================
# Test: Service Constructor
# ============================================================================

class TestServiceConstructor(unittest.TestCase):
    """Tests for service constructor and dependency injection."""

    def test_service_accepts_repository_injection(self):
        """Test that service accepts repository via constructor injection."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()

        # Act
        service = OAuthAccountRestorationService(repository=mock_repository)

        # Assert
        self.assertIsNotNone(service)

    def test_service_uses_injected_repository(self):
        """Test that service uses the injected repository."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        mock_repository.get_all_accounts.return_value = []

        service = OAuthAccountRestorationService(repository=mock_repository)

        # Act
        service.scan_corrupted_accounts()

        # Assert: The injected repository was used
        mock_repository.get_all_accounts.assert_called_once()


# ============================================================================
# Test: Corrupted Account Detection Edge Cases
# ============================================================================

class TestCorruptedAccountDetectionEdgeCases(unittest.TestCase):
    """Additional edge case tests for corrupted account detection."""

    def test_whitespace_only_token_is_not_corrupted(self):
        """Test that whitespace-only oauth_refresh_token is treated as empty."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        service = OAuthAccountRestorationService(repository=mock_repository)

        whitespace_account = MockEmailAccount(
            id=1,
            email_address="whitespace@gmail.com",
            auth_method="imap",
            oauth_refresh_token="   ",  # Whitespace only
            app_password=None,
            updated_at=datetime.now(timezone.utc)
        )

        # Act
        is_corrupted = service.is_account_corrupted(whitespace_account)

        # Assert
        self.assertFalse(
            is_corrupted,
            "Account with whitespace-only oauth_refresh_token should NOT be corrupted"
        )

    def test_auth_method_case_sensitivity(self):
        """Test that auth_method check handles case variations."""
        from services.oauth_account_restoration_service import (
            OAuthAccountRestorationService
        )

        # Arrange
        mock_repository = MagicMock()
        service = OAuthAccountRestorationService(repository=mock_repository)

        # Test various case variations
        test_cases = [
            ("IMAP", True),   # Uppercase should be detected
            ("Imap", True),   # Mixed case should be detected
            ("OAUTH", False), # Already OAuth (uppercase)
            ("OAuth", False), # Already OAuth (mixed case)
        ]

        for auth_method, expected_corrupted in test_cases:
            account = MockEmailAccount(
                id=1,
                email_address="test@gmail.com",
                auth_method=auth_method,
                oauth_refresh_token="valid-token",
                app_password=None,
                updated_at=datetime.now(timezone.utc)
            )

            # Act
            is_corrupted = service.is_account_corrupted(account)

            # Assert
            self.assertEqual(
                is_corrupted,
                expected_corrupted,
                f"auth_method='{auth_method}' should be corrupted={expected_corrupted}"
            )


if __name__ == '__main__':
    unittest.main()
