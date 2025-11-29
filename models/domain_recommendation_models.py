"""
Domain Recommendation Data Models.

This module provides data structures for domain blocking recommendations
during email processing. The DomainRecommendation represents a single
recommendation to block a domain based on its category and frequency.
"""
from dataclasses import dataclass
from typing import Dict, List, Any, Optional


@dataclass(frozen=True)
class DomainRecommendation:
    """
    Represents a recommendation to block a specific domain.

    This is an immutable data structure that contains:
    - domain: The sender domain being recommended for blocking
    - category: The qualifying category (Marketing, Advertising, Wants-Money)
    - count: Number of emails from this domain in this category

    The frozen=True makes this dataclass immutable after creation.
    """
    domain: str
    category: str
    count: int

    def to_dict(self) -> Dict[str, any]:
        """
        Convert the recommendation to a dictionary.

        Returns:
            Dictionary with domain, category, and count fields
        """
        return {
            "domain": self.domain,
            "category": self.category,
            "count": self.count
        }


@dataclass
class RecommendationSummary:
    """
    Represents a summary of domain blocking recommendations.

    This dataclass aggregates all recommendations and provides
    methods for serialization and accessing derived properties.

    Attributes:
        recommendations: List of DomainRecommendation objects
        total_count: Total number of qualifying emails matched
    """
    recommendations: List[DomainRecommendation]
    total_count: int

    @property
    def domain_count(self) -> int:
        """
        Get the count of unique (domain, category) pairs.

        Returns:
            Number of recommendations in the list
        """
        return len(self.recommendations)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the summary to a dictionary for API response.

        Returns:
            Dictionary with keys:
            - recommended_domains_to_block: list of recommendation dicts
            - total_emails_matched: total count of qualifying emails
            - unique_domains_count: number of unique recommendations
        """
        return {
            "recommended_domains_to_block": [r.to_dict() for r in self.recommendations],
            "total_emails_matched": self.total_count,
            "unique_domains_count": self.domain_count
        }


@dataclass(frozen=True)
class NotificationResult:
    """
    Represents the result of sending a recommendation email notification.

    This is an immutable data structure that contains:
    - success: Whether the notification was sent successfully
    - recipient: The email address that received the notification
    - recommendations_count: Number of recommendations in the notification
    - error_message: Error details if sending failed (None if successful)

    The frozen=True makes this dataclass immutable after creation.
    """
    success: bool
    recipient: str
    recommendations_count: int
    error_message: Optional[str]
