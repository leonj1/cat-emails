# Gap Analysis: Audit Counts Phase 1 - Database Schema

**Date**: 2025-12-05
**Feature**: Email Processing Audit Count Database Columns
**Source**: specs/DRAFT-audit-counts-phase1-database.md, tests/bdd/audit-counts-phase1-database.feature

---

## Executive Summary

Phase 1 adds three new integer columns (`emails_reviewed`, `emails_tagged`, `emails_deleted`) to the `ProcessingRun` model. This is a **greenfield addition** - no refactoring required.

---

## Current State Analysis

### ProcessingRun Model (`/root/repo/models/database.py:204-225`)

Current columns:
- `id` (Integer, primary key)
- `email_address` (Text, not null)
- `start_time` (DateTime, not null)
- `end_time` (DateTime, nullable)
- `state` (Text, not null)
- `current_step` (Text, nullable)
- `emails_found` (Integer, default=0)
- `emails_processed` (Integer, default=0)
- `error_message` (Text, nullable)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**Missing columns** (to be added):
- `emails_reviewed` (Integer, default=0, not null)
- `emails_tagged` (Integer, default=0, not null)
- `emails_deleted` (Integer, default=0, not null)

---

## Reuse Opportunities

### 1. Pattern: Column Definition Style
The existing columns use SQLAlchemy `Column()` with `Integer`, `default=0`:
```python
emails_found = Column(Integer, default=0)
emails_processed = Column(Integer, default=0)
```

**Recommendation**: Follow this exact pattern for new columns.

### 2. Pattern: Migration Directory Structure
Project uses `/root/repo/migrations/` for Python-based migrations (not Flyway SQL).

Existing migrations:
- `002_modify_processing_runs.py` - Previous ProcessingRun modifications

**Recommendation**: Create `005_add_audit_count_columns.py` following the same pattern.

### 3. Pattern: Test Structure
Integration tests for ProcessingRun exist in:
- `/root/repo/tests/test_integration_background_processing.py`

No dedicated `test_models.py` exists - tests are embedded in feature-specific files.

**Recommendation**: Create tests in a new file or extend existing integration tests.

---

## New Components Needed

| Component | Location | Lines Est. |
|-----------|----------|------------|
| 3 new columns | `/root/repo/models/database.py` | ~3 lines |
| Migration script | `/root/repo/migrations/005_add_audit_count_columns.py` | ~50 lines |
| Unit tests | `/root/repo/tests/test_processing_run_audit_columns.py` | ~80 lines |

---

## Refactoring Assessment

### Verdict: NO REFACTORING REQUIRED

Reasons:
1. **Additive change only** - New columns do not modify existing functionality
2. **No code conflicts** - ProcessingRun has no `emails_reviewed/tagged/deleted` references
3. **Clean patterns exist** - Existing column definitions provide clear template
4. **Migration structure clear** - Python-based migrations in `/root/repo/migrations/`

---

## Files Affected

| File | Action | Impact |
|------|--------|--------|
| `/root/repo/models/database.py` | MODIFY | Add 3 column definitions to ProcessingRun class |
| `/root/repo/migrations/005_add_audit_count_columns.py` | CREATE | New migration file |
| `/root/repo/tests/test_processing_run_audit_columns.py` | CREATE | New test file for audit columns |

---

## Dependencies

- None. This is the foundation layer for the audit counts feature.

## Risks

- **Low**: SQLite schema changes via ALTER TABLE are straightforward
- **Low**: Default values ensure backward compatibility with existing records

---

## GO Signal

**STATUS: READY FOR IMPLEMENTATION**

- No refactoring needed
- Clear patterns to follow
- Minimal file changes
- Low risk addition
