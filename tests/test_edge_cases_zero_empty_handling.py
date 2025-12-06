"""
Tests for edge cases in emails_categorized and emails_skipped audit fields.

Based on BDD scenarios from tests/bdd/enhance_audit_records.feature:
- Scenario: Audit record handles zero categorized emails
- Scenario: Audit record handles zero skipped emails
- Scenario: Audit record handles empty batch
- Scenario: New audit record initializes counts to zero

These tests cover edge cases for:
- Zero is stored as integer 0, not None
- Empty batch (increment with 0) is valid no-op
- Minimal session lifecycle produces valid archived run
- History isolation between runs
"""
import unittest

from services.processing_status_manager import (
    ProcessingStatusManager,
    ProcessingState,
    AccountStatus,
)


class TestZeroCountsInCompletedRuns(unittest.TestCase):
    """
    Scenario: Audit record handles zero categorized emails
    Scenario: Audit record handles zero skipped emails

    Given a processing session has started
    When all emails in the batch are skipped (or categorized)
    Then the emails_categorized (or emails_skipped) count should be 0
    And the other count should match the batch size

    Validates that zero is stored as integer 0, not None.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_archived_run_shows_zero_categorized_when_none_processed(self):
        """
        Test that archived run shows emails_categorized as 0 when all are skipped.

        Given a processing session has started
        When all emails in the batch are skipped
        Then the emails_categorized count should be 0
        And the emails_skipped count should match the batch size
        """
        # Arrange
        batch_size = 10
        self.status_manager.start_processing("user@example.com")

        # Act: All emails skipped, none categorized
        self.status_manager.increment_skipped(batch_size)
        self.status_manager.complete_processing()
        recent_runs = self.status_manager.get_recent_runs(limit=1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]

        self.assertEqual(
            archived_run['emails_categorized'],
            0,
            f"emails_categorized should be 0 when none processed, got {archived_run.get('emails_categorized')}"
        )
        self.assertEqual(
            archived_run['emails_skipped'],
            batch_size,
            f"emails_skipped should match batch size {batch_size}, got {archived_run.get('emails_skipped')}"
        )

    def test_archived_run_shows_zero_skipped_when_none_processed(self):
        """
        Test that archived run shows emails_skipped as 0 when all are categorized.

        Given a processing session has started
        When all emails in the batch are categorized successfully
        Then the emails_skipped count should be 0
        And the emails_categorized count should match the batch size
        """
        # Arrange
        batch_size = 15
        self.status_manager.start_processing("user@example.com")

        # Act: All emails categorized, none skipped
        self.status_manager.increment_categorized(batch_size)
        self.status_manager.complete_processing()
        recent_runs = self.status_manager.get_recent_runs(limit=1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]

        self.assertEqual(
            archived_run['emails_skipped'],
            0,
            f"emails_skipped should be 0 when none skipped, got {archived_run.get('emails_skipped')}"
        )
        self.assertEqual(
            archived_run['emails_categorized'],
            batch_size,
            f"emails_categorized should match batch size {batch_size}, got {archived_run.get('emails_categorized')}"
        )

    def test_archived_run_has_both_fields_as_zero_not_none(self):
        """
        Test that archived run has both fields as integer 0, not None.

        Validates that zero counts are stored as the integer value 0,
        not as None or any other falsy value.
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act: Complete session with no increments (empty batch)
        self.status_manager.complete_processing()
        recent_runs = self.status_manager.get_recent_runs(limit=1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]

        # Verify type is int, not None
        self.assertIsNotNone(
            archived_run['emails_categorized'],
            "emails_categorized should not be None"
        )
        self.assertIsNotNone(
            archived_run['emails_skipped'],
            "emails_skipped should not be None"
        )

        # Verify value is exactly 0
        self.assertIs(
            type(archived_run['emails_categorized']),
            int,
            f"emails_categorized should be int, got {type(archived_run['emails_categorized'])}"
        )
        self.assertIs(
            type(archived_run['emails_skipped']),
            int,
            f"emails_skipped should be int, got {type(archived_run['emails_skipped'])}"
        )

        self.assertEqual(archived_run['emails_categorized'], 0)
        self.assertEqual(archived_run['emails_skipped'], 0)


