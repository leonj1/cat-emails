# Gap Analysis: Core Audit Fields for Categorized and Skipped Emails

## Overview

This analysis identifies reuse opportunities and implementation requirements for adding `emails_categorized` and `emails_skipped` fields to the audit records system.

## Feature Requirements

Based on `tests/bdd/core_fields_audit_records.feature`:

1. ProcessingRun model must include `emails_categorized` column
2. ProcessingRun model must include `emails_skipped` column
3. AccountStatus dataclass must include `emails_categorized` field
4. AccountStatus dataclass must include `emails_skipped` field

## Existing Code Analysis

### 1. ProcessingRun Model (models/database.py)

**Location**: `/root/repo/models/database.py`, lines 204-230

**Existing Pattern**:
```python
class ProcessingRun(Base):
    # ... existing columns ...
    emails_reviewed = Column(Integer, default=0, nullable=False)
    emails_tagged = Column(Integer, default=0, nullable=False)
    emails_deleted = Column(Integer, default=0, nullable=False)
```

**Reuse Opportunity**: Follow identical pattern for new columns:
```python
emails_categorized = Column(Integer, default=0, nullable=False)
emails_skipped = Column(Integer, default=0, nullable=False)
```

### 2. AccountStatus Dataclass (services/processing_status_manager.py)

**Location**: `/root/repo/services/processing_status_manager.py`, lines 59-83

**Existing Pattern**:
```python
@dataclass
class AccountStatus:
    email_address: str
    state: ProcessingState
    current_step: str
    # ... other fields ...
    emails_reviewed: int = 0
    emails_tagged: int = 0
    emails_deleted: int = 0
```

**Reuse Opportunity**: Follow identical pattern for new fields:
```python
emails_categorized: int = 0
emails_skipped: int = 0
```

### 3. Database Migration (sql/)

**Existing Pattern**: Flyway migrations in `/root/repo/sql/`
- V1__initial_schema.sql - Contains processing_runs table with audit columns
- V2__clear_failed_flyway_records.sql - Example migration

**New Migration Required**: `V3__add_categorized_skipped_columns.sql`
```sql
ALTER TABLE processing_runs ADD COLUMN emails_categorized INT DEFAULT 0 NOT NULL;
ALTER TABLE processing_runs ADD COLUMN emails_skipped INT DEFAULT 0 NOT NULL;
```

### 4. Test Patterns

**Model Tests**: `/root/repo/tests/test_processing_run_audit_columns.py`
- Tests for column existence
- Tests for Integer type
- Tests for default value of 0
- Tests for nullable=False
- Tests for storing/retrieving custom values

**Service Tests**: `/root/repo/tests/test_processing_status_manager_audit_counts.py`
- Tests for dataclass field existence
- Tests for initial value of 0
- Tests for increment methods
- Tests for preservation on completion
- Tests for no-op behavior without active session

## Implementation Requirements

### Files to Modify

| File | Change |
|------|--------|
| `models/database.py` | Add 2 columns to ProcessingRun class |
| `services/processing_status_manager.py` | Add 2 fields to AccountStatus dataclass |

### Files to Create

| File | Purpose |
|------|---------|
| `sql/V3__add_categorized_skipped_columns.sql` | New Flyway migration |
| `tests/test_core_fields_categorized_skipped.py` | BDD-derived tests for new fields |

## Refactoring Assessment

**Refactoring Needed**: NO

The existing code follows clean patterns that can be extended without modification:
- ProcessingRun model already has similar audit columns
- AccountStatus dataclass already has similar audit fields
- Test patterns are well-established and can be replicated

## Reuse Summary

| Component | Reuse Type | Notes |
|-----------|------------|-------|
| Column definition pattern | Direct reuse | Copy emails_reviewed pattern |
| Dataclass field pattern | Direct reuse | Copy emails_reviewed pattern |
| Migration pattern | Template reuse | Follow V2 structure |
| Test patterns | Template reuse | Follow test_processing_run_audit_columns.py |

## GO Signal

**STATUS: GO**

- No refactoring required
- Clear patterns exist for all components
- Implementation is straightforward extension of existing patterns
- Test patterns are well-established

## Implementation Order

1. Create database migration (V3__add_categorized_skipped_columns.sql)
2. Add columns to ProcessingRun model
3. Add fields to AccountStatus dataclass
4. Write tests based on Gherkin scenarios
5. Verify all scenarios pass
