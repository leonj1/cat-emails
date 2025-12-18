"""
SQLAlchemy implementation of DatabaseRepositoryInterface.

This concrete implementation uses SQLAlchemy ORM to interact with SQLite databases
(both local file-based and remote SQLite Cloud).
"""
import os
from typing import List, Dict, Optional, Any, TypeVar, Type
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, and_, func, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from repositories.database_repository_interface import DatabaseRepositoryInterface
from models.database import (
    Base, EmailAccount, EmailSummary, CategorySummary, SenderSummary,
    DomainSummary, ProcessingRun, UserSettings, AccountCategoryStats,
    ProcessedEmailLog, get_database_url, init_database
)
from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class SQLAlchemyRepository(DatabaseRepositoryInterface):
    """SQLAlchemy-based repository implementation"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize repository with optional database path.
        
        Args:
            db_path: Database path or connection string. If not provided,
                     must be set via DATABASE_PATH environment variable.
        """
        self.db_path = db_path
        self.engine = None
        self.SessionFactory = None
        self._session: Optional[Session] = None
        
        if db_path:
            self.connect(db_path)
    
    # ==================== Connection Management ====================
    
    def connect(self, db_path: Optional[str] = None) -> None:
        """Initialize database connection"""
        if db_path:
            self.db_path = db_path
        
        if not self.db_path:
            env_db_path = os.getenv("DATABASE_PATH")
            if env_db_path and env_db_path.strip():
                self.db_path = env_db_path
            else:
                msg = (
                    "Database path must be provided either via constructor parameter or "
                    "DATABASE_PATH environment variable. No fallback path is configured."
                )
                raise ValueError(msg)
        
        try:
            self.engine = init_database(self.db_path)
            self.SessionFactory = sessionmaker(bind=self.engine)
            logger.info(f"Database repository connected to: {self.db_path}")
        except Exception as e:
            logger.exception("Failed to connect to database: %s", e)
            msg = f"Failed to connect to database: {e!s}"
            raise ConnectionError(msg) from e
    
    def disconnect(self) -> None:
        """Close database connection"""
        if self._session:
            self._session.close()
            self._session = None
        
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.SessionFactory = None
            logger.info("Database repository disconnected")
    
    def is_connected(self) -> bool:
        """Check if repository is connected"""
        return self.engine is not None and self.SessionFactory is not None

    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status information"""
        if not self.engine or not self.SessionFactory:
            return {
                "connected": False,
                "status": "Not connected - database not initialized",
                "error": "Repository not connected. Call connect() first.",
                "details": {
                    "db_path": self.db_path,
                    "engine_initialized": self.engine is not None,
                    "session_factory_initialized": self.SessionFactory is not None
                }
            }

        # Try to execute a simple query to verify connection
        try:
            session = self._get_session()
            # Execute a simple query to test connection
            session.execute(text("SELECT 1"))
            return {
                "connected": True,
                "status": "Connected and operational",
                "error": None,
                "details": {
                    "db_path": self.db_path,
                    "engine_initialized": True,
                    "session_factory_initialized": True
                }
            }
        except Exception as e:
            logger.exception("Database connection test failed: %s", e)
            return {
                "connected": False,
                "status": "Connection test failed",
                "error": str(e),
                "details": {
                    "db_path": self.db_path,
                    "engine_initialized": self.engine is not None,
                    "session_factory_initialized": self.SessionFactory is not None
                }
            }
    
    def _get_session(self) -> Session:
        """Get or create a session"""
        if not self.is_connected():
            msg = "Repository not connected. Call connect() first."
            raise ConnectionError(msg)
        
        # Use existing session or create new one
        if self._session is None:
            self._session = self.SessionFactory()
        
        return self._session
    
    # ==================== Generic CRUD Operations ====================
    
    def add(self, entity: T) -> T:
        """Add a new entity to the database"""
        session = self._get_session()
        try:
            session.add(entity)
            session.commit()
            session.refresh(entity)
        except IntegrityError as e:
            session.rollback()
            logger.exception("Integrity error adding entity: %s", e)
            raise
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Database error adding entity: %s", e)
            raise
        else:
            return entity
    
    def add_all(self, entities: List[T]) -> List[T]:
        """Add multiple entities in a single transaction"""
        session = self._get_session()
        try:
            session.add_all(entities)
            session.commit()
            for entity in entities:
                session.refresh(entity)
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Database error adding entities: %s", e)
            raise
        else:
            return entities
    
    def get_by_id(self, model_class: Type[T], entity_id: Any) -> Optional[T]:
        """Get entity by primary key ID"""
        session = self._get_session()
        return session.query(model_class).get(entity_id)
    
    def find_one(self, model_class: Type[T], **filters) -> Optional[T]:
        """Find a single entity matching filters"""
        session = self._get_session()
        return session.query(model_class).filter_by(**filters).first()
    
    def find_all(self, model_class: Type[T], **filters) -> List[T]:
        """Find all entities matching filters"""
        session = self._get_session()
        return session.query(model_class).filter_by(**filters).all()
    
    def update(self, entity: T) -> T:
        """Update an existing entity"""
        session = self._get_session()
        try:
            session.merge(entity)
            session.commit()
            session.refresh(entity)
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Database error updating entity: %s", e)
            raise
        else:
            return entity
    
    def delete(self, entity: T) -> None:
        """Delete an entity from database"""
        session = self._get_session()
        try:
            session.delete(entity)
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Database error deleting entity: %s", e)
            raise
    
    def delete_by_id(self, model_class: Type[T], entity_id: Any) -> bool:
        """Delete entity by primary key ID"""
        entity = self.get_by_id(model_class, entity_id)
        if entity:
            self.delete(entity)
            return True
        return False
    
    def count(self, model_class: Type[T], **filters) -> int:
        """Count entities matching filters"""
        session = self._get_session()
        return session.query(model_class).filter_by(**filters).count()
    
    # ==================== Processing Run Operations ====================
    
    def create_processing_run(self, email_address: str) -> str:
        """Start a new email processing run"""
        session = self._get_session()
        try:
            run = ProcessingRun(
                email_address=email_address,
                start_time=datetime.utcnow(),
                state='started'
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return f"run-{run.id}"
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Error creating processing run: %s", e)
            raise
    
    def get_processing_run(self, run_id: str) -> Optional[ProcessingRun]:
        """Get processing run by ID"""
        numeric_id = int(run_id.replace('run-', ''))
        return self.get_by_id(ProcessingRun, numeric_id)
    
    def update_processing_run(self, run_id: str, **updates) -> None:
        """Update processing run with new data"""
        run = self.get_processing_run(run_id)
        if run:
            session = self._get_session()
            try:
                for key, value in updates.items():
                    setattr(run, key, value)
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                logger.exception("Error updating processing run: %s", e)
                raise
    
    def complete_processing_run(
        self, 
        run_id: str, 
        metrics: Dict[str, int],
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """Mark processing run as complete with final metrics"""
        run = self.get_processing_run(run_id)
        if run:
            session = self._get_session()
            try:
                run.end_time = datetime.utcnow()
                run.emails_processed = metrics.get('processed', 0)
                run.state = 'completed' if success else 'error'
                run.error_message = error_message
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                logger.exception("Error completing processing run: %s", e)
                raise
    
    def get_recent_processing_runs(self, limit: int = 10, email_address: Optional[str] = None) -> List[ProcessingRun]:
        """Get recent processing runs"""
        session = self._get_session()
        query = session.query(ProcessingRun)
        
        if email_address:
            query = query.filter_by(email_address=email_address)
        
        return query.order_by(ProcessingRun.start_time.desc()).limit(limit).all()
    
    # ==================== Email Summary Operations ====================
    
    def save_email_summary(self, summary_data: Dict, account_id: Optional[int] = None) -> EmailSummary:
        """Save email processing summary with categories and senders"""
        session = self._get_session()
        try:
            # Create main summary
            summary = EmailSummary(
                account_id=account_id,
                date=datetime.utcnow(),
                total_emails_processed=summary_data['total_processed'],
                total_emails_deleted=summary_data['total_deleted'],
                total_emails_archived=summary_data['total_archived'],
                total_emails_skipped=summary_data.get('total_skipped', 0),
                processing_duration_seconds=summary_data.get('processing_duration', 0),
                scan_interval_hours=summary_data.get('scan_hours', 0)
            )
            
            # Add category summaries
            for category, stats in summary_data.get('categories', {}).items():
                cat_summary = CategorySummary(
                    category_name=category,
                    email_count=stats['count'],
                    deleted_count=stats.get('deleted', 0),
                    archived_count=stats.get('archived', 0)
                )
                summary.categories.append(cat_summary)
            
            # Add sender summaries
            for sender, count in summary_data.get('senders', {}).items():
                sender_summary = SenderSummary(
                    sender_email=sender,
                    email_count=count
                )
                summary.senders.append(sender_summary)
            
            # Add domain summaries
            for domain, stats in summary_data.get('domains', {}).items():
                domain_summary = DomainSummary(
                    domain=domain,
                    email_count=stats['count'],
                    deleted_count=stats.get('deleted', 0),
                    archived_count=stats.get('archived', 0),
                    is_blocked=stats.get('is_blocked', False)
                )
                summary.domains.append(domain_summary)
            
            session.add(summary)
            session.commit()
            session.refresh(summary)
            return summary
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Error saving email summary: %s", e)
            raise
    
    def get_summaries_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        account_id: Optional[int] = None
    ) -> List[EmailSummary]:
        """Get email summaries within date range"""
        session = self._get_session()
        query = session.query(EmailSummary).filter(
            and_(
                EmailSummary.date >= start_date,
                EmailSummary.date <= end_date
            )
        )
        
        if account_id is not None:
            query = query.filter_by(account_id=account_id)
        
        return query.order_by(EmailSummary.date.desc()).all()
    
    # ==================== Account Operations ====================
    
    def get_account_by_email(self, email_address: str) -> Optional[EmailAccount]:
        """Get email account by email address"""
        return self.find_one(EmailAccount, email_address=email_address)
    
    def get_all_accounts(self, active_only: bool = False) -> List[EmailAccount]:
        """Get all email accounts"""
        session = self._get_session()
        query = session.query(EmailAccount)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        return query.order_by(EmailAccount.email_address).all()
    
    def create_or_update_account(
        self, 
        email_address: str,
        gmail_app_password: Optional[str] = None,
        **kwargs
    ) -> EmailAccount:
        """Create new account or update existing one"""
        account = self.get_account_by_email(email_address)
        session = self._get_session()
        
        try:
            if account:
                # Update existing account
                if gmail_app_password is not None:
                    account.gmail_app_password = gmail_app_password
                for key, value in kwargs.items():
                    if hasattr(account, key):
                        setattr(account, key, value)
                account.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(account)
            else:
                # Create new account
                account = EmailAccount(
                    email_address=email_address,
                    gmail_app_password=gmail_app_password,
                    **kwargs
                )
                session.add(account)
                session.commit()
                session.refresh(account)
            
            return account
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Error creating/updating account: %s", e)
            raise
    
    def deactivate_account(self, email_address: str) -> bool:
        """Deactivate an email account"""
        account = self.get_account_by_email(email_address)
        if account:
            session = self._get_session()
            try:
                account.is_active = False
                account.updated_at = datetime.utcnow()
                session.commit()
                return True
            except SQLAlchemyError as e:
                session.rollback()
                logger.exception("Error deactivating account: %s", e)
                raise
        return False
    
    def delete_account(self, email_address: str) -> bool:
        """Delete account and all related data"""
        account = self.get_account_by_email(email_address)
        if account:
            self.delete(account)
            return True
        return False
    
    # ==================== Settings Operations ====================
    
    def get_setting(self, key: str) -> Optional[UserSettings]:
        """Get setting by key"""
        return self.find_one(UserSettings, setting_key=key)
    
    def set_setting(self, key: str, value: str, setting_type: str = 'string', description: str = '') -> UserSettings:
        """Create or update a setting"""
        setting = self.get_setting(key)
        session = self._get_session()
        
        try:
            if setting:
                setting.setting_value = value
                setting.setting_type = setting_type
                if description:
                    setting.description = description
                setting.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(setting)
            else:
                setting = UserSettings(
                    setting_key=key,
                    setting_value=value,
                    setting_type=setting_type,
                    description=description
                )
                session.add(setting)
                session.commit()
                session.refresh(setting)
            
            return setting
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Error setting value: %s", e)
            raise
    
    def get_all_settings(self) -> List[UserSettings]:
        """Get all settings"""
        return self.find_all(UserSettings)
    
    # ==================== Category Statistics Operations ====================
    
    def get_account_category_stats(
        self, 
        account_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[AccountCategoryStats]:
        """Get category statistics for account"""
        session = self._get_session()
        query = session.query(AccountCategoryStats).filter_by(account_id=account_id)
        
        if start_date:
            query = query.filter(AccountCategoryStats.processing_date >= start_date)
        if end_date:
            query = query.filter(AccountCategoryStats.processing_date <= end_date)
        
        return query.all()
    
    def update_account_category_stats(
        self,
        account_id: int,
        category_name: str,
        count_increment: int = 1,
        processing_date: Optional[date] = None
    ) -> AccountCategoryStats:
        """Update or create category statistics for account"""
        if processing_date is None:
            processing_date = date.today()
        
        session = self._get_session()
        
        try:
            # Try to find existing stat
            stat = session.query(AccountCategoryStats).filter_by(
                account_id=account_id,
                category_name=category_name,
                processing_date=processing_date
            ).first()

            if stat:
                stat.email_count += count_increment
                stat.updated_at = datetime.utcnow()
            else:
                stat = AccountCategoryStats(
                    account_id=account_id,
                    category_name=category_name,
                    email_count=count_increment,
                    processing_date=processing_date
                )
                session.add(stat)
            
            session.commit()
            session.refresh(stat)
            return stat
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Error updating category stats: %s", e)
            raise
    
    # ==================== Deduplication Operations ====================
    
    def is_email_processed(self, email_address: str, message_id: str) -> bool:
        """Check if email has been processed already"""
        count = self.count(ProcessedEmailLog, account_email=email_address, message_id=message_id)
        return count > 0
    
    def mark_email_processed(
        self,
        email_address: str,
        message_id: str,
        category: Optional[str] = None,
        action_taken: Optional[str] = None
    ) -> ProcessedEmailLog:
        """Mark email as processed to prevent duplicate processing"""
        session = self._get_session()

        try:
            record = ProcessedEmailLog(
                account_email=email_address,
                message_id=message_id,
                processed_at=datetime.utcnow()
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record
        except IntegrityError:
            # Already exists, that's fine
            session.rollback()
            return self.find_one(ProcessedEmailLog, account_email=email_address, message_id=message_id)
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Error marking email as processed: %s", e)
            raise
    
    def get_processed_emails_count(
        self,
        email_address: str,
        since: Optional[datetime] = None
    ) -> int:
        """Get count of processed emails"""
        session = self._get_session()
        query = session.query(ProcessedEmailLog).filter_by(account_email=email_address)

        if since:
            query = query.filter(ProcessedEmailLog.processed_at >= since)

        return query.count()
    
    def cleanup_old_processed_emails(
        self,
        days_to_keep: int = 30,
        email_address: Optional[str] = None
    ) -> int:
        """Delete old processed email records"""
        session = self._get_session()
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        try:
            query = session.query(ProcessedEmailLog).filter(
                ProcessedEmailLog.processed_at < cutoff_date
            )

            if email_address:
                query = query.filter_by(account_email=email_address)
            
            deleted_count = query.delete()
            session.commit()
            return deleted_count
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Error cleaning up old records: %s", e)
            raise
    
    # ==================== OAuth Token Operations ====================

    def update_account_oauth_tokens(
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
            email_address: Account email address
            refresh_token: Long-lived refresh token
            access_token: Short-lived access token
            token_expiry: When the access token expires
            scopes: List of granted OAuth scopes

        Returns:
            Updated EmailAccount or None if not found
        """
        import json

        account = self.get_account_by_email(email_address)
        if not account:
            logger.warning(f"Account not found for OAuth update: {email_address}")
            return None

        session = self._get_session()
        try:
            account.auth_method = 'oauth'
            account.oauth_refresh_token = refresh_token
            account.oauth_access_token = access_token
            account.oauth_token_expiry = token_expiry
            account.oauth_scopes = json.dumps(scopes)
            account.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(account)
            logger.info(f"Updated OAuth tokens for account: {email_address}")
            return account
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Error updating OAuth tokens: %s", e)
            raise

    def get_account_oauth_tokens(self, email_address: str) -> Optional[Dict[str, Any]]:
        """
        Get OAuth tokens for an account.

        Args:
            email_address: Account email address

        Returns:
            Dict with OAuth token data or None if not found/not OAuth
        """
        import json

        account = self.get_account_by_email(email_address)
        if not account:
            return None

        if account.auth_method != 'oauth':
            return None

        scopes = []
        if account.oauth_scopes:
            try:
                scopes = json.loads(account.oauth_scopes)
            except json.JSONDecodeError:
                scopes = []

        return {
            'email_address': account.email_address,
            'auth_method': account.auth_method,
            'refresh_token': account.oauth_refresh_token,
            'access_token': account.oauth_access_token,
            'token_expiry': account.oauth_token_expiry,
            'scopes': scopes,
            'client_id': account.oauth_client_id,
            'client_secret': account.oauth_client_secret,
        }

    def clear_account_oauth_tokens(self, email_address: str) -> bool:
        """
        Clear OAuth tokens for an account (revoke OAuth access).

        Args:
            email_address: Account email address

        Returns:
            True if tokens were cleared, False if account not found
        """
        account = self.get_account_by_email(email_address)
        if not account:
            return False

        session = self._get_session()
        try:
            account.auth_method = 'imap'
            account.oauth_refresh_token = None
            account.oauth_access_token = None
            account.oauth_token_expiry = None
            account.oauth_scopes = None
            account.updated_at = datetime.utcnow()
            session.commit()
            logger.info(f"Cleared OAuth tokens for account: {email_address}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Error clearing OAuth tokens: %s", e)
            raise

    def update_account_access_token(
        self,
        email_address: str,
        access_token: str,
        token_expiry: datetime,
    ) -> bool:
        """
        Update just the access token for an account (after refresh).

        Args:
            email_address: Account email address
            access_token: New short-lived access token
            token_expiry: When the access token expires

        Returns:
            True if updated, False if account not found
        """
        account = self.get_account_by_email(email_address)
        if not account:
            return False

        session = self._get_session()
        try:
            account.oauth_access_token = access_token
            account.oauth_token_expiry = token_expiry
            account.updated_at = datetime.utcnow()
            session.commit()
            logger.debug(f"Updated access token for account: {email_address}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception("Error updating access token: %s", e)
            raise

    # ==================== Transaction Management ====================

    def begin_transaction(self) -> None:
        """Start a new transaction"""
        session = self._get_session()
        session.begin()

    def commit_transaction(self) -> None:
        """Commit current transaction"""
        session = self._get_session()
        session.commit()

    def rollback_transaction(self) -> None:
        """Rollback current transaction"""
        session = self._get_session()
        session.rollback()
