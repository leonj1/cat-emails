"""
Blocking Recommendation Service Implementation.

Analyzes email category tallies and generates intelligent recommendations
for categories users should consider blocking.
"""
from datetime import date, datetime, timedelta
from typing import Dict, List

from services.interfaces.blocking_recommendation_interface import (
    IBlockingRecommendationService
)
from services.interfaces.category_aggregation_config_interface import (
    ICategoryAggregationConfig
)
from repositories.category_tally_repository_interface import (
    ICategoryTallyRepository
)
from models.recommendation_models import (
    BlockingRecommendation,
    BlockingRecommendationResult,
    RecommendationReason,
    RecommendationStrength,
    DailyBreakdown
)
from services.trend_calculator import (
    calculate_trend,
    calculate_trend_percentage_change,
    generate_trend_factor
)


class BlockingRecommendationService(IBlockingRecommendationService):
    """
    Implementation of blocking recommendation service.

    Analyzes email category tallies and generates recommendations based on:
    - Percentage thresholds (HIGH: >=25%, MEDIUM: >=15%, LOW: >=threshold)
    - Volume minimums (minimum_count)
    - Category exclusions (Personal, Work-related, Financial-Notification)
    - Already blocked categories
    """

    def __init__(
        self,
        repository: ICategoryTallyRepository,
        config: ICategoryAggregationConfig,
        domain_service
    ):
        """
        Initialize the blocking recommendation service.

        Args:
            repository: Repository for accessing category tallies
            config: Configuration for thresholds and exclusions
            domain_service: Domain service for fetching blocked categories
        """
        self._repository = repository
        self._config = config
        self._domain_service = domain_service

    def get_recommendations(
        self,
        email_address: str,
        days: int = 7
    ) -> BlockingRecommendationResult:
        """
        Get blocking recommendations for an email account.

        Algorithm (per spec section 4.3):
        1. Fetch tallies for the rolling window period
        2. Aggregate counts by category
        3. Calculate total emails and percentages
        4. Filter out excluded categories
        5. Filter out categories below minimum count
        6. Filter out categories below percentage threshold
        7. Assign strength levels (HIGH/MEDIUM/LOW)
        8. Sort by email count descending
        9. Fetch already blocked categories

        Args:
            email_address: Email account address to analyze
            days: Number of days to look back (default: 7)

        Returns:
            BlockingRecommendationResult with recommendations and metadata
        """
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Fetch tallies for the period
        tallies = self._repository.get_tallies_for_period(
            email_address,
            start_date,
            end_date
        )

        # Aggregate counts by category
        category_totals: Dict[str, int] = {}
        for tally in tallies:
            for category, count in tally.category_counts.items():
                category_totals[category] = category_totals.get(category, 0) + count

        # Calculate total emails
        total_emails = sum(category_totals.values())

        # Get configuration values
        threshold_pct = self._config.get_recommendation_threshold_percentage()
        min_count = self._config.get_minimum_email_count()
        excluded = self._config.get_excluded_categories()

        # Generate recommendations
        recommendations: List[BlockingRecommendation] = []

        for category, count in category_totals.items():
            # Skip excluded categories
            if category in excluded:
                continue

            # Skip categories below minimum count
            if count < min_count:
                continue

            # Calculate percentage
            percentage = (count / total_emails * 100) if total_emails > 0 else 0.0

            # Skip categories below percentage threshold
            if percentage < threshold_pct:
                continue

            # Determine strength level (HIGH >= 25%, MEDIUM >= 15%, LOW >= threshold)
            if percentage >= 25.0:
                strength = RecommendationStrength.HIGH
            elif percentage >= 15.0:
                strength = RecommendationStrength.MEDIUM
            else:
                strength = RecommendationStrength.LOW

            # Generate reason
            strength_text = strength.value.upper()
            reason = (
                f"{strength_text} priority: {category} represents "
                f"{percentage:.0f}% of your inbox ({count} emails)"
            )

            # Create recommendation
            recommendation = BlockingRecommendation(
                category=category,
                strength=strength,
                email_count=count,
                percentage=round(percentage, 1),
                reason=reason
            )
            recommendations.append(recommendation)

        # Sort by email count descending
        recommendations.sort(key=lambda r: r.email_count, reverse=True)

        # Fetch already blocked categories
        already_blocked = self.get_blocked_categories_for_account(email_address)

        # Return result
        return BlockingRecommendationResult(
            email_address=email_address,
            period_start=start_date,
            period_end=end_date,
            total_emails_analyzed=total_emails,
            recommendations=recommendations,
            already_blocked=already_blocked,
            generated_at=datetime.now()
        )

    def get_recommendation_reasons(
        self,
        email_address: str,
        category: str,
        days: int = 7
    ) -> RecommendationReason:
        """
        Get detailed reasons why a category is recommended for blocking.

        Provides comprehensive breakdown including:
        - Daily tallies
        - Trend analysis (increasing/decreasing/stable)
        - Comparable categories
        - Recommendation factors

        Args:
            email_address: Email account address
            category: Category to analyze
            days: Number of days to look back (default: 7)

        Returns:
            RecommendationReason with detailed breakdown
        """
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Fetch tallies for the period
        tallies = self._repository.get_tallies_for_period(
            email_address,
            start_date,
            end_date
        )

        # Build daily breakdown for the category
        daily_counts: Dict[date, int] = {}
        category_totals: Dict[str, int] = {}

        for tally in tallies:
            # Record daily count for this category
            daily_counts[tally.tally_date] = tally.category_counts.get(category, 0)

            # Build totals for all categories
            for cat, count in tally.category_counts.items():
                category_totals[cat] = category_totals.get(cat, 0) + count

        # Create daily breakdown objects (sorted by date)
        daily_breakdown = [
            DailyBreakdown(date=day, count=daily_counts.get(day, 0))
            for day in sorted(daily_counts.keys())
        ]

        # Calculate trend
        trend_direction = calculate_trend(daily_breakdown)
        trend_pct_change = calculate_trend_percentage_change(daily_breakdown)

        # Calculate total and percentage
        total_count = category_totals.get(category, 0)
        total_emails = sum(category_totals.values())
        percentage = (total_count / total_emails * 100) if total_emails > 0 else 0.0

        # Build comparable categories (other top categories with percentages)
        comparable = {}
        for cat, count in category_totals.items():
            if cat != category:
                cat_pct = (count / total_emails * 100) if total_emails > 0 else 0.0
                comparable[cat] = round(cat_pct, 1)

        # Generate recommendation factors
        factors = [
            f"High volume: {total_count} emails in {category}",
            f"Significant percentage: {percentage:.1f}% of inbox",
            generate_trend_factor(trend_direction, trend_pct_change)
        ]

        return RecommendationReason(
            category=category,
            total_count=total_count,
            percentage=round(percentage, 1),
            daily_breakdown=daily_breakdown,
            trend_direction=trend_direction,
            trend_percentage_change=round(trend_pct_change, 1),
            comparable_categories=comparable,
            recommendation_factors=factors
        )

    def get_blocked_categories_for_account(
        self,
        email_address: str
    ) -> List[str]:
        """
        Get list of categories blocked globally (not per-account).

        NOTE: Current implementation returns GLOBAL blocked categories from
        the Control API. The email_address parameter is part of the interface
        contract but is currently unused since the domain_service does not
        support per-account category blocking. Future enhancement could add
        account-specific blocking by passing email_address to domain service.

        Args:
            email_address: Email account address (currently unused - returns global categories)

        Returns:
            List of category names that are globally blocked
        """
        # email_address is unused because fetch_blocked_categories() returns global config
        # This is intentional - interface designed for future per-account blocking support
        blocked_categories_list = self._domain_service.fetch_blocked_categories()
        return [bc.category for bc in blocked_categories_list]
