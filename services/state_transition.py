"""
State transition tracking for email processing runs.

This module provides data models and tracking functionality for recording
state transitions during email processing, enabling Gantt chart visualizations
and processing performance analysis.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
import threading
from services.interfaces.state_transition_tracker_interface import IStateTransitionTracker


@dataclass
class StateTransition:
    """Data model for individual state transitions during email processing."""
    state: str
    step_description: str
    timestamp: datetime
    duration_seconds: Optional[float] = None

    def to_dict(self) -> dict:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with state, step_description, timestamp (ISO format), and duration_seconds
        """
        return {
            'state': self.state,
            'step_description': self.step_description,
            'timestamp': self.timestamp.isoformat(),
            'duration_seconds': self.duration_seconds
        }


class StateTransitionTracker(IStateTransitionTracker):
    """
    Thread-safe implementation for tracking state transitions during email processing.

    This class maintains an in-memory list of state transitions in chronological order,
    with support for duration calculation and thread-safe operations.
    """

    def __init__(self):
        """Initialize the state transition tracker."""
        self._transitions: List[StateTransition] = []
        self._lock = threading.Lock()

    def record_transition(self, state: str, step_description: str, timestamp: datetime) -> None:
        """
        Record a state transition.

        Args:
            state: The processing state name
            step_description: Human-readable description of the step
            timestamp: When the transition occurred (must be provided)
        """
        with self._lock:
            transition = StateTransition(
                state=state,
                step_description=step_description,
                timestamp=timestamp,
                duration_seconds=None
            )
            self._transitions.append(transition)

    def get_transitions(self) -> List[StateTransition]:
        """
        Get all recorded transitions.

        Returns:
            List of StateTransition objects in chronological order
        """
        with self._lock:
            # Return a copy to prevent external modification
            return self._transitions.copy()

    def finalize(self) -> List[StateTransition]:
        """
        Calculate durations and return complete list with duration_seconds populated.

        Durations are calculated as the time difference between consecutive transitions.
        The last transition always has duration_seconds = 0.0.

        Returns:
            List of StateTransition objects with duration_seconds calculated
        """
        with self._lock:
            if not self._transitions:
                return []

            # Create a copy for finalization
            finalized_transitions = []

            for i, transition in enumerate(self._transitions):
                # Create a new StateTransition with calculated duration
                if i < len(self._transitions) - 1:
                    # Calculate duration until next transition
                    next_transition = self._transitions[i + 1]
                    duration = (next_transition.timestamp - transition.timestamp).total_seconds()
                else:
                    # Last transition has 0.0 duration
                    duration = 0.0

                finalized_transition = StateTransition(
                    state=transition.state,
                    step_description=transition.step_description,
                    timestamp=transition.timestamp,
                    duration_seconds=duration
                )
                finalized_transitions.append(finalized_transition)

            return finalized_transitions

    def clear(self) -> None:
        """Clear all transitions for next run."""
        with self._lock:
            self._transitions.clear()
