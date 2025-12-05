#!/usr/bin/env python3
"""
MySQL-specific migration for adding audit count columns to processing_runs.

This migration is designed to run at MySQL repository initialization time
and adds the columns if they are missing.
"""

from sqlalchemy import text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from utils.logger import get_logger

logger = get_logger(__name__)


def column_exists(engine, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def table_exists(engine, table_name: str) -> bool:
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def run_audit_columns_migration(engine) -> bool:
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
        logger.debug("processing_runs table doesn't exist yet, skipping audit columns migration")
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
                logger.info(f"Adding missing column {column_name} to processing_runs")
                session.execute(text(
                    f"ALTER TABLE processing_runs ADD COLUMN {column_name} {column_def}"
                ))
                session.commit()
                logger.info(f"Added {column_name} column to processing_runs")
            else:
                logger.debug(f"Column {column_name} already exists in processing_runs")

        return True

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to run audit columns migration: {e}")
        return False
    finally:
        session.close()
