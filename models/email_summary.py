"""
Models for email processing summaries and reports.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class EmailAction(str, Enum):
    """Actions taken on emails."""
    KEPT = "kept"
    DELETED = "deleted"
    ARCHIVED = "archived"


class ProcessedEmail(BaseModel):
    """Record of a single processed email."""
    message_id: str = Field(description="Unique email message ID")
    sender: str = Field(description="Email sender address")
    subject: str = Field(description="Email subject line")
    category: str = Field(description="Assigned category")
    action: EmailAction = Field(description="Action taken on the email")
    processed_at: datetime = Field(default_factory=datetime.now, description="When the email was processed")
    sender_domain: Optional[str] = Field(None, description="Domain of the sender")
    was_pre_categorized: bool = Field(False, description="Whether email was pre-categorized by domain rules")


class CategoryCount(BaseModel):
    """Category with count."""
    category: str = Field(description="Category name")
    count: int = Field(description="Number of emails in this category")
    percentage: float = Field(description="Percentage of total emails")


class EmailSummaryStats(BaseModel):
    """Aggregated email processing statistics."""
    start_time: datetime = Field(description="Start of the reporting period")
    end_time: datetime = Field(description="End of the reporting period")
    total_processed: int = Field(description="Total emails processed")
    total_kept: int = Field(description="Emails kept in inbox")
    total_deleted: int = Field(description="Emails deleted/archived")
    top_categories: List[CategoryCount] = Field(description="Top categories by count")
    processing_hours: float = Field(description="Hours covered in this period")
    
    @property
    def deletion_rate(self) -> float:
        """Calculate percentage of emails deleted."""
        if self.total_processed == 0:
            return 0.0
        return (self.total_deleted / self.total_processed) * 100
    
    @property
    def kept_rate(self) -> float:
        """Calculate percentage of emails kept."""
        if self.total_processed == 0:
            return 0.0
        return (self.total_kept / self.total_processed) * 100


class DailySummaryReport(BaseModel):
    """Complete daily summary report."""
    report_id: str = Field(description="Unique report identifier")
    generated_at: datetime = Field(default_factory=datetime.now, description="When report was generated")
    report_type: str = Field(description="Morning (8am) or Evening (8pm)")
    stats: EmailSummaryStats = Field(description="Statistical summary")
    processed_emails: List[ProcessedEmail] = Field(description="All processed emails in period")
    
    def get_top_senders(self, limit: int = 5) -> List[Dict[str, any]]:
        """Get top email senders by count."""
        sender_counts = {}
        for email in self.processed_emails:
            sender = email.sender_domain or email.sender
            sender_counts[sender] = sender_counts.get(sender, 0) + 1
        
        sorted_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"sender": sender, "count": count, "percentage": (count / len(self.processed_emails)) * 100}
            for sender, count in sorted_senders[:limit]
        ]