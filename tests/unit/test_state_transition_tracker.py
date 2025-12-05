"""
Tests for State Transition Tracking for Email Processing Runs (TDD Red Phase).

This module tests the state transition tracking functionality that enables
Gantt chart visualizations and processing performance analysis.

Components tested:
1. StateTransition Dataclass - Data model for individual state transitions
2. IStateTransitionTracker Interface - Contract for tracking operations
3. StateTransitionTracker Implementation - Thread-safe transition tracking
4. ProcessingStatusManager Integration - State transitions in archived runs

Based on Gherkin scenarios from tests/bdd/state_transition_tracking.feature:
- Record state transitions during email processing
- Calculate duration between state transitions
- Clear state transitions when run completes
- State transitions persist in archived run data

These tests follow TDD Red phase - they will fail until implementation is complete.
"""
import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Protocol
from dataclasses import dataclass
import threading
import time


# ============================================================================
# SECTION 1: StateTransition Dataclass Tests
# ============================================================================

class TestStateTransitionDataclassExists(unittest.TestCase):
    """
    Tests to verify the StateTransition data model exists with required fields.

    The StateTransition model should be defined in:
    services/state_transition.py

    Fields required:
    - state (str): The processing state name
    - step_description (str): Human-readable description of the step
    - timestamp (datetime): When the transition occurred
    - duration_seconds (Optional[float]): Duration until next transition
    """

    def test_state_transition_dataclass_exists(self):
        """
        Test that StateTransition dataclass exists in services/state_transition.py.

        The implementation should define StateTransition as a dataclass.
        """
        # Act & Assert
        from services.state_transition import StateTransition

        self.assertTrue(
            hasattr(StateTransition, '__dataclass_fields__'),
            "StateTransition should be a dataclass"
        )

    def test_state_transition_has_state_field(self):
        """
        Test that StateTransition has state field of type str.
        """
        from services.state_transition import StateTransition

        self.assertIn(
            'state',
            StateTransition.__dataclass_fields__,
            "StateTransition should have 'state' field"
        )

        field = StateTransition.__dataclass_fields__['state']
        self.assertEqual(
            field.type,
            str,
            "state field should be of type str"
        )

    def test_state_transition_has_step_description_field(self):
        """
        Test that StateTransition has step_description field of type str.
        """
        from services.state_transition import StateTransition

        self.assertIn(
            'step_description',
            StateTransition.__dataclass_fields__,
            "StateTransition should have 'step_description' field"
        )

        field = StateTransition.__dataclass_fields__['step_description']
        self.assertEqual(
            field.type,
            str,
            "step_description field should be of type str"
        )

    def test_state_transition_has_timestamp_field(self):
        """
        Test that StateTransition has timestamp field of type datetime.
        """
        from services.state_transition import StateTransition

        self.assertIn(
            'timestamp',
            StateTransition.__dataclass_fields__,
            "StateTransition should have 'timestamp' field"
        )

        field = StateTransition.__dataclass_fields__['timestamp']
        self.assertEqual(
            field.type,
            datetime,
            "timestamp field should be of type datetime"
        )

    def test_state_transition_has_duration_seconds_field(self):
        """
        Test that StateTransition has duration_seconds field of type Optional[float].
        """
        from services.state_transition import StateTransition

        self.assertIn(
            'duration_seconds',
            StateTransition.__dataclass_fields__,
            "StateTransition should have 'duration_seconds' field"
        )

        field = StateTransition.__dataclass_fields__['duration_seconds']
        field_type_str = str(field.type)
        self.assertTrue(
            'float' in field_type_str and ('None' in field_type_str or 'Optional' in field_type_str),
            f"duration_seconds field should be of type Optional[float], got {field.type}"
        )


class TestStateTransitionCreation(unittest.TestCase):
    """
    Tests for creating StateTransition instances with valid data.
    """

    def test_create_state_transition_with_all_fields(self):
        """
        Test creating a StateTransition with all fields populated.
        """
        from services.state_transition import StateTransition

        # Arrange
        timestamp = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Act
        transition = StateTransition(
            state="CONNECTING",
            step_description="Connecting to Gmail IMAP",
            timestamp=timestamp,
            duration_seconds=5.0
        )

        # Assert
        self.assertEqual(transition.state, "CONNECTING")
        self.assertEqual(transition.step_description, "Connecting to Gmail IMAP")
        self.assertEqual(transition.timestamp, timestamp)
        self.assertEqual(transition.duration_seconds, 5.0)

    def test_create_state_transition_with_none_duration(self):
        """
        Test creating a StateTransition with None duration (before finalization).
        """
        from services.state_transition import StateTransition

        # Arrange
        timestamp = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Act
        transition = StateTransition(
            state="FETCHING",
            step_description="Fetching emails",
            timestamp=timestamp,
            duration_seconds=None
        )

        # Assert
        self.assertIsNone(transition.duration_seconds)


