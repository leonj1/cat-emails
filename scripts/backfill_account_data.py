#!/usr/bin/env python3
"""
Data backfill script for Cat-Emails account tracking system.

This script migrates existing email_summaries data to work with the new account tracking system by:
1. Creating EmailAccount records from existing data
2. Linking existing summaries to accounts  
3. Generating account_category_stats from historical data

Usage:
    python3 scripts/backfill_account_data.py --dry-run
    python3 scripts/backfill_account_data.py --email user@gmail.com --verbose
    python3 scripts/backfill_account_data.py --database ./custom/path/summaries.db
"""

import argparse
import logging
import os
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from collections import defaultdict

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.database import (
    EmailAccount, EmailSummary, CategorySummary, AccountCategoryStats,
    init_database, get_session, get_database_url
)
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError


class BackfillMigrator:
    """Handles the backfill migration from old email_summaries to account tracking."""
    
    def __init__(self, db_path: str, dry_run: bool = False, verbose: bool = False):
        self.db_path = db_path
        self.dry_run = dry_run
        self.verbose = verbose
        self.engine = None
        self.session = None
        
        # Set up logging
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        if dry_run:
            self.logger.info("DRY RUN MODE: No changes will be made to the database")

    def __enter__(self):
        """Context manager entry - establish database connection."""
        try:
            self.engine = create_engine(get_database_url(self.db_path))
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            self.logger.info(f"Connected to database: {self.db_path}")
            return self
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up database connection."""
        if self.session:
            if exc_type is not None:
                self.logger.error("Rolling back transaction due to error")
                self.session.rollback()
            else:
                if not self.dry_run:
                    self.session.commit()
                    self.logger.info("Transaction committed successfully")
                else:
                    self.session.rollback()
                    self.logger.info("DRY RUN: Transaction rolled back")
            
            self.session.close()
        
        if self.engine:
            self.engine.dispose()

    def discover_accounts(self, email_override: Optional[str] = None) -> List[str]:
        """
        Discover email accounts from existing data and environment variables.
        
        Args:
            email_override: Override email address to use instead of environment discovery
            
        Returns:
            List of unique email addresses discovered
        """
        discovered_emails = set()
        
        # 1. Use override email if provided
        if email_override:
            discovered_emails.add(email_override)
            self.logger.info(f"Using override email: {email_override}")
        
        # 2. Check environment variables
        gmail_email = os.getenv('GMAIL_EMAIL')
        if gmail_email:
            discovered_emails.add(gmail_email)
            self.logger.info(f"Found GMAIL_EMAIL environment variable: {gmail_email}")
        
        summary_recipient = os.getenv('SUMMARY_RECIPIENT_EMAIL')
        if summary_recipient:
            discovered_emails.add(summary_recipient)
            self.logger.info(f"Found SUMMARY_RECIPIENT_EMAIL environment variable: {summary_recipient}")
        
        # 3. Check if there are existing accounts in the database
        existing_accounts = self.session.query(EmailAccount).all()
        for account in existing_accounts:
            discovered_emails.add(account.email_address)
            self.logger.info(f"Found existing account in database: {account.email_address}")
        
        # 4. If no accounts discovered, check if there's summary data and prompt for email
        if not discovered_emails:
            summary_count = self.session.query(EmailSummary).count()
            if summary_count > 0:
                self.logger.warning(
                    f"Found {summary_count} email summaries but no email accounts could be discovered. "
                    "Please provide an email address using --email parameter."
                )
                return []
        
        result = list(discovered_emails)
        self.logger.info(f"Discovered {len(result)} unique email account(s): {result}")
        return result

    def create_accounts(self, email_addresses: List[str]) -> Dict[str, int]:
        """
        Create EmailAccount records for discovered email addresses.
        
        Args:
            email_addresses: List of email addresses to create accounts for
            
        Returns:
            Dictionary mapping email address to account ID
        """
        account_mapping = {}
        
        for email in email_addresses:
            try:
                # Check if account already exists
                existing_account = self.session.query(EmailAccount).filter_by(
                    email_address=email
                ).first()
                
                if existing_account:
                    account_mapping[email] = existing_account.id
                    self.logger.info(f"Account already exists: {email} (ID: {existing_account.id})")
                    continue
                
                # Create new account
                account = EmailAccount(
                    email_address=email,
                    display_name=email.split('@')[0].title(),  # Simple display name
                    is_active=True,
                    created_at=datetime.now(UTC)
                )
                
                if not self.dry_run:
                    self.session.add(account)
                    self.session.flush()  # Get the ID without committing
                    account_id = account.id
                else:
                    account_id = 999  # Placeholder for dry run
                
                account_mapping[email] = account_id
                self.logger.info(f"{'DRY RUN: Would create' if self.dry_run else 'Created'} account: {email} (ID: {account_id})")
                
            except IntegrityError as e:
                self.logger.error(f"Failed to create account for {email}: {e}")
                self.session.rollback()
                raise
        
        return account_mapping

    def link_summaries_to_accounts(self, account_mapping: Dict[str, int]) -> int:
        """
        Link existing email_summaries records to accounts.
        
        Args:
            account_mapping: Dictionary mapping email address to account ID
            
        Returns:
            Number of summaries updated
        """
        # For single account setups, link all summaries to the primary account
        if len(account_mapping) == 1:
            primary_email = list(account_mapping.keys())[0]
            account_id = account_mapping[primary_email]
            
            # Find summaries that don't have account_id set
            unlinked_summaries = self.session.query(EmailSummary).filter(
                EmailSummary.account_id.is_(None)
            ).all()
            
            updated_count = 0
            for summary in unlinked_summaries:
                if not self.dry_run:
                    summary.account_id = account_id
                updated_count += 1
                
                self.logger.debug(f"{'DRY RUN: Would link' if self.dry_run else 'Linked'} summary ID {summary.id} to account {primary_email}")
            
            self.logger.info(f"{'DRY RUN: Would update' if self.dry_run else 'Updated'} {updated_count} email summaries with account ID {account_id}")
            return updated_count
        
        # Multi-account setup - this is more complex and might require additional logic
        # For now, we'll link all to the first account found
        elif len(account_mapping) > 1:
            self.logger.warning(
                f"Multiple accounts discovered: {list(account_mapping.keys())}. "
                "All existing summaries will be linked to the first account. "
                "Manual review may be needed."
            )
            
            primary_email = list(account_mapping.keys())[0]
            account_id = account_mapping[primary_email]
            
            unlinked_summaries = self.session.query(EmailSummary).filter(
                EmailSummary.account_id.is_(None)
            ).all()
            
            updated_count = 0
            for summary in unlinked_summaries:
                if not self.dry_run:
                    summary.account_id = account_id
                updated_count += 1
            
            self.logger.info(f"{'DRY RUN: Would update' if self.dry_run else 'Updated'} {updated_count} summaries to account {primary_email}")
            return updated_count
        
        else:
            self.logger.warning("No accounts to link summaries to")
            return 0

    def generate_category_stats(self, account_mapping: Dict[str, int]) -> int:
        """
        Generate AccountCategoryStats from existing CategorySummary data.
        
        Args:
            account_mapping: Dictionary mapping email address to account ID
            
        Returns:
            Number of category stats records created
        """
        created_count = 0
        
        for email, account_id in account_mapping.items():
            self.logger.info(f"Generating category stats for account: {email} (ID: {account_id})")
            
            # Get all summaries for this account that have categories
            summaries_with_categories = self.session.query(EmailSummary).filter(
                EmailSummary.account_id == account_id
            ).join(CategorySummary).all()
            
            # Group by date and category
            stats_data = defaultdict(lambda: defaultdict(lambda: {
                'email_count': 0,
                'deleted_count': 0, 
                'archived_count': 0,
                'kept_count': 0
            }))
            
            for summary in summaries_with_categories:
                summary_date = summary.date.date()  # Convert datetime to date
                
                for category in summary.categories:
                    key = (summary_date, category.category_name)
                    stats = stats_data[summary_date][category.category_name]
                    
                    # Accumulate stats (in case there are multiple summaries per day)
                    stats['email_count'] += category.email_count
                    stats['deleted_count'] += category.deleted_count
                    stats['archived_count'] += category.archived_count
                    
                    # Calculate kept count (total - deleted - archived)
                    kept = category.email_count - category.deleted_count - category.archived_count
                    stats['kept_count'] += max(0, kept)  # Ensure non-negative
            
            # Create AccountCategoryStats records
            for summary_date, categories in stats_data.items():
                for category_name, stats in categories.items():
                    # Check if record already exists
                    existing_stat = self.session.query(AccountCategoryStats).filter_by(
                        account_id=account_id,
                        date=summary_date,
                        category_name=category_name
                    ).first()
                    
                    if existing_stat:
                        self.logger.debug(f"Category stats already exist for {email} on {summary_date} for {category_name}")
                        continue
                    
                    # Create new stat record
                    category_stat = AccountCategoryStats(
                        account_id=account_id,
                        date=summary_date,
                        category_name=category_name,
                        email_count=stats['email_count'],
                        deleted_count=stats['deleted_count'],
                        archived_count=stats['archived_count'],
                        kept_count=stats['kept_count'],
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC)
                    )
                    
                    if not self.dry_run:
                        self.session.add(category_stat)
                    
                    created_count += 1
                    self.logger.debug(
                        f"{'DRY RUN: Would create' if self.dry_run else 'Created'} category stat: "
                        f"{category_name} for {summary_date} (count: {stats['email_count']})"
                    )
        
        self.logger.info(f"{'DRY RUN: Would create' if self.dry_run else 'Created'} {created_count} category statistics records")
        return created_count

    def validate_migration(self) -> bool:
        """
        Validate the migration results.
        
        Returns:
            True if validation passes, False otherwise
        """
        self.logger.info("Validating migration results...")
        
        try:
            # Check 1: All email_summaries should have account_id
            unlinked_summaries = self.session.query(EmailSummary).filter(
                EmailSummary.account_id.is_(None)
            ).count()
            
            if unlinked_summaries > 0:
                self.logger.error(f"Validation failed: {unlinked_summaries} summaries still have null account_id")
                return False
            
            # Check 2: AccountCategoryStats should have data
            category_stats_count = self.session.query(AccountCategoryStats).count()
            if category_stats_count == 0:
                # This might be OK if there are no categories in the historical data
                category_summaries_count = self.session.query(CategorySummary).count()
                if category_summaries_count > 0:
                    self.logger.error("Validation failed: No category stats created but category summaries exist")
                    return False
                else:
                    self.logger.info("No category statistics expected (no historical category data)")
            
            # Check 3: Account counts
            accounts_count = self.session.query(EmailAccount).count()
            summaries_count = self.session.query(EmailSummary).count()
            
            self.logger.info(f"Validation summary:")
            self.logger.info(f"  - Email accounts: {accounts_count}")
            self.logger.info(f"  - Email summaries: {summaries_count}")
            self.logger.info(f"  - Category statistics: {category_stats_count}")
            self.logger.info(f"  - Unlinked summaries: {unlinked_summaries}")
            
            # Check 4: Data consistency
            for account in self.session.query(EmailAccount).all():
                summaries_for_account = self.session.query(EmailSummary).filter_by(
                    account_id=account.id
                ).count()
                
                stats_for_account = self.session.query(AccountCategoryStats).filter_by(
                    account_id=account.id
                ).count()
                
                self.logger.info(f"  - Account {account.email_address}: {summaries_for_account} summaries, {stats_for_account} category stats")
            
            self.logger.info("Migration validation passed!")
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed with error: {e}")
            return False

    def run_migration(self, email_override: Optional[str] = None) -> bool:
        """
        Run the complete migration process.
        
        Args:
            email_override: Override email address to use
            
        Returns:
            True if migration successful, False otherwise
        """
        try:
            self.logger.info("Starting account data backfill migration...")
            
            # Step 1: Discover accounts
            email_addresses = self.discover_accounts(email_override)
            if not email_addresses:
                self.logger.error("No email accounts could be discovered. Cannot proceed with migration.")
                return False
            
            # Step 2: Create accounts
            account_mapping = self.create_accounts(email_addresses)
            if not account_mapping:
                self.logger.error("Failed to create any accounts. Migration aborted.")
                return False
            
            # Step 3: Link summaries to accounts
            updated_summaries = self.link_summaries_to_accounts(account_mapping)
            
            # Step 4: Generate category statistics
            created_stats = self.generate_category_stats(account_mapping)
            
            # Step 5: Validate migration
            if not self.dry_run:
                if not self.validate_migration():
                    self.logger.error("Migration validation failed. Rolling back...")
                    self.session.rollback()
                    return False
            
            self.logger.info("Migration completed successfully!")
            self.logger.info(f"Summary:")
            self.logger.info(f"  - Accounts created/found: {len(account_mapping)}")
            self.logger.info(f"  - Summaries linked: {updated_summaries}")
            self.logger.info(f"  - Category stats created: {created_stats}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            self.session.rollback()
            raise


def main():
    """Main entry point for the backfill script."""
    parser = argparse.ArgumentParser(
        description="Backfill existing email_summaries data for account tracking system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Dry run to see what would be changed
    python3 scripts/backfill_account_data.py --dry-run
    
    # Run migration with specific email
    python3 scripts/backfill_account_data.py --email user@gmail.com
    
    # Run with custom database location
    python3 scripts/backfill_account_data.py --database ./custom/summaries.db
    
    # Verbose output
    python3 scripts/backfill_account_data.py --verbose
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making changes'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--database', '--db',
        default='./email_summaries/summaries.db',
        help='Path to the SQLite database file (default: ./email_summaries/summaries.db)'
    )
    
    parser.add_argument(
        '--email',
        help='Gmail email address to use for account creation (overrides environment variables)'
    )
    
    args = parser.parse_args()
    
    # Verify database file exists
    if not os.path.exists(args.database):
        print(f"Error: Database file does not exist: {args.database}", file=sys.stderr)
        return 1
    
    try:
        with BackfillMigrator(args.database, args.dry_run, args.verbose) as migrator:
            success = migrator.run_migration(args.email)
            return 0 if success else 1
            
    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())