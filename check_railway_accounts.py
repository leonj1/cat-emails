#!/usr/bin/env python3
"""
Script to check Gmail accounts in the Railway database.
"""
import os
import sys
from sqlalchemy import create_engine, text
from models.database import init_database, EmailAccount
from sqlalchemy.orm import sessionmaker

def main():
    """Query and display Gmail accounts from the database."""

    print("=" * 60)
    print("🔍 Checking Gmail Accounts in Railway Database")
    print("=" * 60)

    # Get database path from environment or use default
    db_path = os.getenv("DATABASE_PATH", "./email_summaries/summaries.db")
    print(f"\n📁 Database Path: {db_path}")
    print(f"📁 Database exists: {os.path.exists(db_path)}")

    if os.path.exists(db_path):
        print(f"📁 Database size: {os.path.getsize(db_path)} bytes")

    try:
        # Initialize database connection
        engine = init_database(db_path)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            # Query all email accounts
            accounts = session.query(EmailAccount).all()

            print(f"\n📊 Total Accounts Found: {len(accounts)}")

            if len(accounts) == 0:
                print("\n⚠️  No Gmail accounts found in the database!")
                print("\nPossible reasons:")
                print("  1. Accounts haven't been registered yet via API")
                print("  2. Database is empty or newly created")
                print("  3. Looking at wrong database path")

                # Check if table exists
                result = session.execute(text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='email_accounts'
                """))
                if result.fetchone():
                    print("\n✅ email_accounts table exists (but is empty)")
                else:
                    print("\n❌ email_accounts table does NOT exist")

                # List all tables
                print("\n📋 Available tables:")
                tables = session.execute(text("""
                    SELECT name FROM sqlite_master WHERE type='table'
                """))
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("\n" + "=" * 60)
                print("📧 Gmail Accounts:")
                print("=" * 60)

                for idx, account in enumerate(accounts, 1):
                    print(f"\n{idx}. {account.email_address}")
                    print(f"   ID: {account.id}")
                    print(f"   Display Name: {account.display_name or 'N/A'}")
                    print(f"   Active: {'✅ Yes' if account.is_active else '❌ No'}")
                    print(f"   Has Password: {'✅ Yes' if account.app_password else '❌ No'}")
                    if account.app_password:
                        # Mask the password
                        pwd_len = len(account.app_password)
                        if pwd_len > 4:
                            masked = f"{account.app_password[:2]}{'*' * (pwd_len - 4)}{account.app_password[-2:]}"
                        else:
                            masked = "*" * pwd_len
                        print(f"   Password (masked): {masked} (length: {pwd_len})")
                    print(f"   Last Scan: {account.last_scan_at or 'Never'}")
                    print(f"   Created: {account.created_at}")
                    print(f"   Updated: {account.updated_at}")

            # Check processing runs
            print("\n" + "=" * 60)
            print("🏃 Recent Processing Runs:")
            print("=" * 60)

            runs = session.execute(text("""
                SELECT email_address, start_time, end_time, state, emails_processed
                FROM processing_runs
                ORDER BY start_time DESC
                LIMIT 10
            """))

            run_count = 0
            for run in runs:
                run_count += 1
                print(f"\n{run_count}. Email: {run[0]}")
                print(f"   Started: {run[1]}")
                print(f"   Ended: {run[2] or 'In Progress'}")
                print(f"   State: {run[3]}")
                print(f"   Processed: {run[4] or 0} emails")

            if run_count == 0:
                print("\nNo processing runs found.")

    except Exception as e:
        print(f"\n❌ Error querying database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