class TestStateTransitionToDict(unittest.TestCase):
    """
    Tests for StateTransition.to_dict() method.

    Scenario: State transitions persist in archived run data
    Then each transition should have state, step_description, timestamp, and duration_seconds
    """

    def test_to_dict_returns_complete_dictionary(self):
        """
        Test that to_dict() returns a dictionary with all fields.
        """
        from services.state_transition import StateTransition

        # Arrange
        timestamp = datetime(2025, 1, 1, 10, 0, 5, tzinfo=timezone.utc)
        transition = StateTransition(
            state="CONNECTING",
            step_description="Connecting to Gmail IMAP",
            timestamp=timestamp,
            duration_seconds=5.0
        )

        # Act
        result = transition.to_dict()

        # Assert
        expected = {
            "state": "CONNECTING",
            "step_description": "Connecting to Gmail IMAP",
            "timestamp": "2025-01-01T10:00:05+00:00",
            "duration_seconds": 5.0
        }
        self.assertEqual(
            result,
            expected,
            f"to_dict() should return {expected}, got {result}"
        )

    def test_to_dict_formats_timestamp_as_iso(self):
        """
        Test that to_dict() converts timestamp to ISO format string.
        """
        from services.state_transition import StateTransition

        # Arrange
        timestamp = datetime(2025, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        transition = StateTransition(
            state="FETCHING",
            step_description="Fetching emails",
            timestamp=timestamp,
            duration_seconds=10.5
        )

        # Act
        result = transition.to_dict()

        # Assert
        self.assertEqual(
            result["timestamp"],
            "2025-06-15T14:30:45+00:00",
            "timestamp should be in ISO format"
        )

    def test_to_dict_with_none_duration(self):
        """
        Test that to_dict() handles None duration_seconds.
        """
        from services.state_transition import StateTransition

        # Arrange
        timestamp = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        transition = StateTransition(
            state="COMPLETED",
            step_description="Processing completed",
            timestamp=timestamp,
            duration_seconds=None
        )

        # Act
        result = transition.to_dict()

        # Assert
        self.assertIsNone(
            result["duration_seconds"],
            "duration_seconds should be None in dict output"
        )


# ============================================================================
# SECTION 2: IStateTransitionTracker Interface Tests
# ============================================================================

class TestIStateTransitionTrackerInterfaceExists(unittest.TestCase):
    """
    Tests to verify the IStateTransitionTracker interface exists
    and has the correct methods.

    The interface should define:
    - record_transition(state, step_description, timestamp) -> None
    - get_transitions() -> List[StateTransition]
    - finalize() -> List[StateTransition]
    - clear() -> None
    """

    def test_interface_exists(self):
        """
        Test that IStateTransitionTracker interface exists.

        The implementation should define an interface in:
        services/interfaces/state_transition_tracker_interface.py
        """
        # Act & Assert
        from services.interfaces.state_transition_tracker_interface import (
            IStateTransitionTracker
        )

        import inspect
        self.assertTrue(
            inspect.isabstract(IStateTransitionTracker) or
            hasattr(IStateTransitionTracker, '__protocol_attrs__'),
            "IStateTransitionTracker should be an abstract class or Protocol"
        )

    def test_interface_has_record_transition_method(self):
        """
        Test that interface defines record_transition method.

        The record_transition method should:
        - Accept state (str), step_description (str), timestamp (datetime)
        - Return None
        - Record a state transition
        """
        from services.interfaces.state_transition_tracker_interface import (
            IStateTransitionTracker
        )
        import inspect

        methods = [name for name, _ in inspect.getmembers(
            IStateTransitionTracker,
            predicate=inspect.isfunction
        )]
        self.assertIn(
            "record_transition",
            methods,
            "IStateTransitionTracker should have record_transition method"
        )

    def test_interface_has_get_transitions_method(self):
        """
        Test that interface defines get_transitions method.

        The get_transitions method should:
        - Accept no arguments
        - Return List[StateTransition]
        """
        from services.interfaces.state_transition_tracker_interface import (
            IStateTransitionTracker
        )
        import inspect

        methods = [name for name, _ in inspect.getmembers(
            IStateTransitionTracker,
            predicate=inspect.isfunction
        )]
        self.assertIn(
            "get_transitions",
            methods,
            "IStateTransitionTracker should have get_transitions method"
        )

    def test_interface_has_finalize_method(self):
        """
        Test that interface defines finalize method.

        The finalize method should:
        - Calculate durations between transitions
        - Return complete list with duration_seconds populated
        """
        from services.interfaces.state_transition_tracker_interface import (
            IStateTransitionTracker
        )
        import inspect

        methods = [name for name, _ in inspect.getmembers(
            IStateTransitionTracker,
            predicate=inspect.isfunction
        )]
        self.assertIn(
            "finalize",
            methods,
            "IStateTransitionTracker should have finalize method"
        )

    def test_interface_has_clear_method(self):
        """
        Test that interface defines clear method.

        The clear method should:
        - Accept no arguments
        - Return None
        - Clear all transitions for next run
        """
        from services.interfaces.state_transition_tracker_interface import (
            IStateTransitionTracker
        )
        import inspect

        methods = [name for name, _ in inspect.getmembers(
            IStateTransitionTracker,
            predicate=inspect.isfunction
        )]
        self.assertIn(
            "clear",
            methods,
            "IStateTransitionTracker should have clear method"
        )


# ============================================================================
# SECTION 3: StateTransitionTracker Implementation Tests
# ============================================================================

class TestStateTransitionTrackerCreation(unittest.TestCase):
    """
    Tests for StateTransitionTracker instantiation.
    """

    def test_tracker_class_exists(self):
        """
        Test that StateTransitionTracker class exists.

        The implementation should be in:
        services/state_transition.py
        """
        from services.state_transition import StateTransitionTracker

        self.assertTrue(
            callable(StateTransitionTracker),
            "StateTransitionTracker should be a callable class"
        )

    def test_tracker_can_be_instantiated(self):
        """
        Test that StateTransitionTracker can be instantiated.
        """
        from services.state_transition import StateTransitionTracker

        # Act
        tracker = StateTransitionTracker()

        # Assert
        self.assertIsNotNone(tracker)

    def test_tracker_implements_interface(self):
        """
        Test that StateTransitionTracker implements IStateTransitionTracker.
        """
        from services.state_transition import StateTransitionTracker
        from services.interfaces.state_transition_tracker_interface import (
            IStateTransitionTracker
        )

        tracker = StateTransitionTracker()

        self.assertIsInstance(
            tracker,
            IStateTransitionTracker,
            "StateTransitionTracker should implement IStateTransitionTracker"
        )


class TestRecordStateTransitions(unittest.TestCase):
    """
    Scenario: Record state transitions during email processing

    Given a processing run is started for "user@gmail.com"
    When the processing state changes to "CONNECTING" with step "Connecting to Gmail IMAP"
    And the processing state changes to "FETCHING" with step "Fetching emails"
    And the processing state changes to "CATEGORIZING" with step "Categorizing emails"
    Then 3 state transitions should be recorded
    And each transition should have a timestamp
    And each transition should have the state and step description
    """

    def test_record_single_transition(self):
        """
        Test recording a single state transition.
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        timestamp = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Act
        tracker.record_transition("CONNECTING", "Connecting to Gmail IMAP", timestamp)
        transitions = tracker.get_transitions()

        # Assert
        self.assertEqual(
            len(transitions),
            1,
            f"Should have 1 transition recorded, got {len(transitions)}"
        )

    def test_record_multiple_transitions(self):
        """
        Test recording multiple state transitions.

        Given a processing run is started for "user@gmail.com"
        When the processing state changes through CONNECTING, FETCHING, CATEGORIZING
        Then 3 state transitions should be recorded
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        base_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Act
        tracker.record_transition(
            "CONNECTING",
            "Connecting to Gmail IMAP",
            base_time
        )
        tracker.record_transition(
            "FETCHING",
            "Fetching emails",
            base_time + timedelta(seconds=5)
        )
        tracker.record_transition(
            "CATEGORIZING",
            "Categorizing emails",
            base_time + timedelta(seconds=15)
        )

        transitions = tracker.get_transitions()

        # Assert
        self.assertEqual(
            len(transitions),
            3,
            f"Should have 3 transitions recorded, got {len(transitions)}"
        )

    def test_each_transition_has_timestamp(self):
        """
        Test that each transition has a timestamp.
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        base_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Act
        tracker.record_transition("CONNECTING", "Connecting to Gmail IMAP", base_time)
        tracker.record_transition("FETCHING", "Fetching emails", base_time + timedelta(seconds=5))
        transitions = tracker.get_transitions()

        # Assert
        for i, transition in enumerate(transitions):
            self.assertIsNotNone(
                transition.timestamp,
                f"Transition {i} should have a timestamp"
            )
            self.assertIsInstance(
                transition.timestamp,
                datetime,
                f"Transition {i} timestamp should be a datetime object"
            )

    def test_each_transition_has_state_and_step_description(self):
        """
        Test that each transition has the state and step description.
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        base_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Act
        tracker.record_transition("CONNECTING", "Connecting to Gmail IMAP", base_time)
        tracker.record_transition("FETCHING", "Fetching emails", base_time + timedelta(seconds=5))
        tracker.record_transition("CATEGORIZING", "Categorizing emails", base_time + timedelta(seconds=15))

        transitions = tracker.get_transitions()

        # Assert
        self.assertEqual(transitions[0].state, "CONNECTING")
        self.assertEqual(transitions[0].step_description, "Connecting to Gmail IMAP")

        self.assertEqual(transitions[1].state, "FETCHING")
        self.assertEqual(transitions[1].step_description, "Fetching emails")

        self.assertEqual(transitions[2].state, "CATEGORIZING")
        self.assertEqual(transitions[2].step_description, "Categorizing emails")


class TestCalculateDurationBetweenTransitions(unittest.TestCase):
    """
    Scenario: Calculate duration between state transitions

    Given a processing run is started for "user@gmail.com" at "2025-01-01 10:00:00"
    When the processing state changes to "CONNECTING" at "2025-01-01 10:00:00"
    And the processing state changes to "FETCHING" at "2025-01-01 10:00:05"
    Then the CONNECTING transition should have a duration of 5.0 seconds
    """

    def test_finalize_calculates_duration_between_transitions(self):
        """
        Test that finalize() calculates duration between consecutive transitions.
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        time_0 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        time_5 = datetime(2025, 1, 1, 10, 0, 5, tzinfo=timezone.utc)

        tracker.record_transition("CONNECTING", "Connecting to Gmail IMAP", time_0)
        tracker.record_transition("FETCHING", "Fetching emails", time_5)

        # Act
        finalized = tracker.finalize()

        # Assert
        self.assertEqual(
            finalized[0].duration_seconds,
            5.0,
            f"CONNECTING transition should have duration of 5.0 seconds, got {finalized[0].duration_seconds}"
        )

    def test_finalize_multiple_transitions_calculates_all_durations(self):
        """
        Test that finalize() calculates duration for all transitions.
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        time_0 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        time_5 = datetime(2025, 1, 1, 10, 0, 5, tzinfo=timezone.utc)
        time_15 = datetime(2025, 1, 1, 10, 0, 15, tzinfo=timezone.utc)
        time_20 = datetime(2025, 1, 1, 10, 0, 20, tzinfo=timezone.utc)

        tracker.record_transition("CONNECTING", "Connecting", time_0)
        tracker.record_transition("FETCHING", "Fetching", time_5)
        tracker.record_transition("CATEGORIZING", "Categorizing", time_15)
        tracker.record_transition("COMPLETED", "Completed", time_20)

        # Act
        finalized = tracker.finalize()

        # Assert
        self.assertEqual(finalized[0].duration_seconds, 5.0, "CONNECTING duration should be 5.0")
        self.assertEqual(finalized[1].duration_seconds, 10.0, "FETCHING duration should be 10.0")
        self.assertEqual(finalized[2].duration_seconds, 5.0, "CATEGORIZING duration should be 5.0")

    def test_finalize_last_transition_has_zero_duration(self):
        """
        Test that the last transition has duration_seconds = 0.0.
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        time_0 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        time_5 = datetime(2025, 1, 1, 10, 0, 5, tzinfo=timezone.utc)

        tracker.record_transition("CONNECTING", "Connecting", time_0)
        tracker.record_transition("COMPLETED", "Completed", time_5)

        # Act
        finalized = tracker.finalize()

        # Assert
        self.assertEqual(
            finalized[-1].duration_seconds,
            0.0,
            f"Last transition should have duration_seconds = 0.0, got {finalized[-1].duration_seconds}"
        )

    def test_finalize_handles_same_timestamp_transitions(self):
        """
        Test that finalize() handles transitions with same timestamp (0.0 seconds duration).
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        same_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        tracker.record_transition("STATE_A", "Step A", same_time)
        tracker.record_transition("STATE_B", "Step B", same_time)

        # Act
        finalized = tracker.finalize()

        # Assert
        self.assertEqual(
            finalized[0].duration_seconds,
            0.0,
            "Duration between same-timestamp transitions should be 0.0"
        )


class TestClearStateTransitions(unittest.TestCase):
    """
    Scenario: Clear state transitions when run completes

    Given a processing run is started for "user@gmail.com"
    And state transitions have been recorded
    When the processing run is archived
    Then the transitions should be included in the archived run
    And the active transition list should be cleared
    """

    def test_clear_removes_all_transitions(self):
        """
        Test that clear() removes all recorded transitions.
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        timestamp = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        tracker.record_transition("CONNECTING", "Connecting", timestamp)
        tracker.record_transition("FETCHING", "Fetching", timestamp + timedelta(seconds=5))

        # Verify we have transitions
        self.assertEqual(len(tracker.get_transitions()), 2)

        # Act
        tracker.clear()

        # Assert
        transitions = tracker.get_transitions()
        self.assertEqual(
            len(transitions),
            0,
            f"After clear(), should have 0 transitions, got {len(transitions)}"
        )

    def test_clear_allows_new_transitions(self):
        """
        Test that after clear(), new transitions can be recorded.
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        timestamp = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        tracker.record_transition("OLD_STATE", "Old step", timestamp)
        tracker.clear()

        # Act
        tracker.record_transition("NEW_STATE", "New step", timestamp + timedelta(seconds=10))
        transitions = tracker.get_transitions()

        # Assert
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0].state, "NEW_STATE")
        self.assertEqual(transitions[0].step_description, "New step")


