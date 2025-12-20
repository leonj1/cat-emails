# DRAFT Specification: Increment Methods for Audit Records

## Task Reference
- **Digest Task**: 1.2 Increment Methods - Increment Behavior
- **Status**: In Progress
- **Parent**: Enhance Audit Records for Email Processing

## Overview

Add two increment methods to `ProcessingStatusManager` for tracking emails categorized and emails skipped during processing runs. These methods follow the exact pattern established by existing increment methods (`increment_reviewed`, `increment_tagged`, `increment_deleted`).

## Interfaces Needed

No new interfaces required. The methods extend the existing `ProcessingStatusManager` class which already has the established pattern.

### Method Signatures

```python
def increment_categorized(self, count: int = 1) -> None:
    """
    Increment the count of emails categorized during processing.

    Args:
        count: Number of emails to add to the categorized count (default: 1)

    Note:
        This is a no-op if no processing session is active.
        Thread-safe operation using internal lock.
    """

def increment_skipped(self, count: int = 1) -> None:
    """
    Increment the count of emails skipped during processing.

    Args:
        count: Number of emails to add to the skipped count (default: 1)

    Note:
        This is a no-op if no processing session is active.
        Thread-safe operation using internal lock.
    """
```

## Data Models

No new data models required. The `AccountStatus` dataclass already has the fields from sub-task 1.1:
- `emails_categorized: int = 0`
- `emails_skipped: int = 0`

## Logic Flow

### increment_categorized() Pseudocode

```
FUNCTION increment_categorized(count: int = 1) -> None:
    ACQUIRE self._lock:
        IF self._current_status IS None:
            RETURN  # No-op, silently ignore

        self._current_status.emails_categorized += count
    RELEASE lock
```

### increment_skipped() Pseudocode

```
FUNCTION increment_skipped(count: int = 1) -> None:
    ACQUIRE self._lock:
        IF self._current_status IS None:
            RETURN  # No-op, silently ignore

        self._current_status.emails_skipped += count
    RELEASE lock
```

## Implementation Location

**File**: `/root/repo/services/processing_status_manager.py`
**Insert After**: Line 315 (after `increment_deleted` method)

## Test Cases

Tests should be added to validate:

1. **Default increment (count=1)**
   - Start session, call `increment_categorized()`, verify count is 1
   - Start session, call `increment_skipped()`, verify count is 1

2. **Batch increment (count > 1)**
   - Start session, call `increment_categorized(5)`, verify count is 5
   - Start session, call `increment_skipped(10)`, verify count is 10

3. **Cumulative increments**
   - Start session, call `increment_categorized()` 3 times, verify count is 3
   - Start session, call `increment_skipped()` 3 times, verify count is 3

4. **Mixed batch and single increments**
   - Start session, call `increment_categorized(5)`, then `increment_categorized()`, verify count is 6

## Context Budget

| Category | Count | Estimated Lines |
|----------|-------|-----------------|
| Files to read | 1 | ~50 lines (existing increment methods pattern) |
| New code to write | ~30 lines | 2 methods with docstrings |
| Test code to write | ~60 lines | 4-6 test cases |
| **Estimated context usage** | **~15%** | Well under 60% threshold |

## Dependencies

- **Prerequisite**: Sub-task 1.1 (Core Fields) - COMPLETED
- **Fields exist**: `emails_categorized` and `emails_skipped` in AccountStatus dataclass
- **Lock mechanism**: Uses existing `self._lock` (threading.Lock)

## Acceptance Criteria

1. Both methods exist and follow exact pattern of `increment_reviewed`
2. Thread-safe using `self._lock` context manager
3. No-op behavior when `self._current_status` is None
4. Default count parameter is 1
5. Docstrings follow existing style exactly
6. All existing tests continue to pass
7. New tests for increment behavior pass

## Out of Scope (Handled by Later Sub-tasks)

- No-session edge case tests (sub-task 1.4)
- Thread safety stress tests (sub-task 1.6)
- API response verification (sub-task 1.7)
- Database persistence verification (sub-task 1.5)
