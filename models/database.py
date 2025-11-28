"""
Database models for email summary persistence
"""
import os
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date, Float, Boolean, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class UserSettings(Base):
    """Global user settings and preferences"""
    __tablename__ = 'user_settings'
    
    id = Column(Integer, primary_key=True)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(String(255), nullable=False)
    setting_type = Column(String(50), default='string')  # string, integer, float, boolean
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('setting_key', name='uq_setting_key'),
    )


class EmailAccount(Base):
    """Email account information for multi-account support"""
    __tablename__ = 'email_accounts'

    id = Column(Integer, primary_key=True)
    email_address = Column(String(255), unique=True, nullable=False, index=True)
    app_password = Column(String(255))  # Gmail app-specific password for IMAP access
    display_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)
    last_scan_at = Column(DateTime)
    
    # Relationships
    email_summaries = relationship("EmailSummary", back_populates="email_account", cascade="all, delete-orphan")
    category_stats = relationship("AccountCategoryStats", back_populates="email_account", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_email_active', 'email_address', 'is_active'),
    )


class EmailSummary(Base):
    """Daily email processing summary"""
    __tablename__ = 'email_summaries'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('email_accounts.id'), nullable=True)  # Nullable for backward compatibility
    date = Column(DateTime, nullable=False, index=True)
    
    # Core metrics
    total_emails_processed = Column(Integer, default=0)
    total_emails_deleted = Column(Integer, default=0)
    total_emails_archived = Column(Integer, default=0)
    total_emails_skipped = Column(Integer, default=0)
    
    # Processing metrics
    processing_duration_seconds = Column(Float)
    scan_interval_hours = Column(Integer)
    
    # Relationships
    email_account = relationship("EmailAccount", back_populates="email_summaries")
    categories = relationship("CategorySummary", back_populates="email_summary", cascade="all, delete-orphan")
    senders = relationship("SenderSummary", back_populates="email_summary", cascade="all, delete-orphan")
    domains = relationship("DomainSummary", back_populates="email_summary", cascade="all, delete-orphan")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_date_created', 'date', 'created_at'),
    )


class CategorySummary(Base):
    """Email category statistics for a summary period"""
    __tablename__ = 'category_summaries'
    
    id = Column(Integer, primary_key=True)
    email_summary_id = Column(Integer, ForeignKey('email_summaries.id'), nullable=False)
    
    category_name = Column(String(100), nullable=False)
    email_count = Column(Integer, default=0)
    deleted_count = Column(Integer, default=0)
    archived_count = Column(Integer, default=0)
    
    email_summary = relationship("EmailSummary", back_populates="categories")
    
    __table_args__ = (
        Index('idx_summary_category', 'email_summary_id', 'category_name'),
    )


class SenderSummary(Base):
    """Sender statistics for a summary period"""
    __tablename__ = 'sender_summaries'
    
    id = Column(Integer, primary_key=True)
    email_summary_id = Column(Integer, ForeignKey('email_summaries.id'), nullable=False)
    
    sender_email = Column(String(255), nullable=False)
    sender_name = Column(String(255))
    email_count = Column(Integer, default=0)
    deleted_count = Column(Integer, default=0)
    archived_count = Column(Integer, default=0)
    
    email_summary = relationship("EmailSummary", back_populates="senders")
    
    __table_args__ = (
        Index('idx_summary_sender', 'email_summary_id', 'sender_email'),
    )


class RepeatOffenderPattern(Base):
    """Track email patterns that are consistently marked for deletion"""
    __tablename__ = 'repeat_offender_patterns'
    
    id = Column(Integer, primary_key=True)
    account_name = Column(String(255), nullable=False)
    
    # Pattern identifiers (at least one must be set)
    sender_email = Column(String(255), nullable=True)
    sender_domain = Column(String(255), nullable=True)
    subject_pattern = Column(String(500), nullable=True)
    
    # Tracking information
    category = Column(String(100), nullable=False)  # Original category like "WantsMoney"
    total_occurrences = Column(Integer, default=0)
    deletion_count = Column(Integer, default=0)
    confidence_score = Column(Float, default=0.0)  # deletion_count / total_occurrences
    
    # Timestamps
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    marked_as_repeat_offender = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        Index('idx_account_sender', 'account_name', 'sender_email'),
        Index('idx_account_domain', 'account_name', 'sender_domain'),
        Index('idx_account_subject', 'account_name', 'subject_pattern'),
        Index('idx_active_patterns', 'account_name', 'is_active'),
    )