class TestEmptyBatchIncrement(unittest.TestCase):
    """
    Scenario: Audit record handles empty batch

    Given a processing session has started
    When an empty batch is processed
    Then the emails_categorized count should be 0
    And the emails_skipped count should be 0

    Validates that increment with 0 is a valid no-op.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_increment_categorized_with_zero_does_not_change_count(self):
        """
        Test that increment_categorized(0) does not change the count.

        When an empty batch is processed
        Then the emails_categorized count should remain 0
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")
        initial_status = self.status_manager.get_current_status()
        initial_count = initial_status['emails_categorized']

        # Act: Increment by 0 (empty batch)
        self.status_manager.increment_categorized(0)
        final_status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            final_status['emails_categorized'],
            initial_count,
            f"emails_categorized should remain {initial_count} after incrementing by 0, "
            f"got {final_status.get('emails_categorized')}"
        )

    def test_increment_skipped_with_zero_does_not_change_count(self):
        """
        Test that increment_skipped(0) does not change the count.

        When an empty batch is processed
        Then the emails_skipped count should remain 0
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")
        initial_status = self.status_manager.get_current_status()
        initial_count = initial_status['emails_skipped']

        # Act: Increment by 0 (empty batch)
        self.status_manager.increment_skipped(0)
        final_status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            final_status['emails_skipped'],
            initial_count,
            f"emails_skipped should remain {initial_count} after incrementing by 0, "
            f"got {final_status.get('emails_skipped')}"
        )

    def test_zero_increment_followed_by_nonzero_increment(self):
        """
        Test that zero increments do not affect subsequent non-zero increments.

        When zero increments are followed by non-zero increments
        Then only the non-zero values should be accumulated
        """
        # Arrange
        self.status_manager.start_processing("user@example.com")

        # Act: Mix of zero and non-zero increments
        self.status_manager.increment_categorized(0)
        self.status_manager.increment_categorized(5)
        self.status_manager.increment_categorized(0)
        self.status_manager.increment_categorized(3)

        self.status_manager.increment_skipped(0)
        self.status_manager.increment_skipped(2)
        self.status_manager.increment_skipped(0)

        status = self.status_manager.get_current_status()

        # Assert
        self.assertEqual(
            status['emails_categorized'],
            8,
            f"emails_categorized should be 8 (0+5+0+3), got {status.get('emails_categorized')}"
        )
        self.assertEqual(
            status['emails_skipped'],
            2,
            f"emails_skipped should be 2 (0+2+0), got {status.get('emails_skipped')}"
        )


class TestImmediateCompleteAfterStart(unittest.TestCase):
    """
    Scenario: New audit record initializes counts to zero

    Given no processing has occurred
    When a new processing session begins
    Then the initial emails_categorized count should be 0
    And the initial emails_skipped count should be 0

    Validates minimal session lifecycle produces valid archived run.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_start_then_complete_produces_valid_archived_run(self):
        """
        Test that starting and immediately completing produces a valid archived run.

        When a session starts and immediately completes
        Then the archived run should have valid zero counts
        """
        # Arrange & Act
        self.status_manager.start_processing("user@example.com")
        self.status_manager.complete_processing()

        recent_runs = self.status_manager.get_recent_runs(limit=1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]

        self.assertEqual(
            archived_run['emails_categorized'],
            0,
            f"emails_categorized should be 0 for immediate complete, got {archived_run.get('emails_categorized')}"
        )
        self.assertEqual(
            archived_run['emails_skipped'],
            0,
            f"emails_skipped should be 0 for immediate complete, got {archived_run.get('emails_skipped')}"
        )

    def test_immediate_complete_archived_run_has_all_required_keys(self):
        """
        Test that immediate complete produces archived run with all required keys.

        When a session starts and immediately completes
        Then the archived run should contain all required audit fields
        """
        # Arrange & Act
        self.status_manager.start_processing("user@example.com")
        self.status_manager.complete_processing()

        recent_runs = self.status_manager.get_recent_runs(limit=1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]

        # Verify all required keys are present
        required_keys = [
            'email_address',
            'start_time',
            'end_time',
            'final_state',
            'emails_categorized',
            'emails_skipped',
            'emails_reviewed',
            'emails_tagged',
            'emails_deleted'
        ]

        for key in required_keys:
            self.assertIn(
                key,
                archived_run,
                f"Archived run should contain '{key}' field"
            )


