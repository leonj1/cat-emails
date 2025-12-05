# BDD Specification: API Enhancement for Gantt Chart Text

## Feature Overview

Integrate Gantt chart text generation into the processing history API response. Each completed run will include a `gantt_chart_text` field containing valid Mermaid syntax that the UI can render independently.

## Gherkin Feature File

**Location**: `./tests/bdd/api_enhancement_gantt.feature`

## Scenario Summary

| Category | Count | Description |
|----------|-------|-------------|
| API Response Enhancement | 1 | Include gantt_chart_text in response |
| Multiple Runs | 1 | Each run has its own chart |
| Empty History | 1 | Handle no completed runs |
| Backward Compatibility | 1 | Existing fields unchanged |
| Error Handling | 1 | Failed runs with partial charts |
| **Total** | **5** | Complete API integration coverage |

## Key Scenarios

### 1. Include gantt_chart_text in processing history response

Validates that completed runs include:
- `gantt_chart_text` field in the response
- Valid Mermaid syntax starting with "gantt"
- Title containing the email address

### 2. Return gantt chart for each run per account

Verifies that:
- Multiple runs each have their own `gantt_chart_text`
- Charts correctly reference the associated email address
- Runs from different accounts are properly isolated

### 3. Handle empty history with no completed runs

Edge case handling:
- Empty `recent_runs` array
- `total_retrieved` is 0
- No errors thrown

### 4. Maintain backward compatibility with existing API consumers

Ensures all existing fields remain unchanged:
- email_address
- start_time
- end_time
- duration_seconds
- final_state
- final_step
- emails_reviewed
- emails_tagged
- emails_deleted
- state_transitions

The `gantt_chart_text` is additive, not replacing any existing field.

### 5. Generate Gantt chart for run that failed during processing

Error state handling:
- Failed runs are included in response
- Gantt chart shows partial progress up to error
- Error state is indicated in the chart

## API Response Schema

```json
{
  "recent_runs": [
    {
      "email_address": "user@gmail.com",
      "start_time": "2025-01-01T10:00:00",
      "end_time": "2025-01-01T10:02:30",
      "duration_seconds": 150.0,
      "final_state": "COMPLETED",
      "final_step": "Processing completed",
      "emails_reviewed": 45,
      "emails_tagged": 40,
      "emails_deleted": 5,
      "state_transitions": [...],
      "gantt_chart_text": "gantt\n    title Email Processing: user@gmail.com\n    ..."
    }
  ],
  "total_retrieved": 1
}
```

## Implementation Components

1. **ProcessingStatusManager Enhancement** (`/root/repo/services/processing_status_manager.py`)
   - Call `GanttChartGenerator.generate()` during `complete_processing()`
   - Add `gantt_chart_text` to archived run dictionary

2. **GanttChartGenerator** (from Sub-task 2)
   - Already implemented in `/root/repo/services/gantt_chart_generator.py`
   - Converts `state_transitions` to Mermaid syntax

## Dependencies

- **Sub-task 1**: StateTransition dataclass, state_transitions in archived runs
- **Sub-task 2**: GanttChartGenerator with generate() method

## Acceptance Criteria

1. ✅ gantt_chart_text included in processing history response
2. ✅ Each run has its own gantt_chart_text
3. ✅ Empty history returns empty array without errors
4. ✅ All existing API fields remain unchanged
5. ✅ Failed runs include partial Gantt charts
6. ✅ UI can render the Mermaid syntax independently
