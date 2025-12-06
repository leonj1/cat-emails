# DRAFT Specification: Data Integrity and Persistence

## Sub-task 1.5: Data Integrity and Persistence for emails_categorized and emails_skipped

### Status: DRAFT
### Parent Task: Enhance Audit Records for Email Processing
### Created: 2025-12-06

---

## Overview

This specification defines the requirements for verifying data persistence and creating a Python migration for the `emails_categorized` and `emails_skipped` audit fields.

### What Already Exists

| Component | Status | Location |
|-----------|--------|----------|
| ProcessingRun model columns | EXISTS | `models/database.py:224-225` |
| AccountStatus dataclass fields | EXISTS | `services/processing_status_manager.py:72-73` |
| Increment methods | EXISTS | `services/processing_status_manager.py:317-351` |
| Flyway SQL migration (MySQL) | EXISTS | `sql/V3__add_categorized_skipped_columns.sql` |
| Python migration (SQLite) | PENDING | `migrations/006_add_categorized_skipped_columns.py` |
| Persistence verification tests | PENDING | New test file required |

### What This Task Delivers

1. **Python Migration 006**: For SQLite databases (following pattern from migration 005)
2. **Persistence Verification Tests**: Ensure counts survive database round-trips

---

## Interfaces Needed

### IMigration Interface (Conceptual)

```python
class IMigration(Protocol):
    """Migration interface following existing pattern from migrations/005"""

    def upgrade(db_path: Optional[str] = None, engine=None) -> None:
        """Apply migration - add columns if they don't exist"""
        ...

    def downgrade(db_path: Optional[str] = None, engine=None) -> None:
        """Rollback migration - remove columns"""
        ...
```

### IDataPersistence Interface (Test Verification)

```python
class IDataPersistence(Protocol):
    """Verification interface for persistence tests"""

    def save_processing_run(run: ProcessingRun) -> int:
        """Save a processing run and return ID"""
        ...

    def load_processing_run(run_id: int) -> ProcessingRun:
        """Load a processing run by ID"""
        ...
```

---

## Data Models

### ProcessingRun (Already Exists)

```python
# models/database.py - Lines 224-225
emails_categorized = Column(Integer, default=0, nullable=False)
emails_skipped = Column(Integer, default=0, nullable=False)
```

No changes needed to the model.

---

## Logic Flow

### Migration 006 Upgrade Flow

```text
START upgrade()
    |
    v
GET database engine (db_path or engine parameter)
    |
    v
CHECK if processing_runs table exists
    |-- No --> RAISE MigrationError
    |-- Yes --> Continue
    v
CHECK if emails_categorized column exists
    |-- Yes --> Log "already exists", skip
    |-- No --> ADD COLUMN emails_categorized INTEGER NOT NULL DEFAULT 0
    v
CHECK if emails_skipped column exists
    |-- Yes --> Log "already exists", skip
    |-- No --> ADD COLUMN emails_skipped INTEGER NOT NULL DEFAULT 0
    v
BACKFILL existing records with NULL values to 0 (defensive)
    |
    v
COMMIT transaction
    |
    v
END
```

### Migration 006 Downgrade Flow

```text
START downgrade()
    |
    v
GET database engine
    |
    v
CHECK if processing_runs table exists
    |-- No --> Log "nothing to rollback", return
    |-- Yes --> Continue
    v
CREATE backup table WITHOUT emails_categorized/emails_skipped
    |
    v
COPY data from processing_runs to backup
    |
    v
DROP processing_runs table
    |
    v
RENAME backup to processing_runs
    |
    v
RECREATE indexes
    |
    v
COMMIT
    |
    v
END
```

### Persistence Test Flow

```text
START test_persistence()
    |
    v
CREATE in-memory SQLite database
    |
    v
RUN migration 006 upgrade
    |
    v
CREATE ProcessingRun with emails_categorized=42, emails_skipped=17
    |
    v
SAVE to database
    |
    v
CLOSE and REOPEN session (simulate restart)
    |
    v
LOAD ProcessingRun by ID
    |
    v
ASSERT emails_categorized == 42
ASSERT emails_skipped == 17
    |
    v
END
```

---

## Test Scenarios

### Scenario 1: Migration Adds Columns

```gherkin
Feature: Migration 006 adds emails_categorized and emails_skipped columns

  Scenario: Migration creates columns when they don't exist
    Given a SQLite database with processing_runs table
    And the table does not have emails_categorized column
    And the table does not have emails_skipped column
    When migration 006 upgrade is executed
    Then the emails_categorized column exists
    And the emails_skipped column exists
    And both columns have default value 0
```

