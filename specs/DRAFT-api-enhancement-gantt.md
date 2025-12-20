# DRAFT: API Enhancement and Integration for Gantt Chart Text

## Overview

This specification defines the integration of the Gantt chart generation feature into the API response layer. The goal is to include the `gantt_chart_text` field in the historical audit response so the UI can render Gantt charts independently.

**Dependencies**:
- Sub-task 1 (Completed): `StateTransition` dataclass and `StateTransitionTracker` integrated into `ProcessingStatusManager`
- Sub-task 2 (Completed): `IGanttChartGenerator` interface and `GanttChartGenerator` implementation

## Interfaces Needed

### 1. IGanttChartTextEnricher (New Interface)

Abstracts the enrichment of archived run data with Gantt chart text.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class IGanttChartTextEnricher(ABC):
    """Interface for enriching archived run data with Gantt chart text."""

    @abstractmethod
    def enrich_run(self, archived_run: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add gantt_chart_text field to an archived run record.

        Args:
            archived_run: Dictionary containing archived run data with 'state_transitions'

        Returns:
            The same dictionary with 'gantt_chart_text' field added
        """
        pass

    @abstractmethod
    def enrich_runs(self, archived_runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch enrichment for multiple archived runs.

        Args:
            archived_runs: List of archived run dictionaries

        Returns:
            List of enriched dictionaries with 'gantt_chart_text' fields
        """
        pass
```

## Data Models

### Updated Archived Run Schema

The existing archived run dictionary structure remains unchanged, with one new optional field:

```python
archived_run = {
    # Existing fields (unchanged)
    'email_address': str,
    'start_time': str,  # ISO format
    'end_time': str,    # ISO format
    'duration_seconds': float,
    'final_state': str,
    'final_step': str,
    'error_message': Optional[str],
    'final_progress': Optional[Dict],
    'emails_reviewed': int,
    'emails_tagged': int,
    'emails_deleted': int,
    'state_transitions': List[Dict],  # Added in Sub-task 1

    # New field
    'gantt_chart_text': Optional[str]  # Mermaid Gantt chart syntax
}
```

## Logic Flow

### Enrichment at Archive Time (ProcessingStatusManager.complete_processing)

```pseudocode
FUNCTION complete_processing():
    # ... existing logic ...

    # After finalizing transitions
    transitions = self._transition_tracker.finalize()

    # Generate Gantt chart text if we have transitions
    gantt_chart_text = None
    IF transitions NOT EMPTY:
        gantt_generator = GanttChartGenerator()
        gantt_chart_text = gantt_generator.generate(
            transitions=transitions,
            title=self._current_status.email_address,
            include_zero_duration=False
        )

    # Create archived run record with gantt_chart_text
    archived_run = {
        # ... existing fields ...
        'state_transitions': [t.to_dict() for t in transitions],
        'gantt_chart_text': gantt_chart_text
    }

    # Add to history
    self._recent_runs.append(archived_run)
```

### Lazy Enrichment for Legacy Runs

For backward compatibility, legacy runs without `gantt_chart_text` can be enriched on-the-fly:

```pseudocode
FUNCTION enrich_run(archived_run):
    # Skip if already enriched
    IF 'gantt_chart_text' IN archived_run:
        RETURN archived_run

    # Check for state_transitions
    transitions_data = archived_run.GET('state_transitions', [])

    IF transitions_data IS EMPTY:
        # Legacy run without transition data
        archived_run['gantt_chart_text'] = None
        RETURN archived_run

    # Reconstruct StateTransition objects
    transitions = []
    FOR t_dict IN transitions_data:
        transition = StateTransition(
            state=t_dict['state'],
            step_description=t_dict['step_description'],
            timestamp=datetime.fromisoformat(t_dict['timestamp']),
            duration_seconds=t_dict.get('duration_seconds')
        )
        transitions.APPEND(transition)

    # Generate Gantt chart
    gantt_generator = GanttChartGenerator()
    archived_run['gantt_chart_text'] = gantt_generator.generate(
        transitions=transitions,
        title=archived_run.get('email_address', 'Unknown'),
        include_zero_duration=False
    )

    RETURN archived_run
```

## API Response Changes

### GET /api/processing/history

**Current Response**:
```json
{
    "recent_runs": [
        {
            "email_address": "user@example.com",
            "start_time": "2025-12-05T10:00:00Z",
            "end_time": "2025-12-05T10:05:00Z",
            "duration_seconds": 300.0,
            "final_state": "COMPLETED",
            "final_step": "Processing completed",
            "error_message": null,
            "final_progress": null,
            "emails_reviewed": 50,
            "emails_tagged": 10,
            "emails_deleted": 5,
            "state_transitions": [...]
        }
    ],
    "total_retrieved": 1,
    "timestamp": "2025-12-05T10:30:00Z"
}
```

**Updated Response** (with new field):
```json
{
    "recent_runs": [
        {
            "email_address": "user@example.com",
            "start_time": "2025-12-05T10:00:00Z",
            "end_time": "2025-12-05T10:05:00Z",
            "duration_seconds": 300.0,
            "final_state": "COMPLETED",
            "final_step": "Processing completed",
            "error_message": null,
            "final_progress": null,
            "emails_reviewed": 50,
            "emails_tagged": 10,
            "emails_deleted": 5,
            "state_transitions": [...],
            "gantt_chart_text": "gantt\n    title Email Processing: user@example.com\n    dateFormat YYYY-MM-DD HH:mm:ss\n    axisFormat %H:%M:%S\n\n    section Initialization\n    Initializing processing :done, idle_0, 2025-12-05 10:00:00, 5s\n..."
        }
    ],
    "total_retrieved": 1,
    "timestamp": "2025-12-05T10:30:00Z"
}
```

### GET /api/status (with include_recent=true)

Same structure applies to the `recent_runs` array in the unified status response.

## Edge Cases

### 1. Empty History (No Completed Runs)

```json
{
    "recent_runs": [],
    "total_retrieved": 0,
    "timestamp": "2025-12-05T10:30:00Z"
}
```

- No change needed - empty array is backward compatible

### 2. Run Failed with ERROR State

```json
{
    "recent_runs": [
        {
            "email_address": "user@example.com",
            "final_state": "ERROR",
            "error_message": "Authentication failed",
            "state_transitions": [
                {"state": "IDLE", "step_description": "Initializing", "timestamp": "...", "duration_seconds": 2.0},
                {"state": "CONNECTING", "step_description": "Connecting to Gmail", "timestamp": "...", "duration_seconds": 3.0},
                {"state": "ERROR", "step_description": "Authentication failed", "timestamp": "...", "duration_seconds": 0.0}
            ],
            "gantt_chart_text": "gantt\n    title Email Processing: user@example.com\n    ..."
        }
    ]
}
```

- Gantt chart is generated normally showing the partial progress
- ERROR state appears in the "Error" section

### 3. Legacy Runs Without Transition Data

```json
{
    "recent_runs": [
        {
            "email_address": "legacy@example.com",
            "start_time": "2025-11-01T10:00:00Z",
            "state_transitions": [],
            "gantt_chart_text": null
        }
    ]
}
```

- `gantt_chart_text` is `null` when no transition data exists
- UI must handle null gracefully (show placeholder or skip rendering)

### 4. Zero-Duration Transitions

- Zero-duration transitions are excluded from Gantt chart by default (`include_zero_duration=False`)
- This keeps charts clean and focuses on meaningful processing phases

## Backward Compatibility

### Existing Fields Unchanged

All existing response fields remain:
- `email_address`
- `start_time`
- `end_time`
- `duration_seconds`
- `final_state`
- `final_step`
- `error_message`
- `final_progress`
- `emails_reviewed`
- `emails_tagged`
- `emails_deleted`
- `state_transitions`

### New Field is Optional

- `gantt_chart_text` is added as an optional field
- Value can be `null` for legacy runs or runs without transition data
- Existing API consumers can ignore this field

### No Breaking Changes

- Response structure is additive only
- No fields removed or renamed
- No changes to request parameters

## Implementation Location

### Files to Modify

1. **`/root/repo/services/processing_status_manager.py`**
   - Import `GanttChartGenerator` from `services.gantt_chart_generator`
   - Modify `complete_processing()` to generate Gantt chart text
   - Add `gantt_chart_text` to archived_run dictionary

2. **`/root/repo/services/interfaces/gantt_chart_text_enricher_interface.py`** (New)
   - Define `IGanttChartTextEnricher` interface

3. **`/root/repo/services/gantt_chart_text_enricher.py`** (New)
   - Implement `GanttChartTextEnricher` for lazy enrichment of legacy runs

### Files Unchanged

- `/root/repo/api_service.py` - No changes needed, already returns `get_recent_runs()` output
- Existing API endpoint logic remains unchanged

## Context Budget Estimate

| Category | Count | Estimated Lines |
|----------|-------|-----------------|
| Files to read | 3 | ~800 lines |
| New code to write | ~50 lines | - |
| Test code to write | ~80 lines | - |
| **Estimated context usage** | **~15%** | Acceptable |

### Breakdown

- **Read**: `processing_status_manager.py` (420 lines), `gantt_chart_generator.py` (164 lines), `state_transition.py` (121 lines)
- **Write**: Modify `complete_processing()` method (~15 lines), new interface (~15 lines), new enricher class (~30 lines)
- **Tests**: Unit tests for enricher (~40 lines), integration tests for API response (~40 lines)

## Acceptance Criteria

1. `GET /api/processing/history` returns `gantt_chart_text` field for each run
2. `GET /api/status?include_recent=true` returns `gantt_chart_text` field for each run
3. Failed runs (ERROR state) still generate partial Gantt charts
4. Legacy runs without transition data have `gantt_chart_text: null`
5. All existing response fields remain unchanged
6. No API contract breaking changes
