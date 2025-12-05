"""
Tests for ProcessingStatusManager Audit Count Service Layer.

Based on BDD scenarios from tests/bdd/audit-counts-phase2-service-layer.feature:
- Scenario: Account status includes audit count fields with default values
- Scenario: Incrementing reviewed count during processing
- Scenario: Incrementing tagged count during processing
- Scenario: Incrementing deleted count during processing
- Scenario: Audit counts are preserved when processing completes
- Scenario: Incrementing counts without active session is ignored

These tests follow TDD approach (Red phase) - tests will FAIL until the
ProcessingStatusManager is updated with the required audit count methods.

The implementation should add to AccountStatus dataclass:
    emails_reviewed: int = 0
    emails_tagged: int = 0
    emails_deleted: int = 0

The implementation should add to ProcessingStatusManager:
    increment_reviewed(count: int = 1) -> None
    increment_tagged(count: int = 1) -> None
    increment_deleted(count: int = 1) -> None

And modify complete_processing() to include audit counts in archived run.
"""
import unittest
from unittest.mock import Mock, patch

from services.processing_status_manager import (
    ProcessingStatusManager,
    ProcessingState,
    AccountStatus,
)


class TestAccountStatusAuditCountFields(unittest.TestCase):
    """
    Scenario: Account status includes audit count fields with default values

    When a processing session starts for "user@example.com"
    Then the current status shows emails reviewed as 0
    And the current status shows emails tagged as 0
    And the current status shows emails deleted as 0
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        # Ensure no active session remains
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_account_status_has_emails_reviewed_field(self):
        """
        Test that AccountStatus dataclass has emails_reviewed field.

        The implementation should add to AccountStatus:
            emails_reviewed: int = 0
        """
        # Assert: AccountStatus has emails_reviewed attribute
        self.assertTrue(
            hasattr(AccountStatus, '__dataclass_fields__'),
            "AccountStatus should be a dataclass"
        )
        self.assertIn(
            'emails_reviewed',
            AccountStatus.__dataclass_fields__,
            "AccountStatus should have 'emails_reviewed' field"
        )

    def test_account_status_has_emails_tagged_field(self):
        """
        Test that AccountStatus dataclass has emails_tagged field.

        The implementation should add to AccountStatus:
            emails_tagged: int = 0
        """
        # Assert: AccountStatus has emails_tagged attribute
        self.assertIn(
            'emails_tagged',
            AccountStatus.__dataclass_fields__,
            "AccountStatus should have 'emails_tagged' field"
        )

    def test_account_status_has_emails_deleted_field(self):
        """
        Test that AccountStatus dataclass has emails_deleted field.

        The implementation should add to AccountStatus:
            emails_deleted: int = 0
        """
        # Assert: AccountStatus has emails_deleted attribute
        self.assertIn(
            'emails_deleted',
            AccountStatus.__dataclass_fields__,
            "AccountStatus should have 'emails_deleted' field"
        )

    def test_start_processing_initializes_emails_reviewed_to_zero(self):
        """
        Test that starting a processing session sets emails_reviewed to 0.

        When a processing session starts for "user@example.com"
        Then the current status shows emails reviewed as 0
        """
        # Arrange
        test_email = "user@example.com"

        # Act
        self.status_manager.start_processing(test_email)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertIsNotNone(status, "Status should not be None after starting processing")
        self.assertIn(
            'emails_reviewed',
            status,
            "Status should include 'emails_reviewed' field"
        )
        self.assertEqual(
            status['emails_reviewed'],
            0,
            f"emails_reviewed should be 0, got {status.get('emails_reviewed')}"
        )

    def test_start_processing_initializes_emails_tagged_to_zero(self):
        """
        Test that starting a processing session sets emails_tagged to 0.

        When a processing session starts for "user@example.com"
        Then the current status shows emails tagged as 0
        """
        # Arrange
        test_email = "user@example.com"

        # Act
        self.status_manager.start_processing(test_email)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertIsNotNone(status, "Status should not be None after starting processing")
        self.assertIn(
            'emails_tagged',
            status,
            "Status should include 'emails_tagged' field"
        )
        self.assertEqual(
            status['emails_tagged'],
            0,
            f"emails_tagged should be 0, got {status.get('emails_tagged')}"
        )

    def test_start_processing_initializes_emails_deleted_to_zero(self):
        """
        Test that starting a processing session sets emails_deleted to 0.

        When a processing session starts for "user@example.com"
        Then the current status shows emails deleted as 0
        """
        # Arrange
        test_email = "user@example.com"

        # Act
        self.status_manager.start_processing(test_email)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertIsNotNone(status, "Status should not be None after starting processing")
        self.assertIn(
            'emails_deleted',
            status,
            "Status should include 'emails_deleted' field"
        )
        self.assertEqual(
            status['emails_deleted'],
            0,
            f"emails_deleted should be 0, got {status.get('emails_deleted')}"
        )


class TestIncrementReviewedCount(unittest.TestCase):
    """
    Scenario: Incrementing reviewed count during processing

    Given a processing session is active for "user@example.com"
    When 5 emails are marked as reviewed
    And 3 more emails are marked as reviewed
    Then the current status shows emails reviewed as 8
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_processing_status_manager_has_increment_reviewed_method(self):
        """
        Test that ProcessingStatusManager has increment_reviewed method.

        The implementation should add:
            def increment_reviewed(self, count: int = 1) -> None:
        """
        # Assert: Method exists
        self.assertTrue(
            hasattr(self.status_manager, 'increment_reviewed'),
            "ProcessingStatusManager should have 'increment_reviewed' method"
        )
        self.assertTrue(
            callable(getattr(self.status_manager, 'increment_reviewed')),
            "'increment_reviewed' should be callable"
        )

    def test_increment_reviewed_by_one(self):
        """
        Test that increment_reviewed() increments emails_reviewed by 1.

        Given a processing session is active
        When 1 email is marked as reviewed
        Then emails_reviewed should be 1
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_reviewed(1)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_reviewed'],
            1,
            f"emails_reviewed should be 1 after one increment, got {status.get('emails_reviewed')}"
        )

    def test_increment_reviewed_by_multiple(self):
        """
        Test that increment_reviewed(5) increments emails_reviewed by 5.

        Given a processing session is active
        When 5 emails are marked as reviewed
        Then emails_reviewed should be 5
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_reviewed(5)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_reviewed'],
            5,
            f"emails_reviewed should be 5, got {status.get('emails_reviewed')}"
        )

    def test_multiple_increments_accumulate_reviewed(self):
        """
        Test that multiple increment_reviewed calls accumulate correctly.

        Given a processing session is active for "user@example.com"
        When 5 emails are marked as reviewed
        And 3 more emails are marked as reviewed
        Then the current status shows emails reviewed as 8
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_reviewed(5)
        self.status_manager.increment_reviewed(3)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_reviewed'],
            8,
            f"emails_reviewed should be 8 after 5+3 increments, got {status.get('emails_reviewed')}"
        )


class TestIncrementTaggedCount(unittest.TestCase):
    """
    Scenario: Incrementing tagged count during processing

    Given a processing session is active for "user@example.com"
    When 4 emails are marked as tagged
    Then the current status shows emails tagged as 4
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_processing_status_manager_has_increment_tagged_method(self):
        """
        Test that ProcessingStatusManager has increment_tagged method.

        The implementation should add:
            def increment_tagged(self, count: int = 1) -> None:
        """
        # Assert: Method exists
        self.assertTrue(
            hasattr(self.status_manager, 'increment_tagged'),
            "ProcessingStatusManager should have 'increment_tagged' method"
        )
        self.assertTrue(
            callable(getattr(self.status_manager, 'increment_tagged')),
            "'increment_tagged' should be callable"
        )

    def test_increment_tagged_by_one(self):
        """
        Test that increment_tagged() increments emails_tagged by 1.

        Given a processing session is active
        When 1 email is marked as tagged
        Then emails_tagged should be 1
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_tagged(1)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_tagged'],
            1,
            f"emails_tagged should be 1 after one increment, got {status.get('emails_tagged')}"
        )

    def test_increment_tagged_by_multiple(self):
        """
        Test that increment_tagged(4) increments emails_tagged by 4.

        Given a processing session is active for "user@example.com"
        When 4 emails are marked as tagged
        Then the current status shows emails tagged as 4
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_tagged(4)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_tagged'],
            4,
            f"emails_tagged should be 4, got {status.get('emails_tagged')}"
        )

    def test_multiple_increments_accumulate_tagged(self):
        """
        Test that multiple increment_tagged calls accumulate correctly.

        Given a processing session is active
        When 2 emails are marked as tagged
        And 3 more emails are marked as tagged
        Then emails_tagged should be 5
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_tagged(2)
        self.status_manager.increment_tagged(3)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_tagged'],
            5,
            f"emails_tagged should be 5 after 2+3 increments, got {status.get('emails_tagged')}"
        )


class TestIncrementDeletedCount(unittest.TestCase):
    """
    Scenario: Incrementing deleted count during processing

    Given a processing session is active for "user@example.com"
    When 2 emails are marked as deleted
    Then the current status shows emails deleted as 2
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_processing_status_manager_has_increment_deleted_method(self):
        """
        Test that ProcessingStatusManager has increment_deleted method.

        The implementation should add:
            def increment_deleted(self, count: int = 1) -> None:
        """
        # Assert: Method exists
        self.assertTrue(
            hasattr(self.status_manager, 'increment_deleted'),
            "ProcessingStatusManager should have 'increment_deleted' method"
        )
        self.assertTrue(
            callable(getattr(self.status_manager, 'increment_deleted')),
            "'increment_deleted' should be callable"
        )

    def test_increment_deleted_by_one(self):
        """
        Test that increment_deleted() increments emails_deleted by 1.

        Given a processing session is active
        When 1 email is marked as deleted
        Then emails_deleted should be 1
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_deleted(1)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_deleted'],
            1,
            f"emails_deleted should be 1 after one increment, got {status.get('emails_deleted')}"
        )

    def test_increment_deleted_by_multiple(self):
        """
        Test that increment_deleted(2) increments emails_deleted by 2.

        Given a processing session is active for "user@example.com"
        When 2 emails are marked as deleted
        Then the current status shows emails deleted as 2
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_deleted(2)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_deleted'],
            2,
            f"emails_deleted should be 2, got {status.get('emails_deleted')}"
        )

    def test_multiple_increments_accumulate_deleted(self):
        """
        Test that multiple increment_deleted calls accumulate correctly.

        Given a processing session is active
        When 1 email is marked as deleted
        And 3 more emails are marked as deleted
        Then emails_deleted should be 4
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_deleted(1)
        self.status_manager.increment_deleted(3)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_deleted'],
            4,
            f"emails_deleted should be 4 after 1+3 increments, got {status.get('emails_deleted')}"
        )


class TestAuditCountsPreservedOnComplete(unittest.TestCase):
    """
    Scenario: Audit counts are preserved when processing completes

    Given a processing session is active for "user@example.com"
    And 100 emails are marked as reviewed
    And 50 emails are marked as tagged
    And 25 emails are marked as deleted
    When the processing session completes
    Then the most recent run shows emails reviewed as 100
    And the most recent run shows emails tagged as 50
    And the most recent run shows emails deleted as 25
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_archived_run_includes_emails_reviewed(self):
        """
        Test that completed run archive includes emails_reviewed.

        Given a processing session with 100 emails reviewed
        When the session completes
        Then the archived run should have emails_reviewed = 100
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")
        self.status_manager.increment_reviewed(100)

        # Act
        self.status_manager.complete_processing()
        recent_runs = self.status_manager.get_recent_runs(limit=1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]
        self.assertIn(
            'emails_reviewed',
            archived_run,
            "Archived run should include 'emails_reviewed' field"
        )
        self.assertEqual(
            archived_run['emails_reviewed'],
            100,
            f"Archived emails_reviewed should be 100, got {archived_run.get('emails_reviewed')}"
        )

    def test_archived_run_includes_emails_tagged(self):
        """
        Test that completed run archive includes emails_tagged.

        Given a processing session with 50 emails tagged
        When the session completes
        Then the archived run should have emails_tagged = 50
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")
        self.status_manager.increment_tagged(50)

        # Act
        self.status_manager.complete_processing()
        recent_runs = self.status_manager.get_recent_runs(limit=1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]
        self.assertIn(
            'emails_tagged',
            archived_run,
            "Archived run should include 'emails_tagged' field"
        )
        self.assertEqual(
            archived_run['emails_tagged'],
            50,
            f"Archived emails_tagged should be 50, got {archived_run.get('emails_tagged')}"
        )

    def test_archived_run_includes_emails_deleted(self):
        """
        Test that completed run archive includes emails_deleted.

        Given a processing session with 25 emails deleted
        When the session completes
        Then the archived run should have emails_deleted = 25
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")
        self.status_manager.increment_deleted(25)

        # Act
        self.status_manager.complete_processing()
        recent_runs = self.status_manager.get_recent_runs(limit=1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]
        self.assertIn(
            'emails_deleted',
            archived_run,
            "Archived run should include 'emails_deleted' field"
        )
        self.assertEqual(
            archived_run['emails_deleted'],
            25,
            f"Archived emails_deleted should be 25, got {archived_run.get('emails_deleted')}"
        )

    def test_archived_run_includes_all_audit_counts(self):
        """
        Test that completed run archive includes all three audit counts.

        Given a processing session is active for "user@example.com"
        And 100 emails are marked as reviewed
        And 50 emails are marked as tagged
        And 25 emails are marked as deleted
        When the processing session completes
        Then the most recent run shows emails reviewed as 100
        And the most recent run shows emails tagged as 50
        And the most recent run shows emails deleted as 25
        """
        # Arrange
        expected_reviewed = 100
        expected_tagged = 50
        expected_deleted = 25

        self.status_manager.start_processing("user@example.com")
        self.status_manager.increment_reviewed(expected_reviewed)
        self.status_manager.increment_tagged(expected_tagged)
        self.status_manager.increment_deleted(expected_deleted)

        # Act
        self.status_manager.complete_processing()
        recent_runs = self.status_manager.get_recent_runs(limit=1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]

        self.assertEqual(
            archived_run.get('emails_reviewed'),
            expected_reviewed,
            f"Archived emails_reviewed should be {expected_reviewed}, got {archived_run.get('emails_reviewed')}"
        )
        self.assertEqual(
            archived_run.get('emails_tagged'),
            expected_tagged,
            f"Archived emails_tagged should be {expected_tagged}, got {archived_run.get('emails_tagged')}"
        )
        self.assertEqual(
            archived_run.get('emails_deleted'),
            expected_deleted,
            f"Archived emails_deleted should be {expected_deleted}, got {archived_run.get('emails_deleted')}"
        )


class TestIncrementCountsWithoutActiveSession(unittest.TestCase):
    """
    Scenario: Incrementing counts without active session is ignored

    When 5 emails are marked as reviewed without an active session
    And 3 emails are marked as tagged without an active session
    And 2 emails are marked as deleted without an active session
    Then no error occurs
    And the audit counts return all zeros
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_increment_reviewed_without_session_does_not_raise(self):
        """
        Test that increment_reviewed without active session does not raise an error.

        When 5 emails are marked as reviewed without an active session
        Then no error occurs
        """
        # Arrange: Ensure no active session
        self.assertFalse(
            self.status_manager.is_processing(),
            "Should not have active session at start of test"
        )

        # Act & Assert: Should not raise
        try:
            self.status_manager.increment_reviewed(5)
        except Exception as e:
            self.fail(
                f"increment_reviewed should not raise exception without active session, got: {e}"
            )

    def test_increment_tagged_without_session_does_not_raise(self):
        """
        Test that increment_tagged without active session does not raise an error.

        When 3 emails are marked as tagged without an active session
        Then no error occurs
        """
        # Arrange: Ensure no active session
        self.assertFalse(
            self.status_manager.is_processing(),
            "Should not have active session at start of test"
        )

        # Act & Assert: Should not raise
        try:
            self.status_manager.increment_tagged(3)
        except Exception as e:
            self.fail(
                f"increment_tagged should not raise exception without active session, got: {e}"
            )

    def test_increment_deleted_without_session_does_not_raise(self):
        """
        Test that increment_deleted without active session does not raise an error.

        When 2 emails are marked as deleted without an active session
        Then no error occurs
        """
        # Arrange: Ensure no active session
        self.assertFalse(
            self.status_manager.is_processing(),
            "Should not have active session at start of test"
        )

        # Act & Assert: Should not raise
        try:
            self.status_manager.increment_deleted(2)
        except Exception as e:
            self.fail(
                f"increment_deleted should not raise exception without active session, got: {e}"
            )

    def test_all_increments_without_session_no_error(self):
        """
        Test that all increment methods without active session do not raise errors.

        When 5 emails are marked as reviewed without an active session
        And 3 emails are marked as tagged without an active session
        And 2 emails are marked as deleted without an active session
        Then no error occurs
        """
        # Arrange: Ensure no active session
        self.assertFalse(
            self.status_manager.is_processing(),
            "Should not have active session at start of test"
        )

        # Act & Assert: All should complete without error
        try:
            self.status_manager.increment_reviewed(5)
            self.status_manager.increment_tagged(3)
            self.status_manager.increment_deleted(2)
        except Exception as e:
            self.fail(
                f"increment methods should not raise exception without active session, got: {e}"
            )

    def test_get_current_status_returns_none_without_session(self):
        """
        Test that get_current_status returns None when there is no active session.

        This confirms that audit counts are not accessible without a session.
        """
        # Arrange: Ensure no active session
        self.assertFalse(
            self.status_manager.is_processing(),
            "Should not have active session at start of test"
        )

        # Act
        status = self.status_manager.get_current_status()

        # Assert
        self.assertIsNone(
            status,
            "get_current_status should return None without active session"
        )

    def test_increments_without_session_do_not_affect_next_session(self):
        """
        Test that increments without session do not carry over to next session.

        When increments are called without active session
        And then a new session starts
        Then the new session should have all audit counts at 0
        """
        # Arrange: Call increments without session
        self.status_manager.increment_reviewed(5)
        self.status_manager.increment_tagged(3)
        self.status_manager.increment_deleted(2)

        # Act: Start a new session
        self.status_manager.start_processing("new@example.com")
        status = self.status_manager.get_current_status()

        # Assert: All counts should be 0
        self.assertEqual(
            status.get('emails_reviewed'),
            0,
            f"emails_reviewed should be 0 for new session, got {status.get('emails_reviewed')}"
        )
        self.assertEqual(
            status.get('emails_tagged'),
            0,
            f"emails_tagged should be 0 for new session, got {status.get('emails_tagged')}"
        )
        self.assertEqual(
            status.get('emails_deleted'),
            0,
            f"emails_deleted should be 0 for new session, got {status.get('emails_deleted')}"
        )


