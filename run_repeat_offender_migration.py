#!/usr/bin/env python3

"""Manually run the repeat offender patterns migration."""

import sqlite3
import os

def run_migration():
    """Run the repeat offender patterns migration."""
    db_path = "./email_summaries/summaries.db"
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='repeat_offender_patterns'")
        if cursor.fetchone():
            print("Table 'repeat_offender_patterns' already exists")
            return
        
        # Create the table
        cursor.execute("""
            CREATE TABLE repeat_offender_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name VARCHAR(255) NOT NULL,
                
                -- Pattern identifiers (at least one must be set)
                sender_email VARCHAR(255) NULL,
                sender_domain VARCHAR(255) NULL,
                subject_pattern VARCHAR(500) NULL,
                
                -- Tracking information
                category VARCHAR(100) NOT NULL,
                total_occurrences INTEGER DEFAULT 0,
                deletion_count INTEGER DEFAULT 0,
                confidence_score REAL DEFAULT 0.0,
                
                -- Timestamps
                first_seen DATETIME NOT NULL,
                last_seen DATETIME NOT NULL,
                marked_as_repeat_offender DATETIME NULL,
                
                -- Status
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Add indexes
        cursor.execute("CREATE INDEX idx_account_sender ON repeat_offender_patterns (account_name, sender_email)")
        cursor.execute("CREATE INDEX idx_account_domain ON repeat_offender_patterns (account_name, sender_domain)")
        cursor.execute("CREATE INDEX idx_account_subject ON repeat_offender_patterns (account_name, subject_pattern)")
        cursor.execute("CREATE INDEX idx_active_patterns ON repeat_offender_patterns (account_name, is_active)")
        
        conn.commit()
        print("Successfully created repeat_offender_patterns table with indexes")
        
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
