"""
Tests for API Enhancement for Gantt Chart Text (TDD Red Phase).

This module tests the integration of GanttChartGenerator into ProcessingStatusManager
to include gantt_chart_text field in the processing history API response.

Based on Gherkin scenarios from the BDD specification:
1. Include gantt_chart_text in processing history response
2. Return gantt chart for each run per account
3. Handle empty history with no completed runs
4. Maintain backward compatibility with existing API consumers
5. Generate Gantt chart for run that failed during processing

These tests follow TDD Red phase - they will fail until implementation is complete.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any


# ============================================================================
# SECTION 1: Test Fixtures and Helper Functions
# ============================================================================

def create_test_processing_run(
    manager: Any,
    email_address: str,
    states_with_steps: List[tuple],
    include_error: bool
) -> None:
    """
    Helper function to create a complete processing run with state transitions.

    Args:
        manager: ProcessingStatusManager instance
        email_address: The email address for this run
        states_with_steps: List of (state, step_description) tuples
        include_error: If True, end with ERROR state instead of COMPLETED
    """
    from services.processing_status_manager import ProcessingState

    manager.start_processing(email_address)

    for state, step in states_with_steps:
        if isinstance(state, str):
            state = ProcessingState[state]
        manager.update_status(state, step)

    if include_error:
        manager.update_status(ProcessingState.ERROR, "Processing failed", error_message="Test error")

    manager.complete_processing()


# ============================================================================
# SECTION 2: Include gantt_chart_text in processing history response
# ============================================================================

class TestIncludeGanttChartTextInResponse(unittest.TestCase):
    """
    Scenario: Include gantt_chart_text in processing history response

    Given a completed processing run exists for "user@gmail.com"
    And the run has recorded state transitions
    When the processing history is requested
    Then the response should include a "gantt_chart_text" field for the run
    And the gantt_chart_text should contain valid Mermaid syntax starting with "gantt"
    And the gantt_chart_text should contain a title with "user@gmail.com"
    """

    def test_archived_run_contains_gantt_chart_text_field(self):
        """
        Test that a completed processing run includes gantt_chart_text field.

        Then the response should include a "gantt_chart_text" field for the run

        The implementation should:
        - Call GanttChartGenerator.generate() during complete_processing()
        - Add gantt_chart_text to the archived_run dictionary
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail IMAP")
        manager.update_status(ProcessingState.FETCHING, "Fetching emails from inbox")
        manager.update_status(ProcessingState.CATEGORIZING, "Categorizing 45 emails")
        manager.update_status(ProcessingState.LABELING, "Applying Gmail labels")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)

        # Assert
        self.assertEqual(
            len(recent_runs),
            1,
            "Should have 1 archived run"
        )

        archived_run = recent_runs[0]
        self.assertIn(
            'gantt_chart_text',
            archived_run,
            f"Archived run should contain 'gantt_chart_text' field. Keys found: {list(archived_run.keys())}"
        )

    def test_gantt_chart_text_contains_mermaid_gantt_header(self):
        """
        Test that gantt_chart_text contains valid Mermaid syntax starting with "gantt".

        And the gantt_chart_text should contain valid Mermaid syntax starting with "gantt"
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail IMAP")
        manager.update_status(ProcessingState.FETCHING, "Fetching emails")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        gantt_text = archived_run.get('gantt_chart_text')
        self.assertIsNotNone(
            gantt_text,
            "gantt_chart_text should not be None"
        )
        self.assertTrue(
            gantt_text.strip().startswith('gantt'),
            f"gantt_chart_text should start with 'gantt'. Got: {gantt_text[:100] if gantt_text else 'None'}..."
        )

    def test_gantt_chart_text_contains_email_in_title(self):
        """
        Test that gantt_chart_text contains a title with the email address.

        And the gantt_chart_text should contain a title with "user@gmail.com"
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail IMAP")
        manager.update_status(ProcessingState.FETCHING, "Fetching emails")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        gantt_text = archived_run.get('gantt_chart_text')
        self.assertIn(
            'user@gmail.com',
            gantt_text,
            f"gantt_chart_text should contain email address 'user@gmail.com'. Got:\n{gantt_text}"
        )

    def test_gantt_chart_text_is_valid_mermaid_syntax(self):
        """
        Test that the generated gantt_chart_text is valid Mermaid syntax.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        manager = ProcessingStatusManager(50)
        generator = GanttChartGenerator()

        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail IMAP")
        manager.update_status(ProcessingState.FETCHING, "Fetching emails")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        gantt_text = archived_run.get('gantt_chart_text')
        is_valid = generator.validate_syntax(gantt_text)
        self.assertTrue(
            is_valid,
            f"gantt_chart_text should be valid Mermaid syntax. Got:\n{gantt_text}"
        )


# ============================================================================
# SECTION 3: Return gantt chart for each run per account
# ============================================================================

class TestGanttChartForEachRun(unittest.TestCase):
    """
    Scenario: Return gantt chart for each run per account

    Given completed processing runs exist for:
      | email_address   |
      | user1@gmail.com |
      | user2@gmail.com |
      | user1@gmail.com |
    When the processing history is requested
    Then each of the 3 runs should have its own gantt_chart_text
    And the gantt chart for user1 runs should reference "user1@gmail.com"
    And the gantt chart for user2 runs should reference "user2@gmail.com"
    """

    def test_multiple_runs_each_have_gantt_chart_text(self):
        """
        Test that each of 3 runs has its own gantt_chart_text.

        Then each of the 3 runs should have its own gantt_chart_text
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)

        # Create 3 processing runs
        for email in ["user1@gmail.com", "user2@gmail.com", "user1@gmail.com"]:
            manager.start_processing(email)
            manager.update_status(ProcessingState.CONNECTING, "Connecting")
            manager.update_status(ProcessingState.FETCHING, "Fetching emails")
            manager.complete_processing()

        # Act
        recent_runs = manager.get_recent_runs(10)

        # Assert
        self.assertEqual(
            len(recent_runs),
            3,
            f"Should have 3 archived runs, got {len(recent_runs)}"
        )

        for i, run in enumerate(recent_runs):
            self.assertIn(
                'gantt_chart_text',
                run,
                f"Run {i} should have 'gantt_chart_text' field"
            )
            self.assertIsNotNone(
                run['gantt_chart_text'],
                f"Run {i} gantt_chart_text should not be None"
            )

    def test_user1_runs_reference_user1_email(self):
        """
        Test that user1 runs have gantt charts referencing user1@gmail.com.

        And the gantt chart for user1 runs should reference "user1@gmail.com"
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)

        # Create runs
        for email in ["user1@gmail.com", "user2@gmail.com", "user1@gmail.com"]:
            manager.start_processing(email)
            manager.update_status(ProcessingState.CONNECTING, "Connecting")
            manager.update_status(ProcessingState.FETCHING, "Fetching emails")
            manager.complete_processing()

        # Act
        recent_runs = manager.get_recent_runs(10)

        # Assert - Find runs for user1
        user1_runs = [run for run in recent_runs if run['email_address'] == "user1@gmail.com"]
        self.assertEqual(
            len(user1_runs),
            2,
            f"Should have 2 runs for user1@gmail.com, got {len(user1_runs)}"
        )

        for run in user1_runs:
            gantt_text = run.get('gantt_chart_text', '')
            self.assertIn(
                'user1@gmail.com',
                gantt_text,
                f"User1 run gantt chart should reference 'user1@gmail.com'. Got:\n{gantt_text}"
            )

    def test_user2_runs_reference_user2_email(self):
        """
        Test that user2 runs have gantt charts referencing user2@gmail.com.

        And the gantt chart for user2 runs should reference "user2@gmail.com"
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)

        # Create runs
        for email in ["user1@gmail.com", "user2@gmail.com", "user1@gmail.com"]:
            manager.start_processing(email)
            manager.update_status(ProcessingState.CONNECTING, "Connecting")
            manager.update_status(ProcessingState.FETCHING, "Fetching emails")
            manager.complete_processing()

        # Act
        recent_runs = manager.get_recent_runs(10)

        # Assert - Find runs for user2
        user2_runs = [run for run in recent_runs if run['email_address'] == "user2@gmail.com"]
        self.assertEqual(
            len(user2_runs),
            1,
            f"Should have 1 run for user2@gmail.com, got {len(user2_runs)}"
        )

        for run in user2_runs:
            gantt_text = run.get('gantt_chart_text', '')
            self.assertIn(
                'user2@gmail.com',
                gantt_text,
                f"User2 run gantt chart should reference 'user2@gmail.com'. Got:\n{gantt_text}"
            )

    def test_gantt_charts_are_independent_per_run(self):
        """
        Test that each run has an independent gantt chart, not shared.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)

        # Create runs with different transitions
        manager.start_processing("user1@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "First connecting")
        manager.complete_processing()

        manager.start_processing("user2@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Second connecting")
        manager.update_status(ProcessingState.FETCHING, "Second fetching")
        manager.complete_processing()

        # Act
        recent_runs = manager.get_recent_runs(10)

        # Assert - Gantt charts should be different
        gantt_texts = [run.get('gantt_chart_text', '') for run in recent_runs]
        self.assertEqual(
            len(gantt_texts),
            2,
            "Should have 2 gantt charts"
        )
        self.assertNotEqual(
            gantt_texts[0],
            gantt_texts[1],
            "Each run should have a unique gantt chart"
        )


# ============================================================================
# SECTION 4: Handle empty history with no completed runs
# ============================================================================

class TestEmptyHistoryHandling(unittest.TestCase):
    """
    Scenario: Handle empty history with no completed runs

    Given no processing runs have been completed
    When the processing history is requested
    Then the response should contain an empty recent_runs array
    And total_retrieved should be 0
    """

    def test_empty_history_returns_empty_array(self):
        """
        Test that no completed runs returns an empty recent_runs array.

        Then the response should contain an empty recent_runs array
        """
        from services.processing_status_manager import ProcessingStatusManager

        # Arrange
        manager = ProcessingStatusManager(50)

        # Act - Request history without any completed runs
        recent_runs = manager.get_recent_runs(10)

        # Assert
        self.assertEqual(
            recent_runs,
            [],
            f"Empty history should return empty list, got {recent_runs}"
        )

    def test_empty_history_has_zero_total(self):
        """
        Test that empty history has total_retrieved of 0.

        And total_retrieved should be 0
        """
        from services.processing_status_manager import ProcessingStatusManager

        # Arrange
        manager = ProcessingStatusManager(50)

        # Act
        recent_runs = manager.get_recent_runs(10)

        # Assert
        self.assertEqual(
            len(recent_runs),
            0,
            f"Empty history should have 0 runs, got {len(recent_runs)}"
        )

    def test_empty_history_no_errors(self):
        """
        Test that requesting empty history does not raise errors.
        """
        from services.processing_status_manager import ProcessingStatusManager

        # Arrange
        manager = ProcessingStatusManager(50)

        # Act & Assert - Should not raise any exception
        try:
            recent_runs = manager.get_recent_runs(10)
            # Also verify we can access runs safely
            for run in recent_runs:
                _ = run.get('gantt_chart_text')
        except Exception as e:
            self.fail(f"Empty history request should not raise exception, got {e}")


# ============================================================================
# SECTION 5: Maintain backward compatibility with existing API consumers
# ============================================================================

class TestBackwardCompatibility(unittest.TestCase):
    """
    Scenario: Maintain backward compatibility with existing API consumers

    Given a completed processing run exists with state transitions
    When the processing history is requested
    Then the response should include all existing fields:
      | field            |
      | email_address    |
      | start_time       |
      | end_time         |
      | duration_seconds |
      | final_state      |
      | final_step       |
      | emails_reviewed  |
      | emails_tagged    |
      | emails_deleted   |
      | state_transitions |
    And gantt_chart_text should be an additional field, not replacing any existing field
    """

    def test_archived_run_contains_email_address(self):
        """
        Test that archived run contains email_address field.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        self.assertIn(
            'email_address',
            archived_run,
            "Archived run should contain 'email_address' field"
        )
        self.assertEqual(
            archived_run['email_address'],
            'user@gmail.com',
            "email_address should be 'user@gmail.com'"
        )

    def test_archived_run_contains_start_time(self):
        """
        Test that archived run contains start_time field.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        self.assertIn(
            'start_time',
            archived_run,
            "Archived run should contain 'start_time' field"
        )
        self.assertIsNotNone(
            archived_run['start_time'],
            "start_time should not be None"
        )

    def test_archived_run_contains_end_time(self):
        """
        Test that archived run contains end_time field.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        self.assertIn(
            'end_time',
            archived_run,
            "Archived run should contain 'end_time' field"
        )

    def test_archived_run_contains_duration_seconds(self):
        """
        Test that archived run contains duration_seconds field.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        self.assertIn(
            'duration_seconds',
            archived_run,
            "Archived run should contain 'duration_seconds' field"
        )

    def test_archived_run_contains_final_state(self):
        """
        Test that archived run contains final_state field.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        self.assertIn(
            'final_state',
            archived_run,
            "Archived run should contain 'final_state' field"
        )

    def test_archived_run_contains_final_step(self):
        """
        Test that archived run contains final_step field.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        self.assertIn(
            'final_step',
            archived_run,
            "Archived run should contain 'final_step' field"
        )

    def test_archived_run_contains_emails_reviewed(self):
        """
        Test that archived run contains emails_reviewed field.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        self.assertIn(
            'emails_reviewed',
            archived_run,
            "Archived run should contain 'emails_reviewed' field"
        )

    def test_archived_run_contains_emails_tagged(self):
        """
        Test that archived run contains emails_tagged field.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        self.assertIn(
            'emails_tagged',
            archived_run,
            "Archived run should contain 'emails_tagged' field"
        )

    def test_archived_run_contains_emails_deleted(self):
        """
        Test that archived run contains emails_deleted field.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        self.assertIn(
            'emails_deleted',
            archived_run,
            "Archived run should contain 'emails_deleted' field"
        )

    def test_archived_run_contains_state_transitions(self):
        """
        Test that archived run contains state_transitions field.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        self.assertIn(
            'state_transitions',
            archived_run,
            "Archived run should contain 'state_transitions' field"
        )

    def test_gantt_chart_text_is_additive_field(self):
        """
        Test that gantt_chart_text is an additional field, not replacing any existing field.

        And gantt_chart_text should be an additional field, not replacing any existing field
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert - All existing fields plus gantt_chart_text
        expected_fields = [
            'email_address',
            'start_time',
            'end_time',
            'duration_seconds',
            'final_state',
            'final_step',
            'emails_reviewed',
            'emails_tagged',
            'emails_deleted',
            'state_transitions',
            'gantt_chart_text'  # New additive field
        ]

        for field in expected_fields:
            self.assertIn(
                field,
                archived_run,
                f"Archived run should contain '{field}' field"
            )

    def test_complete_response_structure(self):
        """
        Test the complete response structure with all fields.

        This test verifies the entire archived run response structure.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail IMAP")
        manager.update_status(ProcessingState.FETCHING, "Fetching emails")
        manager.increment_reviewed(45)
        manager.increment_tagged(40)
        manager.increment_deleted(5)

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert - Complete structure validation
        self.assertEqual(archived_run['email_address'], 'user@gmail.com')
        self.assertIsNotNone(archived_run['start_time'])
        self.assertIsNotNone(archived_run['end_time'])
        self.assertIsNotNone(archived_run['duration_seconds'])
        self.assertEqual(archived_run['final_state'], 'COMPLETED')
        self.assertIsNotNone(archived_run['final_step'])
        self.assertEqual(archived_run['emails_reviewed'], 45)
        self.assertEqual(archived_run['emails_tagged'], 40)
        self.assertEqual(archived_run['emails_deleted'], 5)
        self.assertIsInstance(archived_run['state_transitions'], list)
        self.assertIsNotNone(archived_run['gantt_chart_text'])
        self.assertTrue(archived_run['gantt_chart_text'].strip().startswith('gantt'))


# ============================================================================
# SECTION 6: Generate Gantt chart for run that failed during processing
# ============================================================================

class TestFailedRunGanttChart(unittest.TestCase):
    """
    Scenario: Generate Gantt chart for run that failed during processing

    Given a processing run for "user@gmail.com" ended with ERROR state
    And the run has recorded state transitions including the error
    When the processing history is requested
    Then the response should include the failed run
    And the gantt_chart_text should contain partial progress up to the error
    And the gantt_chart_text should indicate the error state
    """

    def test_failed_run_included_in_response(self):
        """
        Test that failed runs are included in the processing history response.

        Then the response should include the failed run
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail IMAP")
        manager.update_status(ProcessingState.FETCHING, "Fetching emails")
        manager.update_status(ProcessingState.ERROR, "Connection failed", error_message="IMAP timeout")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)

        # Assert
        self.assertEqual(
            len(recent_runs),
            1,
            "Failed run should be included in history"
        )

        archived_run = recent_runs[0]
        self.assertEqual(
            archived_run['final_state'],
            'ERROR',
            f"Failed run should have final_state='ERROR', got {archived_run['final_state']}"
        )

    def test_failed_run_has_gantt_chart_text(self):
        """
        Test that failed runs have gantt_chart_text field.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail IMAP")
        manager.update_status(ProcessingState.FETCHING, "Fetching emails")
        manager.update_status(ProcessingState.ERROR, "Connection failed", error_message="IMAP timeout")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        self.assertIn(
            'gantt_chart_text',
            archived_run,
            "Failed run should have gantt_chart_text field"
        )
        self.assertIsNotNone(
            archived_run['gantt_chart_text'],
            "Failed run gantt_chart_text should not be None"
        )

    def test_failed_run_gantt_shows_partial_progress(self):
        """
        Test that failed run gantt chart shows partial progress up to the error.

        And the gantt_chart_text should contain partial progress up to the error
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail IMAP")
        manager.update_status(ProcessingState.FETCHING, "Fetching emails")
        manager.update_status(ProcessingState.ERROR, "Connection failed", error_message="IMAP timeout")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]
        gantt_text = archived_run.get('gantt_chart_text', '')

        # Assert - Should show CONNECTING and FETCHING steps before error
        # The gantt chart should contain tasks for completed states
        self.assertIn(
            'gantt',
            gantt_text,
            "Gantt chart should have header"
        )
        # Should show the steps that were completed before error
        # Look for evidence of partial progress
        has_initialization = 'section Initialization' in gantt_text or 'Connecting' in gantt_text
        has_fetching = 'section Fetching' in gantt_text or 'Fetching' in gantt_text
        self.assertTrue(
            has_initialization or has_fetching,
            f"Gantt chart should show partial progress. Got:\n{gantt_text}"
        )

    def test_failed_run_gantt_indicates_error_state(self):
        """
        Test that failed run gantt chart indicates the error state.

        And the gantt_chart_text should indicate the error state
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail IMAP")
        manager.update_status(ProcessingState.ERROR, "Processing failed", error_message="Test error")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]
        gantt_text = archived_run.get('gantt_chart_text', '')

        # Assert - Should indicate error state in the chart
        # Could be section Error, or the error step description
        has_error_indication = (
            'Error' in gantt_text or
            'error' in gantt_text.lower() or
            'failed' in gantt_text.lower()
        )
        self.assertTrue(
            has_error_indication,
            f"Gantt chart should indicate error state. Got:\n{gantt_text}"
        )


# ============================================================================
# SECTION 7: Edge Cases and Additional Tests
# ============================================================================

class TestGanttChartGenerationEdgeCases(unittest.TestCase):
    """
    Additional tests for edge cases in Gantt chart text generation.
    """

    def test_run_with_no_state_transitions(self):
        """
        Test handling of run that completes immediately with no state transitions.
        """
        from services.processing_status_manager import ProcessingStatusManager

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")

        # Act - Complete immediately without state updates
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert - Should still have gantt_chart_text (even if minimal)
        self.assertIn(
            'gantt_chart_text',
            archived_run,
            "Run with no state transitions should still have gantt_chart_text"
        )

    def test_run_with_only_idle_transition(self):
        """
        Test handling of run with only IDLE initial state.
        """
        from services.processing_status_manager import ProcessingStatusManager

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        gantt_text = archived_run.get('gantt_chart_text')
        # Should have at least the header
        self.assertIsNotNone(gantt_text)
        if gantt_text:
            self.assertTrue(
                gantt_text.strip().startswith('gantt'),
                "Gantt chart should start with 'gantt' header"
            )

    def test_gantt_chart_with_special_characters_in_email(self):
        """
        Test Gantt chart generation with special characters in email address.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        special_email = "user+alias@gmail.com"
        manager.start_processing(special_email)
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        gantt_text = archived_run.get('gantt_chart_text', '')
        self.assertIn(
            special_email,
            gantt_text,
            f"Gantt chart should handle special characters in email. Got:\n{gantt_text}"
        )

    def test_gantt_chart_type_is_string(self):
        """
        Test that gantt_chart_text is a string type.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        gantt_text = archived_run.get('gantt_chart_text')
        self.assertIsInstance(
            gantt_text,
            str,
            f"gantt_chart_text should be a string, got {type(gantt_text)}"
        )

    def test_gantt_chart_text_not_empty_for_completed_run(self):
        """
        Test that gantt_chart_text is not empty for a completed run with transitions.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail")
        manager.update_status(ProcessingState.FETCHING, "Fetching emails")
        manager.update_status(ProcessingState.CATEGORIZING, "Categorizing")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        gantt_text = archived_run.get('gantt_chart_text', '')
        self.assertGreater(
            len(gantt_text),
            0,
            "gantt_chart_text should not be empty for completed run with transitions"
        )


