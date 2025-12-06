---
executor: bdd
source_feature: ./specs/DRAFT-python-migration-006-core.md
---

<objective>
Implement Python Migration 006 that adds `emails_categorized` and `emails_skipped` columns to the `processing_runs` table in SQLite databases. This migration provides idempotent upgrade/downgrade operations for databases that may not have Flyway applied.
</objective>

<gherkin>
Feature: Python Migration 006 - Add Categorized and Skipped Columns
  As a system administrator
  I want to run a Python migration that adds audit tracking columns
  So that SQLite databases without Flyway can track categorized and skipped email counts

  Background:
    Given a SQLite database with a processing_runs table
    And the database uses SQLAlchemy for connections

  Scenario: Migration creates columns when missing
    Given the processing_runs table does NOT have emails_categorized column
    And the processing_runs table does NOT have emails_skipped column
    When the migration upgrade() is executed
    Then emails_categorized column exists with INTEGER type
    And emails_categorized column has DEFAULT 0
    And emails_skipped column exists with INTEGER type
    And emails_skipped column has DEFAULT 0
    And the migration logs success messages

  Scenario: Migration is idempotent - safe to run multiple times
    Given the processing_runs table already has emails_categorized column
    And the processing_runs table already has emails_skipped column
    When the migration upgrade() is executed
    Then no error is raised
    And the columns remain unchanged
    And the column defaults are preserved
    And the migration logs "already exists" messages

  Scenario: Migration downgrade removes columns
    Given the processing_runs table has emails_categorized column
    And the processing_runs table has emails_skipped column
    And the table contains existing data rows
    When the migration downgrade() is executed
    Then emails_categorized column no longer exists
    And emails_skipped column no longer exists
    And all other columns are preserved
    And all existing data rows are preserved
    And all table indexes are recreated
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **Migration file**: `migrations/006_add_categorized_skipped_columns.py`
   - Version: 006
   - Description: "Add emails_categorized and emails_skipped columns to processing_runs"

2. **upgrade() function**:
   - Check if processing_runs table exists (raise MigrationError if not)
   - For each column (emails_categorized, emails_skipped):
     - Check if column exists using SQLAlchemy inspector
     - If NOT exists: ALTER TABLE ADD COLUMN with INTEGER NOT NULL DEFAULT 0
     - If exists: Log "already exists" and skip (idempotent)
   - Backfill NULL values to 0 for defensive compatibility
   - Commit transaction on success

3. **downgrade() function**:
   - Check if processing_runs table exists
   - SQLite doesn't support DROP COLUMN directly, so:
     - Create backup table WITHOUT the two new columns
     - Copy all data (excluding new columns)
     - Drop original table
     - Rename backup to original name
     - Recreate all indexes
   - Handle case where columns don't exist (idempotent)

4. **Helper functions** (reuse from migration 005):
   - `get_engine(db_path, engine)` - Get SQLAlchemy engine
   - `table_exists(engine, table_name)` - Check table existence
   - `column_exists(engine, table_name, column_name)` - Check column existence

5. **Command-line interface**:
   - `--action upgrade|downgrade`
   - `--db-path` for database path
   - `--verbose` for debug logging

Edge Cases to Handle:
- Table doesn't exist (raise MigrationError)
- Columns already exist (skip silently - idempotent)
- Columns already removed during downgrade (skip silently)
- NULL values in existing data (backfill to 0)
- Database connection failures (proper exception handling)
</requirements>

<context>
DRAFT Specification: specs/DRAFT-python-migration-006-core.md

**Reuse Opportunities from Gap Analysis:**

1. **migrations/005_add_audit_count_columns.py** (EXACT PATTERN):
   - Copy structure entirely, change only:
     - Version number (005 -> 006)
     - Column names (emails_reviewed/tagged/deleted -> emails_categorized/emails_skipped)
     - Description text
   - Reuse: `get_engine()`, `table_exists()`, `column_exists()`, `MigrationError`
   - Follow same error handling patterns

2. **models/database.py** (Reference):
   - ProcessingRun model already has `emails_categorized` and `emails_skipped` columns (lines 224-225)
   - This migration is for SQLite databases that don't use Flyway

**New Components:**
- `migrations/006_add_categorized_skipped_columns.py` - New migration file
- `tests/test_migration_006.py` - Test file for migration
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios first
2. Implement migration code to make tests pass
3. Ensure all scenarios are green

**Architecture Guidelines:**
- Follow strict-architecture rules (500 lines max)
- Follow exact pattern from migrations/005_add_audit_count_columns.py
- Use SQLAlchemy for all database operations
- Maintain thread-safety considerations
- Keep migration file under 300 lines

**Implementation Steps:**
1. Create test file with 3 test classes (one per scenario)
2. Create migration file following 005 pattern
3. Test upgrade creates columns with correct type and default
4. Test upgrade is idempotent (no error on re-run)
5. Test downgrade removes columns and preserves data
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Migration creates columns when missing
- [ ] Scenario: Migration is idempotent - safe to run multiple times
- [ ] Scenario: Migration downgrade removes columns

Additional verification:
- [ ] Migration file exists at correct path
- [ ] All imports work correctly
- [ ] Command-line interface works
- [ ] Integration with existing database models
</verification>

<success_criteria>
- Migration file exists at `migrations/006_add_categorized_skipped_columns.py`
- `upgrade()` adds both columns with INTEGER type and DEFAULT 0
- `upgrade()` is idempotent - running twice does not error or duplicate columns
- `downgrade()` removes both columns while preserving other data
- All 3 BDD scenarios pass as tests
- Test file exists at `tests/test_migration_006.py`
- Code follows project coding standards
- Migration follows exact pattern from migration 005
</success_criteria>
