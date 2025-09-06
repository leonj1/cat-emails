#!/usr/bin/env python3
"""
Migration 001: Add Account Tracking

This migration adds multi-account support to the Cat-Emails project by:
1. Creating email_accounts table to track different email accounts
2. Creating account_category_stats table for per-account category statistics
3. Adding account_id foreign key to existing email_summaries table
4. Creating appropriate indexes for performance

Version: 001
Created: 2025-01-29
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Boolean, Date, 
    ForeignKey, Index, UniqueConstraint, text, inspect
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the existing database module
sys.path.append(str(Path(__file__).parent.parent))
from models.database import get_database_url, Base

# Define new tables using SQLAlchemy declarative base
class EmailAccount(Base):
    """Email account tracking table"""
    __tablename__ = 'email_accounts'
    
    id = Column(Integer, primary_key=True)
    email_address = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_scan_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_email_accounts_email_address', 'email_address'),
        Index('idx_email_accounts_is_active', 'is_active'),
    )


class AccountCategoryStats(Base):
    """Per-account category statistics table"""
    __tablename__ = 'account_category_stats'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('email_accounts.id'), nullable=False)
    date = Column(Date, nullable=False)
    category_name = Column(String(100), nullable=False)
    email_count = Column(Integer, default=0, nullable=False)
    deleted_count = Column(Integer, default=0, nullable=False)
    archived_count = Column(Integer, default=0, nullable=False)
    kept_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_account_category_stats_account_date', 'account_id', 'date'),
        Index('idx_account_category_stats_date_account', 'date', 'account_id'),
        Index('idx_account_category_stats_category', 'category_name'),
        UniqueConstraint('account_id', 'date', 'category_name', name='uq_account_date_category'),
    )


def get_engine(db_path: Optional[str] = None):
    """Get database engine"""
    if db_path is None:
        db_path = "./email_summaries/summaries.db"
    
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
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def upgrade(db_path: Optional[str] = None):
    """Apply the migration (upgrade database schema)"""
    logger.info("Starting migration 001: Add Account Tracking")
    
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Step 1: Create email_accounts table
        logger.info("Creating email_accounts table...")
        if not table_exists(engine, 'email_accounts'):
            EmailAccount.__table__.create(engine)
            logger.info("✓ Created email_accounts table")
        else:
            logger.info("✓ email_accounts table already exists")
        
        # Step 2: Create account_category_stats table
        logger.info("Creating account_category_stats table...")
        if not table_exists(engine, 'account_category_stats'):
            AccountCategoryStats.__table__.create(engine)
            logger.info("✓ Created account_category_stats table")
        else:
            logger.info("✓ account_category_stats table already exists")
        
        # Step 3: Add account_id column to email_summaries table
        logger.info("Adding account_id column to email_summaries table...")
        if not column_exists(engine, 'email_summaries', 'account_id'):
            # Add the column
            session.execute(text(
                "ALTER TABLE email_summaries ADD COLUMN account_id INTEGER"
            ))
            logger.info("✓ Added account_id column to email_summaries")
            
            # Create the foreign key constraint (SQLite doesn't support adding FK constraints to existing tables easily)
            # We'll create an index instead for performance
            session.execute(text(
                "CREATE INDEX idx_email_summaries_account_id ON email_summaries(account_id)"
            ))
            logger.info("✓ Created index on email_summaries.account_id")
        else:
            logger.info("✓ account_id column already exists in email_summaries")
        
        session.commit()
        logger.info("✓ Migration 001 completed successfully")
        
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error during migration: {e}")
        raise
    finally:
        session.close()


def downgrade(db_path: Optional[str] = None):
    """Rollback the migration (downgrade database schema)"""
    logger.info("Starting rollback of migration 001: Add Account Tracking")
    
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Step 1: Remove account_id column from email_summaries
        # Note: SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        logger.info("Removing account_id column from email_summaries...")
        if column_exists(engine, 'email_summaries', 'account_id'):
            # Drop the index first
            try:
                session.execute(text("DROP INDEX IF EXISTS idx_email_summaries_account_id"))
            except Exception as e:
                logger.warning(f"Could not drop index: {e}")
            
            # For SQLite, we need to recreate the table without the account_id column
            # This is complex, so we'll just warn the user for manual intervention
            logger.warning(
                "SQLite doesn't support DROP COLUMN easily. "
                "The account_id column in email_summaries will remain but can be ignored. "
                "For complete removal, manual intervention is required."
            )
        
        # Step 2: Drop account_category_stats table
        logger.info("Dropping account_category_stats table...")
        if table_exists(engine, 'account_category_stats'):
            session.execute(text("DROP TABLE account_category_stats"))
            logger.info("✓ Dropped account_category_stats table")
        
        # Step 3: Drop email_accounts table
        logger.info("Dropping email_accounts table...")
        if table_exists(engine, 'email_accounts'):
            session.execute(text("DROP TABLE email_accounts"))
            logger.info("✓ Dropped email_accounts table")
        
        session.commit()
        logger.info("✓ Migration 001 rollback completed")
        
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Rollback failed: {e}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error during rollback: {e}")
        raise
    finally:
        session.close()


def main():
    """Main function for running migration from command line"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration 001: Add Account Tracking")
    parser.add_argument('--action', choices=['upgrade', 'downgrade'], default='upgrade',
                       help='Migration action to perform')
    parser.add_argument('--db-path', type=str, 
                       help='Database path (default: ./email_summaries/summaries.db)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
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