#!/usr/bin/env python3
"""
Script to check Gmail accounts in the Railway database.

Connects to a SQLite database (configurable via DATABASE_PATH environment
variable) and displays all EmailAccount records with masked passwords,
plus recent processing_runs.

Usage:
    DATABASE_PATH=/path/to/db.sqlite python3 check_railway_accounts.py

Exit codes:
    0: Success
    1: Error (invalid path, database error, or unexpected exception)
"""
import os
import sys
import traceback

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from models.database import init_database, EmailAccount


def mask_password(password: str) -> str:
    """Mask a password for display, preserving first and last 2 chars."""
    pwd_len = len(password)
    if pwd_len > 4:
        return f"{password[:2]}{'*' * (pwd_len - 4)}{password[-2:]}"
    else:
        return "*" * pwd_len


def main() -> None:
    """Query and display Gmail accounts from the database."""

    print("=" * 60)
    print("🔍 Checking Gmail Accounts in Railway Database")
    print("=" * 60)

    # Get database path from environment or use default
    raw_db_path = os.getenv("DATABASE_PATH", "./email_summaries/summaries.db")
    db_path = os.path.expanduser(raw_db_path)
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)

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
                    display_name = account.display_name or 'N/A'
                    print(f"   Display Name: {display_name}")
                    is_active = account.is_active
                    active_status = '✅ Yes' if is_active else '❌ No'
                    print(f"   Active: {active_status}")
                    has_pwd = '✅ Yes' if account.app_password else '❌ No'
                    print(f"   Has Password: {has_pwd}")
                    if account.app_password:
                        masked = mask_password(account.app_password)
                        pwd_len = len(account.app_password)
                        print(f"   Password (masked): {masked}")
                        print(f"   Password length: {pwd_len}")
                    print(f"   Last Scan: {account.last_scan_at or 'Never'}")
                    print(f"   Created: {account.created_at}")
                    print(f"   Updated: {account.updated_at}")

            # Check processing runs
            print("\n" + "=" * 60)
            print("🏃 Recent Processing Runs:")
            print("=" * 60)

            # Constants
            MAX_RECENT_RUNS = 10

            runs = session.execute(text("""
                SELECT email_address, start_time, end_time,
                       state, emails_processed
                FROM processing_runs
                ORDER BY start_time DESC
                LIMIT :limit
            """), {"limit": MAX_RECENT_RUNS})

            runs_list = list(runs)
            for idx, run in enumerate(runs_list, 1):
                print(f"\n{idx}. Email: {run[0]}")
                print(f"   Started: {run[1]}")
                print(f"   Ended: {run[2] or 'In Progress'}")
                print(f"   State: {run[3]}")
                print(f"   Processed: {run[4] or 0} emails")

            if len(runs_list) == 0:
                print("\nNo processing runs found.")

    except (SQLAlchemyError, OSError) as e:
        print(f"\n❌ Error querying database: {e}")
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