class TestStateTransitionTrackerEdgeCases(unittest.TestCase):
    """
    Test edge cases and boundary conditions for StateTransitionTracker.
    """

    def test_empty_tracker_returns_empty_list(self):
        """
        Test that a new tracker with no data returns empty list.
        """
        from services.state_transition import StateTransitionTracker

        tracker = StateTransitionTracker()
        transitions = tracker.get_transitions()

        self.assertEqual(
            transitions,
            [],
            f"Empty tracker should return empty list, got {transitions}"
        )

    def test_finalize_empty_tracker_returns_empty_list(self):
        """
        Test that finalize() on empty tracker returns empty list.
        """
        from services.state_transition import StateTransitionTracker

        tracker = StateTransitionTracker()
        finalized = tracker.finalize()

        self.assertEqual(
            finalized,
            [],
            f"Finalizing empty tracker should return empty list, got {finalized}"
        )

    def test_finalize_single_transition_has_zero_duration(self):
        """
        Test that finalizing a single transition gives it 0.0 duration.
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        timestamp = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        tracker.record_transition("ONLY_STATE", "Only step", timestamp)

        # Act
        finalized = tracker.finalize()

        # Assert
        self.assertEqual(len(finalized), 1)
        self.assertEqual(
            finalized[0].duration_seconds,
            0.0,
            "Single transition should have 0.0 duration"
        )

    def test_get_transitions_returns_chronological_order(self):
        """
        Test that get_transitions() returns transitions in chronological order.
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        time_1 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        time_2 = datetime(2025, 1, 1, 10, 0, 5, tzinfo=timezone.utc)
        time_3 = datetime(2025, 1, 1, 10, 0, 10, tzinfo=timezone.utc)

        # Record in order
        tracker.record_transition("FIRST", "First", time_1)
        tracker.record_transition("SECOND", "Second", time_2)
        tracker.record_transition("THIRD", "Third", time_3)

        # Act
        transitions = tracker.get_transitions()

        # Assert
        self.assertEqual(transitions[0].state, "FIRST")
        self.assertEqual(transitions[1].state, "SECOND")
        self.assertEqual(transitions[2].state, "THIRD")


