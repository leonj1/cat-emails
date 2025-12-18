"""
Service for managing account and category statistics.
Handles business logic for account management and email category tracking.
"""
import logging
from utils.logger import get_logger
import re
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from sqlalchemy import create_engine, func, and_, or_
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

from clients.account_category_client_interface import AccountCategoryClientInterface
from models.database import (
    Base, EmailAccount, AccountCategoryStats, get_database_url, init_database
)
from models.account_models import (
    TopCategoriesResponse, CategoryStats, DatePeriod,
    EmailAccountInfo, AccountListResponse
)
from repositories.database_repository_interface import DatabaseRepositoryInterface
from repositories.mysql_repository import MySQLRepository

logger = get_logger(__name__)


class AccountCategoryClient(AccountCategoryClientInterface):
    """Client for managing email accounts and category statistics."""

    def __init__(self, repository: Optional[DatabaseRepositoryInterface] = None, 
                 db_session: Optional[Session] = None, db_path: Optional[str] = None):
        """
        Initialize the AccountCategoryClient with dependency injection.
        
        Args:
            repository: Optional repository implementation. Takes priority over other options
            db_session: Optional existing database session (legacy, for backward compatibility)
            db_path: Path to the database file (legacy parameter, not used with MySQL)
        """
        if repository:
            # Use injected repository - treat it as session-owning source
            self.repository = repository
            self.session = None
            self.owns_session = True  # Repository owns session creation
            self.owns_repository = False
            self.engine = getattr(repository, 'engine', None)
            self.Session = getattr(repository, 'SessionFactory', None)
        elif db_session:
            # Legacy: Direct session injection (creates a wrapper repository internally)
            self.repository = None  # Not using repository pattern in this mode
            self.session = db_session
            self.owns_session = False
            self.owns_repository = False
            self.engine = None
            self.Session = None
        else:
            # Create default MySQL repository
            self.repository = MySQLRepository()
            self.session = None
            self.owns_session = True
            self.owns_repository = True
            self.engine = getattr(self.repository, 'engine', None)
            self.Session = getattr(self.repository, 'SessionFactory', None)
        
        logger.info("AccountCategoryClient initialized")
    
    def close(self) -> None:
        """Close repository connection if owned by this client."""
        if getattr(self, 'owns_repository', False) and self.repository:
            if hasattr(self.repository, 'disconnect'):
                self.repository.disconnect()
                logger.info("Closed owned repository connection")

    
    def _get_session(self) -> Session:
        """Get a database session (either provided or create new one)."""
        if self.session:
            return self.session
        elif self.Session:
            return self.Session()
        else:
            raise ValueError("No database session available")
    
    def _detach_account(self, account: EmailAccount) -> EmailAccount:
        """
        Create a detached copy of an EmailAccount to avoid lazy loading issues.

        Args:
            account: Session-bound EmailAccount object

        Returns:
            New EmailAccount object with copied attributes
        """
        return EmailAccount(
            id=account.id,
            email_address=account.email_address,
            display_name=account.display_name,
            app_password=account.app_password,
            is_active=account.is_active,
            last_scan_at=account.last_scan_at,
            created_at=account.created_at,
            updated_at=account.updated_at,
            auth_method=account.auth_method,
            oauth_client_id=account.oauth_client_id,
            oauth_client_secret=account.oauth_client_secret,
            oauth_refresh_token=account.oauth_refresh_token,
            oauth_access_token=account.oauth_access_token,
            oauth_token_expiry=account.oauth_token_expiry,
            oauth_scopes=account.oauth_scopes,
        )

    def _validate_email_address(self, email_address: str) -> str:
        """
        Validate email address format.

        Args:
            email_address: Email address to validate

        Returns:
            Normalized email address (lowercase)

        Raises:
            ValueError: If email format is invalid
        """
        if not email_address or not isinstance(email_address, str):
            raise ValueError("Email address must be a non-empty string")

        # Basic email validation regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email_address.strip()):
            raise ValueError(f"Invalid email address format: {email_address}")

        return email_address.strip().lower()
    
    def get_or_create_account(
        self,
        email_address: str,
        display_name: Optional[str] = None,
        app_password: Optional[str] = None,
        auth_method: str = "imap",
        oauth_refresh_token: Optional[str] = None,
    ) -> EmailAccount:
        """
        Get existing account or create a new one.

        Args:
            email_address: Gmail email address
            display_name: Optional display name for the account
            app_password: Optional Gmail app-specific password for IMAP access
            auth_method: Authentication method ('imap' or 'oauth')
            oauth_refresh_token: OAuth refresh token (required if auth_method is 'oauth')

        Returns:
            EmailAccount object (existing or newly created)

        Raises:
            ValueError: If email address is invalid
        """
        email_address = self._validate_email_address(email_address)

        try:
            if self.owns_session:
                with self._get_session() as session:
                    return self._get_or_create_account_impl(
                        session, email_address, display_name, app_password,
                        auth_method, oauth_refresh_token
                    )
            else:
                return self._get_or_create_account_impl(
                    self.session, email_address, display_name, app_password,
                    auth_method, oauth_refresh_token
                )
        except Exception as e:
            logger.error(f"Error in get_or_create_account for {email_address}: {str(e)}")
            raise
    
    def _get_or_create_account_impl(
        self,
        session: Session,
        email_address: str,
        display_name: Optional[str],
        app_password: Optional[str],
        auth_method: str = "imap",
        oauth_refresh_token: Optional[str] = None,
    ) -> EmailAccount:
        """Implementation of get_or_create_account that works with a session."""
        try:
            # Try to get existing account
            account = session.query(EmailAccount).filter_by(email_address=email_address).first()

            if account:
                # Update existing account
                updated = False
                if display_name and display_name != account.display_name:
                    account.display_name = display_name
                    updated = True
                if app_password and app_password != account.app_password:
                    account.app_password = app_password
                    updated = True
                if auth_method and auth_method != account.auth_method:
                    account.auth_method = auth_method
                    updated = True
                if oauth_refresh_token and oauth_refresh_token != account.oauth_refresh_token:
                    account.oauth_refresh_token = oauth_refresh_token
                    updated = True
                if not account.is_active:
                    account.is_active = True
                    updated = True
                if updated:
                    account.updated_at = datetime.utcnow()
                    session.commit()
                    logger.info(f"Updated existing account: {email_address}")

                # For owns_session=True, detach from session to avoid lazy loading issues
                if self.owns_session:
                    return self._detach_account(account)
                else:
                    return account
            else:
                # Create new account
                account = EmailAccount(
                    email_address=email_address,
                    display_name=display_name,
                    app_password=app_password,
                    auth_method=auth_method,
                    oauth_refresh_token=oauth_refresh_token,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(account)
                session.commit()
                logger.info(f"Created new account: {email_address}")

                # For owns_session=True, detach from session to avoid lazy loading issues
                if self.owns_session:
                    return self._detach_account(account)
                else:
                    return account

        except IntegrityError as e:
            session.rollback()
            logger.error(f"Database integrity error creating account {email_address}: {str(e)}")
            raise ValueError(f"Account creation failed due to database constraint: {str(e)}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error in _get_or_create_account_impl: {str(e)}")
            raise
    
    def get_account_by_email(self, email_address: str) -> Optional[EmailAccount]:
        """
        Retrieve account by email address.

        Args:
            email_address: Gmail email address

        Returns:
            EmailAccount object if found, None otherwise

        Raises:
            ValueError: If email address is invalid
        """
        email_address = self._validate_email_address(email_address)

        try:
            if self.owns_session:
                with self._get_session() as session:
                    account = session.query(EmailAccount).filter_by(email_address=email_address).first()
                    if account:
                        # Detach from session to avoid lazy loading issues
                        return self._detach_account(account)
                    return None
            else:
                return self.session.query(EmailAccount).filter_by(email_address=email_address).first()
        except Exception as e:
            logger.error(f"Error retrieving account {email_address}: {str(e)}")
            raise
    
    def update_account_last_scan(self, email_address: str) -> None:
        """
        Update the last_scan_at timestamp for an account.
        
        Args:
            email_address: Gmail email address
            
        Raises:
            ValueError: If email address is invalid
        """
        email_address = self._validate_email_address(email_address)
        
        try:
            # Get or create account first
            account = self.get_or_create_account(email_address)
            
            if self.owns_session:
                with self._get_session() as session:
                    # Re-query to get account in this session
                    account = session.query(EmailAccount).filter_by(email_address=email_address).first()
                    if account:
                        account.last_scan_at = datetime.utcnow()
                        account.updated_at = datetime.utcnow()
                        session.commit()
                        logger.debug(f"Updated last_scan_at for account: {email_address}")
            else:
                account.last_scan_at = datetime.utcnow()
                account.updated_at = datetime.utcnow()
                self.session.commit()
                logger.debug(f"Updated last_scan_at for account: {email_address}")
                
        except Exception as e:
            logger.error(f"Error updating last_scan_at for {email_address}: {str(e)}")
            raise
    
    def record_category_stats(self, email_address: str, stats_date: date, 
                            category_stats: Dict[str, Dict[str, int]]) -> None:
        """
        Record daily category statistics for an account.
        
        Args:
            email_address: Gmail email address
            stats_date: Date for the statistics
            category_stats: Dictionary with format:
                {"Marketing": {"total": 10, "deleted": 8, "kept": 2, "archived": 0}}
                
        Raises:
            ValueError: If email address is invalid or data format is wrong
        """
        email_address = self._validate_email_address(email_address)
        
        if not isinstance(category_stats, dict):
            raise ValueError("category_stats must be a dictionary")
        
        try:
            # Get or create account
            account = self.get_or_create_account(email_address)
            
            if self.owns_session:
                with self._get_session() as session:
                    self._record_category_stats_impl(session, account.id, stats_date, category_stats)
            else:
                self._record_category_stats_impl(self.session, account.id, stats_date, category_stats)
                
        except Exception as e:
            logger.error(f"Error recording category stats for {email_address}: {str(e)}")
            raise
    
    def _record_category_stats_impl(self, session: Session, account_id: int, 
                                  stats_date: date, category_stats: Dict[str, Dict[str, int]]) -> None:
        """Implementation of record_category_stats that works with a session."""
        try:
            for category_name, stats in category_stats.items():
                if not isinstance(stats, dict):
                    logger.warning(f"Skipping invalid stats for category {category_name}: not a dict")
                    continue
                
                # Extract counts with defaults
                total_count = stats.get('total', 0)
                deleted_count = stats.get('deleted', 0)
                archived_count = stats.get('archived', 0)
                kept_count = stats.get('kept', 0)
                
                # Validate counts
                if total_count < 0 or deleted_count < 0 or archived_count < 0 or kept_count < 0:
                    logger.warning(f"Skipping negative counts for category {category_name}")
                    continue
                
                # Use upsert logic
                existing_stat = session.query(AccountCategoryStats).filter_by(
                    account_id=account_id,
                    date=stats_date,
                    category_name=category_name
                ).first()
                
                if existing_stat:
                    # Update existing record
                    existing_stat.email_count = total_count
                    existing_stat.deleted_count = deleted_count
                    existing_stat.archived_count = archived_count
                    existing_stat.kept_count = kept_count
                    existing_stat.updated_at = datetime.utcnow()
                    logger.debug(f"Updated stats for {category_name} on {stats_date}")
                else:
                    # Create new record
                    new_stat = AccountCategoryStats(
                        account_id=account_id,
                        date=stats_date,
                        category_name=category_name,
                        email_count=total_count,
                        deleted_count=deleted_count,
                        archived_count=archived_count,
                        kept_count=kept_count,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(new_stat)
                    logger.debug(f"Created new stats for {category_name} on {stats_date}")
            
            session.commit()
            logger.info(f"Recorded category stats for account {account_id} on {stats_date}")
            
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Database integrity error recording stats: {str(e)}")
            raise ValueError(f"Failed to record category stats due to database constraint: {str(e)}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error in _record_category_stats_impl: {str(e)}")
            raise
    
    def get_top_categories(self, email_address: str, days: int, 
                          limit: int = 10, include_counts: bool = False) -> TopCategoriesResponse:
        """
        Get top categories for an account over specified days.
        
        Args:
            email_address: Gmail email address
            days: Number of days to look back from today (1-365)
            limit: Maximum number of categories to return (1-50)
            include_counts: Whether to include detailed breakdown counts
            
        Returns:
            TopCategoriesResponse with category statistics
            
        Raises:
            ValueError: If parameters are invalid or account not found
        """
        # Validate inputs
        email_address = self._validate_email_address(email_address)
        
        if not isinstance(days, int) or days < 1 or days > 365:
            raise ValueError("days must be an integer between 1 and 365")
        
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            raise ValueError("limit must be an integer between 1 and 50")
        
        try:
            # Get account
            account = self.get_account_by_email(email_address)
            if not account:
                raise ValueError(f"No account found for email address: {email_address}")
            
            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=days-1)  # -1 because today counts as day 1
            
            if self.owns_session:
                with self._get_session() as session:
                    return self._get_top_categories_impl(
                        session, account.id, email_address, start_date, end_date, days, limit, include_counts
                    )
            else:
                return self._get_top_categories_impl(
                    self.session, account.id, email_address, start_date, end_date, days, limit, include_counts
                )
                
        except Exception as e:
            logger.error(f"Error getting top categories for {email_address}: {str(e)}")
            raise
    
    def _get_top_categories_impl(self, session: Session, account_id: int, email_address: str,
                               start_date: date, end_date: date, days: int, 
                               limit: int, include_counts: bool) -> TopCategoriesResponse:
        """Implementation of get_top_categories that works with a session."""
        try:
            # Query category statistics with aggregation
            query = session.query(
                AccountCategoryStats.category_name,
                func.sum(AccountCategoryStats.email_count).label('total_count'),
                func.sum(AccountCategoryStats.kept_count).label('total_kept'),
                func.sum(AccountCategoryStats.deleted_count).label('total_deleted'),
                func.sum(AccountCategoryStats.archived_count).label('total_archived')
            ).filter(
                and_(
                    AccountCategoryStats.account_id == account_id,
                    AccountCategoryStats.date >= start_date,
                    AccountCategoryStats.date <= end_date
                )
            ).group_by(
                AccountCategoryStats.category_name
            ).order_by(
                func.sum(AccountCategoryStats.email_count).desc()
            ).limit(limit)
            
            results = query.all()
            
            # Calculate totals for percentage calculation
            total_emails = sum(result.total_count for result in results)
            
            # Build category stats
            top_categories = []
            for result in results:
                percentage = (result.total_count / total_emails * 100) if total_emails > 0 else 0.0
                
                category_stat = CategoryStats(
                    category=result.category_name,
                    total_count=result.total_count,
                    percentage=round(percentage, 2)
                )
                
                # Add detailed counts if requested
                if include_counts:
                    category_stat.kept_count = result.total_kept
                    category_stat.deleted_count = result.total_deleted
                    category_stat.archived_count = result.total_archived
                
                top_categories.append(category_stat)
            
            # Create period info
            period = DatePeriod(
                start_date=start_date,
                end_date=end_date,
                days=days
            )
            
            response = TopCategoriesResponse(
                email_address=email_address,
                period=period,
                total_emails=total_emails,
                top_categories=top_categories
            )
            
            logger.info(f"Retrieved top {len(top_categories)} categories for {email_address} "
                       f"over {days} days ({total_emails} total emails)")
            
            return response
            
        except Exception as e:
            logger.error(f"Unexpected error in _get_top_categories_impl: {str(e)}")
            raise
    
    def get_all_accounts(self, active_only: bool = True) -> List[EmailAccount]:
        """
        Get list of all tracked accounts.
        
        Args:
            active_only: Filter to only active accounts
            
        Returns:
            List of EmailAccount objects
        """
        try:
            if self.owns_session:
                with self._get_session() as session:
                    query = session.query(EmailAccount)
                    if active_only:
                        query = query.filter_by(is_active=True)
                    
                    accounts = query.order_by(EmailAccount.email_address).all()
                    # Detach from session to avoid lazy loading issues
                    return [self._detach_account(acc) for acc in accounts]
            else:
                query = self.session.query(EmailAccount)
                if active_only:
                    query = query.filter_by(is_active=True)
                
                return query.order_by(EmailAccount.email_address).all()
                
        except Exception as e:
            logger.error(f"Error retrieving all accounts: {str(e)}")
            raise
    
    def deactivate_account(self, email_address: str) -> bool:
        """
        Mark account as inactive.
        
        Args:
            email_address: Gmail email address
            
        Returns:
            True if account found and deactivated, False otherwise
            
        Raises:
            ValueError: If email address is invalid
        """
        email_address = self._validate_email_address(email_address)
        
        try:
            if self.owns_session:
                with self._get_session() as session:
                    account = session.query(EmailAccount).filter_by(email_address=email_address).first()
                    if account:
                        account.is_active = False
                        account.updated_at = datetime.utcnow()
                        session.commit()
                        logger.info(f"Deactivated account: {email_address}")
                        return True
                    else:
                        logger.warning(f"Account not found for deactivation: {email_address}")
                        return False
            else:
                account = self.session.query(EmailAccount).filter_by(email_address=email_address).first()
                if account:
                    account.is_active = False
                    account.updated_at = datetime.utcnow()
                    self.session.commit()
                    logger.info(f"Deactivated account: {email_address}")
                    return True
                else:
                    logger.warning(f"Account not found for deactivation: {email_address}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deactivating account {email_address}: {str(e)}")
            raise

    def delete_account(self, email_address: str) -> bool:
        """
        Delete account and all associated data.

        Args:
            email_address: Gmail email address

        Returns:
            True if account found and deleted, False otherwise

        Raises:
            ValueError: If email address is invalid
        """
        email_address = self._validate_email_address(email_address)

        try:
            if self.owns_session:
                with self._get_session() as session:
                    account = session.query(EmailAccount).filter_by(email_address=email_address).first()
                    if account:
                        # Delete the account - cascade will handle related records
                        session.delete(account)
                        session.commit()
                        logger.info(f"Deleted account and all associated data: {email_address}")
                        return True
                    else:
                        logger.warning(f"Account not found for deletion: {email_address}")
                        return False
            else:
                account = self.session.query(EmailAccount).filter_by(email_address=email_address).first()
                if account:
                    # Delete the account - cascade will handle related records
                    self.session.delete(account)
                    self.session.commit()
                    logger.info(f"Deleted account and all associated data: {email_address}")
                    return True
                else:
                    logger.warning(f"Account not found for deletion: {email_address}")
                    return False

        except Exception as e:
            logger.error(f"Database error in delete_account: {str(e)}")
            raise

    def update_oauth_tokens(
        self,
        email_address: str,
        refresh_token: str,
        access_token: str,
        token_expiry: datetime,
        scopes: List[str],
    ) -> Optional[EmailAccount]:
        """
        Update OAuth tokens for an account.

        Args:
            email_address: Gmail email address
            refresh_token: Long-lived refresh token
            access_token: Short-lived access token
            token_expiry: When the access token expires
            scopes: List of granted OAuth scopes

        Returns:
            Updated EmailAccount or None if not found
        """
        import json

        email_address = self._validate_email_address(email_address)

        try:
            if self.owns_session:
                with self._get_session() as session:
                    account = session.query(EmailAccount).filter_by(email_address=email_address).first()
                    if not account:
                        logger.warning(f"Account not found for OAuth update: {email_address}")
                        return None

                    account.auth_method = 'oauth'
                    account.oauth_refresh_token = refresh_token
                    account.oauth_access_token = access_token
                    account.oauth_token_expiry = token_expiry
                    account.oauth_scopes = json.dumps(scopes)
                    account.updated_at = datetime.utcnow()
                    session.commit()
                    logger.info(f"Updated OAuth tokens for account: {email_address}")
                    return self._detach_account(account)
            else:
                account = self.session.query(EmailAccount).filter_by(email_address=email_address).first()
                if not account:
                    logger.warning(f"Account not found for OAuth update: {email_address}")
                    return None

                account.auth_method = 'oauth'
                account.oauth_refresh_token = refresh_token
                account.oauth_access_token = access_token
                account.oauth_token_expiry = token_expiry
                account.oauth_scopes = json.dumps(scopes)
                account.updated_at = datetime.utcnow()
                self.session.commit()
                logger.info(f"Updated OAuth tokens for account: {email_address}")
                return account

        except Exception as e:
            logger.error(f"Error updating OAuth tokens for {email_address}: {str(e)}")
            raise

    def get_oauth_status(self, email_address: str) -> Optional[Dict]:
        """
        Get OAuth connection status for an account.

        Args:
            email_address: Gmail email address

        Returns:
            Dict with OAuth status or None if account not found
        """
        import json

        email_address = self._validate_email_address(email_address)

        try:
            account = self.get_account_by_email(email_address)
            if not account:
                return None

            scopes = []
            if account.oauth_scopes:
                try:
                    scopes = json.loads(account.oauth_scopes)
                except json.JSONDecodeError:
                    scopes = []

            return {
                'connected': account.auth_method == 'oauth' and account.oauth_refresh_token is not None,
                'auth_method': account.auth_method or 'imap',
                'scopes': scopes if account.auth_method == 'oauth' else None,
                'token_expiry': account.oauth_token_expiry if account.auth_method == 'oauth' else None,
            }

        except Exception as e:
            logger.error(f"Error getting OAuth status for {email_address}: {str(e)}")
            raise

    def clear_oauth_tokens(self, email_address: str) -> bool:
        """
        Clear OAuth tokens for an account (revoke OAuth access).

        Args:
            email_address: Gmail email address

        Returns:
            True if tokens were cleared, False if account not found
        """
        email_address = self._validate_email_address(email_address)

        try:
            if self.owns_session:
                with self._get_session() as session:
                    account = session.query(EmailAccount).filter_by(email_address=email_address).first()
                    if not account:
                        return False

                    account.auth_method = 'imap'
                    account.oauth_refresh_token = None
                    account.oauth_access_token = None
                    account.oauth_token_expiry = None
                    account.oauth_scopes = None
                    account.updated_at = datetime.utcnow()
                    session.commit()
                    logger.info(f"Cleared OAuth tokens for account: {email_address}")
                    return True
            else:
                account = self.session.query(EmailAccount).filter_by(email_address=email_address).first()
                if not account:
                    return False

                account.auth_method = 'imap'
                account.oauth_refresh_token = None
                account.oauth_access_token = None
                account.oauth_token_expiry = None
                account.oauth_scopes = None
                account.updated_at = datetime.utcnow()
                self.session.commit()
                logger.info(f"Cleared OAuth tokens for account: {email_address}")
                return True

        except Exception as e:
            logger.error(f"Error clearing OAuth tokens for {email_address}: {str(e)}")
            raise


# Example usage and testing
if __name__ == "__main__":
    # Example usage of AccountCategoryClient
    service = AccountCategoryClient()
    
    try:
        # Create/get an account
        account = service.get_or_create_account("test@gmail.com", "Test User")
        print(f"Account created/retrieved: {account.email_address}")
        
        # Record some category stats
        from datetime import date
        today = date.today()
        test_stats = {
            "Marketing": {"total": 10, "deleted": 8, "kept": 2, "archived": 0},
            "Personal": {"total": 5, "deleted": 0, "kept": 5, "archived": 0},
            "Work-related": {"total": 3, "deleted": 1, "kept": 2, "archived": 0}
        }
        
        service.record_category_stats("test@gmail.com", today, test_stats)
        print("Category stats recorded")
        
        # Get top categories
        response = service.get_top_categories("test@gmail.com", days=7, limit=10, include_counts=True)
        print(f"Top categories for {response.email_address}:")
        for category in response.top_categories:
            print(f"  {category.category}: {category.total_count} emails ({category.percentage}%)")
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
    finally:
        if 'service' in locals():
            service.close()
            print("Service closed")
