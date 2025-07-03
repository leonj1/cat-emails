"""
Database models for email summary persistence
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class EmailSummary(Base):
    """Daily email processing summary"""
    __tablename__ = 'email_summaries'
    
    id = Column(Integer, primary_key=True)
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


class ProcessingRun(Base):
    """Individual email processing run details"""
    __tablename__ = 'processing_runs'
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), unique=True, nullable=False)  # UUID for each run
    
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    
    # Metrics
    emails_fetched = Column(Integer, default=0)
    emails_processed = Column(Integer, default=0)
    emails_deleted = Column(Integer, default=0)
    emails_archived = Column(Integer, default=0)
    emails_error = Column(Integer, default=0)
    
    # Configuration
    scan_hours = Column(Integer)
    
    # Error tracking
    error_message = Column(Text)
    success = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_run_time', 'started_at', 'completed_at'),
    )


# Database initialization functions
def get_database_url(db_path: str = "./email_summaries/summaries.db") -> str:
    """Get the database URL"""
    return f"sqlite:///{db_path}"


def init_database(db_path: str = "./email_summaries/summaries.db"):
    """Initialize the database schema"""
    engine = create_engine(get_database_url(db_path))
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get a database session"""
    Session = sessionmaker(bind=engine)
    return Session()