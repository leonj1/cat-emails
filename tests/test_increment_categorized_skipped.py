"""
Tests for ProcessingStatusManager increment_categorized and increment_skipped methods.

Based on BDD scenarios from tests/bdd/increment_methods_audit_records.feature:
- Scenario: Increment categorized count with default value
- Scenario: Increment skipped count with batch value
- Scenario: Increment is silent when no session is active
- Scenario: Increments are cumulative within a session

These tests follow TDD approach (Red phase) - tests will FAIL until the
ProcessingStatusManager is updated with the required increment methods.

The implementation should add to ProcessingStatusManager:
    increment_categorized(count: int) -> None
    increment_skipped(count: int) -> None

Following the exact pattern of increment_reviewed, increment_tagged, increment_deleted:
- Thread-safe using self._lock
- Silent no-op when no active session
- Cumulative increments within a session
"""
import unittest

from services.processing_status_manager import (
    ProcessingStatusManager,
    ProcessingState,
    AccountStatus,
)


class TestIncrementCategorizedDefaultValue(unittest.TestCase):
    """
    Scenario: Increment categorized count with default value

    Given an active processing session exists
    When the system records an email as categorized
    Then the categorized email count increases by one
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_processing_status_manager_has_increment_categorized_method(self):
        """
        Test that ProcessingStatusManager has increment_categorized method.

        The implementation should add:
            def increment_categorized(self, count: int) -> None:
        """
        # Assert: Method exists
        self.assertTrue(
            hasattr(self.status_manager, 'increment_categorized'),
            "ProcessingStatusManager should have 'increment_categorized' method"
        )
        self.assertTrue(
            callable(getattr(self.status_manager, 'increment_categorized')),
            "'increment_categorized' should be callable"
        )

    def test_increment_categorized_by_one(self):
        """
        Test that increment_categorized(1) increments emails_categorized by 1.

        Given an active processing session exists
        When the system records an email as categorized
        Then the categorized email count increases by one
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_categorized(1)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_categorized'],
            1,
            f"emails_categorized should be 1 after one increment, got {status.get('emails_categorized')}"
        )


class TestIncrementSkippedBatchValue(unittest.TestCase):
    """
    Scenario: Increment skipped count with batch value

    Given an active processing session exists
    When the system records five emails as skipped
    Then the skipped email count increases by five
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_processing_status_manager_has_increment_skipped_method(self):
        """
        Test that ProcessingStatusManager has increment_skipped method.

        The implementation should add:
            def increment_skipped(self, count: int) -> None:
        """
        # Assert: Method exists
        self.assertTrue(
            hasattr(self.status_manager, 'increment_skipped'),
            "ProcessingStatusManager should have 'increment_skipped' method"
        )
        self.assertTrue(
            callable(getattr(self.status_manager, 'increment_skipped')),
            "'increment_skipped' should be callable"
        )

    def test_increment_skipped_by_five(self):
        """
        Test that increment_skipped(5) increments emails_skipped by 5.

        Given an active processing session exists
        When the system records five emails as skipped
        Then the skipped email count increases by five
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_skipped(5)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_skipped'],
            5,
            f"emails_skipped should be 5, got {status.get('emails_skipped')}"
        )


