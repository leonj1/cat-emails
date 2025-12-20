---
executor: bdd
source_feature: ./tests/bdd/state_transition_tracking.feature
---

<objective>
Implement the State Transition Tracking feature as defined by the BDD scenarios below.
The implementation must make all Gherkin scenarios pass.

This is Part 1 of 3 for the Gantt Chart Text Generation feature. It provides the foundational
layer that records timestamps for each processing state change, calculates durations between
transitions, and stores the transition history in archived run data.
</objective>

<gherkin>
Feature: State Transition Tracking for Email Processing Runs
  As a system administrator
  I want state transitions to be tracked during email processing
  So that I can generate Gantt chart visualizations and analyze processing performance

  Background:
    Given the processing status manager is initialized
    And state transition tracking is enabled

  Scenario: Record state transitions during email processing
    Given a processing run is started for "user@gmail.com"
    When the processing state changes to "CONNECTING" with step "Connecting to Gmail IMAP"
    And the processing state changes to "FETCHING" with step "Fetching emails"
    And the processing state changes to "CATEGORIZING" with step "Categorizing emails"
    Then 3 state transitions should be recorded
    And each transition should have a timestamp
    And each transition should have the state and step description

  Scenario: Calculate duration between state transitions
    Given a processing run is started for "user@gmail.com" at "2025-01-01 10:00:00"
    When the processing state changes to "CONNECTING" at "2025-01-01 10:00:00"
    And the processing state changes to "FETCHING" at "2025-01-01 10:00:05"
    Then the CONNECTING transition should have a duration of 5.0 seconds

  Scenario: Clear state transitions when run completes
    Given a processing run is started for "user@gmail.com"
    And state transitions have been recorded
    When the processing run is archived
    Then the transitions should be included in the archived run
    And the active transition list should be cleared

  Scenario: State transitions persist in archived run data
    Given a completed processing run with transitions
    When the run is archived to history
    Then the archived run should contain state_transitions array
    And each transition should have state, step_description, timestamp, and duration_seconds
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **StateTransition Dataclass** (`services/state_transition.py`)
   - Fields: state (str), step_description (str), timestamp (datetime), duration_seconds (Optional[float])
   - Method: to_dict() for JSON serialization with ISO format timestamps

2. **IStateTransitionTracker Interface** (`services/interfaces/state_transition_tracker_interface.py`)
   - record_transition(state, step_description, timestamp) - Record a state transition
   - get_transitions() - Get all recorded transitions as List[StateTransition]
   - finalize() - Calculate durations, return complete list with duration_seconds populated
   - clear() - Clear all transitions for next run

3. **StateTransitionTracker Implementation** (`services/state_transition.py`)
   - Thread-safe implementation with threading.Lock
   - In-memory storage of transitions in chronological order
   - Duration calculation: difference between consecutive transition timestamps
   - Last transition has duration_seconds = 0.0

4. **ProcessingStatusManager Integration** (`services/processing_status_manager.py`)
   - Add StateTransitionTracker instance
   - start_processing(): Clear tracker, record initial IDLE transition
   - update_status(): Record each state change as a transition
   - complete_processing(): Finalize transitions, add state_transitions to archived run dict

Edge Cases to Handle:
- Thread-safe operation for concurrent access
- Empty transition list returns empty array
- Duration calculation handles same-timestamp transitions (0.0 seconds)
- Backward compatible - existing archived run fields unchanged
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-state-transition-tracking.md
Gap Analysis: specs/GAP-ANALYSIS.md
DRAFT Specification: specs/DRAFT-state-transition-tracking.md

Reuse Opportunities (from gap analysis):
- ProcessingState enum from processing_status_manager.py for state names
- Thread-safe pattern with threading.RLock from ProcessingStatusManager
- to_dict() pattern for JSON serialization from AccountStatus
- Interface pattern from services/interfaces/blocking_recommendation_collector_interface.py
- Test structure from tests/unit/test_blocking_recommendation_collector.py

New Components Needed:
- services/state_transition.py (StateTransition dataclass + StateTransitionTracker class)
- services/interfaces/state_transition_tracker_interface.py
- tests/unit/test_state_transition_tracker.py

Files to Modify:
- services/processing_status_manager.py (integration with tracker)
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Maintain consistency with project structure
- Place interface in services/interfaces/ directory
- Place implementation in services/ directory
- Place tests in tests/unit/ directory

Code Patterns to Follow:
```python
# Interface pattern (from existing codebase)
from abc import ABC, abstractmethod

class IStateTransitionTracker(ABC):
    @abstractmethod
    def record_transition(self, state: str, step_description: str, timestamp: Optional[datetime] = None) -> None:
        pass

# Dataclass pattern (from existing codebase)
@dataclass
class StateTransition:
    state: str
    step_description: str
    timestamp: datetime
    duration_seconds: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            'state': self.state,
            'step_description': self.step_description,
            'timestamp': self.timestamp.isoformat(),
            'duration_seconds': self.duration_seconds
        }

# Thread-safe pattern (from ProcessingStatusManager)
class StateTransitionTracker(IStateTransitionTracker):
    def __init__(self):
        self._transitions: List[StateTransition] = []
        self._lock = threading.Lock()
```

Integration Pattern:
```python
# In ProcessingStatusManager.__init__
self._transition_tracker = StateTransitionTracker()

# In ProcessingStatusManager.start_processing
self._transition_tracker.clear()
self._transition_tracker.record_transition("IDLE", "Initializing processing")

# In ProcessingStatusManager.update_status
self._transition_tracker.record_transition(state.name, step)

# In ProcessingStatusManager.complete_processing
transitions = self._transition_tracker.finalize()
archived_run['state_transitions'] = [t.to_dict() for t in transitions]
self._transition_tracker.clear()
```
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Record state transitions during email processing
- [ ] Scenario: Calculate duration between state transitions
- [ ] Scenario: Clear state transitions when run completes
- [ ] Scenario: State transitions persist in archived run data
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- Thread-safe operation verified
- Backward compatible with existing ProcessingStatusManager behavior
- StateTransition dataclass has to_dict() method
- Durations correctly calculated between consecutive transitions
- state_transitions array included in archived run dictionaries
</success_criteria>
