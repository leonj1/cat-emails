"""
Service for tracking and summarizing email processing activities.
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import logging
from collections import Counter

from models.email_summary import (
    ProcessedEmail, 
    EmailSummaryStats, 
    DailySummaryReport,
    CategoryCount,
    EmailAction
)


logger = logging.getLogger(__name__)


class EmailSummaryService:
    """Service for tracking processed emails and generating summaries."""
    
    def __init__(self, data_dir: str = "./email_summaries"):
        """
        Initialize the summary service.
        
        Args:
            data_dir: Directory to store summary data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.current_file = self.data_dir / "current_tracking.json"
        self.archive_dir = self.data_dir / "archives"
        self.archive_dir.mkdir(exist_ok=True)
        
    def track_email(self, 
                   message_id: str,
                   sender: str,
                   subject: str,
                   category: str,
                   action: str,
                   sender_domain: Optional[str] = None,
                   was_pre_categorized: bool = False) -> None:
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
        """
        try:
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