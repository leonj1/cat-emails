#!/usr/bin/env python3
"""
Database migration: Add UserSettings table
"""

import sys
import os
from datetime import datetime

# Add the parent directory to the path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import init_database, UserSettings
from sqlalchemy.orm import sessionmaker


def run_migration(db_path: str = "./email_summaries/summaries.db"):
    """Run the migration to add UserSettings table"""
    print(f"Running migration: Add UserSettings table")
    print(f"Database path: {db_path}")
    
    try:
        # Initialize database (this will create the UserSettings table if it doesn't exist)
        engine = init_database(db_path)
        Session = sessionmaker(bind=engine)
        
        # Initialize default settings
        with Session() as session:
            # Check if default settings already exist
            existing_lookback = session.query(UserSettings).filter_by(
                setting_key='lookback_hours'
            ).first()
            
            if not existing_lookback:
                # Add default lookback hours setting
                default_lookback = UserSettings(
                    setting_key='lookback_hours',
                    setting_value='2',
                    setting_type='integer',
                    description='Number of hours to look back when scanning for emails'
                )
                session.add(default_lookback)
                print("Added default lookback_hours setting: 2")
            else:
                print(f"lookback_hours setting already exists: {existing_lookback.setting_value}")
            
            # Check for scan interval setting
            existing_scan = session.query(UserSettings).filter_by(
                setting_key='scan_interval_minutes'
            ).first()
            
            if not existing_scan:
                # Add default scan interval setting
                default_scan = UserSettings(
                    setting_key='scan_interval_minutes',
                    setting_value='5',
                    setting_type='integer',
                    description='Interval in minutes between background email scans'
                )
                session.add(default_scan)
                print("Added default scan_interval_minutes setting: 5")
            else:
                print(f"scan_interval_minutes setting already exists: {existing_scan.setting_value}")
            
            session.commit()
        
        print("Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    # Allow custom database path via command line argument
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./email_summaries/summaries.db"
    
    print("=" * 50)
    print("Cat-Emails Database Migration")
    print("Adding UserSettings table")
    print("=" * 50)
    
    success = run_migration(db_path)
    
    if success:
        print("\n✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