### Scenario 2: Migration Is Idempotent

```gherkin
  Scenario: Migration is idempotent (safe to run multiple times)
    Given a SQLite database with processing_runs table
    And migration 006 has already been applied
    When migration 006 upgrade is executed again
    Then no error occurs
    And the columns still exist with correct properties
```

### Scenario 3: Counts Persist to Database

```gherkin
  Scenario: emails_categorized persists to database
    Given a ProcessingRun record with emails_categorized = 42
    When the record is saved to the database
    And the database session is closed
    And a new session loads the record by ID
    Then emails_categorized equals 42

  Scenario: emails_skipped persists to database
    Given a ProcessingRun record with emails_skipped = 17
    When the record is saved to the database
    And the database session is closed
    And a new session loads the record by ID
    Then emails_skipped equals 17
```

### Scenario 4: Accumulated Counts Persist Correctly

```gherkin
  Scenario: Multiple increments persist as cumulative total
    Given a ProcessingStatusManager with an active session
    When increment_categorized(10) is called
    And increment_categorized(5) is called
    And increment_skipped(3) is called
    And the session completes
    And the archived run is saved to database
    Then the database record shows emails_categorized = 15
    And the database record shows emails_skipped = 3
```

### Scenario 5: Migration Downgrade Removes Columns

```gherkin
  Scenario: Migration downgrade removes the new columns
    Given a SQLite database with emails_categorized and emails_skipped columns
    When migration 006 downgrade is executed
    Then the emails_categorized column no longer exists
    And the emails_skipped column no longer exists
    And all other columns remain intact
```

---

## Files to Create

### 1. migrations/006_add_categorized_skipped_columns.py

Python migration file following the exact pattern from `migrations/005_add_audit_count_columns.py`:

- `upgrade()` function: Adds `emails_categorized` and `emails_skipped` columns
- `downgrade()` function: Removes the columns using SQLite table rebuild
- Idempotent: Safe to run multiple times
- Supports both `db_path` and `engine` parameters

### 2. tests/test_data_integrity_persistence.py

Test file containing:

- Test class for migration upgrade
- Test class for migration idempotency
- Test class for persistence verification
- Test class for migration downgrade

---

## Context Budget

| Category | Count | Lines (Est.) |
|----------|-------|--------------|
| Files to read | 3 | ~400 lines |
| - migrations/005_add_audit_count_columns.py | 1 | ~284 lines |
| - models/database.py | 1 | ~319 lines (already read) |
| - services/processing_status_manager.py | 1 | ~474 lines (already read) |
| New code to write | 1 | ~200 lines |
| - migrations/006_add_categorized_skipped_columns.py | 1 | ~200 lines |
| Test code to write | 1 | ~150 lines |
| - tests/test_data_integrity_persistence.py | 1 | ~150 lines |
| **Total new code** | 2 files | ~350 lines |
| **Estimated context usage** | | ~25% |

### Scope Assessment: APPROVED

- Context usage: ~25% (well under 60% threshold)
- Single migration file (follows existing pattern)
- Single test file (focused scope)
- No API changes required
- No model changes required

---

## Implementation Notes

### Migration Pattern to Follow

The migration should exactly follow the pattern from `migrations/005_add_audit_count_columns.py`:

1. Use `column_exists()` helper to check before adding
2. Use raw SQL `ALTER TABLE ... ADD COLUMN` for SQLite compatibility
3. Include defensive backfill for NULL values
4. Implement proper downgrade using SQLite table rebuild pattern
5. Include CLI main() for standalone execution

### Test Database Setup

Tests should use in-memory SQLite database with:

```python
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
```

### Key Assertions

1. Column existence verification using SQLAlchemy inspector
2. Default value verification (should be 0)
3. Round-trip persistence (save -> close -> load -> verify)
4. Accumulated increment persistence (multiple increments -> single persisted value)

---

## Dependencies

- SQLAlchemy (existing)
- models/database.py (ProcessingRun model - existing)
- migrations/005_add_audit_count_columns.py (pattern reference - existing)

---

## Success Criteria

1. [ ] Migration 006 adds columns when missing
2. [ ] Migration 006 is idempotent (no error on re-run)
3. [ ] Migration 006 downgrade removes columns cleanly
4. [ ] ProcessingRun with emails_categorized persists and loads correctly
5. [ ] ProcessingRun with emails_skipped persists and loads correctly
6. [ ] Accumulated counts from multiple increments persist as total
7. [ ] All tests pass (`make test` succeeds)
