"""
Service for tracking and summarizing email processing activities.
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging
from collections import Counter, defaultdict

from models.email_summary import (
    ProcessedEmail, 
    EmailSummaryStats, 
    DailySummaryReport,
    CategoryCount,
    EmailAction
)
from services.database_service import DatabaseService


logger = logging.getLogger(__name__)


class EmailSummaryService:
    """Service for tracking processed emails and generating summaries."""
    
    def __init__(self, data_dir: str = "./email_summaries", use_database: bool = True):
        """
        Initialize the summary service.
        
        Args:
            data_dir: Directory to store summary data
            use_database: Whether to persist summaries to database
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.current_file = self.data_dir / "current_tracking.json"
        self.archive_dir = self.data_dir / "archives"
        self.archive_dir.mkdir(exist_ok=True)
        
        # Initialize database service if enabled
        self.use_database = use_database
        self.db_service = None
        if use_database:
            try:
                self.db_service = DatabaseService(
                    db_path=str(self.data_dir / "summaries.db")
                )
                logger.info("Database service initialized for email summaries")
            except Exception as e:
                logger.error(f"Failed to initialize database service: {str(e)}")
                self.use_database = False
        
        # Track current run ID if using database
        self.current_run_id = None
        
        # Track run metrics
        self.run_metrics = {
            'fetched': 0,
            'processed': 0,
            'deleted': 0,
            'archived': 0,
            'error': 0
        }
        
        # Track summary data for database
        self.category_stats = defaultdict(lambda: {'count': 0, 'deleted': 0, 'archived': 0})
        self.sender_stats = defaultdict(lambda: {'count': 0, 'deleted': 0, 'archived': 0, 'name': ''})
        self.domain_stats = defaultdict(lambda: {'count': 0, 'deleted': 0, 'archived': 0, 'is_blocked': False})
        
        # Performance tracking
        self.performance_metrics = {
            'start_time': None,
            'end_time': None,
            'email_processing_times': [],  # List of (email_id, processing_time) tuples
            'total_emails': 0
        }
    
    def start_processing_run(self, scan_hours: int = 2) -> None:
        """Start a new processing run."""
        # Reset performance metrics
        self.performance_metrics['start_time'] = datetime.now()
        self.performance_metrics['email_processing_times'] = []
        self.performance_metrics['total_emails'] = 0
        
        if self.db_service and self.use_database:
            self.current_run_id = self.db_service.start_processing_run(scan_hours)
            logger.info(f"Started processing run: {self.current_run_id}")
    
    def complete_processing_run(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """Complete the current processing run."""
        # Finalize performance metrics
        self.performance_metrics['end_time'] = datetime.now()
        self.performance_metrics['total_emails'] = self.run_metrics['processed']
        
        if self.db_service and self.use_database and self.current_run_id:
            self.db_service.complete_processing_run(
                self.current_run_id, 
                self.run_metrics,
                success=success,
                error_message=error_message
            )
            logger.info(f"Completed processing run: {self.current_run_id}")
            self.current_run_id = None
        
    def track_email(self, 
                   message_id: str,
                   sender: str,
                   subject: str,
                   category: str,
                   action: str,
                   sender_domain: Optional[str] = None,
                   was_pre_categorized: bool = False,
                   processing_time: Optional[float] = None) -> None:
        """
        Track a processed email.
        
        Args:
            message_id: Unique email identifier
            sender: Email sender
            subject: Email subject
            category: Assigned category
            action: Action taken (kept/deleted)
            sender_domain: Domain of sender
            was_pre_categorized: Whether pre-categorized by domain rules
            processing_time: Time taken to process this email in seconds
        """
        try:
            # Track performance metrics
            if processing_time is not None:
                self.performance_metrics['email_processing_times'].append(
                    (message_id, processing_time)
                )
            
            # Create processed email record
            email_record = ProcessedEmail(
                message_id=message_id,
                sender=sender,
                subject=subject[:200],  # Limit subject length
                category=category,
                action=EmailAction.DELETED if action == "deleted" else EmailAction.KEPT,
                sender_domain=sender_domain,
                was_pre_categorized=was_pre_categorized
            )
            
            # Load existing data
            existing_data = self._load_current_data()
            existing_data.append(email_record.model_dump())
            
            # Save updated data
            self._save_current_data(existing_data)
            logger.debug(f"Tracked email: {message_id}")
            
            # Update statistics for database
            if self.use_database:
                # Update run metrics
                self.run_metrics['processed'] += 1
                if action == "deleted":
                    self.run_metrics['deleted'] += 1
                else:
                    self.run_metrics['archived'] += 1
                
                # Update category stats
                self.category_stats[category]['count'] += 1
                if action == "deleted":
                    self.category_stats[category]['deleted'] += 1
                else:
                    self.category_stats[category]['archived'] += 1
                
                # Update sender stats
                self.sender_stats[sender]['count'] += 1
                self.sender_stats[sender]['name'] = sender.split('@')[0] if '@' in sender else sender
                if action == "deleted":
                    self.sender_stats[sender]['deleted'] += 1
                else:
                    self.sender_stats[sender]['archived'] += 1
                
                # Update domain stats
                if sender_domain:
                    self.domain_stats[sender_domain]['count'] += 1
                    if action == "deleted":
                        self.domain_stats[sender_domain]['deleted'] += 1
                    else:
                        self.domain_stats[sender_domain]['archived'] += 1
            
        except Exception as e:
            logger.error(f"Failed to track email {message_id}: {str(e)}")
    
    def generate_summary(self, report_type: str = "Daily") -> Optional[DailySummaryReport]:
        """
        Generate a summary report from tracked emails.
        
        Args:
            report_type: Type of report (Morning/Evening/Daily)
            
        Returns:
            DailySummaryReport or None if no data
        """
        try:
            # Load tracked data
            tracked_data = self._load_current_data()
            if not tracked_data:
                logger.warning("No tracked emails to summarize")
                return None
            
            # Convert to ProcessedEmail objects
            emails = [ProcessedEmail(**data) for data in tracked_data]
            
            # Calculate time range
            if emails:
                start_time = min(email.processed_at for email in emails)
                end_time = max(email.processed_at for email in emails)
                hours = (end_time - start_time).total_seconds() / 3600
            else:
                start_time = datetime.now()
                end_time = datetime.now()
                hours = 0
            
            # Calculate statistics
            total_processed = len(emails)
            total_kept = sum(1 for email in emails if email.action == EmailAction.KEPT)
            total_deleted = sum(1 for email in emails if email.action == EmailAction.DELETED)
            
            # Calculate top categories
            category_counts = Counter(email.category for email in emails)
            top_categories = []
            
            for category, count in category_counts.most_common(10):
                percentage = (count / total_processed) * 100 if total_processed > 0 else 0
                top_categories.append(CategoryCount(
                    category=category,
                    count=count,
                    percentage=round(percentage, 1)
                ))
            
            # Create summary stats
            stats = EmailSummaryStats(
                start_time=start_time,
                end_time=end_time,
                total_processed=total_processed,
                total_kept=total_kept,
                total_deleted=total_deleted,
                top_categories=top_categories,
                processing_hours=round(hours, 1)
            )
            
            # Create report
            report = DailySummaryReport(
                report_id=f"{report_type.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                report_type=report_type,
                stats=stats,
                processed_emails=emails
            )
            
            logger.info(f"Generated {report_type} summary: {total_processed} emails processed")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            return None
    
    def clear_tracked_data(self) -> None:
        """Clear current tracking data after sending summary."""
        try:
            # Save to database if enabled
            if self.db_service and self.use_database:
                # Calculate total skipped (if needed)
                total_skipped = self.run_metrics.get('fetched', 0) - self.run_metrics.get('processed', 0)
                
                # Prepare summary data
                summary_data = {
                    'total_processed': self.run_metrics['processed'],
                    'total_deleted': self.run_metrics['deleted'],
                    'total_archived': self.run_metrics['archived'],
                    'total_skipped': total_skipped,
                    'processing_duration': 0,  # Will be calculated by processing run
                    'scan_hours': 2,  # Default, should be passed from main
                    'categories': dict(self.category_stats),
                    'senders': dict(self.sender_stats),
                    'domains': dict(self.domain_stats)
                }
                
                # Save to database
                try:
                    summary_id = self.db_service.save_email_summary(summary_data)
                    logger.info(f"Saved summary to database with ID: {summary_id}")
                except Exception as e:
                    logger.error(f"Failed to save summary to database: {str(e)}")
            
            # Archive current data first
            if self.current_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_file = self.archive_dir / f"tracked_{timestamp}.json"
                
                # Move to archive
                data = self._load_current_data()
                if data:
                    with open(archive_file, 'w') as f:
                        json.dump(data, f, indent=2, default=str)
                
                # Clear current file
                self._save_current_data([])
                logger.info("Cleared tracked data after archiving")
            
            # Reset statistics
            self.run_metrics = {
                'fetched': 0,
                'processed': 0,
                'deleted': 0,
                'archived': 0,
                'error': 0
            }
            self.category_stats.clear()
            self.sender_stats.clear()
            self.domain_stats.clear()
                
        except Exception as e:
            logger.error(f"Failed to clear tracked data: {str(e)}")
    
    def _load_current_data(self) -> List[Dict]:
        """Load current tracking data."""
        if not self.current_file.exists():
            return []
        
        try:
            with open(self.current_file, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to load tracking data: {str(e)}")
            return []
    
    def _save_current_data(self, data: List[Dict]) -> None:
        """Save tracking data."""
        try:
            with open(self.current_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save tracking data: {str(e)}")
    
    def get_stats_since(self, hours: int = 24) -> Dict[str, any]:
        """
        Get quick statistics for the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with basic statistics
        """
        try:
            data = self._load_current_data()
            if not data:
                return {"total": 0, "kept": 0, "deleted": 0}
            
            # Filter by time
            cutoff = datetime.now() - timedelta(hours=hours)
            recent_emails = [
                ProcessedEmail(**d) for d in data 
                if datetime.fromisoformat(d['processed_at'].replace('Z', '+00:00')) > cutoff
            ]
            
            return {
                "total": len(recent_emails),
                "kept": sum(1 for e in recent_emails if e.action == EmailAction.KEPT),
                "deleted": sum(1 for e in recent_emails if e.action == EmailAction.DELETED),
                "categories": Counter(e.category for e in recent_emails).most_common(5)
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}")
            return {"total": 0, "kept": 0, "deleted": 0}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate and return performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        metrics = {
            'emails_per_minute': 0,
            'avg_processing_time': 0,
            'total_duration_minutes': 0,
            'peak_processing_time': 0,
            'min_processing_time': 0
        }
        
        # Calculate total duration
        if self.performance_metrics['start_time'] and self.performance_metrics['end_time']:
            duration = (self.performance_metrics['end_time'] - 
                       self.performance_metrics['start_time']).total_seconds()
            metrics['total_duration_minutes'] = duration / 60
            
            # Calculate emails per minute
            if duration > 0 and self.performance_metrics['total_emails'] > 0:
                metrics['emails_per_minute'] = (
                    self.performance_metrics['total_emails'] / (duration / 60)
                )
        
        # Calculate processing time stats
        if self.performance_metrics['email_processing_times']:
            processing_times = [t[1] for t in self.performance_metrics['email_processing_times']]
            metrics['avg_processing_time'] = sum(processing_times) / len(processing_times)
            metrics['peak_processing_time'] = max(processing_times)
            metrics['min_processing_time'] = min(processing_times)
        
        return metrics