class TestIncrementSilentWhenNoSession(unittest.TestCase):
    """
    Scenario: Increment is silent when no session is active

    Given no processing session is active
    When the system attempts to record an email as categorized
    Then no error occurs
    And no count is recorded
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_increment_categorized_without_session_does_not_raise(self):
        """
        Test that increment_categorized without active session does not raise an error.

        Given no processing session is active
        When the system attempts to record an email as categorized
        Then no error occurs
        """
        # Arrange: Ensure no active session
        self.assertFalse(
            self.status_manager.is_processing(),
            "Should not have active session at start of test"
        )

        # Act & Assert: Should not raise
        try:
            self.status_manager.increment_categorized(1)
        except Exception as e:
            self.fail(
                f"increment_categorized should not raise exception without active session, got: {e}"
            )

    def test_increment_skipped_without_session_does_not_raise(self):
        """
        Test that increment_skipped without active session does not raise an error.

        Given no processing session is active
        When the system attempts to record emails as skipped
        Then no error occurs
        """
        # Arrange: Ensure no active session
        self.assertFalse(
            self.status_manager.is_processing(),
            "Should not have active session at start of test"
        )

        # Act & Assert: Should not raise
        try:
            self.status_manager.increment_skipped(5)
        except Exception as e:
            self.fail(
                f"increment_skipped should not raise exception without active session, got: {e}"
            )

    def test_get_current_status_returns_none_without_session(self):
        """
        Test that get_current_status returns None when there is no active session.

        And no count is recorded (verified by status being None)
        """
        # Arrange: Ensure no active session
        self.assertFalse(
            self.status_manager.is_processing(),
            "Should not have active session at start of test"
        )

        # Attempt increments without session
        self.status_manager.increment_categorized(1)
        self.status_manager.increment_skipped(5)

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
        self.status_manager.increment_categorized(10)
        self.status_manager.increment_skipped(20)

        # Act: Start a new session
        self.status_manager.start_processing("new@example.com")
        status = self.status_manager.get_current_status()

        # Assert: All counts should be 0
        self.assertEqual(
            status.get('emails_categorized'),
            0,
            f"emails_categorized should be 0 for new session, got {status.get('emails_categorized')}"
        )
        self.assertEqual(
            status.get('emails_skipped'),
            0,
            f"emails_skipped should be 0 for new session, got {status.get('emails_skipped')}"
        )


class TestIncrementsCumulativeWithinSession(unittest.TestCase):
    """
    Scenario: Increments are cumulative within a session

    Given an active processing session exists
    When the system records three emails as categorized
    And the system records two more emails as categorized
    Then the categorized email count shows five total
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_multiple_increments_accumulate_categorized(self):
        """
        Test that multiple increment_categorized calls accumulate correctly.

        Given an active processing session exists
        When the system records three emails as categorized
        And the system records two more emails as categorized
        Then the categorized email count shows five total
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_categorized(3)
        self.status_manager.increment_categorized(2)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_categorized'],
            5,
            f"emails_categorized should be 5 after 3+2 increments, got {status.get('emails_categorized')}"
        )

    def test_multiple_increments_accumulate_skipped(self):
        """
        Test that multiple increment_skipped calls accumulate correctly.

        Given an active processing session exists
        When the system records 4 emails as skipped
        And the system records 6 more emails as skipped
        Then the skipped email count shows 10 total
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_skipped(4)
        self.status_manager.increment_skipped(6)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_skipped'],
            10,
            f"emails_skipped should be 10 after 4+6 increments, got {status.get('emails_skipped')}"
        )

    def test_mixed_increments_accumulate_independently(self):
        """
        Test that categorized and skipped increments are tracked independently.

        Given an active processing session exists
        When the system records multiple categorized and skipped emails
        Then each counter tracks its own total
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act
        self.status_manager.increment_categorized(2)
        self.status_manager.increment_skipped(3)
        self.status_manager.increment_categorized(1)
        self.status_manager.increment_skipped(2)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_categorized'],
            3,
            f"emails_categorized should be 3 (2+1), got {status.get('emails_categorized')}"
        )
        self.assertEqual(
            status['emails_skipped'],
            5,
            f"emails_skipped should be 5 (3+2), got {status.get('emails_skipped')}"
        )


class TestAuditCountsPreservedOnComplete(unittest.TestCase):
    """
    Test that categorized and skipped audit counts are preserved when processing completes.

    Given a processing session is active
    And emails are marked as categorized and skipped
    When the processing session completes
    Then the archived run shows the correct counts
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_archived_run_includes_emails_categorized(self):
        """
        Test that completed run archive includes emails_categorized.

        Given a processing session with 15 emails categorized
        When the session completes
        Then the archived run should have emails_categorized = 15
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")
        self.status_manager.increment_categorized(15)

        # Act
        self.status_manager.complete_processing()
        recent_runs = self.status_manager.get_recent_runs(limit=1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]
        self.assertIn(
            'emails_categorized',
            archived_run,
            "Archived run should include 'emails_categorized' field"
        )
        self.assertEqual(
            archived_run['emails_categorized'],
            15,
            f"Archived emails_categorized should be 15, got {archived_run.get('emails_categorized')}"
        )

    def test_archived_run_includes_emails_skipped(self):
        """
        Test that completed run archive includes emails_skipped.

        Given a processing session with 7 emails skipped
        When the session completes
        Then the archived run should have emails_skipped = 7
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")
        self.status_manager.increment_skipped(7)

        # Act
        self.status_manager.complete_processing()
        recent_runs = self.status_manager.get_recent_runs(limit=1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]
        self.assertIn(
            'emails_skipped',
            archived_run,
            "Archived run should include 'emails_skipped' field"
        )
        self.assertEqual(
            archived_run['emails_skipped'],
            7,
            f"Archived emails_skipped should be 7, got {archived_run.get('emails_skipped')}"
        )

    def test_archived_run_includes_both_categorized_and_skipped(self):
        """
        Test that completed run archive includes both categorized and skipped counts.

        Given a processing session with 20 categorized and 5 skipped
        When the session completes
        Then the archived run shows both counts correctly
        """
        # Arrange
        expected_categorized = 20
        expected_skipped = 5

        self.status_manager.start_processing("user@example.com")
        self.status_manager.increment_categorized(expected_categorized)
        self.status_manager.increment_skipped(expected_skipped)

        # Act
        self.status_manager.complete_processing()
        recent_runs = self.status_manager.get_recent_runs(limit=1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]

        self.assertEqual(
            archived_run.get('emails_categorized'),
            expected_categorized,
            f"Archived emails_categorized should be {expected_categorized}, got {archived_run.get('emails_categorized')}"
        )
        self.assertEqual(
            archived_run.get('emails_skipped'),
            expected_skipped,
            f"Archived emails_skipped should be {expected_skipped}, got {archived_run.get('emails_skipped')}"
        )


