"""
MySQL-specific migration for adding audit count columns to processing_runs.

This migration is designed to run at MySQL repository initialization time
and adds the columns if they are missing.
"""

from typing import TYPE_CHECKING

from sqlalchemy import text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from utils.logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

logger = get_logger(__name__)


def column_exists(engine: "Engine", table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
    except SQLAlchemyError as exc:
        logger.warning(
            "Failed to check column existence for %s.%s: %s",
            table_name,
            column_name,
            exc,
        )
        return False
    else:
        return column_name in columns


def table_exists(engine: "Engine", table_name: str) -> bool:
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def run_audit_columns_migration(engine: "Engine") -> bool:
    """
    Add audit count columns to processing_runs table if they don't exist.

    This is a MySQL-compatible migration that checks for missing columns
    and adds them with appropriate defaults.

    Args:
        engine: SQLAlchemy engine connected to MySQL

    Returns:
        True if migration ran successfully, False otherwise
    """
    if not table_exists(engine, 'processing_runs'):
        logger.debug(
            "processing_runs table doesn't exist yet, skipping audit columns migration"
        )
        return True

    Session = sessionmaker(bind=engine)
    session = Session()

    columns_to_add = [
        ('emails_reviewed', 'INTEGER NOT NULL DEFAULT 0'),
        ('emails_tagged', 'INTEGER NOT NULL DEFAULT 0'),
        ('emails_deleted', 'INTEGER NOT NULL DEFAULT 0'),
    ]

    try:
        for column_name, column_def in columns_to_add:
            if not column_exists(engine, 'processing_runs', column_name):
                logger.info(
                    "Adding missing column %s to processing_runs",
                    column_name,
                )
                try:
                    session.execute(text(
                        f"ALTER TABLE processing_runs ADD COLUMN {column_name} {column_def}"
                    ))
                    session.commit()
                    logger.info(
                        "Added %s column to processing_runs",
                        column_name,
                    )
                except OperationalError as e:
                    # Handle race condition: if another instance added the column
                    # between our check and ALTER, MySQL error 1060 (duplicate column)
                    session.rollback()
                    if "1060" in str(e.orig) or "Duplicate column" in str(e.orig):
                        logger.debug(
                            "Column %s already exists (added by concurrent deployment)",
                            column_name,
                        )
                    else:
                        # Re-raise if it's a different operational error
                        raise
            else:
                logger.debug(
                    "Column %s already exists in processing_runs",
                    column_name,
                )
    except SQLAlchemyError:
        session.rollback()
        logger.exception("Failed to run audit columns migration")
        return False
    else:
        return True
    finally:
        session.close()