class TestStateTransitionTrackerThreadSafety(unittest.TestCase):
    """
    Test thread-safe operation for concurrent access.
    """

    def test_concurrent_record_transitions(self):
        """
        Test that concurrent record_transition calls are thread-safe.
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        base_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        num_threads = 10
        transitions_per_thread = 5
        errors = []

        def record_transitions(thread_id: int):
            try:
                for i in range(transitions_per_thread):
                    timestamp = base_time + timedelta(seconds=thread_id * 10 + i)
                    tracker.record_transition(
                        f"STATE_{thread_id}_{i}",
                        f"Step {thread_id}-{i}",
                        timestamp
                    )
            except Exception as e:
                errors.append(e)

        # Act
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=record_transitions, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Assert
        self.assertEqual(
            len(errors),
            0,
            f"No errors should occur during concurrent access, got {errors}"
        )

        transitions = tracker.get_transitions()
        expected_count = num_threads * transitions_per_thread
        self.assertEqual(
            len(transitions),
            expected_count,
            f"Should have {expected_count} transitions, got {len(transitions)}"
        )

    def test_concurrent_read_and_write(self):
        """
        Test that concurrent reads and writes are thread-safe.
        """
        from services.state_transition import StateTransitionTracker

        # Arrange
        tracker = StateTransitionTracker()
        base_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        errors = []
        read_results = []

        def writer():
            try:
                for i in range(20):
                    timestamp = base_time + timedelta(seconds=i)
                    tracker.record_transition(f"STATE_{i}", f"Step {i}", timestamp)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(20):
                    transitions = tracker.get_transitions()
                    read_results.append(len(transitions))
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Act
        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)

        writer_thread.start()
        reader_thread.start()

        writer_thread.join()
        reader_thread.join()

        # Assert
        self.assertEqual(
            len(errors),
            0,
            f"No errors should occur during concurrent read/write, got {errors}"
        )


# ============================================================================
# SECTION 4: ProcessingStatusManager Integration Tests
# ============================================================================

class TestProcessingStatusManagerTransitionIntegration(unittest.TestCase):
    """
    Tests for ProcessingStatusManager integration with StateTransitionTracker.

    These tests verify that:
    - ProcessingStatusManager has a StateTransitionTracker instance
    - start_processing() clears tracker and records initial IDLE transition
    - update_status() records each state change as a transition
    - complete_processing() finalizes transitions and adds to archived run
    """

    def test_processing_status_manager_has_transition_tracker(self):
        """
        Test that ProcessingStatusManager has a StateTransitionTracker instance.
        """
        from services.processing_status_manager import ProcessingStatusManager

        # Act
        manager = ProcessingStatusManager(50)

        # Assert
        self.assertTrue(
            hasattr(manager, '_transition_tracker') or hasattr(manager, 'transition_tracker'),
            "ProcessingStatusManager should have a transition_tracker attribute"
        )

    def test_start_processing_clears_transition_tracker(self):
        """
        Test that start_processing() clears the transition tracker.
        """
        from services.processing_status_manager import ProcessingStatusManager

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("first@gmail.com")
        manager.update_status(
            manager.__class__.__module__.split('.')[0],
            "Test step"
        )
        manager.complete_processing()

        # Act - Start new processing
        manager.start_processing("second@gmail.com")

        # Get transitions (implementation may vary)
        tracker = getattr(manager, '_transition_tracker', None) or getattr(manager, 'transition_tracker', None)
        if tracker:
            transitions = tracker.get_transitions()
            # Should have been cleared and have only initial transition
            self.assertLessEqual(
                len(transitions),
                1,
                "Transition tracker should be cleared on new processing start"
            )

    def test_update_status_records_transition(self):
        """
        Test that update_status() records a state transition.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")

        # Act
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail IMAP")
        manager.update_status(ProcessingState.FETCHING, "Fetching emails")
        manager.update_status(ProcessingState.CATEGORIZING, "Categorizing emails")

        # Assert
        tracker = getattr(manager, '_transition_tracker', None) or getattr(manager, 'transition_tracker', None)
        if tracker:
            transitions = tracker.get_transitions()
            # Should have at least the 3 state changes we made
            # (may also include initial IDLE transition)
            self.assertGreaterEqual(
                len(transitions),
                3,
                f"Should have at least 3 transitions, got {len(transitions)}"
            )


