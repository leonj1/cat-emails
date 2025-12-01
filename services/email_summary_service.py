"""
Service for tracking and summarizing email processing activities.
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging
from utils.logger import get_logger
from collections import Counter, defaultdict

from models.email_summary import (
    ProcessedEmail,
    EmailSummaryStats,
    DailySummaryReport,
    CategoryCount,
    DomainCount,
    EmailAction
)
from services.database_service import DatabaseService
from clients.account_category_client import AccountCategoryClient


logger = get_logger(__name__)


class EmailSummaryService:
    """Service for tracking processed emails and generating summaries."""
    
    def __init__(self, data_dir: str = "./email_summaries", use_database: bool = True,
                 gmail_email: Optional[str] = None,
                 repository=None):
        """
        Initialize the summary service.

        Args:
            data_dir: Directory to store summary data
            use_database: Whether to persist summaries to database
            gmail_email: Gmail account email for account tracking (optional)
            repository: MySQLRepository instance for dependency injection (optional, creates new if not provided)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.current_file = self.data_dir / "current_tracking.json"
        self.archive_dir = self.data_dir / "archives"
        self.archive_dir.mkdir(exist_ok=True)

        # Store gmail account email for account tracking
        self.gmail_email = gmail_email

        # Initialize database service if enabled
        self.use_database = use_database
        self.db_service = None
        self.account_service = None

        # Track if we own the repository (created it) so we know if we should clean it up
        self._owns_repository = False
        self._repository = None

        if use_database:
            try:
                # Use provided repository or create a new one
                if repository is not None:
                    shared_repository = repository
                    logger.info("Using provided repository instance for email summaries")
                else:
                    from repositories.mysql_repository import MySQLRepository
                    shared_repository = MySQLRepository()
                    self._owns_repository = True
                    logger.info("Created new repository instance for email summaries")

                # Store reference to repository
                self._repository = shared_repository

                self.db_service = DatabaseService(repository=shared_repository)
                logger.info("Database service initialized for email summaries")

                # Initialize account category service with same repository
                try:
                    self.account_service = AccountCategoryClient(repository=shared_repository)
                    logger.info("Account category client initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize account service: {str(e)}")
                    # Continue without account service for backward compatibility

            except Exception as e:
                logger.error(f"Failed to initialize database service: {str(e)}")
                self.use_database = False
        
        # Track current run ID and account ID if using database
        self.current_run_id = None
        self.current_account_id = None
        
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

        logger.info(f"Processing run started for {self.gmail_email or 'unknown'}")

        # Get or create account if account service is available and gmail_email is set
        if self.account_service and self.gmail_email:
            try:
                # Create account and get its ID, but don't keep reference to avoid session issues
                account = self.account_service.get_or_create_account(self.gmail_email)
                self.current_account_id = account.id
                account_id = account.id  # Store ID before account object goes out of scope
                logger.info(f"Processing run linked to account: {self.gmail_email} (ID: {account_id})")
                
                # Update last scan timestamp (in separate try/catch to avoid blocking main flow)
                try:
                    self.account_service.update_account_last_scan(self.gmail_email)
                except Exception as scan_error:
                    logger.warning(f"Failed to update last scan time: {str(scan_error)}")
                    
            except Exception as e:
                logger.warning(f"Failed to link to account {self.gmail_email}: {str(e)}")
                # Try to get account ID as fallback
                try:
                    existing_account = self.account_service.get_account_by_email(self.gmail_email)
                    if existing_account:
                        self.current_account_id = existing_account.id
                        logger.info(f"Fallback: Retrieved account ID {existing_account.id} for {self.gmail_email}")
                except Exception as fallback_error:
                    logger.warning(f"Fallback account retrieval also failed: {str(fallback_error)}")
                    self.current_account_id = None
        
        if self.db_service and self.use_database:
            # Use the Gmail account email as the identifier for the processing run
            email_address = self.gmail_email or "unknown"
            self.current_run_id = self.db_service.start_processing_run(email_address)
            logger.info(f"Started processing run: {self.current_run_id}")
    
    def complete_processing_run(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """Complete the current processing run."""
        # Finalize performance metrics
        self.performance_metrics['end_time'] = datetime.now()
        self.performance_metrics['total_emails'] = self.run_metrics['processed']

        status = "completed" if success else "failed"
        logger.info(f"Processing run {status} for {self.gmail_email or 'unknown'}")

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
            report_type: Type of report (Morning/Evening/Daily/Weekly/Monthly)
            
        Returns:
            DailySummaryReport or None if no data
        """
        try:
            # For weekly/monthly reports, try to get historical data from database
            if report_type in ["Weekly", "Monthly"] and self.db_service and self.use_database:
                # Calculate date range based on report type
                end_date = datetime.now()
                if report_type == "Weekly":
                    start_date = end_date - timedelta(days=7)
                else:  # Monthly
                    start_date = end_date - timedelta(days=30)
                
                # Try to get historical summaries from database
                historical_data = self._get_historical_data(start_date, end_date)
                if historical_data:
                    return self._generate_historical_summary(historical_data, report_type)
            
            # Load tracked data for current period
            tracked_data = self._load_current_data()
            if not tracked_data:
                logger.warning("No tracked emails to summarize")
                return None
            
            # Convert to ProcessedEmail objects
            emails = [ProcessedEmail(**data) for data in tracked_data]
            
            # Calculate time range using performance metrics if available
            if self.performance_metrics['start_time'] and self.performance_metrics['end_time']:
                start_time = self.performance_metrics['start_time']
                end_time = self.performance_metrics['end_time']
                hours = (end_time - start_time).total_seconds() / 3600
            elif emails:
                # Fallback to email timestamps if performance metrics not available
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
            
            # Calculate domain statistics
            kept_domains = defaultdict(int)
            archived_domains = defaultdict(int)
            
            for email in emails:
                domain = email.sender_domain or email.sender.split('@')[-1] if '@' in email.sender else email.sender
                if email.action == EmailAction.KEPT:
                    kept_domains[domain] += 1
                elif email.action in [EmailAction.DELETED, EmailAction.ARCHIVED]:
                    archived_domains[domain] += 1
            
            # Get top 10 kept domains
            top_kept_domains = []
            for domain, count in sorted(kept_domains.items(), key=lambda x: x[1], reverse=True)[:10]:
                percentage = (count / total_kept) * 100 if total_kept > 0 else 0
                top_kept_domains.append(DomainCount(
                    domain=domain,
                    count=count,
                    percentage=round(percentage, 1),
                    action=EmailAction.KEPT
                ))
            
            # Get top 10 archived domains
            top_archived_domains = []
            archived_total = total_deleted  # Using total_deleted as it includes archived
            for domain, count in sorted(archived_domains.items(), key=lambda x: x[1], reverse=True)[:10]:
                percentage = (count / archived_total) * 100 if archived_total > 0 else 0
                top_archived_domains.append(DomainCount(
                    domain=domain,
                    count=count,
                    percentage=round(percentage, 1),
                    action=EmailAction.DELETED
                ))
            
            # Create summary stats
            stats = EmailSummaryStats(
                start_time=start_time,
                end_time=end_time,
                total_processed=total_processed,
                total_kept=total_kept,
                total_deleted=total_deleted,
                top_categories=top_categories,
                top_kept_domains=top_kept_domains,
                top_archived_domains=top_archived_domains,
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
                
                # Save to database with account_id if available
                try:
                    summary_id = self.db_service.save_email_summary(summary_data, self.current_account_id)
                    logger.info(f"Saved summary to database with ID: {summary_id}")
                    
                    # Also record account category stats if account service is available
                    if self.account_service and self.gmail_email and self.current_account_id:
                        try:
                            # Convert category stats to the format expected by AccountCategoryClient
                            account_category_stats = {}
                            for category, stats in self.category_stats.items():
                                account_category_stats[category] = {
                                    'total': stats['count'],
                                    'deleted': stats['deleted'], 
                                    'archived': stats['archived'],
                                    'kept': stats['count'] - stats['deleted']  # kept = total - deleted
                                }
                            
                            # Record today's category stats for this account
                            from datetime import date
                            self.account_service.record_category_stats(
                                self.gmail_email, 
                                date.today(), 
                                account_category_stats
                            )
                            logger.info(f"Recorded account category stats for {self.gmail_email}")
                            
                        except Exception as e:
                            logger.warning(f"Failed to record account category stats: {str(e)}")
                            # Don't fail the entire operation for account stats errors
                            
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
            
            # Reset performance metrics
            self.performance_metrics = {
                'start_time': None,
                'end_time': None,
                'email_processing_times': [],
                'total_emails': 0
            }
                
        except Exception as e:
            logger.error(f"Failed to clear tracked data: {str(e)}")
    
    def set_gmail_account(self, gmail_email: str) -> None:
        """
        Set the Gmail account for account tracking.
        
        Args:
            gmail_email: Gmail account email address
        """
        self.gmail_email = gmail_email
        
        # Reset account ID to force re-lookup on next run
        self.current_account_id = None
        logger.info(f"Gmail account set for tracking: {gmail_email}")
    
    def get_account_info(self) -> Optional[Dict[str, any]]:
        """
        Get information about the current account.
        
        Returns:
            Dictionary with account info or None if no account service
        """
        if not self.account_service or not self.gmail_email:
            return None
            
        try:
            account = self.account_service.get_account_by_email(self.gmail_email)
            if account:
                # Extract all data immediately to avoid session issues
                account_info = {
                    'email': account.email_address,
                    'display_name': account.display_name,
                    'is_active': account.is_active,
                    'last_scan_at': account.last_scan_at,
                    'created_at': account.created_at,
                    'account_id': account.id
                }
                return account_info
        except Exception as e:
            logger.error(f"Failed to get account info: {str(e)}")
        
        return None
    
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
    
    def _get_historical_data(self, start_date: datetime, end_date: datetime) -> Optional[Dict]:
        """Get historical summary data from database."""
        if not self.db_service:
            return None
            
        try:
            # Query summaries from database within date range
            # This is a placeholder - actual implementation would query the database
            logger.info(f"Querying historical data from {start_date} to {end_date}")
            # For now, return None to fall back to current data
            return None
        except Exception as e:
            logger.error(f"Failed to get historical data: {str(e)}")
            return None
    
    def _generate_historical_summary(self, historical_data: Dict, report_type: str) -> Optional[DailySummaryReport]:
        """Generate summary from historical data."""
        # This would aggregate historical data into a summary
        # For now, this is a placeholder
        return None
    
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

    def close(self) -> None:
        """
        Clean up resources. Only disconnects the repository if this service created it.

        If a repository was injected via the constructor, it's the caller's responsibility
        to manage its lifecycle.
        """
        if self._owns_repository and self._repository is not None:
            try:
                self._repository.disconnect()
                logger.info("Disconnected repository (owned by EmailSummaryService)")
            except Exception as e:
                logger.error(f"Failed to disconnect repository: {str(e)}")
            finally:
                self._repository = None
        elif self._repository is not None:
            logger.debug("Repository not owned by EmailSummaryService, skipping disconnect")
