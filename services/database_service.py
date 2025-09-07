"""
Database service for managing email summary persistence
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from uuid import uuid4
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import Session, sessionmaker

from models.database import (
    Base, EmailSummary, CategorySummary, SenderSummary, 
    DomainSummary, ProcessingRun, get_database_url, init_database
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing database operations"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path if (isinstance(db_path, str) and db_path.strip()) else os.getenv("DATABASE_PATH") or "./email_summaries/summaries.db"
        self.engine = None
        self.Session = None
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure database exists and is initialized"""
        # Create directory if it doesn't exist
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # Initialize database
        self.engine = init_database(self.db_path)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"Database initialized at {self.db_path}")
    
    def start_processing_run(self, email_address: str) -> str:
        """Start a new processing run and return its ID (format: 'run-<id>')"""
        
        with self.Session() as session:
            run = ProcessingRun(
                email_address=email_address,
                start_time=datetime.utcnow(),
                state='started'
            )
            session.add(run)
            session.commit()
            # Use the auto-incrementing DB ID for consistency across the system
            return f"run-{run.id}"
    
    def complete_processing_run(self, run_id: str, metrics: Dict[str, int], 
                               success: bool = True, error_message: Optional[str] = None):
        """Complete a processing run with final metrics"""
        with self.Session() as session:
            run = session.query(ProcessingRun).filter_by(id=int(run_id.replace('run-', ''))).first()
            if run:
                run.end_time = datetime.utcnow()
                run.emails_processed = metrics.get('processed', 0)
                run.state = 'completed' if success else 'error'
                run.error_message = error_message
                session.commit()
    
    def save_email_summary(self, summary_data: Dict, account_id: Optional[int] = None):
        """Save email summary to database"""
        with self.Session() as session:
            # Create main summary
            summary = EmailSummary(
                account_id=account_id,  # Link to account if provided
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
            for sender_email, stats in summary_data.get('senders', {}).items():
                sender_summary = SenderSummary(
                    sender_email=sender_email,
                    sender_name=stats.get('name', ''),
                    email_count=stats['count'],
                    deleted_count=stats.get('deleted', 0),
                    archived_count=stats.get('archived', 0)
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
            
            return summary.id
    
    def get_summary_by_period(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get aggregated summary for a time period"""
        with self.Session() as session:
            # Get main metrics
            summaries = session.query(
                func.sum(EmailSummary.total_emails_processed).label('total_processed'),
                func.sum(EmailSummary.total_emails_deleted).label('total_deleted'),
                func.sum(EmailSummary.total_emails_archived).label('total_archived'),
                func.sum(EmailSummary.total_emails_skipped).label('total_skipped'),
                func.avg(EmailSummary.processing_duration_seconds).label('avg_duration'),
                func.count(EmailSummary.id).label('summary_count')
            ).filter(
                and_(
                    EmailSummary.date >= start_date,
                    EmailSummary.date <= end_date
                )
            ).first()
            
            # Get top categories
            categories = session.query(
                CategorySummary.category_name,
                func.sum(CategorySummary.email_count).label('total_count'),
                func.sum(CategorySummary.deleted_count).label('total_deleted')
            ).join(EmailSummary).filter(
                and_(
                    EmailSummary.date >= start_date,
                    EmailSummary.date <= end_date
                )
            ).group_by(CategorySummary.category_name).order_by(
                func.sum(CategorySummary.email_count).desc()
            ).limit(10).all()
            
            # Get top domains
            domains = session.query(
                DomainSummary.domain,
                func.sum(DomainSummary.email_count).label('total_count'),
                func.sum(DomainSummary.deleted_count).label('total_deleted'),
                DomainSummary.is_blocked
            ).join(EmailSummary).filter(
                and_(
                    EmailSummary.date >= start_date,
                    EmailSummary.date <= end_date
                )
            ).group_by(DomainSummary.domain, DomainSummary.is_blocked).order_by(
                func.sum(DomainSummary.email_count).desc()
            ).limit(10).all()
            
            # Get top senders
            senders = session.query(
                SenderSummary.sender_email,
                SenderSummary.sender_name,
                func.sum(SenderSummary.email_count).label('total_count'),
                func.sum(SenderSummary.deleted_count).label('total_deleted')
            ).join(EmailSummary).filter(
                and_(
                    EmailSummary.date >= start_date,
                    EmailSummary.date <= end_date
                )
            ).group_by(SenderSummary.sender_email, SenderSummary.sender_name).order_by(
                func.sum(SenderSummary.email_count).desc()
            ).limit(10).all()
            
            return {
                'period': {
                    'start': start_date,
                    'end': end_date
                },
                'metrics': {
                    'total_processed': summaries.total_processed or 0,
                    'total_deleted': summaries.total_deleted or 0,
                    'total_archived': summaries.total_archived or 0,
                    'total_skipped': summaries.total_skipped or 0,
                    'avg_processing_seconds': summaries.avg_duration or 0,
                    'summary_count': summaries.summary_count or 0
                },
                'categories': [
                    {
                        'name': cat.category_name,
                        'count': cat.total_count,
                        'deleted': cat.total_deleted
                    } for cat in categories
                ],
                'domains': [
                    {
                        'domain': dom.domain,
                        'count': dom.total_count,
                        'deleted': dom.total_deleted,
                        'is_blocked': dom.is_blocked
                    } for dom in domains
                ],
                'senders': [
                    {
                        'email': sender.sender_email,
                        'name': sender.sender_name,
                        'count': sender.total_count,
                        'deleted': sender.total_deleted
                    } for sender in senders
                ]
            }
    
    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict:
        """Get summary for a specific day"""
        if not date:
            date = datetime.utcnow().date()
        else:
            date = date.date()
        
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        
        return self.get_summary_by_period(start, end)
    
    def get_weekly_summary(self, weeks_ago: int = 0) -> Dict:
        """Get summary for a specific week"""
        today = datetime.utcnow().date()
        # Get start of week (Monday)
        start_of_week = today - timedelta(days=today.weekday() + (weeks_ago * 7))
        end_of_week = start_of_week + timedelta(days=6)
        
        start = datetime.combine(start_of_week, datetime.min.time())
        end = datetime.combine(end_of_week, datetime.max.time())
        
        return self.get_summary_by_period(start, end)
    
    def get_monthly_summary(self, months_ago: int = 0) -> Dict:
        """Get summary for a specific month"""
        today = datetime.utcnow()
        
        # Calculate target month
        target_month = today.month - months_ago
        target_year = today.year
        
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        # Get first and last day of month
        start = datetime(target_year, target_month, 1)
        
        # Calculate last day of month
        if target_month == 12:
            end = datetime(target_year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end = datetime(target_year, target_month + 1, 1) - timedelta(seconds=1)
        
        return self.get_summary_by_period(start, end)
    
    def get_processing_runs(self, limit: int = 100) -> List[Dict]:
        """Get recent processing runs"""
        with self.Session() as session:
            runs = session.query(ProcessingRun).order_by(
                ProcessingRun.start_time.desc()
            ).limit(limit).all()
            
            return [
                {
                    'run_id': f"run-{run.id}",
                    'started_at': run.start_time,
                    'completed_at': run.end_time,
                    'duration_seconds': (run.end_time - run.start_time).total_seconds() if run.end_time else None,
                    'emails_processed': run.emails_processed,
                    'emails_deleted': 0,  # Not tracked in current model
                    'success': run.state == 'completed' and not run.error_message,
                    'error_message': run.error_message
                } for run in runs
            ]
    
    def get_category_trends(self, days: int = 30) -> Dict[str, List[Tuple[datetime, int]]]:
        """Get category trends over time"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        with self.Session() as session:
            trends = session.query(
                EmailSummary.date,
                CategorySummary.category_name,
                func.sum(CategorySummary.email_count).label('count')
            ).join(CategorySummary).filter(
                EmailSummary.date >= start_date
            ).group_by(
                EmailSummary.date,
                CategorySummary.category_name
            ).order_by(EmailSummary.date).all()
            
            # Organize by category
            category_trends = {}
            for date, category, count in trends:
                if category not in category_trends:
                    category_trends[category] = []
                category_trends[category].append((date, count))
            
            return category_trends
