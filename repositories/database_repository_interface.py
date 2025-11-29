"""
Database repository interface for abstracting data access operations.

This interface follows the Repository Pattern to decouple business logic
from data access implementation, making it easier to:
- Swap database providers (e.g., local SQLite to SQLite Cloud)
- Write unit tests with mock repositories
- Apply consistent data access patterns
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, TypeVar, Type
from datetime import datetime, date

# Generic type for database models
T = TypeVar('T')


class DatabaseRepositoryInterface(ABC):
    """Abstract interface for all database operations"""
    
    # ==================== Connection Management ====================
    
    @abstractmethod
    def connect(self, db_path: Optional[str] = None) -> None:
        """
        Initialize database connection.
        
        Args:
            db_path: Optional database path (or connection string for remote DBs)
        
        Raises:
            ValueError: If connection parameters are invalid
            ConnectionError: If unable to connect to database
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection and cleanup resources"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if repository is connected to database"""
        pass

    @abstractmethod
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed connection status information.

        Returns:
            Dict with keys:
                - connected (bool): Whether database is connected
                - status (str): Human-readable status message
                - error (str, optional): Error message if connection failed
                - details (dict, optional): Additional connection details
        """
        pass
    
    # ==================== Generic CRUD Operations ====================
    
    @abstractmethod
    def add(self, entity: T) -> T:
        """
        Add a new entity to the database.
        
        Args:
            entity: Database model instance to add
            
        Returns:
            The added entity with ID populated
            
        Raises:
            IntegrityError: If unique constraints are violated
        """
        pass
    
    @abstractmethod
    def add_all(self, entities: List[T]) -> List[T]:
        """
        Add multiple entities in a single transaction.
        
        Args:
            entities: List of database model instances
            
        Returns:
            List of added entities with IDs populated
        """
        pass
    
    @abstractmethod
    def get_by_id(self, model_class: Type[T], entity_id: Any) -> Optional[T]:
        """
        Get entity by primary key ID.
        
        Args:
            model_class: The model class to query
            entity_id: Primary key value
            
        Returns:
            Entity instance or None if not found
        """
        pass
    
    @abstractmethod
    def find_one(self, model_class: Type[T], **filters) -> Optional[T]:
        """
        Find a single entity matching filters.
        
        Args:
            model_class: The model class to query
            **filters: Column name/value pairs to filter by
            
        Returns:
            First matching entity or None
        """
        pass
    
    @abstractmethod
    def find_all(self, model_class: Type[T], **filters) -> List[T]:
        """
        Find all entities matching filters.
        
        Args:
            model_class: The model class to query
            **filters: Column name/value pairs to filter by
            
        Returns:
            List of matching entities (empty list if none found)
        """
        pass
    
    @abstractmethod
    def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: Entity instance with modified fields
            
        Returns:
            Updated entity
        """
        pass
    
    @abstractmethod
    def delete(self, entity: T) -> None:
        """
        Delete an entity from database.
        
        Args:
            entity: Entity instance to delete
        """
        pass
    
    @abstractmethod
    def delete_by_id(self, model_class: Type[T], entity_id: Any) -> bool:
        """
        Delete entity by primary key ID.
        
        Args:
            model_class: The model class
            entity_id: Primary key value
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    def count(self, model_class: Type[T], **filters) -> int:
        """
        Count entities matching filters.
        
        Args:
            model_class: The model class to query
            **filters: Column name/value pairs to filter by
            
        Returns:
            Count of matching entities
        """
        pass
    
    # ==================== Processing Run Operations ====================
    
    @abstractmethod
    def create_processing_run(self, email_address: str) -> str:
        """
        Start a new email processing run.
        
        Args:
            email_address: Email account being processed
            
        Returns:
            Processing run ID (format: 'run-<id>')
        """
        pass
    
    @abstractmethod
    def get_processing_run(self, run_id: str) -> Optional[Any]:
        """Get processing run by ID"""
        pass
    
    @abstractmethod
    def update_processing_run(self, run_id: str, **updates) -> None:
        """
        Update processing run with new data.
        
        Args:
            run_id: Processing run ID
            **updates: Fields to update (e.g., state='completed', end_time=datetime.now())
        """
        pass
    
    @abstractmethod
    def complete_processing_run(
        self, 
        run_id: str, 
        metrics: Dict[str, int],
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """
        Mark processing run as complete with final metrics.
        
        Args:
            run_id: Processing run ID
            metrics: Processing metrics (processed, deleted, etc.)
            success: Whether processing succeeded
            error_message: Error message if failed
        """
        pass
    
    @abstractmethod
    def get_recent_processing_runs(self, limit: int = 10, email_address: Optional[str] = None) -> List[Any]:
        """
        Get recent processing runs.
        
        Args:
            limit: Maximum number of runs to return
            email_address: Optional filter by email address
            
        Returns:
            List of ProcessingRun entities
        """
        pass
    
    # ==================== Email Summary Operations ====================
    
    @abstractmethod
    def save_email_summary(self, summary_data: Dict, account_id: Optional[int] = None) -> Any:
        """
        Save email processing summary with categories and senders.
        
        Args:
            summary_data: Summary data dict with categories, senders, etc.
            account_id: Optional account ID to link summary to
            
        Returns:
            Created EmailSummary entity
        """
        pass
    
    @abstractmethod
    def get_summaries_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        account_id: Optional[int] = None
    ) -> List[Any]:
        """
        Get email summaries within date range.
        
        Args:
            start_date: Start of range
            end_date: End of range
            account_id: Optional filter by account
            
        Returns:
            List of EmailSummary entities
        """
        pass
    
    # ==================== Account Operations ====================
    
    @abstractmethod
    def get_account_by_email(self, email_address: str) -> Optional[Any]:
        """Get email account by email address"""
        pass
    
    @abstractmethod
    def get_all_accounts(self, active_only: bool = False) -> List[Any]:
        """
        Get all email accounts.
        
        Args:
            active_only: If True, only return active accounts
            
        Returns:
            List of EmailAccount entities
        """
        pass
    
    @abstractmethod
    def create_or_update_account(
        self, 
        email_address: str,
        gmail_app_password: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Create new account or update existing one.
        
        Args:
            email_address: Email address
            gmail_app_password: Optional Gmail app password
            **kwargs: Additional account fields
            
        Returns:
            EmailAccount entity
        """
        pass
    
    @abstractmethod
    def deactivate_account(self, email_address: str) -> bool:
        """
        Deactivate an email account.
        
        Args:
            email_address: Email address to deactivate
            
        Returns:
            True if deactivated, False if not found
        """
        pass
    
    @abstractmethod
    def delete_account(self, email_address: str) -> bool:
        """
        Delete account and all related data.
        
        Args:
            email_address: Email address to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    # ==================== Settings Operations ====================
    
    @abstractmethod
    def get_setting(self, key: str) -> Optional[Any]:
        """
        Get setting by key.
        
        Args:
            key: Setting key
            
        Returns:
            UserSettings entity or None
        """
        pass
    
    @abstractmethod
    def set_setting(self, key: str, value: str, setting_type: str = 'string', description: str = '') -> Any:
        """
        Create or update a setting.
        
        Args:
            key: Setting key
            value: Setting value
            setting_type: Type of setting (string, integer, boolean, etc.)
            description: Human-readable description
            
        Returns:
            UserSettings entity
        """
        pass
    
    @abstractmethod
    def get_all_settings(self) -> List[Any]:
        """Get all settings"""
        pass
    
    # ==================== Category Statistics Operations ====================
    
    @abstractmethod
    def get_account_category_stats(
        self, 
        account_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Any]:
        """
        Get category statistics for account.
        
        Args:
            account_id: Account ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of AccountCategoryStats entities
        """
        pass
    
    @abstractmethod
    def update_account_category_stats(
        self,
        account_id: int,
        category_name: str,
        count_increment: int = 1,
        processing_date: Optional[date] = None
    ) -> Any:
        """
        Update or create category statistics for account.
        
        Args:
            account_id: Account ID
            category: Email category name
            count_increment: Number to increment count by
            processing_date: Date of processing (defaults to today)
            
        Returns:
            AccountCategoryStats entity
        """
        pass
    
    # ==================== Deduplication Operations ====================
    
    @abstractmethod
    def is_email_processed(self, email_address: str, message_id: str) -> bool:
        """
        Check if email has been processed already.
        
        Args:
            email_address: Email account
            message_id: Gmail message ID
            
        Returns:
            True if already processed
        """
        pass
    
    @abstractmethod
    def mark_email_processed(
        self,
        email_address: str,
        message_id: str,
        category: Optional[str] = None,
        action_taken: Optional[str] = None
    ) -> Any:
        """
        Mark email as processed to prevent duplicate processing.
        
        Args:
            email_address: Email account
            message_id: Gmail message ID
            category: Categorization result
            action_taken: Action taken (archived, deleted, etc.)
            
        Returns:
            ProcessedEmailLog entity
        """
        pass
    
    @abstractmethod
    def get_processed_emails_count(
        self,
        email_address: str,
        since: Optional[datetime] = None
    ) -> int:
        """
        Get count of processed emails.
        
        Args:
            email_address: Email account
            since: Optional datetime to count from
            
        Returns:
            Count of processed emails
        """
        pass
    
    @abstractmethod
    def cleanup_old_processed_emails(
        self,
        days_to_keep: int = 30,
        email_address: Optional[str] = None
    ) -> int:
        """
        Delete old processed email records.
        
        Args:
            days_to_keep: Keep records from this many days
            email_address: Optional filter by account
            
        Returns:
            Number of records deleted
        """
        pass
    
    # ==================== Transaction Management ====================
    
    @abstractmethod
    def begin_transaction(self) -> None:
        """Start a new transaction"""
        pass
    
    @abstractmethod
    def commit_transaction(self) -> None:
        """Commit current transaction"""
        pass
    
    @abstractmethod
    def rollback_transaction(self) -> None:
        """Rollback current transaction"""
        pass
