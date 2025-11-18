"""
MySQL implementation of DatabaseRepositoryInterface.

This concrete implementation uses SQLAlchemy ORM to interact with MySQL databases.
Supports both local MySQL servers and cloud-hosted MySQL (e.g., AWS RDS, Google Cloud SQL, Azure Database).
"""
import os
from typing import List, Dict, Optional, Any, TypeVar, Type
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, and_, func, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.pool import QueuePool

from repositories.database_repository_interface import DatabaseRepositoryInterface
from models.database import (
    Base, EmailAccount, EmailSummary, CategorySummary, SenderSummary,
    DomainSummary, ProcessingRun, UserSettings, AccountCategoryStats,
    ProcessedEmailLog
)
from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class MySQLRepository(DatabaseRepositoryInterface):
    """MySQL-based repository implementation"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        connection_string: Optional[str] = None,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_recycle: int = 3600,
        echo: bool = False
    ):
        """
        Initialize MySQL repository.
        
        Args:
            host: MySQL server host (e.g., 'localhost', '10.0.0.1')
            port: MySQL server port (default: 3306)
            database: Database name
            username: MySQL username
            password: MySQL password
            connection_string: Optional full MySQL connection string (overrides individual params)
                              Format: mysql+pymysql://user:pass@host:port/dbname
            pool_size: Number of connections to keep in pool (default: 5)
            max_overflow: Max connections beyond pool_size (default: 10)
            pool_recycle: Recycle connections after this many seconds (default: 3600)
            echo: Enable SQLAlchemy query logging (default: False)
        
        Environment Variables (used if parameters not provided):
            MYSQL_HOST or DATABASE_HOST
            MYSQL_PORT or DATABASE_PORT
            MYSQL_DATABASE or DATABASE_NAME
            MYSQL_USER or DATABASE_USER
            MYSQL_PASSWORD or DATABASE_PASSWORD
            MYSQL_URL or DATABASE_URL (full connection string)
        """
        self.connection_string = connection_string
        self.host = host
        self.port = port or 3306
        self.database = database
        self.username = username
        self.password = password
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_recycle = pool_recycle
        self.echo = echo
        
        self.engine = None
        self.SessionFactory = None
        self._session: Optional[Session] = None

        # Auto-connect if credentials provided or available in environment
        if connection_string or (host and database and username):
            self.connect()
        else:
            # Try to connect if environment variables are available
            try:
                self.connect()
            except ValueError:
                # No credentials available - this is OK, caller should provide them later
                logger.debug("MySQLRepository initialized without credentials - connect() must be called with credentials")
    
    # ==================== Connection Management ====================
    
    def connect(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        connection_string: Optional[str] = None
    ) -> None:
        """
        Initialize MySQL database connection.
        
        Args:
            host: MySQL server host
            port: MySQL server port
            database: Database name
            username: MySQL username
            password: MySQL password
            connection_string: Optional full connection string
        """
        # Update parameters if provided
        if connection_string:
            self.connection_string = connection_string
        if host:
            self.host = host
        if port:
            self.port = port
        if database:
            self.database = database
        if username:
            self.username = username
        if password:
            self.password = password
        
        # Build connection string
        conn_str = self._build_connection_string()
        
        try:
            # Create engine with connection pooling
            self.engine = create_engine(
                conn_str,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=True,  # Verify connections before using
                echo=self.echo
            )
            
            # Create all tables if they don't exist
            Base.metadata.create_all(self.engine)
            
            self.SessionFactory = sessionmaker(bind=self.engine)
            
            logger.info(f"MySQL repository connected to: {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to MySQL database: {str(e)}")
            raise ConnectionError(f"Failed to connect to MySQL database: {str(e)}") from e
    
    def _build_connection_string(self) -> str:
        """Build MySQL connection string from parameters or environment variables"""
        # Check for full connection string first
        if self.connection_string:
            return self.connection_string
        
        conn_str = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL")
        if conn_str and conn_str.strip():
            return conn_str
        
        # Build from individual parameters
        host = self.host or os.getenv("MYSQL_HOST") or os.getenv("DATABASE_HOST")
        port = self.port or os.getenv("MYSQL_PORT") or os.getenv("DATABASE_PORT") or 3306
        database = self.database or os.getenv("MYSQL_DATABASE") or os.getenv("DATABASE_NAME")
        username = self.username or os.getenv("MYSQL_USER") or os.getenv("DATABASE_USER")
        password = self.password or os.getenv("MYSQL_PASSWORD") or os.getenv("DATABASE_PASSWORD")
        
        # Validate required parameters
        if not all([host, database, username]):
            raise ValueError(
                "MySQL connection requires either:\n"
                "  1. connection_string parameter or MYSQL_URL/DATABASE_URL env var, OR\n"
                "  2. host, database, and username parameters or corresponding env vars:\n"
                "     MYSQL_HOST/DATABASE_HOST, MYSQL_DATABASE/DATABASE_NAME, MYSQL_USER/DATABASE_USER"
            )
        
        # Build connection string
        # Format: mysql+pymysql://user:password@host:port/database
        password_part = f":{password}" if password else ""
        return f"mysql+pymysql://{username}{password_part}@{host}:{port}/{database}"
    
    def disconnect(self) -> None:
        """Close MySQL database connection"""
        if self._session:
            self._session.close()
            self._session = None
        
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.SessionFactory = None
            logger.info("MySQL repository disconnected")
    
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
                    "host": self.host,
                    "port": self.port,
                    "database": self.database,
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
                    "host": self.host,
                    "port": self.port,
                    "database": self.database,
                    "engine_initialized": True,
                    "session_factory_initialized": True,
                    "pool_size": self.pool_size,
                    "max_overflow": self.max_overflow
                }
            }
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return {
                "connected": False,
                "status": "Connection test failed",
                "error": str(e),
                "details": {
                    "host": self.host,
                    "port": self.port,
                    "database": self.database,
                    "engine_initialized": self.engine is not None,
                    "session_factory_initialized": self.SessionFactory is not None
                }
            }
    
    def _get_session(self) -> Session:
        """Get or create a session"""
        if not self.is_connected():
            raise ConnectionError("Repository not connected. Call connect() first.")
        
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
            return entity
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Integrity error adding entity: {str(e)}")
            raise
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error adding entity: {str(e)}")
            raise
    
    def add_all(self, entities: List[T]) -> List[T]:
        """Add multiple entities in a single transaction"""
        session = self._get_session()
        try:
            session.add_all(entities)
            session.commit()
            for entity in entities:
                session.refresh(entity)
            return entities
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error adding entities: {str(e)}")
            raise
    
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
            return entity
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error updating entity: {str(e)}")
            raise
    
    def delete(self, entity: T) -> None:
        """Delete an entity from database"""
        session = self._get_session()
        try:
            session.delete(entity)
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error deleting entity: {str(e)}")
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
            logger.error(f"Error creating processing run: {str(e)}")
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
                logger.error(f"Error updating processing run: {str(e)}")
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
                logger.error(f"Error completing processing run: {str(e)}")
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
            logger.error(f"Error saving email summary: {str(e)}")
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
            logger.error(f"Error creating/updating account: {str(e)}")
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
                logger.error(f"Error deactivating account: {str(e)}")
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
            logger.error(f"Error setting value: {str(e)}")
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
        category: str,
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
                category=category,
                processing_date=processing_date
            ).first()
            
            if stat:
                stat.email_count += count_increment
                stat.updated_at = datetime.utcnow()
            else:
                stat = AccountCategoryStats(
                    account_id=account_id,
                    category=category,
                    email_count=count_increment,
                    processing_date=processing_date
                )
                session.add(stat)
            
            session.commit()
            session.refresh(stat)
            return stat
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating category stats: {str(e)}")
            raise
    
    # ==================== Deduplication Operations ====================
    
    def is_email_processed(self, email_address: str, message_id: str) -> bool:
        """Check if email has been processed already"""
        count = self.count(ProcessedEmailLog, email_address=email_address, message_id=message_id)
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
                email_address=email_address,
                message_id=message_id,
                category=category,
                action_taken=action_taken,
                processed_at=datetime.utcnow()
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record
        except IntegrityError:
            # Already exists, that's fine
            session.rollback()
            return self.find_one(ProcessedEmailLog, email_address=email_address, message_id=message_id)
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error marking email as processed: {str(e)}")
            raise
    
    def get_processed_emails_count(
        self,
        email_address: str,
        since: Optional[datetime] = None
    ) -> int:
        """Get count of processed emails"""
        session = self._get_session()
        query = session.query(ProcessedEmailLog).filter_by(email_address=email_address)
        
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
                query = query.filter_by(email_address=email_address)
            
            deleted_count = query.delete()
            session.commit()
            return deleted_count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error cleaning up old records: {str(e)}")
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
