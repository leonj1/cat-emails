"""
Blocking Recommendation Service Interface.

This interface defines the contract for generating blocking recommendations
based on email category analysis.
"""
from abc import ABC, abstractmethod
from typing import List

from models.recommendation_models import (
    BlockingRecommendationResult,
    RecommendationReason
)


class IBlockingRecommendationService(ABC):
    """
    Abstract interface for blocking recommendation operations.

    This service analyzes email category tallies and generates intelligent
    recommendations for categories users should consider blocking.
    """

    @abstractmethod
    def get_recommendations(
        self,
        email_address: str,
        days: int = 7
    ) -> BlockingRecommendationResult:
        """
        Get blocking recommendations for an email account.

        Analyzes category tallies over a rolling window period and generates
        recommendations based on percentage thresholds and volume.

        Args:
            email_address: Email account address to analyze
            days: Number of days to look back (default: 7)

        Returns:
            BlockingRecommendationResult with recommendations and metadata

        Raises:
            ValueError: If parameters are invalid
        """
        pass

    @abstractmethod
    def get_recommendation_reasons(
        self,
        email_address: str,
        category: str,
        days: int = 7
    ) -> RecommendationReason:
        """
        Get detailed reasons why a category is recommended for blocking.

        Provides comprehensive breakdown including daily tallies, trend analysis,
        and comparison with other categories.

        Args:
            email_address: Email account address
            category: Category to analyze
            days: Number of days to look back (default: 7)

        Returns:
            RecommendationReason with detailed breakdown

        Raises:
            ValueError: If parameters are invalid or category not found
        """
        pass

    @abstractmethod
    def get_blocked_categories_for_account(
        self,
        email_address: str
    ) -> List[str]:
        """
        Get list of categories already blocked for an account.

        Queries the domain service to fetch current blocked categories.

        Args:
            email_address: Email account address

        Returns:
            List of category names that are currently blocked
        """
        pass
