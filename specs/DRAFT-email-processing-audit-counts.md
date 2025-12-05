# DRAFT Specification: Email Processing Audit Counts

## Overview

Extend the `ProcessingRun` audit entry to include detailed email processing metrics:
- **emails_reviewed**: Count of emails examined during the processing run
- **emails_tagged**: Count of emails that received Gmail labels
- **emails_deleted**: Count of emails moved to trash

## Current State

The `ProcessingRun` model currently tracks:
- `id`, `email_address`, `start_time`, `end_time`
- `state`, `current_step`
- `emails_found`, `emails_processed`
- `error_message`, `created_at`, `updated_at`

**Gap**: No granular tracking of reviewed/tagged/deleted counts per processing run.

## Required Changes

### 1. Database Model Changes

**File**: `/root/repo/models/database.py`

Add three new columns to `ProcessingRun` class:

```python
class ProcessingRun(Base):
    """Historical tracking of email processing sessions"""
    __tablename__ = 'processing_runs'

    # ... existing columns ...

    # NEW: Detailed processing metrics
    emails_reviewed = Column(Integer, default=0)   # Emails examined
    emails_tagged = Column(Integer, default=0)     # Emails that received labels
    emails_deleted = Column(Integer, default=0)    # Emails moved to trash
```

### 2. Database Migration

**File**: `/root/repo/sql/V003__add_processing_run_audit_counts.sql`

```sql
-- Add audit count columns to processing_runs table
ALTER TABLE processing_runs
    ADD COLUMN emails_reviewed INT DEFAULT 0,
    ADD COLUMN emails_tagged INT DEFAULT 0,
    ADD COLUMN emails_deleted INT DEFAULT 0;

-- Backfill: For historical runs, assume emails_processed were reviewed
-- This is a conservative estimate; new runs will track these separately
UPDATE processing_runs
SET emails_reviewed = emails_processed
WHERE emails_reviewed = 0 AND emails_processed > 0;
```

### 3. Processing Status Manager Updates

**File**: `/root/repo/services/processing_status_manager.py`

#### 3.1 Update AccountStatus Dataclass

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
    # NEW: Audit counts
    emails_reviewed: int = 0
    emails_tagged: int = 0
    emails_deleted: int = 0
```

#### 3.2 Add Increment Methods to ProcessingStatusManager

```python
def increment_reviewed(self, count: int = 1) -> None:
    """Increment the count of emails reviewed."""
    with self._lock:
        if self._current_status:
            self._current_status.emails_reviewed += count

def increment_tagged(self, count: int = 1) -> None:
    """Increment the count of emails tagged."""
    with self._lock:
        if self._current_status:
            self._current_status.emails_tagged += count

def increment_deleted(self, count: int = 1) -> None:
    """Increment the count of emails deleted."""
    with self._lock:
        if self._current_status:
            self._current_status.emails_deleted += count
```

#### 3.3 Update complete_processing() Archived Run Record

```python
archived_run = {
    'email_address': self._current_status.email_address,
    'start_time': self._current_status.start_time.isoformat(),
    'end_time': self._current_status.last_updated.isoformat(),
    'duration_seconds': duration_seconds,
    'final_state': self._current_status.state.name,
    'final_step': self._current_status.current_step,
    'error_message': self._current_status.error_message,
    'final_progress': self._current_status.progress,
    # NEW: Include audit counts
    'emails_reviewed': self._current_status.emails_reviewed,
    'emails_tagged': self._current_status.emails_tagged,
    'emails_deleted': self._current_status.emails_deleted,
}
```

### 4. Repository Layer Updates

**File**: `/root/repo/repositories/mysql_repository.py`

#### 4.1 Update complete_processing_run Method

```python
def complete_processing_run(
    self,
    run_id: str,
    metrics: Dict[str, int],
    success: bool = True,
    error_message: Optional[str] = None
) -> None:
    """Mark processing run as complete with final metrics"""
    run = self.get_processing_run(run_id)
    if run:
        session = self._get_session()
        try:
            run.end_time = datetime.utcnow()
            run.emails_processed = metrics.get('processed', 0)
            # NEW: Audit counts from metrics
            run.emails_reviewed = metrics.get('reviewed', 0)
            run.emails_tagged = metrics.get('tagged', 0)
            run.emails_deleted = metrics.get('deleted', 0)
            run.state = 'completed' if success else 'error'
            run.error_message = error_message
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error completing processing run: {str(e)}")
            raise
