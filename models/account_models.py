"""
Models for account management and category statistics API endpoints.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime, date


class AccountCategoryStatsRequest(BaseModel):
    """Request model for account category statistics query parameters."""
    days: int = Field(
        ge=1, 
        le=365, 
        description="Number of days to look back from today (1-365 days)"
    )
    limit: int = Field(
        default=10, 
        ge=1, 
        le=50, 
        description="Maximum number of top categories to return (1-50, default: 10)"
    )
    include_counts: bool = Field(
        default=False, 
        description="Whether to include detailed counts breakdown (kept/deleted/archived)"
    )


class CategoryStats(BaseModel):
    """Statistics for a single email category."""
    category: str = Field(description="Email category name (e.g., 'Marketing', 'Personal')")
    total_count: int = Field(ge=0, description="Total number of emails in this category")
    percentage: float = Field(ge=0.0, le=100.0, description="Percentage of total emails this category represents")
    kept_count: Optional[int] = Field(
        None, 
        ge=0, 
        description="Number of emails kept in inbox (only included if include_counts=True)"
    )
    deleted_count: Optional[int] = Field(
        None, 
        ge=0, 
        description="Number of emails deleted (only included if include_counts=True)"
    )
    archived_count: Optional[int] = Field(
        None, 
        ge=0, 
        description="Number of emails archived (only included if include_counts=True)"
    )

    @validator('percentage')
    def validate_percentage(cls, v):
        """Ensure percentage is rounded to 2 decimal places."""
        return round(v, 2)


class DatePeriod(BaseModel):
    """Represents a date range period."""
    start_date: date = Field(description="Start date of the period (inclusive)")
    end_date: date = Field(description="End date of the period (inclusive)")
    days: int = Field(ge=1, description="Number of days in the period")

    @validator('end_date')
    def validate_date_order(cls, v, values):
        """Ensure end_date is not before start_date."""
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be on or after start_date')
        return v

    @validator('days')
    def validate_days_match_range(cls, v, values):
        """Ensure days field matches the actual date range."""
        if 'start_date' in values and 'end_date' in values:
            actual_days = (values['end_date'] - values['start_date']).days + 1
            if v != actual_days:
                raise ValueError(f'days field ({v}) does not match actual date range ({actual_days} days)')
        return v


class TopCategoriesResponse(BaseModel):
    """Response model for top categories by account."""
    email_address: str = Field(description="The Gmail account email address")
    period: DatePeriod = Field(description="Date range that was queried")
    total_emails: int = Field(ge=0, description="Total number of emails processed in the period")
    top_categories: List[CategoryStats] = Field(
        description="List of top categories ranked by email count (descending order)"
    )

    @validator('top_categories')
    def validate_categories_order(cls, v):
        """Ensure categories are ordered by total_count descending."""
        if len(v) > 1:
            for i in range(len(v) - 1):
                if v[i].total_count < v[i + 1].total_count:
                    raise ValueError('Categories must be ordered by total_count descending')
        return v


class EmailAccountInfo(BaseModel):
    """Information about an email account being tracked."""
    id: int = Field(gt=0, description="Unique account identifier")
    email_address: str = Field(description="Gmail email address")
    display_name: Optional[str] = Field(
        None,
        description="Optional display name for the account"
    )
    masked_password: Optional[str] = Field(
        None,
        description="Masked app password showing first 2 and last 2 characters (e.g., 'ab********yz')"
    )
    is_active: bool = Field(
        default=True,
        description="Whether the account is actively being scanned"
    )
    last_scan_at: Optional[datetime] = Field(
        None,
        description="Timestamp of the last successful email scan"
    )
    created_at: datetime = Field(description="When the account was first added to tracking")


class AccountListResponse(BaseModel):
    """Response model for listing all tracked email accounts."""
    accounts: List[EmailAccountInfo] = Field(
        description="List of all tracked email accounts"
    )
    total_count: int = Field(
        ge=0, 
        description="Total number of accounts in the system"
    )

    @validator('total_count')
    def validate_count_matches(cls, v, values):
        """Ensure total_count matches the actual number of accounts."""
        if 'accounts' in values and v != len(values['accounts']):
            raise ValueError('total_count must match the number of accounts in the list')
        return v