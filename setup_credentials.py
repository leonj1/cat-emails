#!/usr/bin/env python3
"""
Helper script to set up Gmail credentials in SQLite database

Usage:
    python3 setup_credentials.py --email your-email@gmail.com --password your-app-password

    Or use environment variables:
    GMAIL_EMAIL=your-email@gmail.com GMAIL_PASSWORD=your-app-password python3 setup_credentials.py
"""
import argparse
import os
import sys
from credentials_service import CredentialsService


def main():
    parser = argparse.ArgumentParser(description="Set up Gmail credentials in SQLite database")
    parser.add_argument("--email", help="Gmail email address (or use GMAIL_EMAIL env var)")
    parser.add_argument("--password", help="Gmail app-specific password (or use GMAIL_PASSWORD env var)")
    parser.add_argument("--db-path", help="Path to credentials database (default: ./credentials.db)")
    parser.add_argument("--list", action="store_true", help="List all stored email addresses")
    parser.add_argument("--delete", help="Delete credentials for specified email address")

    args = parser.parse_args()

    # Initialize service
    db_path = args.db_path or os.getenv('CREDENTIALS_DB_PATH', './credentials.db')
    service = CredentialsService(db_path=db_path)

    # Handle list command
    if args.list:
        emails = service.list_all_emails()
        if emails:
            print(f"Stored email addresses ({len(emails)}):")
            for email in emails:
                print(f"  - {email}")
        else:
            print("No credentials stored in database.")
        return 0

    # Handle delete command
    if args.delete:
        result = service.delete_credentials(args.delete)
        if result:
            print(f"Successfully deleted credentials for: {args.delete}")
            return 0
        else:
            print(f"Failed to delete credentials for: {args.delete}")
            return 1

    # Get email and password from arguments or environment
    email = args.email or os.getenv('GMAIL_EMAIL')
    password = args.password or os.getenv('GMAIL_PASSWORD')

    if not email or not password:
        print("Error: Email and password are required.")
        print("\nProvide them via:")
        print("  1. Command line arguments: --email EMAIL --password PASSWORD")
        print("  2. Environment variables: GMAIL_EMAIL and GMAIL_PASSWORD")
        print("\nOr use --list to list stored emails or --delete EMAIL to delete credentials")
        return 1

    # Store credentials
    result = service.store_credentials(email, password)
    if result:
        print(f"Successfully stored credentials for: {email}")
        print(f"Database location: {db_path}")
        return 0
    else:
        print(f"Failed to store credentials for: {email}")
        return 1


if __name__ == "__main__":
    sys.exit(main())