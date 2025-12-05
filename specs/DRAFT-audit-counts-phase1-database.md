# DRAFT Spec: Audit Counts Phase 1 - Database Schema

## Summary
Add three new integer columns to the ProcessingRun model to track email processing audit counts at the database layer only.

## Scope
- **In Scope**: Database model changes, Flyway migration
- **Out of Scope**: Service layer, API layer, business logic, increment methods

---

## Interfaces Needed

### IProcessingRunRepository (extend existing)
No new interface methods required for Phase 1. Existing repository pattern handles column additions automatically via SQLAlchemy ORM.

---

## Data Models

### ProcessingRun Model (modification)
```python
class ProcessingRun(Base):
    __tablename__ = "processing_runs"

    # Existing fields...
    id: Mapped[int]
    email_address: Mapped[str]
    start_time: Mapped[datetime]
    end_time: Mapped[Optional[datetime]]
    state: Mapped[str]
    current_step: Mapped[Optional[str]]
    emails_found: Mapped[int]
    emails_processed: Mapped[int]
    error_message: Mapped[Optional[str]]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # NEW FIELDS (Phase 1)
    emails_reviewed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_tagged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_deleted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
```

### Column Definitions
| Column | Type | Default | Nullable | Description |
|--------|------|---------|----------|-------------|
| emails_reviewed | INTEGER | 0 | NO | Count of emails examined during processing |
| emails_tagged | INTEGER | 0 | NO | Count of emails that received Gmail labels |
| emails_deleted | INTEGER | 0 | NO | Count of emails permanently deleted |

---

## Migration File

### V003__add_audit_count_columns.sql
```sql
-- Add audit count columns to processing_runs table
ALTER TABLE processing_runs ADD COLUMN emails_reviewed INTEGER NOT NULL DEFAULT 0;
ALTER TABLE processing_runs ADD COLUMN emails_tagged INTEGER NOT NULL DEFAULT 0;
ALTER TABLE processing_runs ADD COLUMN emails_deleted INTEGER NOT NULL DEFAULT 0;
```

---

## Logic Flow

### Phase 1 Implementation Steps
```
1. Open models/database.py
2. Locate ProcessingRun class
3. Add three new column definitions:
   - emails_reviewed = Column(Integer, default=0, nullable=False)
   - emails_tagged = Column(Integer, default=0, nullable=False)
   - emails_deleted = Column(Integer, default=0, nullable=False)
4. Create sql/V003__add_audit_count_columns.sql
5. Run migration to verify schema changes
```

### Verification
```
1. Run: make test (ensure model tests pass)
2. Verify migration applies cleanly
3. Verify columns exist in database schema
4. Verify default values are 0 for new records
```

---

## Context Budget

| Category | Count | Estimate |
|----------|-------|----------|
| Files to read | 2 | ~100 lines (database.py ProcessingRun section, existing migrations) |
| Files to modify | 1 | models/database.py (~15 lines added) |
| Files to create | 1 | sql/V003__add_audit_count_columns.sql (~5 lines) |
| Test code to write | 1 | ~30 lines (model column existence tests) |
| **Total new code** | - | ~50 lines |
| **Estimated context usage** | - | **15%** |

---

## Acceptance Criteria

1. ProcessingRun model has three new Integer columns
2. All columns have default value of 0
3. All columns are NOT NULL
4. Migration V003 exists and applies cleanly
5. Existing tests continue to pass
6. New model tests verify column existence and defaults

---

## Files Affected

| File | Action | Lines Changed |
|------|--------|---------------|
| `/root/repo/models/database.py` | MODIFY | +3 column definitions |
| `/root/repo/sql/V003__add_audit_count_columns.sql` | CREATE | +5 lines |
| `/root/repo/tests/test_models.py` | MODIFY | +30 lines (new tests) |

---

## Dependencies
- None (this is the foundation layer)

## Blocked By
- Nothing

## Blocks
- Phase 1.2: AccountStatus Tracking (requires these columns to exist)
- Phase 1.3: API Response Updates (requires these columns to exist)