class DomainSummary(Base):
    """Domain statistics for a summary period"""
    __tablename__ = 'domain_summaries'
    
    id = Column(Integer, primary_key=True)
    email_summary_id = Column(Integer, ForeignKey('email_summaries.id'), nullable=False)
    
    domain = Column(String(255), nullable=False)
    email_count = Column(Integer, default=0)
    deleted_count = Column(Integer, default=0)
    archived_count = Column(Integer, default=0)
    is_blocked = Column(Boolean, default=False)
    
    email_summary = relationship("EmailSummary", back_populates="domains")
    
    __table_args__ = (
        Index('idx_summary_domain', 'email_summary_id', 'domain'),
    )


class AccountCategoryStats(Base):
    """Category statistics per account per day"""
    __tablename__ = 'account_category_stats'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('email_accounts.id'), nullable=False)
    date = Column(Date, nullable=False)
    category_name = Column(String(100), nullable=False)
    email_count = Column(Integer, default=0)
    deleted_count = Column(Integer, default=0)
    archived_count = Column(Integer, default=0)
    kept_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    email_account = relationship("EmailAccount", back_populates="category_stats")
    
    __table_args__ = (
        UniqueConstraint('account_id', 'date', 'category_name', name='uq_account_date_category'),
        Index('idx_account_date', 'account_id', 'date'),
        Index('idx_account_category', 'account_id', 'category_name'),
        Index('idx_date_category', 'date', 'category_name'),
    )


class ProcessingRun(Base):
    """Historical tracking of email processing sessions"""
    __tablename__ = 'processing_runs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_address = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    state = Column(Text, nullable=False)  # current processing state
    current_step = Column(Text, nullable=True)  # description of current step
    emails_found = Column(Integer, default=0)
    emails_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_processing_runs_email_address', 'email_address'),
        Index('idx_processing_runs_start_time', 'start_time'),
        Index('idx_processing_runs_email_start', 'email_address', 'start_time'),
        Index('idx_processing_runs_state', 'state'),
    )


class ProcessedEmailLog(Base):
    """Log of processed emails to prevent duplicate processing per account"""
    __tablename__ = 'processed_email_log'

    id = Column(Integer, primary_key=True)
    account_email = Column(String(255), nullable=False, index=True)
    message_id = Column(String(255), nullable=False, index=True)
    processed_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        UniqueConstraint('account_email', 'message_id', name='uq_account_email_message_id'),
        Index('idx_processed_account_message', 'account_email', 'message_id'),
    )


class CategoryDailyTally(Base):
    """Daily category tally per email account"""
    __tablename__ = 'category_daily_tallies'

    id = Column(Integer, primary_key=True)
    email_address = Column(String(255), nullable=False, index=True)
    tally_date = Column(Date, nullable=False, index=True)
    category = Column(String(100), nullable=False)
    count = Column(Integer, default=0, nullable=False)
    total_emails = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('email_address', 'tally_date', 'category', name='uq_email_date_category'),
        Index('idx_email_date', 'email_address', 'tally_date'),
        Index('idx_email_category', 'email_address', 'category'),
        Index('idx_date_range', 'email_address', 'tally_date', 'category'),
    )


# Database initialization functions
def get_database_url(db_path: Optional[str] = None) -> str:
    """
    Build an absolute SQLite database URL and ensure the parent directory exists.

    Priority order for database path:
    1) Explicit db_path parameter (if provided)
    2) DATABASE_PATH environment variable
    
    Raises:
        ValueError: If neither db_path nor DATABASE_PATH environment variable is provided
    """
    # Determine the database file path
    env_db_path = os.getenv("DATABASE_PATH")
    chosen_path = None

    if isinstance(db_path, str) and db_path.strip():
        chosen_path = db_path
    elif isinstance(env_db_path, str) and env_db_path.strip():
        chosen_path = env_db_path
    else:
        raise ValueError(
            "Database path must be provided either via 'db_path' parameter or 'DATABASE_PATH' environment variable. "
            "No fallback path is configured."
        )

    # Expand user and make absolute
    db_path_abs = os.path.abspath(os.path.expanduser(chosen_path))

    # Ensure the directory exists
    db_dir = os.path.dirname(db_path_abs)
    os.makedirs(db_dir, exist_ok=True)

    return f"sqlite:///{db_path_abs}"


def init_database(db_path: Optional[str] = None):
    """Initialize the database schema"""
    # For SQLite in multi-threaded app, allow cross-thread access per engine
    engine = create_engine(get_database_url(db_path), connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get a database session"""
    Session = sessionmaker(bind=engine)
    return Session()
