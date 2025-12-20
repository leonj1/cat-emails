# DRAFT: State Transition Tracking for Email Processing Runs

## Overview

Implement state transition tracking for email processing runs. This foundational feature records timestamps for each processing state change, calculates durations between transitions, and stores the transition history in the archived run data structure.

This is **Part 1 of 3** for the Gantt Chart Text Generation feature.

## Objectives

1. Create a `StateTransition` dataclass to represent a single state change with timestamp
2. Create an `IStateTransitionTracker` interface for recording transitions
3. Implement `StateTransitionTracker` class with in-memory storage
4. Integrate transition recording into existing `ProcessingStatusManager`
5. Include transition data in archived run dictionaries

## Interfaces Needed

### 1. StateTransition (Dataclass)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class StateTransition:
    """Represents a single state transition with timestamp."""
    state: str              # ProcessingState name (e.g., "CONNECTING", "FETCHING")
    step_description: str   # Human-readable description (e.g., "Connecting to Gmail IMAP")
    timestamp: datetime     # When this state was entered
    duration_seconds: Optional[float] = None  # Calculated from next transition

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'state': self.state,
            'step_description': self.step_description,
            'timestamp': self.timestamp.isoformat(),
            'duration_seconds': self.duration_seconds
        }
```

### 2. IStateTransitionTracker (Interface)

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime


class IStateTransitionTracker(ABC):
    """Interface for tracking state transitions during processing."""

    @abstractmethod
    def record_transition(
        self,
        state: str,
        step_description: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record a state transition with timestamp.

        Args:
            state: The processing state name (e.g., "CONNECTING")
            step_description: Human-readable step description
            timestamp: Optional explicit timestamp (defaults to now)
        """
        pass

    @abstractmethod
    def get_transitions(self) -> List[StateTransition]:
        """
        Get all recorded transitions for the current run.

        Returns:
            List of StateTransition objects in chronological order
        """
        pass

    @abstractmethod
    def finalize(self) -> List[StateTransition]:
        """
        Finalize the current run's transitions.

        Calculates duration for each transition based on the next transition's
        timestamp. Returns the complete list with durations populated.

        Returns:
            List of StateTransition objects with duration_seconds calculated
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all recorded transitions (called when starting a new run)."""
        pass
```

## Data Models

### StateTransition (Dataclass)

Already defined in Interfaces section. Key fields:
- `state`: String matching ProcessingState enum values
- `step_description`: Human-readable description for display
- `timestamp`: datetime when state was entered
- `duration_seconds`: Calculated field (None until finalized)

### Enhanced Archived Run Dictionary

Current structure in `ProcessingStatusManager.archived_run`:
```python
archived_run = {
    'email_address': str,
    'start_time': str,  # ISO format
    'end_time': str,
    'duration_seconds': float,
    'final_state': str,
    'final_step': str,
    'error_message': Optional[str],
    'final_progress': Optional[Dict],
    'emails_reviewed': int,
    'emails_tagged': int,
    'emails_deleted': int
}
```

Enhanced structure (new field):
```python
archived_run = {
    # ... existing fields unchanged ...
    'state_transitions': [
        {
            'state': 'CONNECTING',
            'step_description': 'Connecting to Gmail IMAP',
            'timestamp': '2025-01-01T10:00:00Z',
            'duration_seconds': 5.2
        },
        # ... more transitions
    ]
}
```

## Logic Flow

### 1. Starting a Processing Run

```
start_processing(email_address):
    1. Clear any existing transitions: tracker.clear()
    2. Record initial transition: tracker.record_transition(
           state="IDLE",
           step_description="Initializing processing"
       )
    3. Continue with existing start_processing logic
```

### 2. Recording State Changes (in update_status)

```
update_status(state, current_step):
    1. Record transition: tracker.record_transition(
           state=state.name,
           step_description=current_step
       )
    2. Continue with existing update_status logic
```

### 3. Completing a Processing Run

