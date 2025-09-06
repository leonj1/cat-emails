#!/usr/bin/env python3
"""
Migration 002: Modify Processing Runs Table

This migration modifies the existing processing_runs table to support
historical tracking of email processing sessions with the following changes:

1. Rename run_id to just id (keeping it as primary key)
2. Add email_address field (not null)
3. Rename started_at to start_time
4. Rename completed_at to end_time
5. Add state field (not null) - current processing state
6. Add current_step field (nullable) - description of current step
7. Rename emails_fetched to emails_found
8. Rename emails_processed to emails_processed (keep as is)
9. Remove unused fields (emails_deleted, emails_archived, emails_error, scan_hours, duration_seconds, success)
10. Keep error_message field
11. Add created_at and updated_at timestamps
12. Add proper indexes for performance

Version: 002
Created: 2025-09-06
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text, 
    Index, text, inspect
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

# Define the new ProcessingRun table structure
class ProcessingRunNew(Base):
    """Individual email processing run details - new structure"""
    __tablename__ = 'processing_runs_new'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_address = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    state = Column(Text, nullable=False)
    current_step = Column(Text, nullable=True)
    emails_found = Column(Integer, default=0)
    emails_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_processing_runs_email_address', 'email_address'),
        Index('idx_processing_runs_start_time', 'start_time'),
        Index('idx_processing_runs_email_start', 'email_address', 'start_time'),
        Index('idx_processing_runs_state', 'state'),
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


def get_table_data(session, table_name: str):
    """Get all data from a table"""
    try:
        result = session.execute(text(f"SELECT * FROM {table_name}"))
        return result.fetchall()
    except Exception:
        return []


def upgrade(db_path: Optional[str] = None):
    """Apply the migration (upgrade database schema)"""
    logger.info("Starting migration 002: Modify Processing Runs Table")
    
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if processing_runs table exists
        if not table_exists(engine, 'processing_runs'):
            logger.info("processing_runs table doesn't exist, creating new one...")
            # Create the new table directly
            ProcessingRunNew.__table__.create(engine)
            logger.info("✓ Created processing_runs table with new structure")
            
            # Rename the table
            session.execute(text("ALTER TABLE processing_runs_new RENAME TO processing_runs"))
            session.commit()
            logger.info("✓ Renamed table to processing_runs")
            return
        
        logger.info("Found existing processing_runs table, migrating structure...")
        
        # Step 1: Create new table with desired structure
        logger.info("Creating new processing_runs table...")
        ProcessingRunNew.__table__.create(engine)
        logger.info("✓ Created processing_runs_new table")
        
        # Step 2: Migrate existing data if any
        logger.info("Migrating existing data...")
        existing_data = get_table_data(session, 'processing_runs')
        
        if existing_data:
            logger.info(f"Found {len(existing_data)} existing records to migrate")
            
            # Get column names from the old table
            old_inspector = inspect(engine)
            old_columns = [col['name'] for col in old_inspector.get_columns('processing_runs')]
            
            for row in existing_data:
                # Create a dictionary from the row data
                row_dict = dict(zip(old_columns, row))
                
                # Map old fields to new fields
                insert_values = {
                    'email_address': 'unknown@example.com',  # Default value since old table doesn't have this
                    'start_time': row_dict.get('started_at', datetime.utcnow()),
                    'end_time': row_dict.get('completed_at'),
                    'state': 'completed' if row_dict.get('completed_at') else 'running',
                    'current_step': None,
                    'emails_found': row_dict.get('emails_fetched', 0),
                    'emails_processed': row_dict.get('emails_processed', 0),
                    'error_message': row_dict.get('error_message'),
                    'created_at': row_dict.get('created_at', datetime.utcnow()),
                    'updated_at': datetime.utcnow()
                }
                
                # Insert into new table
                columns = ', '.join(insert_values.keys())
                placeholders = ', '.join([f":{k}" for k in insert_values.keys()])
                
                session.execute(
                    text(f"INSERT INTO processing_runs_new ({columns}) VALUES ({placeholders})"),
                    insert_values
                )
            
            logger.info(f"✓ Migrated {len(existing_data)} records")
        else:
            logger.info("No existing data to migrate")
        
        # Step 3: Drop old table and rename new one
        logger.info("Replacing old table with new structure...")
        session.execute(text("DROP TABLE processing_runs"))
        session.execute(text("ALTER TABLE processing_runs_new RENAME TO processing_runs"))
        
        session.commit()
        logger.info("✓ Migration 002 completed successfully")
        
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
    logger.info("Starting rollback of migration 002: Modify Processing Runs Table")
    
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if the new processing_runs table exists
        if not table_exists(engine, 'processing_runs'):
            logger.info("processing_runs table doesn't exist, nothing to rollback")
            return
        
        logger.info("Rolling back processing_runs table to original structure...")
        
        # Create the old structure table
        session.execute(text("""
            CREATE TABLE processing_runs_old (
                id INTEGER PRIMARY KEY,
                run_id VARCHAR(50) UNIQUE NOT NULL,
                started_at DATETIME NOT NULL,
                completed_at DATETIME,
                duration_seconds REAL,
                emails_fetched INTEGER DEFAULT 0,
                emails_processed INTEGER DEFAULT 0,
                emails_deleted INTEGER DEFAULT 0,
                emails_archived INTEGER DEFAULT 0,
                emails_error INTEGER DEFAULT 0,
                scan_hours INTEGER,
                error_message TEXT,
                success BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create the old index
        session.execute(text("CREATE INDEX idx_run_time ON processing_runs_old(started_at, completed_at)"))
        
        # Try to migrate data back (this will be lossy since we have different fields)
        existing_data = get_table_data(session, 'processing_runs')
        
        if existing_data:
            logger.info(f"Migrating {len(existing_data)} records back to old structure")
            
            # Get column names from the current table
            inspector = inspect(engine)
            current_columns = [col['name'] for col in inspector.get_columns('processing_runs')]
            
            for i, row in enumerate(existing_data):
                row_dict = dict(zip(current_columns, row))
                
                # Map new fields back to old fields (with data loss)
                insert_values = {
                    'run_id': f"migrated_run_{i}",  # Generate a run_id
                    'started_at': row_dict.get('start_time'),
                    'completed_at': row_dict.get('end_time'),
                    'duration_seconds': None,  # We don't have this anymore
                    'emails_fetched': row_dict.get('emails_found', 0),
                    'emails_processed': row_dict.get('emails_processed', 0),
                    'emails_deleted': 0,  # We don't have this anymore
                    'emails_archived': 0,  # We don't have this anymore
                    'emails_error': 0,  # We don't have this anymore
                    'scan_hours': None,  # We don't have this anymore
                    'error_message': row_dict.get('error_message'),
                    'success': 1 if row_dict.get('state') == 'completed' else 0,
                    'created_at': row_dict.get('created_at')
                }
                
                columns = ', '.join(insert_values.keys())
                placeholders = ', '.join([f":{k}" for k in insert_values.keys()])
                
                session.execute(
                    text(f"INSERT INTO processing_runs_old ({columns}) VALUES ({placeholders})"),
                    insert_values
                )
            
            logger.info(f"✓ Migrated {len(existing_data)} records back to old structure")
        
        # Replace the tables
        session.execute(text("DROP TABLE processing_runs"))
        session.execute(text("ALTER TABLE processing_runs_old RENAME TO processing_runs"))
        
        session.commit()
        logger.info("✓ Migration 002 rollback completed")
        
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
    
    parser = argparse.ArgumentParser(description="Migration 002: Modify Processing Runs Table")
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