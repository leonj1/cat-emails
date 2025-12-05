# DRAFT Specification: Email Processing Audit Counts - Phase 2 (Service Layer)

## Overview

**Phase 2 Focus**: Add audit count tracking to the service layer. This phase extends the `AccountStatus` dataclass and `ProcessingStatusManager` to track emails reviewed, tagged, and deleted during processing.

**Prerequisites**: Phase 1 complete - database columns already exist in `ProcessingRun` model.

**Scope Boundary**: Service layer ONLY. No database changes, no API changes.

## Target File

**Single File Modification**: `/root/repo/services/processing_status_manager.py`

## Interfaces Needed

### IAuditCountTracker Protocol

```python
from typing import Protocol, Dict

class IAuditCountTracker(Protocol):
    """Protocol for tracking email processing audit counts"""

    def increment_reviewed(self, count: int = 1) -> None:
        """Increment the count of emails reviewed during processing"""
        ...

    def increment_tagged(self, count: int = 1) -> None:
        """Increment the count of emails that received labels"""
        ...

    def increment_deleted(self, count: int = 1) -> None:
        """Increment the count of emails deleted/trashed"""
        ...

    def get_audit_counts(self) -> Dict[str, int]:
        """Return current audit counts as dictionary"""
        ...
```

## Data Models

### AccountStatus Dataclass Extension

Add three new integer fields to the existing `AccountStatus` dataclass:

```python
@dataclass
class AccountStatus:
    """Account processing status information"""
    email_address: str
    state: ProcessingState
    current_step: str
    progress: Optional[Dict[str, Any]] = None
    start_time: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    error_message: Optional[str] = None
    # NEW: Audit count fields
    emails_reviewed: int = 0
    emails_tagged: int = 0
    emails_deleted: int = 0
```

### Updated to_dict() Method

The existing `to_dict()` method uses `asdict()` so new fields will be automatically included. No changes needed to that method.

## Logic Flow

### Increment Methods

Each increment method follows this pattern:

```text
increment_reviewed(count=1):
    1. ACQUIRE lock
    2. IF current_status exists:
       a. current_status.emails_reviewed += count
    3. RELEASE lock
```

Same pattern for `increment_tagged()` and `increment_deleted()`.

### Get Audit Counts

```text
get_audit_counts():
    1. ACQUIRE lock
    2. IF current_status exists:
       a. RETURN {reviewed, tagged, deleted} dict
    3. ELSE:
       a. RETURN {0, 0, 0} dict
    4. RELEASE lock
```

### Complete Processing Update

Modify the `archived_run` dictionary in `complete_processing()`:

```text
complete_processing():
    ... existing logic ...

    archived_run = {
        ... existing fields ...
        # NEW: Include audit counts in archived record
        'emails_reviewed': current_status.emails_reviewed,
        'emails_tagged': current_status.emails_tagged,
        'emails_deleted': current_status.emails_deleted,
    }
```

## Implementation Details

### Method Signatures

```python
def increment_reviewed(self, count: int = 1) -> None:
    """
    Increment the count of emails reviewed.

    Args:
        count: Number to increment by (default 1)

    Thread-safe: Uses internal RLock
    """

def increment_tagged(self, count: int = 1) -> None:
    """
    Increment the count of emails that received labels.

    Args:
        count: Number to increment by (default 1)

    Thread-safe: Uses internal RLock
    """

def increment_deleted(self, count: int = 1) -> None:
    """
    Increment the count of emails deleted.

    Args:
        count: Number to increment by (default 1)

    Thread-safe: Uses internal RLock
    """

def get_audit_counts(self) -> Dict[str, int]:
    """
    Get current audit counts.

    Returns:
        Dictionary with keys: emails_reviewed, emails_tagged, emails_deleted
        Returns zeros if no active session

    Thread-safe: Uses internal RLock
    """
```

### Thread Safety

All methods use the existing `self._lock` (RLock) that is already used throughout the class. No additional synchronization primitives needed.

## Acceptance Criteria

