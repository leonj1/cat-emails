"""
Blocking Recommendation Collector Interface.

This interface defines the contract for collecting domain recommendations
during email processing. It tracks domains from qualifying categories
(Marketing, Advertising, Wants-Money) that are not already blocked.
"""
from abc import ABC, abstractmethod
from typing import List, Set

from models.domain_recommendation_models import DomainRecommendation, RecommendationSummary


class IBlockingRecommendationCollector(ABC):
    """
    Abstract interface for collecting domain blocking recommendations.

    This collector is used during email processing to track domains
    that qualify for blocking recommendations based on:
    - Category: Must be Marketing, Advertising, or Wants-Money
    - Not already blocked: Domain must not be in the blocked list
    - Aggregation: Counts are aggregated per (domain, category) pair
    """

    @abstractmethod
    def collect(
        self,
        sender_domain: str,
        category: str,
        blocked_domains: Set[str]
    ) -> None:
        """
        Collect a domain if it qualifies for blocking recommendations.

        Records the domain if:
        - Category is Marketing, Advertising, or Wants-Money
        - Domain is not in the blocked_domains set (case-insensitive)

        Args:
            sender_domain: Email sender domain to evaluate
            category: Email category
            blocked_domains: Set of domains already blocked by the user
        """
        pass

    @abstractmethod
    def get_recommendations(self) -> List[DomainRecommendation]:
        """
        Get the list of domain blocking recommendations.

        Returns:
            List of DomainRecommendation objects sorted by:
            1. Count descending (most emails first)
            2. Domain alphabetically (for same count)
        """
        pass

    @abstractmethod
    def get_summary(self) -> RecommendationSummary:
        """
        Get the complete recommendation summary.

        Returns:
            RecommendationSummary object containing:
            - recommendations: List of DomainRecommendation objects
            - total_count: Total number of qualifying emails matched
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        Clear all collected recommendations and reset state.

        This should be called at the start of each processing run
        to ensure recommendations reflect only the current run.
        """
        pass