class TestArchivedRunContainsStateTransitions(unittest.TestCase):
    """
    Scenario: State transitions persist in archived run data

    Given a completed processing run with transitions
    When the run is archived to history
    Then the archived run should contain state_transitions array
    And each transition should have state, step_description, timestamp, and duration_seconds
    """

    def test_archived_run_contains_state_transitions_array(self):
        """
        Test that archived run contains state_transitions array.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail IMAP")
        manager.update_status(ProcessingState.FETCHING, "Fetching emails")
        manager.update_status(ProcessingState.CATEGORIZING, "Categorizing emails")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)

        # Assert
        self.assertEqual(len(recent_runs), 1, "Should have 1 archived run")
        archived_run = recent_runs[0]

        self.assertIn(
            'state_transitions',
            archived_run,
            f"Archived run should contain 'state_transitions' key. Keys found: {archived_run.keys()}"
        )

    def test_archived_transitions_have_required_fields(self):
        """
        Test that each archived transition has state, step_description, timestamp, and duration_seconds.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting to Gmail IMAP")
        manager.update_status(ProcessingState.COMPLETED, "Processing completed")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert
        self.assertIn('state_transitions', archived_run)
        transitions = archived_run['state_transitions']

        self.assertIsInstance(
            transitions,
            list,
            f"state_transitions should be a list, got {type(transitions)}"
        )

        for i, transition in enumerate(transitions):
            self.assertIn(
                'state',
                transition,
                f"Transition {i} should have 'state' field"
            )
            self.assertIn(
                'step_description',
                transition,
                f"Transition {i} should have 'step_description' field"
            )
            self.assertIn(
                'timestamp',
                transition,
                f"Transition {i} should have 'timestamp' field"
            )
            self.assertIn(
                'duration_seconds',
                transition,
                f"Transition {i} should have 'duration_seconds' field"
            )

    def test_transitions_included_in_archived_run(self):
        """
        Scenario: Clear state transitions when run completes
        Then the transitions should be included in the archived run
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

        # Assert
        archived_run = recent_runs[0]
        self.assertIn('state_transitions', archived_run)
        transitions = archived_run['state_transitions']

        # Should have at least the transitions we recorded
        self.assertGreaterEqual(
            len(transitions),
            2,
            f"Should have at least 2 transitions (CONNECTING, FETCHING), got {len(transitions)}"
        )

    def test_active_transition_list_cleared_after_archive(self):
        """
        Scenario: Clear state transitions when run completes
        Then the active transition list should be cleared
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")
        manager.update_status(ProcessingState.FETCHING, "Fetching")

        # Act
        manager.complete_processing()

        # Start new processing to verify tracker was cleared
        manager.start_processing("second@gmail.com")

        # Get tracker to verify it's cleared
        tracker = getattr(manager, '_transition_tracker', None) or getattr(manager, 'transition_tracker', None)
        if tracker:
            transitions = tracker.get_transitions()
            # Should only have initial transition for new run, not previous run's transitions
            self.assertLessEqual(
                len(transitions),
                1,
                "Transition tracker should be cleared after archiving"
            )


class TestBackwardCompatibility(unittest.TestCase):
    """
    Test that existing archived run fields are unchanged.
    """

    def test_existing_archived_run_fields_unchanged(self):
        """
        Test that existing archived run fields are preserved.
        """
        from services.processing_status_manager import ProcessingStatusManager, ProcessingState

        # Arrange
        manager = ProcessingStatusManager(50)
        manager.start_processing("user@gmail.com")
        manager.update_status(ProcessingState.CONNECTING, "Connecting")
        manager.update_status(ProcessingState.COMPLETED, "Done")

        # Act
        manager.complete_processing()
        recent_runs = manager.get_recent_runs(1)
        archived_run = recent_runs[0]

        # Assert - Check existing fields are still present
        expected_existing_fields = [
            'email_address',
            'start_time',
            'end_time',
            'duration_seconds',
            'final_state',
            'final_step',
            'error_message',
            'final_progress',
            'emails_reviewed',
            'emails_tagged',
            'emails_deleted'
        ]

        for field in expected_existing_fields:
            self.assertIn(
                field,
                archived_run,
                f"Existing field '{field}' should be preserved in archived run"
            )


if __name__ == '__main__':
    unittest.main()
