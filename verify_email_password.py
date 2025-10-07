#!/usr/bin/env python3
"""
Command-line utility to verify Gmail app password for email accounts.
Helps diagnose whether a password is missing or incorrect.

Usage:
    python3 verify_email_password.py <email_address>
    python3 verify_email_password.py --check-all
"""
import os
import sys
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def mask_password(password):
    """Mask a password showing only first 2 and last 2 characters."""
    if not password:
        return None

    if len(password) <= 4:
        return "*" * len(password)

    first_two = password[:2]
    last_two = password[-2:]
    middle_stars = "*" * (len(password) - 4)

    return f"{first_two}{middle_stars}{last_two}"


def check_password_status(email_address: str):
    """
    Check the password status for a given email account.

    Returns:
        tuple: (status, message, masked_password) where status is 'missing', 'invalid', 'valid', or 'error'
    """
    try:
        # Import database modules
        from models.database import init_database, get_session, EmailAccount
        from services.gmail_connection_service import GmailConnectionService

        # Initialize database
        engine = init_database()
        session = get_session(engine)

        # Find account in database
        account = session.query(EmailAccount).filter_by(
            email_address=email_address.lower()
        ).first()

        if not account:
            return ('not_found', f"Account '{email_address}' not found in database", None)

        # Get masked password for display
        masked_pwd = mask_password(account.app_password)

        # Check if password exists
        if not account.app_password:
            return ('missing', f"No app password configured for '{email_address}'", masked_pwd)

        logger.info(f"Testing Gmail connection for {email_address}...")

        # Try to connect to Gmail
        connection_service = GmailConnectionService(
            email_address=account.email_address,
            password=account.app_password
        )

        try:
            conn = connection_service.connect()
            conn.logout()
            return ('valid', f"Password verified successfully for '{email_address}'", masked_pwd)

        except Exception as auth_error:
            error_msg = str(auth_error).lower()

            # Determine the type of error
            if "authentication failed" in error_msg or "authenticationfailed" in error_msg:
                return ('invalid', f"Invalid app password for '{email_address}'. The password appears to be incorrect.", masked_pwd)
            elif "2-step verification" in error_msg:
                return ('config', f"2-Step Verification not enabled for '{email_address}'. Please enable it in Gmail settings.", masked_pwd)
            elif "network" in error_msg or "connection" in error_msg:
                return ('network', f"Network error connecting to Gmail for '{email_address}': {str(auth_error)}', masked_pwd)
            else:
                return ('error', f"Connection error for '{email_address}': {str(auth_error)}', masked_pwd)

    except ImportError as e:
        return ('error', f"Missing dependencies: {str(e)}. Please run: pip install -r requirements.txt", None)
    except Exception as e:
        return ('error', f"Unexpected error: {str(e)}', None)
    finally:
        if 'session' in locals():
            session.close()


def check_all_accounts():
    """Check password status for all accounts in the database."""
    try:
        from models.database import init_database, get_session, EmailAccount

        # Initialize database
        engine = init_database()
        session = get_session(engine)

        # Get all accounts
        accounts = session.query(EmailAccount).order_by(EmailAccount.email_address).all()

        if not accounts:
            print("No accounts found in database")
            return

        print(f"\nChecking {len(accounts)} account(s)...\n")
        print("-" * 80)

        results = {
            'valid': [],
            'missing': [],
            'invalid': [],
            'not_found': [],
            'error': [],
            'config': [],
            'network': []
        }

        for account in accounts:
            status, message, masked_pwd = check_password_status(account.email_address)
            results[status].append((account.email_address, message, masked_pwd))

            # Print status with color coding and masked password
            pwd_display = f" [{masked_pwd}]" if masked_pwd else ""
            if status == 'valid':
                print(f"✅ {account.email_address}: Password OK{pwd_display}")
            elif status == 'missing':
                print(f"❌ {account.email_address}: No password configured")
            elif status == 'invalid':
                print(f"❌ {account.email_address}: Invalid password{pwd_display}")
            elif status == 'config':
                print(f"⚠️  {account.email_address}: Configuration issue{pwd_display}")
            elif status == 'network':
                print(f"🌐 {account.email_address}: Network issue{pwd_display}")
            else:
                print(f"❓ {account.email_address}: {message}")

        # Print summary
        print("-" * 80)
        print("\nSummary:")
        print(f"  Valid passwords:    {len(results['valid'])}")
        print(f"  Missing passwords:  {len(results['missing'])}")
        print(f"  Invalid passwords:  {len(results['invalid'])}")
        print(f"  Config issues:      {len(results['config'])}")
        print(f"  Network issues:     {len(results['network'])}")
        print(f"  Other errors:       {len(results['error'])}")

        # Print recommendations
        if results['missing']:
            print("\n📋 Accounts needing passwords:")
            for email, _, _ in results['missing']:
                print(f"  - {email}")
            print("\n  To add a password, use:")
            print("  1. Enable 2-Step Verification in Gmail")
            print("  2. Generate app password at https://myaccount.google.com/apppasswords")
            print("  3. Update account via API: POST /api/accounts with app_password field")

        if results['invalid']:
            print("\n🔑 Accounts with invalid passwords:")
            for email, _, masked_pwd in results['invalid']:
                pwd_display = f" [{masked_pwd}]" if masked_pwd else ""
                print(f"  - {email}{pwd_display}")
            print("\n  To fix, generate a new app password and update the account")

        session.close()

    except ImportError as e:
        print(f"Missing dependencies: {str(e)}")
        print("Please run: pip install -r requirements.txt")
    except Exception as e:
        print(f"Error: {str(e)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Verify Gmail app passwords for email accounts'
    )
    parser.add_argument(
        'email',
        nargs='?',
        help='Email address to verify'
    )
    parser.add_argument(
        '--check-all',
        action='store_true',
        help='Check all accounts in the database'
    )

    args = parser.parse_args()

    if args.check_all:
        check_all_accounts()
    elif args.email:
        status, message, masked_pwd = check_password_status(args.email)

        # Print result with appropriate emoji and masked password
        pwd_display = f" [Password: {masked_pwd}]" if masked_pwd else ""
        if status == 'valid':
            print(f"✅ {message}{pwd_display}")
        elif status == 'missing':
            print(f"❌ {message}")
            print("\nTo fix:")
            print("1. Enable 2-Step Verification in Gmail")
            print("2. Generate app password at https://myaccount.google.com/apppasswords")
            print("3. Update account via API with the app_password field")
        elif status == 'invalid':
            print(f"❌ {message}{pwd_display}")
            print("\nTo fix:")
            print("1. Generate a new app password at https://myaccount.google.com/apppasswords")
            print("2. Update account via API with the new app_password")
        elif status == 'not_found':
            print(f"❓ {message}")
            print("\nTo add this account:")
            print("Use API endpoint: POST /api/accounts")
        elif status == 'config':
            print(f"⚠️  {message}{pwd_display}")
        elif status == 'network':
            print(f"🌐 {message}{pwd_display}")
        else:
            print(f"❌ {message}")
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python3 verify_email_password.py leonj1@gmail.com")
        print("  python3 verify_email_password.py --check-all")


if __name__ == "__main__":
    main()