1. AccountStatus dataclass has three new integer fields with default value 0
2. increment_reviewed() increments emails_reviewed count
3. increment_tagged() increments emails_tagged count
4. increment_deleted() increments emails_deleted count
5. get_audit_counts() returns current counts as dictionary
6. complete_processing() includes audit counts in archived_run record
7. All increment operations are thread-safe (use existing lock)
8. Calling increment methods when no session active is a no-op (no exception)
9. get_current_status() returns audit counts (automatic via to_dict)

## Testing Strategy

### Unit Tests Required

```python
# Test AccountStatus defaults
def test_account_status_has_audit_fields_with_defaults():
    status = AccountStatus(email_address="test@example.com",
                          state=ProcessingState.IDLE,
                          current_step="init")
    assert status.emails_reviewed == 0
    assert status.emails_tagged == 0
    assert status.emails_deleted == 0

# Test increment methods
def test_increment_reviewed():
    manager = ProcessingStatusManager()
    manager.start_processing("test@example.com")
    manager.increment_reviewed()
    manager.increment_reviewed(5)
    assert manager._current_status.emails_reviewed == 6

def test_increment_tagged():
    manager = ProcessingStatusManager()
    manager.start_processing("test@example.com")
    manager.increment_tagged(3)
    assert manager._current_status.emails_tagged == 3

def test_increment_deleted():
    manager = ProcessingStatusManager()
    manager.start_processing("test@example.com")
    manager.increment_deleted(2)
    assert manager._current_status.emails_deleted == 2

# Test increment with no active session (should not raise)
def test_increment_without_session_is_noop():
    manager = ProcessingStatusManager()
    manager.increment_reviewed()  # Should not raise
    manager.increment_tagged()
    manager.increment_deleted()

# Test get_audit_counts
def test_get_audit_counts():
    manager = ProcessingStatusManager()
    manager.start_processing("test@example.com")
    manager.increment_reviewed(10)
    manager.increment_tagged(5)
    manager.increment_deleted(2)
    counts = manager.get_audit_counts()
    assert counts == {
        'emails_reviewed': 10,
        'emails_tagged': 5,
        'emails_deleted': 2
    }

def test_get_audit_counts_no_session():
    manager = ProcessingStatusManager()
    counts = manager.get_audit_counts()
    assert counts == {
        'emails_reviewed': 0,
        'emails_tagged': 0,
        'emails_deleted': 0
    }

# Test complete_processing includes audit counts
def test_complete_processing_archives_audit_counts():
    manager = ProcessingStatusManager()
    manager.start_processing("test@example.com")
    manager.increment_reviewed(100)
    manager.increment_tagged(50)
    manager.increment_deleted(25)
    manager.complete_processing()

    recent = manager.get_recent_runs(limit=1)
    assert len(recent) == 1
    assert recent[0]['emails_reviewed'] == 100
    assert recent[0]['emails_tagged'] == 50
    assert recent[0]['emails_deleted'] == 25

# Test to_dict includes audit counts
def test_to_dict_includes_audit_counts():
    status = AccountStatus(
        email_address="test@example.com",
        state=ProcessingState.PROCESSING,
        current_step="testing",
        emails_reviewed=10,
        emails_tagged=5,
        emails_deleted=2
    )
    result = status.to_dict()
    assert result['emails_reviewed'] == 10
    assert result['emails_tagged'] == 5
    assert result['emails_deleted'] == 2
```

## Context Budget

| Item | Count | Estimated Lines |
|------|-------|-----------------|
| Files to read | 1 | ~343 lines |
| New code to write | ~45 lines | - |
| Test code to write | ~80 lines | - |

**Estimated context usage**: ~15% (Well under 60% threshold)

## Files Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `/root/repo/services/processing_status_manager.py` | Modify | +45 lines |
| `/root/repo/tests/test_processing_status_manager.py` | Create/Modify | +80 lines |

**Total Files**: 2 (under 5 file limit)

## Out of Scope (Handled in Later Phases)

- Database persistence of audit counts (Phase 3 or later)
- API response schema changes (Phase 1.3)
- Overflow protection and validation (Phase 1.4)
- Integration with email processing consumers (separate task)
