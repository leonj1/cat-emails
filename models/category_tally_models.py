"""
Pydantic models for category tally data.

These models represent daily email category tallies and aggregated statistics
for the email category aggregation and blocking recommendations system.
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime, date


class DailyCategoryTally(BaseModel):
    """
    Represents a daily tally of email categories for a specific account.

    This model is used for both input/output in repository operations.
    """
    id: Optional[int] = Field(None, description="Unique identifier (None for new records)")
    email_address: str = Field(description="Email account address")
    tally_date: date = Field(description="Date for this tally")
    category_counts: Dict[str, int] = Field(
        description="Dictionary of category names to email counts"
    )
    total_emails: int = Field(ge=0, description="Total emails across all categories")
    created_at: datetime = Field(description="When this tally was first created")
    updated_at: datetime = Field(description="When this tally was last updated")


class CategorySummaryItem(BaseModel):
    """
    Represents summary statistics for a single email category.

    Used as part of AggregatedCategoryTally to show category-level metrics.
    """
    category: str = Field(description="Email category name")
    total_count: int = Field(ge=0, description="Total emails in this category")
    percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage of total emails this category represents"
    )
    daily_average: float = Field(
        ge=0.0,
        description="Average emails per day for this category"
    )
    trend: Optional[str] = Field(
        None,
        description="Optional trend indicator (e.g., 'increasing', 'decreasing')"
    )


class AggregatedCategoryTally(BaseModel):
    """
    Represents aggregated category statistics across a date range.

    This model combines data from multiple daily tallies to provide
    summary statistics and insights.
    """
    email_address: str = Field(description="Email account address")
    start_date: date = Field(description="Start date of aggregation period")
    end_date: date = Field(description="End date of aggregation period")
    total_emails: int = Field(ge=0, description="Total emails across all days and categories")
    days_with_data: int = Field(ge=0, description="Number of days that have tally data")
    category_summaries: List[CategorySummaryItem] = Field(
        description="List of category summaries with statistics"
    )
