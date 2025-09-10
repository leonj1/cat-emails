#!/usr/bin/env python3

"""Debug script to check database location and processed emails."""

import os
import sys
from sqlalchemy import create_engine, text
from services.database_service import DatabaseService
from services.email_summary_service import EmailSummaryService

def main():
    """Debug database location and contents."""
    
    print("🔍 Database Location Debug")
    print("=" * 50)
    
    # Check current working directory
    print(f"Current working directory: {os.getcwd()}")
    
    # Check environment variables
    print(f"DATABASE_PATH env var: {os.getenv('DATABASE_PATH', 'NOT SET')}")
    
    # Initialize services
    print("\n📁 Service Initialization:")
    
    # Database service
    db_service = DatabaseService()
    print(f"DatabaseService path: {db_service.db_path}")
    print(f"Database file exists: {os.path.exists(db_service.db_path)}")
    
    if os.path.exists(db_service.db_path):
        print(f"Database file size: {os.path.getsize(db_service.db_path)} bytes")
        print(f"Database file modified: {os.path.getmtime(db_service.db_path)}")
    
    # Email summary service
    email_service = EmailSummaryService()
    if email_service.db_service:
        print(f"EmailSummaryService DB path: {email_service.db_service.db_path}")
    
    print(f"EmailSummaryService data_dir: {email_service.data_dir}")
    
    # Check processed emails
    print("\n📧 Processed Email Check:")
    
    try:
        # Connect to database and check contents
        engine = create_engine(f'sqlite:///{db_service.db_path}')
        
        with engine.connect() as conn:
            # Check if processed_email_logs table exists
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='processed_email_logs'
            """))
            
            if result.fetchone():
                print("✅ processed_email_logs table exists")
                
                # Count total processed emails
                count_result = conn.execute(text("SELECT COUNT(*) FROM processed_email_logs"))
                count = count_result.fetchone()[0]
                print(f"📊 Total processed emails: {count}")
                
                if count > 0:
                    # Show recent processed emails
                    recent_result = conn.execute(text("""
                        SELECT account_email, message_id, processed_at 
                        FROM processed_email_logs 
                        ORDER BY processed_at DESC 
                        LIMIT 5
                    """))
                    
                    print("\n🕐 Recent processed emails:")
                    for row in recent_result:
                        print(f"  - {row[0]}: {row[1]} at {row[2]}")
                
                # Check for specific accounts
                accounts_result = conn.execute(text("""
                    SELECT account_email, COUNT(*) as count 
                    FROM processed_email_logs 
                    GROUP BY account_email
                """))
                
                print(f"\n👤 Processed emails by account:")
                for row in accounts_result:
                    print(f"  - {row[0]}: {row[1]} emails")
            else:
                print("❌ processed_email_logs table does not exist")
                
                # Show all tables
                all_tables = conn.execute(text("""
                    SELECT name FROM sqlite_master WHERE type='table'
                """))
                print("Available tables:")
                for row in all_tables:
                    print(f"  - {row[0]}")
                    
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    
    print("\n🐳 Docker Environment Check:")
    print(f"Running in container: {os.path.exists('/.dockerenv')}")
    
    # Check if directories exist
    important_paths = [
        "./email_summaries",
        "/data/email_summaries", 
        "./services",
        "./models"
    ]
    
    for path in important_paths:
        exists = os.path.exists(path)
        print(f"{path}: {'✅' if exists else '❌'}")
        if exists and os.path.isdir(path):
            files = os.listdir(path)[:5]  # First 5 files
            print(f"  Contents: {files}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
