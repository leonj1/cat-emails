# DRAFT Specification: Audit Counts Phase 3 - API Layer

## Overview

Update the `DatabaseService.get_processing_runs()` method to expose the audit count fields (`emails_reviewed`, `emails_tagged`, `emails_deleted`) in API responses.

## Scope

**In Scope (API Layer Only)**:
- Update `get_processing_runs()` return dictionary to include audit count fields
- Map ProcessingRun model fields to API response fields

**Out of Scope**:
- Database schema changes (completed in Phase 1)
- Service layer tracking logic (completed in Phase 2)
- Concurrency safety (deferred to Phase 4)

## Current State

**File**: `/root/repo/services/database_service.py` (lines 287-305)

The `get_processing_runs()` method currently returns:

```python
return [
    {
        'run_id': f"run-{run.id}",
        'started_at': run.start_time,
        'completed_at': run.end_time,
        'duration_seconds': (run.end_time - run.start_time).total_seconds() if run.end_time else None,
        'emails_processed': run.emails_processed,
        'emails_deleted': 0,  # HARDCODED - not reading from model
        'success': run.state == 'completed' and not run.error_message,
        'error_message': run.error_message
    } for run in runs
]
```

**Problem**:
- `emails_deleted` is hardcoded to `0` instead of reading from `run.emails_deleted`
- `emails_reviewed` is not included in the response
- `emails_tagged` is not included in the response

## Required Changes

### 1. Update get_processing_runs() Response Dictionary

**File**: `/root/repo/services/database_service.py`

**Location**: Lines 294-305 (the return statement in `get_processing_runs()`)

**Change**: Update the dictionary comprehension to read actual values from the ProcessingRun model:

```python
def get_processing_runs(self, limit: int = 100) -> List[Dict]:
    """Get recent processing runs with audit counts"""
    with self.Session() as session:
        runs = session.query(ProcessingRun).order_by(
            ProcessingRun.start_time.desc()
        ).limit(limit).all()

        return [
            {
                'run_id': f"run-{run.id}",
                'started_at': run.start_time,
                'completed_at': run.end_time,
                'duration_seconds': (run.end_time - run.start_time).total_seconds() if run.end_time else None,
                'emails_processed': run.emails_processed,
                # UPDATED: Read actual audit counts from model
                'emails_reviewed': run.emails_reviewed or 0,
                'emails_tagged': run.emails_tagged or 0,
                'emails_deleted': run.emails_deleted or 0,
                'success': run.state == 'completed' and not run.error_message,
                'error_message': run.error_message
            } for run in runs
        ]
```

## Interfaces Needed

No new interfaces required. This change updates an existing method's return value.

## Data Models

No new data models required. The ProcessingRun model already contains the required fields (added in Phase 1):

```python
# From /root/repo/models/database.py lines 221-223
emails_reviewed = Column(Integer, default=0, nullable=False)
emails_tagged = Column(Integer, default=0, nullable=False)
emails_deleted = Column(Integer, default=0, nullable=False)
```

## Logic Flow

```text
1. API client calls GET /api/processing/runs
2. API handler calls DatabaseService.get_processing_runs()
3. Method queries ProcessingRun table
4. FOR EACH run:
   a. Build response dict with existing fields
   b. ADD emails_reviewed from run.emails_reviewed (default to 0 if None)
   c. ADD emails_tagged from run.emails_tagged (default to 0 if None)
   d. UPDATE emails_deleted to read from run.emails_deleted (default to 0 if None)
5. Return list of run dictionaries
```

## API Response Format

The `/api/processing/runs` endpoint will return:

```json
{
  "runs": [
    {
      "run_id": "run-123",
      "started_at": "2025-12-04T10:00:00Z",
      "completed_at": "2025-12-04T10:05:00Z",
      "duration_seconds": 300,
      "emails_processed": 50,
      "emails_reviewed": 100,
      "emails_tagged": 45,
      "emails_deleted": 30,
      "success": true,
      "error_message": null
    }
  ]
}
```

## Context Budget

| Item | Count | Estimated Lines |
|------|-------|-----------------|
| Files to read | 2 | ~380 lines |
| - database_service.py | 1 | ~363 lines |
| - database.py (ProcessingRun only) | 1 | ~20 lines (reference only) |
| New code to write | ~6 lines | (3 field additions/changes) |
| Test code to write | ~40 lines | |

**Estimated context usage**: ~15% (Well under 60% threshold)

## Acceptance Criteria

1. `get_processing_runs()` returns `emails_reviewed` field with actual value from database
2. `get_processing_runs()` returns `emails_tagged` field with actual value from database
3. `get_processing_runs()` returns `emails_deleted` field with actual value from database (not hardcoded 0)
4. All new fields default to 0 when database value is None (backward compatibility)
5. Existing fields remain unchanged
6. No breaking changes to existing API consumers

## Testing Strategy

### Unit Tests

**File**: New test or extend existing test for DatabaseService

```python
def test_get_processing_runs_includes_audit_counts():
    """Verify get_processing_runs returns audit count fields"""
    # Setup: Create ProcessingRun with known audit counts
    run = ProcessingRun(
        email_address="test@example.com",
        start_time=datetime.utcnow(),
        state="completed",
        emails_reviewed=100,
        emails_tagged=45,
        emails_deleted=30
    )

    # Execute
    result = database_service.get_processing_runs(limit=1)

    # Assert
    assert result[0]['emails_reviewed'] == 100
    assert result[0]['emails_tagged'] == 45
    assert result[0]['emails_deleted'] == 30

def test_get_processing_runs_defaults_null_audit_counts_to_zero():
    """Verify None audit counts are returned as 0"""
    # Setup: Create ProcessingRun with None audit counts (old records)
    run = ProcessingRun(
        email_address="test@example.com",
        start_time=datetime.utcnow(),
        state="completed",
        emails_reviewed=None,
        emails_tagged=None,
        emails_deleted=None
    )

    # Execute
    result = database_service.get_processing_runs(limit=1)

    # Assert
    assert result[0]['emails_reviewed'] == 0
    assert result[0]['emails_tagged'] == 0
    assert result[0]['emails_deleted'] == 0
```

### Edge Cases

- ProcessingRun with all audit counts as 0
- ProcessingRun with None values (legacy records before migration)
- ProcessingRun with very large counts (integer overflow not expected but noted)

## Implementation Notes

1. Use `or 0` pattern to handle None values from legacy records
2. No changes to method signature or parameters
3. Backward compatible - only adds new fields to response
4. Existing consumers can ignore new fields if not needed

## Dependencies

- Phase 1 (Database columns) must be complete - VERIFIED
- Phase 2 (Service tracking) should be complete for meaningful data - VERIFIED