class TestAccountStatusToDictIncludesAuditCounts(unittest.TestCase):
    """
    Test that AccountStatus.to_dict() includes audit count fields.

    This ensures the audit counts are serializable for API responses.
    """

    def test_to_dict_includes_emails_reviewed(self):
        """
        Test that AccountStatus.to_dict() includes emails_reviewed field.

        The implementation should ensure to_dict() returns emails_reviewed.
        """
        # Arrange
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.PROCESSING,
            current_step="Testing"
        )

        # Act
        result = status.to_dict()

        # Assert
        self.assertIn(
            'emails_reviewed',
            result,
            "to_dict() should include 'emails_reviewed' field"
        )

    def test_to_dict_includes_emails_tagged(self):
        """
        Test that AccountStatus.to_dict() includes emails_tagged field.

        The implementation should ensure to_dict() returns emails_tagged.
        """
        # Arrange
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.PROCESSING,
            current_step="Testing"
        )

        # Act
        result = status.to_dict()

        # Assert
        self.assertIn(
            'emails_tagged',
            result,
            "to_dict() should include 'emails_tagged' field"
        )

    def test_to_dict_includes_emails_deleted(self):
        """
        Test that AccountStatus.to_dict() includes emails_deleted field.

        The implementation should ensure to_dict() returns emails_deleted.
        """
        # Arrange
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.PROCESSING,
            current_step="Testing"
        )

        # Act
        result = status.to_dict()

        # Assert
        self.assertIn(
            'emails_deleted',
            result,
            "to_dict() should include 'emails_deleted' field"
        )


if __name__ == '__main__':
    unittest.main()
