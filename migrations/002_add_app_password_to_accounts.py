#!/usr/bin/env python3
"""
Migration to add app_password field to email_accounts table.

This migration adds support for storing Gmail app-specific passwords
for multi-tenant SaaS functionality where each customer's credentials
need to be stored securely in the database.
"""
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, Column, String, text
from sqlalchemy.exc import OperationalError

# Add parent directory to path to import models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import get_database_url


def upgrade():
    """Add app_password column to email_accounts table."""
    db_url = get_database_url()
    engine = create_engine(db_url)

    with engine.connect() as conn:
        try:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(email_accounts)"))
            columns = [row[1] for row in result]

            if 'app_password' not in columns:
                print("Adding app_password column to email_accounts table...")
                conn.execute(text(
                    "ALTER TABLE email_accounts ADD COLUMN app_password VARCHAR(255)"
                ))
                conn.commit()
                print("✅ Successfully added app_password column")
            else:
                print("ℹ️  app_password column already exists, skipping")

        except OperationalError as e:
            if "no such table" in str(e).lower():
                print("⚠️  email_accounts table doesn't exist. Run init_database first.")
            else:
                raise


def downgrade():
    """Remove app_password column from email_accounts table."""
    db_url = get_database_url()
    engine = create_engine(db_url)

    with engine.connect() as conn:
        try:
            # SQLite doesn't support DROP COLUMN directly
            # We need to recreate the table without the column
            print("Removing app_password column from email_accounts table...")

            # This is complex in SQLite, would need to:
            # 1. Create new table without app_password
            # 2. Copy data
            # 3. Drop old table
            # 4. Rename new table

            print("⚠️  Downgrade not fully implemented for SQLite")
            print("    Would need to recreate table to remove column")

        except OperationalError as e:
            print(f"Error during downgrade: {e}")


def main():
    """Run the migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Add app_password field to email_accounts")
    parser.add_argument(
        "--downgrade",
        action="store_true",
        help="Rollback the migration"
    )

    args = parser.parse_args()

    if args.downgrade:
        downgrade()
    else:
        upgrade()


if __name__ == "__main__":
    main()