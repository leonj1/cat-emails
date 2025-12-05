# BDD Specification: State Transition Tracking

## Overview

This specification defines the behavior for tracking state transitions during email processing runs. State transition tracking is the foundational layer that records timestamps for each processing state change, calculates durations between transitions, and stores the transition history in archived run data.

This is **Part 1 of 3** for the Gantt Chart Text Generation feature.

## User Stories

- As a system administrator, I want state transitions to be tracked during email processing so that I can generate Gantt chart visualizations and analyze processing performance

## Feature Files

| Feature File | Scenarios | Coverage |
|--------------|-----------|----------|
| state_transition_tracking.feature | 4 | Recording, duration calculation, archiving, persistence |

## Scenarios Summary

### state_transition_tracking.feature

1. **Record state transitions during email processing** - Verifies that state changes are captured with timestamps and descriptions as processing progresses through CONNECTING, FETCHING, CATEGORIZING states

2. **Calculate duration between state transitions** - Validates that duration in seconds is correctly calculated based on the time difference between consecutive transitions

3. **Clear state transitions when run completes** - Ensures transitions are archived with the run data and the active transition list is cleared for the next run

4. **State transitions persist in archived run data** - Confirms that archived runs contain a state_transitions array with all required fields (state, step_description, timestamp, duration_seconds)

## Acceptance Criteria

### Recording State Transitions
- Each state change during processing creates a StateTransition record
- Each transition includes: state name, step description, timestamp
- Transitions are stored in chronological order
- Thread-safe operation for concurrent access

### Duration Calculation
- Duration is calculated as the difference between consecutive transition timestamps
- Duration is stored in seconds as a float
- Last transition has duration of 0.0 (or calculated from end_time if available)
- finalize() method populates all duration values

### Archiving and Persistence
- Transitions are included in archived run dictionary as state_transitions array
- Active transition list is cleared after archiving
- Each transition in archive contains: state, step_description, timestamp (ISO format), duration_seconds
- Existing archived run fields remain unchanged (backward compatible)

## Data Model

### StateTransition
```
- state: string (ProcessingState name)
- step_description: string (human-readable description)
- timestamp: datetime (when state was entered)
- duration_seconds: float (calculated from next transition)
```

### Enhanced Archived Run
```
archived_run = {
    # ... existing fields unchanged ...
    'state_transitions': [
        {
            'state': 'CONNECTING',
            'step_description': 'Connecting to Gmail IMAP',
            'timestamp': '2025-01-01T10:00:00Z',
            'duration_seconds': 5.2
        },
        ...
    ]
}
```

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| services/state_transition.py | Create | StateTransition dataclass, IStateTransitionTracker interface, StateTransitionTracker implementation |
| services/processing_status_manager.py | Modify | Integration with state transition tracking |
| tests/unit/test_state_transition_tracker.py | Create | Unit tests for state transition tracking |

**Total: 3 files** (within threshold of 4)

## Dependencies

- None (this is the foundation layer)

## Dependents

- **Part 2 - Gantt Chart Generator Core**: Will consume state_transitions data
- **Part 3 - API Enhancement**: Will expose state_transitions in API response

## Out of Scope

- Gantt chart generation (Part 2)
- API response changes (Part 3)
- Database persistence (in-memory only)
- Historical data migration
