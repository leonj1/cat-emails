# DRAFT Specification: Python Migration 006 - Core

## Task Reference
- **Parent Task**: 1.5 Data Integrity and Persistence (Decomposed)
- **Sub-task**: 1.5a Python Migration 006 - Core
- **Status**: In Progress

## Overview
Create a Python migration script (`migrations/006_add_categorized_skipped_columns.py`) that adds `emails_categorized` and `emails_skipped` columns to the `processing_runs` table. This migration is for SQLite databases that may not have Flyway applied.

## Interfaces Needed

### IMigration (Protocol)
```python
from typing import Protocol
from sqlalchemy import Connection

class IMigration(Protocol):
    """Interface for database migrations."""

    @property
    def version(self) -> int:
        """Return the migration version number."""
        ...

    @property
    def description(self) -> str:
        """Return a human-readable description of the migration."""
        ...

    def upgrade(self, connection: Connection) -> None:
        """Apply the migration (add columns)."""
        ...

    def downgrade(self, connection: Connection) -> None:
        """Revert the migration (remove columns)."""
        ...

    def check_applied(self, connection: Connection) -> bool:
        """Check if the migration has already been applied (idempotency check)."""
        ...
```

## Data Models

### Migration006AddCategorizedSkippedColumns
```python
class Migration006AddCategorizedSkippedColumns:
    """Migration to add emails_categorized and emails_skipped columns."""

    version: int = 6
    description: str = "Add emails_categorized and emails_skipped columns to processing_runs"
    table_name: str = "processing_runs"
    columns: List[str] = ["emails_categorized", "emails_skipped"]
```

## Logic Flow

### upgrade() Pseudocode
```
1. For each column in [emails_categorized, emails_skipped]:
   a. Check if column exists in processing_runs table
   b. If column does NOT exist:
      - Execute ALTER TABLE to add INTEGER column with DEFAULT 0
   c. If column exists:
      - Log "Column already exists, skipping" (idempotent)
2. Return success
```

### downgrade() Pseudocode
```
1. For each column in [emails_categorized, emails_skipped]:
   a. Check if column exists in processing_runs table
   b. If column exists:
      - SQLite does not support DROP COLUMN directly
      - Create temp table without the column
      - Copy data from original table
      - Drop original table
      - Rename temp table to original name
   c. If column does NOT exist:
      - Log "Column already removed, skipping" (idempotent)
2. Return success
```

### check_applied() Pseudocode
```
1. Query sqlite_master or PRAGMA table_info for processing_runs
2. Check if both emails_categorized and emails_skipped columns exist
3. Return True if both exist, False otherwise
```

## BDD Scenarios (3 scenarios)

### Scenario 1: Migration creates columns when missing
```gherkin
Given a SQLite database with processing_runs table
And the table does NOT have emails_categorized column
And the table does NOT have emails_skipped column
When the migration upgrade() is executed
Then emails_categorized column exists with DEFAULT 0
And emails_skipped column exists with DEFAULT 0
```

### Scenario 2: Migration is idempotent (safe to run multiple times)
```gherkin
Given a SQLite database with processing_runs table
And both emails_categorized and emails_skipped columns already exist
When the migration upgrade() is executed
Then no error is raised
And the columns remain unchanged
And the column defaults are preserved
```

### Scenario 3: Migration downgrade removes columns
```gherkin
Given a SQLite database with processing_runs table
And both emails_categorized and emails_skipped columns exist
When the migration downgrade() is executed
Then emails_categorized column no longer exists
And emails_skipped column no longer exists
And all other columns and data are preserved
```

## Context Budget

| Category | Estimate |
|----------|----------|
| Files to read | 2 (~100 lines) - existing migrations for pattern reference |
| New code to write | ~80 lines |
| Test code to write | ~100 lines |
| **Estimated context usage** | **15%** |

## Acceptance Criteria
1. Migration file exists at `migrations/006_add_categorized_skipped_columns.py`
2. `upgrade()` adds both columns with INTEGER type and DEFAULT 0
3. `upgrade()` is idempotent - running twice does not error or duplicate columns
4. `downgrade()` removes both columns while preserving other data
5. `check_applied()` correctly detects migration state
6. All 3 BDD scenarios pass as tests