# ============================================================================
# SECTION 8: Integration with GanttChartGenerator
# ============================================================================

class TestGanttChartGeneratorIntegration(unittest.TestCase):
    """
    Tests for integration between ProcessingStatusManager and GanttChartGenerator.
    """

    def test_complete_processing_calls_gantt_generator(self):
        """
        Test that complete_processing() uses GanttChartGenerator to generate chart.

        The implementation should call GanttChartGenerator.generate() with:
        - The finalized state transitions
        - The email address as title
        - Appropriate include_zero_duration flag
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")
        manager.update_status(ProcessingState.FETCHING, "Fetching")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert - The gantt_chart_text should be valid output from GanttChartGenerator
        gantt_text = archived_run.get('gantt_chart_text', '')
        generator = GanttChartGenerator()

        self.assertTrue(
            generator.validate_syntax(gantt_text),
            f"gantt_chart_text should be valid Mermaid syntax. Got:\n{gantt_text}"
        )

    def test_gantt_chart_uses_state_transitions(self):
        """
        Test that generated gantt chart reflects the actual state transitions.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Test Connecting Step")
        manager.update_status(ProcessingState.FETCHING, "Test Fetching Step")
        manager.update_status(ProcessingState.CATEGORIZING, "Test Categorizing Step")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]
        gantt_text = archived_run.get('gantt_chart_text', '')

        # Assert - The gantt chart should contain the step descriptions
        # At least some of our custom step descriptions should appear
        step_found = (
            "Test Connecting Step" in gantt_text or
            "Test Fetching Step" in gantt_text or
            "Test Categorizing Step" in gantt_text
        )
        self.assertTrue(
            step_found,
            f"Gantt chart should contain step descriptions from state transitions. Got:\n{gantt_text}"
        )


# ============================================================================
# SECTION 9: Gantt Chart None/Missing Handling
# ============================================================================

class TestGanttChartNoneHandling(unittest.TestCase):
    """
    Tests for handling None or missing gantt_chart_text scenarios.
    """

    def test_run_with_empty_transitions_has_gantt_or_none(self):
        """
        Test that a run with no transitions has either a minimal gantt chart or None.

        Depending on implementation, this could be:
        - A minimal gantt chart with just header and title
        - None if there are no transitions to visualize
        """
        from services.processing_status_manager import ProcessingStatusManager

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert - Should have the field, value can be string or None
        self.assertIn(
            'gantt_chart_text',
            archived_run,
            "Archived run should have gantt_chart_text field"
        )

        gantt_text = archived_run.get('gantt_chart_text')
        # Either None or a string are acceptable
        is_valid = (gantt_text is None or isinstance(gantt_text, str))
        self.assertTrue(
            is_valid,
            f"gantt_chart_text should be None or string, got {type(gantt_text)}"
        )


if __name__ == '__main__':
    unittest.main()