```

### 5. Email Summary Service Updates

**File**: `/root/repo/services/email_summary_service.py`

#### 5.1 Extend run_metrics Dictionary

```python
# Track run metrics
self.run_metrics = {
    'fetched': 0,
    'processed': 0,
    'deleted': 0,
    'archived': 0,
    'error': 0,
    # NEW: Audit counts
    'reviewed': 0,
    'tagged': 0,
}
```

#### 5.2 Update track_email Method

When tracking an email, increment the appropriate counters:

```python
def track_email(self, ..., was_tagged: bool = False) -> None:
    # ... existing code ...

    # Update run metrics
    self.run_metrics['processed'] += 1
    self.run_metrics['reviewed'] += 1  # Every processed email was reviewed

    if was_tagged:
        self.run_metrics['tagged'] += 1

    if action == "deleted":
        self.run_metrics['deleted'] += 1
```

### 6. Database Service Updates

**File**: `/root/repo/services/database_service.py`

#### 6.1 Update get_processing_runs Response

```python
def get_processing_runs(self, limit: int = 100) -> List[Dict]:
    """Get recent processing runs"""
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
                # NEW: Audit counts
                'emails_reviewed': run.emails_reviewed,
                'emails_tagged': run.emails_tagged,
                'emails_deleted': run.emails_deleted,
                'success': run.state == 'completed' and not run.error_message,
                'error_message': run.error_message
            } for run in runs
        ]
```

## Interfaces Needed

### IAuditCountTracker Interface

```python
from abc import ABC, abstractmethod

class IAuditCountTracker(ABC):
    """Interface for tracking email processing audit counts"""

    @abstractmethod
    def increment_reviewed(self, count: int = 1) -> None:
        """Increment emails reviewed count"""
        pass

    @abstractmethod
    def increment_tagged(self, count: int = 1) -> None:
        """Increment emails tagged count"""
        pass

    @abstractmethod
    def increment_deleted(self, count: int = 1) -> None:
        """Increment emails deleted count"""
        pass

    @abstractmethod
    def get_audit_counts(self) -> Dict[str, int]:
        """Get current audit counts"""
        pass
```

## Data Models

### ProcessingRunAuditCounts (Value Object)

```python
@dataclass(frozen=True)
class ProcessingRunAuditCounts:
    """Immutable value object for processing run audit counts"""
    emails_reviewed: int = 0
    emails_tagged: int = 0
    emails_deleted: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            'emails_reviewed': self.emails_reviewed,
            'emails_tagged': self.emails_tagged,
            'emails_deleted': self.emails_deleted,
        }
```

## Logic Flow

### Email Processing Flow with Audit Tracking

```text
1. START Processing Run
   - Initialize audit counts to 0
   - Create ProcessingRun record in database

2. FOR EACH email in mailbox:
   a. Fetch email content
   b. INCREMENT emails_reviewed
   c. Categorize email (LLM or rule-based)
   d. IF category requires labeling:
      - Apply Gmail label
      - INCREMENT emails_tagged
   e. IF category requires deletion:
      - Move to trash
      - INCREMENT emails_deleted
   f. Track email in summary service

3. COMPLETE Processing Run
   - Persist final audit counts to ProcessingRun record
   - Archive run to history with all counts
```

### Pseudocode for Email Processor

```python
def process_emails(email_list):
    status_manager.start_processing(email_address)

    for email in email_list:
        # Every email we look at counts as reviewed
        status_manager.increment_reviewed()

        category = categorize(email)

        if should_label(category):
            apply_label(email, category)
            status_manager.increment_tagged()

        if should_delete(category):
            delete_email(email)
            status_manager.increment_deleted()

    # Complete and persist
    status_manager.complete_processing()
```

## API Response Changes

The `/api/processing/runs` endpoint should return:

```json
{
  "runs": [
    {
      "run_id": "run-123",
      "email_address": "user@example.com",
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
| Files to read | 6 | ~1200 lines |
| New code to write | ~80 lines | - |
| Test code to write | ~120 lines | - |
| Migration SQL | ~10 lines | - |

**Estimated context usage**: ~35% (Well under 60% threshold)

## Acceptance Criteria

1. ProcessingRun records include emails_reviewed, emails_tagged, emails_deleted counts
2. Counts are persisted to database when processing completes
3. Existing ProcessingRun records show 0 for new fields (or backfilled from emails_processed)
4. API responses include the new audit count fields
5. Thread-safe increment operations in ProcessingStatusManager
6. Backward compatible - existing code continues to work without modification

## Testing Strategy

### Unit Tests
- Test AccountStatus includes new fields with defaults
- Test increment methods update counts correctly
- Test to_dict() includes new fields
- Test complete_processing() archives new fields

### Integration Tests
- Test full processing flow persists audit counts to database
- Test API returns new fields in response
- Test migration applies cleanly to existing database

### Edge Cases
- Processing run with 0 emails (all counts should be 0)
- Partial processing (reviewed > processed when errors occur)
- Concurrent access to increment methods
