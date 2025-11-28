"""
Pydantic models for blocking recommendation detailed reasons.

These models provide detailed breakdown information for why a category
is recommended for blocking, including daily tallies and trend analysis.
"""
from pydantic import BaseModel, Field
from typing import Dict, List
from enum import Enum
import datetime as dt


class RecommendationStrength(str, Enum):
    """
    Strength levels for blocking recommendations.

    Based on percentage of inbox:
    - HIGH: >= 25% of inbox
    - MEDIUM: >= 15% of inbox
    - LOW: >= threshold (default 10%)
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DailyBreakdown(BaseModel):
    """
    Represents email count for a single day.

    Used to provide daily-level detail in recommendation reasons.
    """
    date: dt.date = Field(description="Date for this count")
    count: int = Field(ge=0, description="Number of emails on this date")


class BlockingRecommendation(BaseModel):
    """
    A single blocking recommendation for an email category.

    Contains the category name, strength level, email count, percentage,
    and human-readable reason for the recommendation.
    """
    category: str = Field(description="Email category name")
    strength: RecommendationStrength = Field(
        description="Recommendation strength: high, medium, or low"
    )
    email_count: int = Field(ge=0, description="Total emails in this category")
    percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage of total emails this category represents"
    )
    reason: str = Field(description="Human-readable reason for this recommendation")


class BlockingRecommendationResult(BaseModel):
    """
    Complete result of a blocking recommendation analysis.

    Contains the analysis period, total emails analyzed, list of recommendations,
    and list of already blocked categories.
    """
    email_address: str = Field(description="Email account address")
    period_start: dt.date = Field(description="Start date of analysis period")
    period_end: dt.date = Field(description="End date of analysis period")
    total_emails_analyzed: int = Field(
        ge=0,
        description="Total emails analyzed across all categories"
    )
    recommendations: List[BlockingRecommendation] = Field(
        description="List of recommendations sorted by email count descending"
    )
    already_blocked: List[str] = Field(
        description="Categories already blocked by the user"
    )
    generated_at: dt.datetime = Field(description="When this analysis was generated")


class RecommendationReason(BaseModel):
    """
    Detailed reasons why a category is recommended for blocking.

    Provides comprehensive information including daily breakdown, trend analysis,
    comparable categories, and specific recommendation factors.
    """
    category: str = Field(description="Email category name")
    total_count: int = Field(ge=0, description="Total emails in this category")
    percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage of total emails this category represents"
    )
    daily_breakdown: List[DailyBreakdown] = Field(
        description="Daily email counts for this category"
    )
    trend_direction: str = Field(
        description="Trend direction: 'increasing', 'decreasing', or 'stable'"
    )
    trend_percentage_change: float = Field(
        description="Percentage change in trend (positive or negative)"
    )
    comparable_categories: Dict[str, float] = Field(
        description="Other categories and their percentages for comparison"
    )
    recommendation_factors: List[str] = Field(
        description="List of human-readable reasons for this recommendation"
    )