```
complete_processing() / error_processing():
    1. Finalize transitions: transitions = tracker.finalize()
    2. Convert to dicts: transition_dicts = [t.to_dict() for t in transitions]
    3. Include in archived_run: archived_run['state_transitions'] = transition_dicts
    4. Archive run to history
    5. Clear tracker: tracker.clear()
```

### 4. Duration Calculation Algorithm

```
finalize():
    transitions = self.get_transitions()
    for i, transition in enumerate(transitions):
        if i < len(transitions) - 1:
            next_transition = transitions[i + 1]
            duration = (next_transition.timestamp - transition.timestamp).total_seconds()
            transition.duration_seconds = duration
        else:
            # Last transition: duration is 0 or calculated from end_time if available
            transition.duration_seconds = 0.0
    return transitions
```

## Implementation Details

### StateTransitionTracker Class

```python
class StateTransitionTracker(IStateTransitionTracker):
    """
    In-memory implementation of state transition tracking.

    Tracks state transitions for the current processing run. Thread-safe
    for use in async processing contexts.
    """

    def __init__(self):
        self._transitions: List[StateTransition] = []
        self._lock = threading.Lock()

    def record_transition(
        self,
        state: str,
        step_description: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        with self._lock:
            self._transitions.append(StateTransition(
                state=state,
                step_description=step_description,
                timestamp=timestamp or datetime.now()
            ))

    def get_transitions(self) -> List[StateTransition]:
        with self._lock:
            return list(self._transitions)

    def finalize(self) -> List[StateTransition]:
        with self._lock:
            for i, transition in enumerate(self._transitions):
                if i < len(self._transitions) - 1:
                    next_t = self._transitions[i + 1]
                    duration = (next_t.timestamp - transition.timestamp).total_seconds()
                    transition.duration_seconds = max(0.0, duration)
                else:
                    transition.duration_seconds = 0.0
            return list(self._transitions)

    def clear(self) -> None:
        with self._lock:
            self._transitions.clear()
```

### Integration Points in ProcessingStatusManager

The `ProcessingStatusManager` class needs these modifications:

1. Add `_transition_tracker: Dict[str, StateTransitionTracker]` for per-account tracking
2. Modify `start_processing()` to initialize tracker and record first transition
3. Modify `update_status()` to record each state change
4. Modify `_archive_run()` to finalize and include transitions

## Context Budget

| Metric | Estimate |
|--------|----------|
| Files to read | 2 (~250 lines) |
| New code to write | ~80 lines |
| Test code to write | ~120 lines |
| **Estimated context usage** | **~18%** |

This is well within the 60% threshold.

## Files to Create/Modify

### New Files
1. `/root/repo/services/state_transition.py` - StateTransition dataclass and interface (~50 lines)
2. `/root/repo/tests/unit/test_state_transition_tracker.py` - Unit tests (~100 lines)

### Modified Files
1. `/root/repo/services/processing_status_manager.py` - Integration (~30 lines added)

**Total files: 3** (within threshold of 4)

## Out of Scope

1. **Gantt Chart Generation**: Covered in Part 2 (Gantt Chart Generator Core)
2. **API Response Changes**: Covered in Part 3 (API Enhancement)
3. **Database Persistence**: State transitions are in-memory only
4. **Historical Data Migration**: Existing archived runs will not have transition data

## Acceptance Criteria

1. `StateTransition` dataclass correctly stores state, description, timestamp, and duration
2. `StateTransitionTracker` records transitions in chronological order
3. `finalize()` correctly calculates duration between consecutive transitions
4. Transitions are included in archived run dictionaries as `state_transitions`
5. Thread-safe operation for concurrent access
6. All unit tests pass
7. Existing functionality remains unaffected (backward compatible)

## Dependencies

- None (this is the foundation layer)

## Dependents

- **1.2 Gantt Chart Generator Core**: Will consume `state_transitions` data
- **1.3 API Enhancement**: Will expose `state_transitions` in API response
