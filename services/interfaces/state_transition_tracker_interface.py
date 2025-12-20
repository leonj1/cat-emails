from abc import ABC, abstractmethod
from datetime import datetime
from typing import List


class IStateTransitionTracker(ABC):
    """Interface for tracking state transitions during email processing."""

    @abstractmethod
    def record_transition(self, state: str, step_description: str, timestamp: datetime) -> None:
        """
        Record a state transition.

        Args:
            state: The processing state name
            step_description: Human-readable description of the step
            timestamp: When the transition occurred (must be provided)
        """
        pass

    @abstractmethod
    def get_transitions(self) -> List['StateTransition']:
        """
        Get all recorded transitions.

        Returns:
            List of StateTransition objects in chronological order
        """
        pass

    @abstractmethod
    def finalize(self) -> List['StateTransition']:
        """
        Calculate durations and return complete list with duration_seconds populated.

        Returns:
            List of StateTransition objects with duration_seconds calculated
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all transitions for next run."""
        pass
