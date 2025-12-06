#!/usr/bin/env python3
"""
Migration 006: Add emails_categorized and emails_skipped columns to ProcessingRun

This migration adds two new audit count columns to the processing_runs table:
1. emails_categorized - Count of emails categorized during processing
2. emails_skipped - Count of emails skipped during processing

All columns are Integer type with default value of 0 and not nullable.

Version: 006
Created: 2025-12-06
"""

import logging
import sys
from typing import Optional

from sqlalchemy import (
    create_engine, text, inspect
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from utils.logger import get_logger
from models.database import get_database_url

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)


class MigrationError(Exception):
    """Raised when a migration fails."""
    pass


def get_engine(db_path: Optional[str] = None, engine=None):
    """
    Get database engine.

    Args:
        db_path: Path to database file. If None, get_database_url will use its default.
        engine: Optional existing SQLAlchemy engine (for MySQL support).

    Returns:
        SQLAlchemy engine instance
    """
    if engine is not None:
        return engine
    database_url = get_database_url(db_path)
    engine = create_engine(database_url, echo=False)
    return engine


def table_exists(engine, table_name: str) -> bool:
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def column_exists(engine, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade(db_path: Optional[str] = None, engine=None):
    """Apply the migration (add emails_categorized and emails_skipped columns)

    Args:
        db_path: Path to database file. If None, get_database_url will use its default.
        engine: Optional existing SQLAlchemy engine (for MySQL support).
    """
    logger.info("Starting migration 006: Add emails_categorized and emails_skipped columns to ProcessingRun")

    engine = get_engine(db_path, engine=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if processing_runs table exists
        if not table_exists(engine, 'processing_runs'):
            logger.error("processing_runs table doesn't exist. Cannot add columns.")
            raise MigrationError("processing_runs table not found")

        logger.info("Found processing_runs table, adding emails_categorized and emails_skipped columns...")

        # Add emails_categorized column if it doesn't exist
        if not column_exists(engine, 'processing_runs', 'emails_categorized'):
            session.execute(text(
                "ALTER TABLE processing_runs ADD COLUMN emails_categorized INTEGER NOT NULL DEFAULT 0"
            ))
            logger.info("✓ Added emails_categorized column to processing_runs")
        else:
            logger.info("✓ emails_categorized column already exists in processing_runs")

        # Add emails_skipped column if it doesn't exist
        if not column_exists(engine, 'processing_runs', 'emails_skipped'):
            session.execute(text(
                "ALTER TABLE processing_runs ADD COLUMN emails_skipped INTEGER NOT NULL DEFAULT 0"
            ))
            logger.info("✓ Added emails_skipped column to processing_runs")
        else:
            logger.info("✓ emails_skipped column already exists in processing_runs")

        # Backfill existing records with default values (if any records exist without values)
        # This is defensive in case DEFAULT wasn't applied properly
        session.execute(text(
            """
            UPDATE processing_runs
            SET emails_categorized = 0
            WHERE emails_categorized IS NULL
            """
        ))
        session.execute(text(
            """
            UPDATE processing_runs
            SET emails_skipped = 0
            WHERE emails_skipped IS NULL
            """
        ))
        logger.info("✓ Backfilled default values for existing records")

        session.commit()
        logger.info("✓ Migration 006 completed successfully")

    except SQLAlchemyError:
        session.rollback()
        logger.exception("Migration failed")
        raise
    except Exception:
        session.rollback()
        logger.exception("Unexpected error during migration")
        raise
    finally:
        session.close()


def downgrade(db_path: Optional[str] = None, engine=None):
    """Rollback the migration (remove emails_categorized and emails_skipped columns)

    Args:
        db_path: Path to database file. If None, get_database_url will use its default.
        engine: Optional existing SQLAlchemy engine (for MySQL support).
    """
    logger.info("Starting rollback of migration 006: Remove emails_categorized and emails_skipped columns")

    engine = get_engine(db_path, engine=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if processing_runs table exists
        if not table_exists(engine, 'processing_runs'):
            logger.info("processing_runs table doesn't exist, nothing to rollback")
            return

        logger.info("Rolling back emails_categorized and emails_skipped columns from processing_runs...")

        # SQLite doesn't support DROP COLUMN directly, so we need to:
        # 1. Create a new table without the audit columns
        # 2. Copy data from old table to new table
        # 3. Drop old table
        # 4. Rename new table to old table name

        # Get existing data
        logger.info("Creating backup table structure...")
        session.execute(text("""
            CREATE TABLE processing_runs_backup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_address TEXT NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                state TEXT NOT NULL,
                current_step TEXT,
                emails_found INTEGER DEFAULT 0,
                emails_processed INTEGER DEFAULT 0,
                error_message TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                emails_reviewed INTEGER DEFAULT 0,
                emails_tagged INTEGER DEFAULT 0,
                emails_deleted INTEGER DEFAULT 0
            )
        """))

        # Copy data (excluding emails_categorized and emails_skipped columns)
        logger.info("Copying data to backup table...")
        session.execute(text("""
            INSERT INTO processing_runs_backup
            (id, email_address, start_time, end_time, state, current_step,
             emails_found, emails_processed, error_message, created_at, updated_at,
             emails_reviewed, emails_tagged, emails_deleted)
            SELECT
                id, email_address, start_time, end_time, state, current_step,
                emails_found, emails_processed, error_message, created_at, updated_at,
                emails_reviewed, emails_tagged, emails_deleted
            FROM processing_runs
        """))

        # Drop old table
        logger.info("Dropping original table...")
        session.execute(text("DROP TABLE processing_runs"))

        # Rename backup table
        logger.info("Renaming backup table...")
        session.execute(text("ALTER TABLE processing_runs_backup RENAME TO processing_runs"))

        # Recreate indexes
        logger.info("Recreating indexes...")
        session.execute(text(
            "CREATE INDEX idx_processing_runs_email_address ON processing_runs(email_address)"
        ))
        session.execute(text(
            "CREATE INDEX idx_processing_runs_start_time ON processing_runs(start_time)"
        ))
        session.execute(text(
            "CREATE INDEX idx_processing_runs_email_start ON processing_runs(email_address, start_time)"
        ))
        session.execute(text(
            "CREATE INDEX idx_processing_runs_state ON processing_runs(state)"
        ))

        session.commit()
        logger.info("✓ Migration 006 rollback completed")

    except SQLAlchemyError:
        session.rollback()
        logger.exception("Rollback failed")
        raise
    except Exception:
        session.rollback()
        logger.exception("Unexpected error during rollback")
        raise
    finally:
        session.close()


def main():
    """Main function for running migration from command line"""
    import argparse

    parser = argparse.ArgumentParser(description="Migration 006: Add emails_categorized and emails_skipped columns")
    parser.add_argument('--action', choices=['upgrade', 'downgrade'], default='upgrade',
                       help='Migration action to perform')
    parser.add_argument('--db-path', type=str,
                       help='Database path')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        if args.action == 'upgrade':
            upgrade(args.db_path)
            print("✓ Migration upgrade completed successfully")
        else:
            downgrade(args.db_path)
            print("✓ Migration downgrade completed successfully")
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