class TestMixedZeroNonZeroHistory(unittest.TestCase):
    """
    Test history isolation between runs with mixed zero and non-zero counts.

    Validates that:
    - Multiple runs maintain independent counts
    - Zero count runs do not affect subsequent runs
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_multiple_runs_maintain_independent_counts(self):
        """
        Test that multiple runs maintain independent audit counts.

        When multiple processing sessions complete
        Then each archived run should have its own independent counts
        """
        # Arrange & Act: Run 1 with non-zero counts
        self.status_manager.start_processing("user1@example.com")
        self.status_manager.increment_categorized(10)
        self.status_manager.increment_skipped(5)
        self.status_manager.complete_processing()

        # Run 2 with different counts
        self.status_manager.start_processing("user2@example.com")
        self.status_manager.increment_categorized(20)
        self.status_manager.increment_skipped(3)
        self.status_manager.complete_processing()

        recent_runs = self.status_manager.get_recent_runs(limit=2)

        # Assert: Most recent first
        self.assertEqual(len(recent_runs), 2, "Should have 2 archived runs")

        run2 = recent_runs[0]  # Most recent
        run1 = recent_runs[1]  # Older

        # Verify run 1 counts
        self.assertEqual(
            run1['emails_categorized'],
            10,
            f"Run 1 emails_categorized should be 10, got {run1.get('emails_categorized')}"
        )
        self.assertEqual(
            run1['emails_skipped'],
            5,
            f"Run 1 emails_skipped should be 5, got {run1.get('emails_skipped')}"
        )

        # Verify run 2 counts
        self.assertEqual(
            run2['emails_categorized'],
            20,
            f"Run 2 emails_categorized should be 20, got {run2.get('emails_categorized')}"
        )
        self.assertEqual(
            run2['emails_skipped'],
            3,
            f"Run 2 emails_skipped should be 3, got {run2.get('emails_skipped')}"
        )

    def test_zero_count_run_does_not_affect_subsequent_runs(self):
        """
        Test that a zero count run does not affect subsequent runs.

        When a run with zero counts completes
        And a subsequent run with non-zero counts completes
        Then each run should maintain its own counts
        """
        # Arrange & Act: Run 1 with zero counts (empty batch)
        self.status_manager.start_processing("user1@example.com")
        self.status_manager.complete_processing()

        # Run 2 with non-zero counts
        self.status_manager.start_processing("user2@example.com")
        self.status_manager.increment_categorized(25)
        self.status_manager.increment_skipped(7)
        self.status_manager.complete_processing()

        recent_runs = self.status_manager.get_recent_runs(limit=2)

        # Assert
        self.assertEqual(len(recent_runs), 2, "Should have 2 archived runs")

        run2 = recent_runs[0]  # Most recent
        run1 = recent_runs[1]  # Older (zero counts)

        # Verify run 1 has zero counts
        self.assertEqual(
            run1['emails_categorized'],
            0,
            f"Run 1 emails_categorized should be 0, got {run1.get('emails_categorized')}"
        )
        self.assertEqual(
            run1['emails_skipped'],
            0,
            f"Run 1 emails_skipped should be 0, got {run1.get('emails_skipped')}"
        )

        # Verify run 2 is NOT affected by run 1's zero counts
        self.assertEqual(
            run2['emails_categorized'],
            25,
            f"Run 2 emails_categorized should be 25, got {run2.get('emails_categorized')}"
        )
        self.assertEqual(
            run2['emails_skipped'],
            7,
            f"Run 2 emails_skipped should be 7, got {run2.get('emails_skipped')}"
        )


if __name__ == '__main__':
    unittest.main()