class TestAccountStatusToDictIncludesNewAuditCounts(unittest.TestCase):
    """
    Test that AccountStatus.to_dict() includes categorized and skipped fields.

    This ensures the new audit counts are serializable for API responses.
    """

    def test_to_dict_includes_emails_categorized(self):
        """
        Test that AccountStatus.to_dict() includes emails_categorized field.

        The implementation should ensure to_dict() returns emails_categorized.
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
            'emails_categorized',
            result,
            "to_dict() should include 'emails_categorized' field"
        )

    def test_to_dict_includes_emails_skipped(self):
        """
        Test that AccountStatus.to_dict() includes emails_skipped field.

        The implementation should ensure to_dict() returns emails_skipped.
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
            'emails_skipped',
            result,
            "to_dict() should include 'emails_skipped' field"
        )

    def test_account_status_has_emails_categorized_field(self):
        """
        Test that AccountStatus dataclass has emails_categorized field.

        The implementation should have in AccountStatus:
            emails_categorized: int = 0
        """
        # Assert: AccountStatus has emails_categorized attribute
        self.assertTrue(
            hasattr(AccountStatus, '__dataclass_fields__'),
            "AccountStatus should be a dataclass"
        )
        self.assertIn(
            'emails_categorized',
            AccountStatus.__dataclass_fields__,
            "AccountStatus should have 'emails_categorized' field"
        )

    def test_account_status_has_emails_skipped_field(self):
        """
        Test that AccountStatus dataclass has emails_skipped field.

        The implementation should have in AccountStatus:
            emails_skipped: int = 0
        """
        # Assert: AccountStatus has emails_skipped attribute
        self.assertIn(
            'emails_skipped',
            AccountStatus.__dataclass_fields__,
            "AccountStatus should have 'emails_skipped' field"
        )


class TestStartProcessingInitializesNewCounts(unittest.TestCase):
    """
    Test that starting a processing session initializes new audit counts to zero.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_start_processing_initializes_emails_categorized_to_zero(self):
        """
        Test that starting a processing session sets emails_categorized to 0.

        When a processing session starts for "user@example.com"
        Then the current status shows emails categorized as 0
        """
        # Arrange
        test_email = "user@example.com"

        # Act
        self.status_manager.start_processing(test_email)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertIsNotNone(status, "Status should not be None after starting processing")
        self.assertIn(
            'emails_categorized',
            status,
            "Status should include 'emails_categorized' field"
        )
        self.assertEqual(
            status['emails_categorized'],
            0,
            f"emails_categorized should be 0, got {status.get('emails_categorized')}"
        )

    def test_start_processing_initializes_emails_skipped_to_zero(self):
        """
        Test that starting a processing session sets emails_skipped to 0.

        When a processing session starts for "user@example.com"
        Then the current status shows emails skipped as 0
        """
        # Arrange
        test_email = "user@example.com"

        # Act
        self.status_manager.start_processing(test_email)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertIsNotNone(status, "Status should not be None after starting processing")
        self.assertIn(
            'emails_skipped',
            status,
            "Status should include 'emails_skipped' field"
        )
        self.assertEqual(
            status['emails_skipped'],
            0,
            f"emails_skipped should be 0, got {status.get('emails_skipped')}"
        )


if __name__ == '__main__':
    unittest.main()
