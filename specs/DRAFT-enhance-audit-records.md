# DRAFT: Enhance Audit Records for Email Processing

## Overview

Add two new tracking fields to the email processing audit system: `emails_categorized` and `emails_skipped`. These fields complement the existing audit tracking to provide complete visibility into email processing outcomes.

## Current State

The `ProcessingRun` model already tracks:
- `email_address` - Account being processed
- `start_time` / `end_time` - Processing duration
- `current_step` - Current processing phase
- `error_message` - Any error that occurred
- `emails_found` - Total emails scanned
- `emails_reviewed` - Emails that went through review
- `emails_tagged` - Emails that received labels
- `emails_deleted` - Emails that were deleted

## Missing Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `emails_categorized` | Integer | 0 | Count of emails successfully assigned a category by AI |
| `emails_skipped` | Integer | 0 | Count of emails skipped (already processed, filtered out, etc.) |

---

## Interfaces Needed

### 1. IEmailCountTracker (Extension)

```python
from abc import ABC, abstractmethod

class IEmailCountTracker(ABC):
    """Interface for tracking email processing counts"""

    @abstractmethod
    def increment_categorized(self, count: int = 1) -> None:
        """Increment the count of categorized emails"""
        pass

    @abstractmethod
    def increment_skipped(self, count: int = 1) -> None:
        """Increment the count of skipped emails"""
        pass
```

### 2. IAuditRecordRepository (Extended Methods)

```python
class IAuditRecordRepository(ABC):
    """Repository interface for audit record persistence"""

    @abstractmethod
    def update_categorized_count(self, run_id: int, count: int) -> None:
        """Update the categorized email count for a processing run"""
        pass

    @abstractmethod
    def update_skipped_count(self, run_id: int, count: int) -> None:
        """Update the skipped email count for a processing run"""
        pass
```

---

## Data Models

### ProcessingRun Model (Extension)

```python
# models/database.py - Add to ProcessingRun class

# Existing fields...
emails_reviewed = Column(Integer, default=0, nullable=False)
emails_tagged = Column(Integer, default=0, nullable=False)
emails_deleted = Column(Integer, default=0, nullable=False)

# NEW FIELDS
emails_categorized = Column(Integer, default=0, nullable=False)
emails_skipped = Column(Integer, default=0, nullable=False)
```

### AccountStatus Dataclass (Extension)

```python
# services/processing_status_manager.py - Extend AccountStatus

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
    emails_reviewed: int = 0
    emails_tagged: int = 0
    emails_deleted: int = 0
    # NEW FIELDS
    emails_categorized: int = 0
    emails_skipped: int = 0
```

---

## Logic Flow

### 1. Increment Methods in ProcessingStatusManager

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
    with self._lock:
        if not self._current_status:
            return
        self._current_status.emails_categorized += count

def increment_skipped(self, count: int = 1) -> None:
    """
    Increment the count of emails skipped during processing.

    Args:
        count: Number of emails to add to the skipped count (default: 1)

    Note:
        This is a no-op if no processing session is active.
        Thread-safe operation using internal lock.
    """
    with self._lock:
        if not self._current_status:
            return
        self._current_status.emails_skipped += count
```

### 2. Archive Run Record Update

```python
# In complete_processing() method, add to archived_run dict:
archived_run = {
    # ... existing fields ...
    'emails_reviewed': self._current_status.emails_reviewed,
    'emails_tagged': self._current_status.emails_tagged,
    'emails_deleted': self._current_status.emails_deleted,
    # NEW FIELDS
    'emails_categorized': self._current_status.emails_categorized,
    'emails_skipped': self._current_status.emails_skipped,
}
```

### 3. API Response Enhancement

The `/api/v1/processing/status` and `/api/v1/processing/history` endpoints should include the new fields in their responses. No interface changes needed - the fields are automatically included via `to_dict()`.

---

## Database Migrations

### Flyway SQL Migration

**File:** `sql/V3__add_categorized_skipped_columns.sql`

```sql
-- Add emails_categorized and emails_skipped columns to processing_runs table
-- These columns track additional audit metrics for email processing

ALTER TABLE processing_runs
ADD COLUMN emails_categorized INTEGER NOT NULL DEFAULT 0;

ALTER TABLE processing_runs
ADD COLUMN emails_skipped INTEGER NOT NULL DEFAULT 0;
```

### Python Migration (Consistency)

**File:** `migrations/006_add_categorized_skipped_columns.py`

```python
"""
Migration: Add emails_categorized and emails_skipped columns
Version: 006
Date: 2025-12-06
"""

def upgrade(connection):
    """Add new audit columns to processing_runs table"""
    cursor = connection.cursor()

    # Check if columns already exist (idempotent)
    cursor.execute("PRAGMA table_info(processing_runs)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    if 'emails_categorized' not in existing_columns:
        cursor.execute(
            "ALTER TABLE processing_runs "
            "ADD COLUMN emails_categorized INTEGER NOT NULL DEFAULT 0"
        )

    if 'emails_skipped' not in existing_columns:
        cursor.execute(
            "ALTER TABLE processing_runs "
            "ADD COLUMN emails_skipped INTEGER NOT NULL DEFAULT 0"
        )

    connection.commit()

def downgrade(connection):
    """SQLite does not support DROP COLUMN in older versions"""
    # No-op for SQLite < 3.35
    pass
```

---

## Files to Modify

| File | Changes | Lines to Add |
|------|---------|--------------|
| `models/database.py` | Add 2 columns to ProcessingRun | ~4 lines |
| `services/processing_status_manager.py` | Add 2 fields to AccountStatus, 2 increment methods, update archived_run | ~30 lines |
| `sql/V3__add_categorized_skipped_columns.sql` | New migration file | ~8 lines |
| `migrations/006_add_categorized_skipped_columns.py` | New migration file | ~30 lines |

---

## Context Budget

| Metric | Estimate |
|--------|----------|
| Files to read | 2 files (~350 lines) |
| New code to write | ~50 lines |
| Test code to write | ~80 lines |
| Estimated context usage | **25%** |

---

## Test Cases

### Unit Tests

1. **test_increment_categorized_updates_count** - Verify increment works
2. **test_increment_categorized_no_active_session** - Verify no-op when no session
3. **test_increment_skipped_updates_count** - Verify increment works
4. **test_increment_skipped_no_active_session** - Verify no-op when no session
5. **test_complete_processing_includes_new_fields** - Verify archived run has new fields
6. **test_account_status_to_dict_includes_new_fields** - Verify serialization

### Integration Tests

1. **test_api_status_includes_new_fields** - Verify API response format
2. **test_migration_adds_columns** - Verify database migration
3. **test_processing_run_persists_new_fields** - Verify database persistence

---

## Acceptance Criteria

1. ProcessingRun model has `emails_categorized` and `emails_skipped` columns
2. AccountStatus dataclass has corresponding tracking fields
3. ProcessingStatusManager has `increment_categorized()` and `increment_skipped()` methods
4. Archived runs include the new fields
5. API responses include the new fields
6. Database migration is idempotent (can be run multiple times safely)
7. All existing tests continue to pass
8. New tests cover the added functionality

---

## Notes

- This spec follows the existing pattern established for `emails_reviewed`, `emails_tagged`, and `emails_deleted`
- Thread-safety is maintained via the existing `_lock` mechanism
- The archived run structure already handles dictionary serialization, so no additional work needed for API responses
- SQLite's lack of DROP COLUMN support (in older versions) means the downgrade migration is a no-op
