# DRAFT: Core Fields - Database Model and Basic Field Existence

## Overview

Add the foundational `emails_categorized` and `emails_skipped` fields to the database model and dataclass. This is the first of 7 sub-tasks for the "Enhance Audit Records" feature.

## Scope

This sub-task focuses ONLY on:
1. Adding columns to the ProcessingRun database model
2. Adding fields to the AccountStatus dataclass
3. Creating the Flyway SQL migration
4. Verifying field initialization defaults

**Out of Scope** (handled in later sub-tasks):
- Increment methods
- Edge case handling
- Thread safety
- API response enhancement

---

## Interfaces Needed

### 1. IProcessingRun (Extended Fields)

```python
from abc import ABC, abstractmethod

class IProcessingRun(ABC):
    """Interface for processing run audit record"""

    @property
    @abstractmethod
    def emails_categorized(self) -> int:
        """Count of emails successfully assigned a category"""
        pass

    @property
    @abstractmethod
    def emails_skipped(self) -> int:
        """Count of emails skipped during processing"""
        pass
```

### 2. IAccountStatus (Extended Fields)

```python
class IAccountStatus(ABC):
    """Interface for in-memory account processing status"""

    @property
    @abstractmethod
    def emails_categorized(self) -> int:
        """Current count of categorized emails in this session"""
        pass

    @property
    @abstractmethod
    def emails_skipped(self) -> int:
        """Current count of skipped emails in this session"""
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

### 1. Field Initialization

When a new ProcessingRun is created:
```
1. SQLAlchemy applies default=0 for emails_categorized
2. SQLAlchemy applies default=0 for emails_skipped
3. Record is saved to database with 0 values
```

When a new AccountStatus is created:
```
1. Dataclass applies default=0 for emails_categorized
2. Dataclass applies default=0 for emails_skipped
3. Status is stored in memory with 0 values
```

### 2. to_dict Serialization

The existing `to_dict()` pattern should include new fields:
```python
def to_dict(self) -> Dict[str, Any]:
    return {
        # ... existing fields ...
        'emails_reviewed': self.emails_reviewed,
        'emails_tagged': self.emails_tagged,
        'emails_deleted': self.emails_deleted,
        'emails_categorized': self.emails_categorized,  # NEW
        'emails_skipped': self.emails_skipped,          # NEW
    }
```

---

## Database Migration

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

---

## Files to Modify

| File | Changes | Lines to Add |
|------|---------|--------------|
| `models/database.py` | Add 2 columns to ProcessingRun | ~4 lines |
| `services/processing_status_manager.py` | Add 2 fields to AccountStatus | ~4 lines |
| `sql/V3__add_categorized_skipped_columns.sql` | New migration file | ~8 lines |

---

## Context Budget

| Metric | Estimate |
|--------|----------|
| Files to read | 2 files (~300 lines) |
| New code to write | ~16 lines |
| Test code to write | ~50 lines |
| Estimated context usage | **15%** |

---

## BDD Scenarios (4 scenarios - within limit)

### Scenario 1: ProcessingRun model has emails_categorized column
```gherkin
Given the ProcessingRun database model
When a new ProcessingRun record is created
Then it should have an emails_categorized field
And the field should be an integer with default value 0
```

### Scenario 2: ProcessingRun model has emails_skipped column
```gherkin
Given the ProcessingRun database model
When a new ProcessingRun record is created
Then it should have an emails_skipped field
And the field should be an integer with default value 0
```

### Scenario 3: AccountStatus dataclass has emails_categorized field
```gherkin
Given the AccountStatus dataclass
When a new AccountStatus instance is created
Then it should have an emails_categorized attribute
And the attribute should default to 0
```

### Scenario 4: AccountStatus dataclass has emails_skipped field
```gherkin
Given the AccountStatus dataclass
When a new AccountStatus instance is created
Then it should have an emails_skipped attribute
And the attribute should default to 0
```

---

## Acceptance Criteria

1. ProcessingRun model has `emails_categorized` Integer column with default=0
2. ProcessingRun model has `emails_skipped` Integer column with default=0
3. AccountStatus dataclass has `emails_categorized` field with default=0
4. AccountStatus dataclass has `emails_skipped` field with default=0
5. Flyway migration V3 exists and adds both columns
6. All existing tests continue to pass

---

## Notes

- This spec follows the existing pattern established for `emails_reviewed`, `emails_tagged`, and `emails_deleted`
- Only 4 BDD scenarios to keep within the scope-manager's limit
- Increment methods and edge cases are deferred to sub-tasks 1.2-1.6
- API response enhancement is deferred to sub-task 1.7
