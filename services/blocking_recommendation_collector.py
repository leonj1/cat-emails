"""
Blocking Recommendation Collector Implementation.

This service collects domain blocking recommendations during email processing.
It tracks domains from qualifying categories that are not already blocked,
aggregates counts, and provides sorted recommendations.
"""
from typing import List, Set, Dict, Tuple
from collections import defaultdict

from services.interfaces.blocking_recommendation_collector_interface import (
    IBlockingRecommendationCollector
)
from models.domain_recommendation_models import DomainRecommendation, RecommendationSummary


class BlockingRecommendationCollector(IBlockingRecommendationCollector):
    """
    Implementation of the blocking recommendation collector.

    This collector:
    1. Filters by qualifying categories: Marketing, Advertising, Wants-Money
    2. Excludes already-blocked domains (case-insensitive comparison)
    3. Aggregates counts per (domain, category) pair
    4. Returns sorted recommendations: count desc, then domain alpha
    """

    # Class-level constant for canonical qualifying categories (public API)
    QUALIFYING_CATEGORIES: Set[str] = {
        "Marketing",
        "Advertising",
        "Wants-Money"
    }

    # Internal set that includes normalized variants
    # Note: EmailProcessorService normalizes categories by removing hyphens,
    # so we accept both "Wants-Money" and "WantsMoney"
    _QUALIFYING_CATEGORIES_INTERNAL: Set[str] = {
        "Marketing",
        "Advertising",
        "Wants-Money",
        "WantsMoney"
    }

    def __init__(self):
        """
        Initialize the collector with empty state.

        Internal state:
        - domain_category_counts: Dict[(domain_lower, category)] -> count
        """
        # Use (domain.lower(), category) as key to track counts
        self._domain_category_counts: Dict[Tuple[str, str], int] = defaultdict(int)

    def collect(
        self,
        sender_domain: str,
        category: str,
        blocked_domains: Set[str]
    ) -> None:
        """
        Collect a domain if it qualifies for blocking recommendations.

        Algorithm:
        1. Check if domain is in blocked_domains (case-insensitive)
        2. Check if category is in QUALIFYING_CATEGORIES
        3. If both checks pass, increment count for (domain, category)

        Args:
            sender_domain: Email sender domain to evaluate
            category: Email category
            blocked_domains: Set of domains already blocked by the user
        """
        # Convert sender_domain to lowercase for case-insensitive comparison
        sender_domain_lower = sender_domain.lower()

        # Check if domain is blocked (case-insensitive)
        blocked_domains_lower = {d.lower() for d in blocked_domains}
        if sender_domain_lower in blocked_domains_lower:
            return

        # Check if category qualifies (use internal set that includes normalized variants)
        if category not in self._QUALIFYING_CATEGORIES_INTERNAL:
            return

        # Increment count for this (domain, category) pair
        key = (sender_domain_lower, category)
        self._domain_category_counts[key] += 1

    def get_recommendations(self) -> List[DomainRecommendation]:
        """
        Get the list of domain blocking recommendations.

        Returns recommendations sorted by:
        1. Count descending (most emails first)
        2. Domain alphabetically (for same count)

        Returns:
            List of DomainRecommendation objects
        """
        recommendations = []

        # Convert internal counts to DomainRecommendation objects
        for (domain, category), count in self._domain_category_counts.items():
            recommendations.append(
                DomainRecommendation(
                    domain=domain,
                    category=category,
                    count=count
                )
            )

        # Sort by count descending, then by domain alphabetically
        recommendations.sort(key=lambda r: (-r.count, r.domain))

        return recommendations

    def clear(self) -> None:
        """
        Clear all collected recommendations and reset state.

        This should be called at the start of each processing run
        to ensure recommendations reflect only the current run.
        """
        self._domain_category_counts.clear()

    def get_total_emails_matched(self) -> int:
        """
        Get the total count of emails matched across all domains.

        This is the sum of all counts for all (domain, category) pairs.

        Returns:
            Total number of qualifying emails collected
        """
        return sum(self._domain_category_counts.values())

    def get_unique_domains_count(self) -> int:
        """
        Get the count of unique (domain, category) pairs.

        Note: Same domain in different categories counts as separate entries.

        Returns:
            Number of unique (domain, category) pairs
        """
        return len(self._domain_category_counts)

    def get_qualifying_categories(self) -> Set[str]:
        """
        Get the set of qualifying categories.

        Returns:
            Set of category names that qualify for blocking recommendations
        """
        return self.QUALIFYING_CATEGORIES.copy()

    def get_summary(self) -> RecommendationSummary:
        """
        Get the complete recommendation summary.

        Returns a RecommendationSummary object containing:
        - recommendations: List of DomainRecommendation objects (sorted)
        - total_count: Total number of qualifying emails matched

        Returns:
            RecommendationSummary object
        """
        recommendations = self.get_recommendations()
        total_count = self.get_total_emails_matched()

        return RecommendationSummary(
            recommendations=recommendations,
            total_count=total_count
        )
