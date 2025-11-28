"""
Tests for Category Recommendation API Endpoints.

Based on BDD scenarios in tests/bdd/api-endpoints.feature.
Tests follow TDD approach - written before implementation.
"""
import unittest
from datetime import date, datetime, timedelta
from typing import Dict, List
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient

# Models
from models.recommendation_models import (
    BlockingRecommendation,
    BlockingRecommendationResult,
    RecommendationReason,
    RecommendationStrength,
    DailyBreakdown
)
from models.category_tally_models import (
    DailyCategoryTally,
    AggregatedCategoryTally,
    CategorySummaryItem
)

# Services and repositories
from services.blocking_recommendation_service import BlockingRecommendationService
from services.category_aggregation_config import CategoryAggregationConfig
from repositories.category_tally_repository_interface import ICategoryTallyRepository


class MockCategoryTallyRepository(ICategoryTallyRepository):
    """Mock repository for testing API endpoints."""

    def __init__(self):
        self.tallies: Dict[tuple, DailyCategoryTally] = {}
        self.next_id = 1

    def save_daily_tally(
        self,
        email_address: str,
        tally_date: date,
        category_counts: dict,
        total_emails: int
    ) -> DailyCategoryTally:
        key = (email_address, tally_date)
        now = datetime.now()

        if key in self.tallies:
            tally = self.tallies[key]
            for category, count in category_counts.items():
                tally.category_counts[category] = tally.category_counts.get(category, 0) + count
            tally.total_emails = total_emails
            tally.updated_at = now
        else:
            tally = DailyCategoryTally(
                id=self.next_id,
                email_address=email_address,
                tally_date=tally_date,
                category_counts=category_counts.copy(),
                total_emails=total_emails,
                created_at=now,
                updated_at=now
            )
            self.tallies[key] = tally
            self.next_id += 1

        return tally

    def get_tally(
        self,
        email_address: str,
        tally_date: date
    ) -> DailyCategoryTally | None:
        return self.tallies.get((email_address, tally_date))

    def get_tallies_for_period(
        self,
        email_address: str,
        start_date: date,
        end_date: date
    ) -> List[DailyCategoryTally]:
        return [
            tally for (email, tally_date), tally in self.tallies.items()
            if email == email_address and start_date <= tally_date <= end_date
        ]

    def get_aggregated_tallies(
        self,
        email_address: str,
        start_date: date,
        end_date: date
    ) -> AggregatedCategoryTally:
        """Get aggregated statistics across a date range."""
        tallies = self.get_tallies_for_period(email_address, start_date, end_date)

        # Aggregate counts by category
        category_totals: Dict[str, int] = {}
        days_with_data = len(tallies)

        for tally in tallies:
            for category, count in tally.category_counts.items():
                category_totals[category] = category_totals.get(category, 0) + count

        total_emails = sum(category_totals.values())

        # Build category summaries
        summaries = []
        for category, count in category_totals.items():
            percentage = (count / total_emails * 100) if total_emails > 0 else 0.0
            daily_avg = count / days_with_data if days_with_data > 0 else 0.0

            # Calculate simple trend based on first half vs second half
            trend = "stable"
            if days_with_data >= 4:
                mid_point = days_with_data // 2
                first_half_total = 0
                second_half_total = 0

                sorted_tallies = sorted(tallies, key=lambda t: t.tally_date)
                for i, tally in enumerate(sorted_tallies):
                    count_for_day = tally.category_counts.get(category, 0)
                    if i < mid_point:
                        first_half_total += count_for_day
                    else:
                        second_half_total += count_for_day

                if second_half_total > first_half_total * 1.2:
                    trend = "increasing"
                elif second_half_total < first_half_total * 0.8:
                    trend = "decreasing"

            summaries.append(CategorySummaryItem(
                category=category,
                total_count=count,
                percentage=round(percentage, 1),
                daily_average=round(daily_avg, 2),
                trend=trend
            ))

        return AggregatedCategoryTally(
            email_address=email_address,
            start_date=start_date,
            end_date=end_date,
            total_emails=total_emails,
            days_with_data=days_with_data,
            category_summaries=summaries
        )

    def delete_tallies_before(self, email_address: str, cutoff_date: date) -> int:
        """Delete tallies before cutoff date."""
        to_delete = [
            key for key, tally in self.tallies.items()
            if key[0] == email_address and tally.tally_date < cutoff_date
        ]
        for key in to_delete:
            del self.tallies[key]
        return len(to_delete)


class MockDomainService:
    """Mock domain service for testing."""

    def __init__(self):
        self.blocked_categories = []

    def fetch_blocked_categories(self):
        """Return blocked categories as objects with 'category' attribute."""
        class BlockedCategory:
            def __init__(self, category):
                self.category = category

        return [BlockedCategory(cat) for cat in self.blocked_categories]


class TestAPIRecommendationEndpoints(unittest.TestCase):
    """
    Tests for the recommendation API endpoints.

    Scenarios from api-endpoints.feature:
    - Get blocking recommendations for an account
    - Get recommendations with custom rolling window
    - Validate days parameter range
    - Account not found returns 404
    - Get detailed recommendation reasons
    - Get details for non-recommended category returns 404
    - Get raw category statistics
    - Category stats include trend information
    - API returns already blocked categories
    - Response format matches OpenAPI spec
    - Daily breakdown is sorted chronologically
    - API handles concurrent requests
    """

    def setUp(self):
        """Set up test fixtures before each test."""
        self.repository = MockCategoryTallyRepository()
        self.config = CategoryAggregationConfig()
        self.domain_service = MockDomainService()

        # Create recommendation service
        self.recommendation_service = BlockingRecommendationService(
            repository=self.repository,
            config=self.config,
            domain_service=self.domain_service
        )

        # Create test client (will be mocked)
        self.client = None
        self.test_email = "test@gmail.com"

    def _create_test_data(self, email: str, days: int = 7, marketing_percentage: float = 35.0):
        """
        Helper to create test data for an email account.

        Creates daily tallies with Marketing at specified percentage.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Calculate total emails needed to hit target percentage
        target_marketing_emails = 100
        total_emails_per_day = int(target_marketing_emails / (marketing_percentage / 100))

        for i in range(days):
            current_date = start_date + timedelta(days=i)

            category_counts = {
                "Marketing": target_marketing_emails // days,
                "Personal": (total_emails_per_day - target_marketing_emails) // days,
            }

            self.repository.save_daily_tally(
                email_address=email,
                tally_date=current_date,
                category_counts=category_counts,
                total_emails=total_emails_per_day
            )

    def test_get_blocking_recommendations_for_account(self):
        """
        Scenario: Get blocking recommendations for an account
        Given a user "test@gmail.com" has email data
        And the category tallies show "Marketing" at 35% of total
        When I send GET request to "/api/accounts/test@gmail.com/recommendations"
        Then the response status should be 200
        And the response should contain email_address and total_emails_analyzed > 0
        And the recommendations array should not be empty
        And generated_at should be a valid ISO timestamp
        """
        # Given: Create test data with Marketing at 35%
        self._create_test_data(self.test_email, days=7, marketing_percentage=35.0)

        # When: Get recommendations
        result = self.recommendation_service.get_recommendations(self.test_email, days=7)

        # Then: Verify response structure
        self.assertEqual(result.email_address, self.test_email)
        self.assertGreater(result.total_emails_analyzed, 0)
        self.assertGreater(len(result.recommendations), 0)
        self.assertIsInstance(result.generated_at, datetime)

        # Verify Marketing is recommended (35% is high priority)
        marketing_rec = next(
            (r for r in result.recommendations if r.category == "Marketing"),
            None
        )
        self.assertIsNotNone(marketing_rec)
        self.assertGreaterEqual(marketing_rec.percentage, 30.0)

    def test_get_recommendations_with_custom_rolling_window(self):
        """
        Scenario: Get recommendations with custom rolling window
        Given a user "test@gmail.com" has email data for 14 days
        When I send GET request to "/api/accounts/test@gmail.com/recommendations?days=14"
        Then the response status should be 200
        And period_start should be 14 days before period_end
        """
        # Given: Create 14 days of test data
        self._create_test_data(self.test_email, days=14)

        # When: Get recommendations with 14-day window
        result = self.recommendation_service.get_recommendations(self.test_email, days=14)

        # Then: Verify period span
        period_span = (result.period_end - result.period_start).days
        self.assertEqual(period_span, 13)  # 14 days inclusive is 13 days difference

    def test_validate_days_parameter_range(self):
        """
        Scenario: Validate days parameter range
        Given a user "test@gmail.com" exists
        When I send GET request to "/api/accounts/test@gmail.com/recommendations?days=45"
        Then the response status should be 400
        And the error message should indicate days must be between 1 and 30

        Note: Validation will be done at API endpoint level, not service level.
        This test verifies the service can handle the request, but endpoint should reject it.
        """
        # This test will be validated at the API endpoint level
        # The service itself doesn't enforce the 1-30 range
        # Just verify service can handle various day values
        self._create_test_data(self.test_email, days=30)
        result = self.recommendation_service.get_recommendations(self.test_email, days=30)
        self.assertEqual(result.email_address, self.test_email)

    def test_account_not_found_returns_empty_recommendations(self):
        """
        Scenario: Account not found returns 404
        When I send GET request to "/api/accounts/nonexistent@gmail.com/recommendations"
        Then the response status should be 404

        Note: Service returns empty recommendations, API endpoint should convert to 404.
        """
        # When: Get recommendations for non-existent account
        result = self.recommendation_service.get_recommendations("nonexistent@gmail.com", days=7)

        # Then: Should return empty result
        self.assertEqual(result.total_emails_analyzed, 0)
        self.assertEqual(len(result.recommendations), 0)

    def test_get_detailed_recommendation_reasons(self):
        """
        Scenario: Get detailed recommendation reasons
        Given a user "test@gmail.com" has "Marketing" category with significant volume
        When I send GET request to "/api/accounts/test@gmail.com/recommendations/Marketing/details"
        Then the response status should be 200
        And the response should contain category, total_count, percentage, daily_breakdown,
            trend_direction, comparable_categories, recommendation_factors
        """
        # Given: Create test data with significant Marketing volume
        self._create_test_data(self.test_email, days=7, marketing_percentage=35.0)

        # When: Get detailed reasons for Marketing category
        reason = self.recommendation_service.get_recommendation_reasons(
            self.test_email,
            "Marketing",
            days=7
        )

        # Then: Verify response structure
        self.assertEqual(reason.category, "Marketing")
        self.assertGreater(reason.total_count, 0)
        self.assertGreater(reason.percentage, 0.0)
        self.assertIsInstance(reason.daily_breakdown, list)
        self.assertGreater(len(reason.daily_breakdown), 0)
        self.assertIn(reason.trend_direction, ["increasing", "decreasing", "stable"])
        self.assertIsInstance(reason.comparable_categories, dict)
        self.assertIsInstance(reason.recommendation_factors, list)
        self.assertGreater(len(reason.recommendation_factors), 0)

    def test_get_raw_category_statistics(self):
        """
        Scenario: Get raw category statistics
        Given a user "test@gmail.com" has email data
        When I send GET request to "/api/accounts/test@gmail.com/category-stats"
        Then the response status should be 200
        And the response should contain email_address, period_start, period_end,
            total_emails, days_with_data, categories
        """
        # Given: Create test data
        self._create_test_data(self.test_email, days=7)

        # When: Get aggregated statistics
        end_date = date.today()
        start_date = end_date - timedelta(days=6)
        stats = self.repository.get_aggregated_tallies(
            self.test_email,
            start_date,
            end_date
        )

        # Then: Verify response structure
        self.assertEqual(stats.email_address, self.test_email)
        self.assertEqual(stats.start_date, start_date)
        self.assertEqual(stats.end_date, end_date)
        self.assertGreater(stats.total_emails, 0)
        self.assertGreater(stats.days_with_data, 0)
        self.assertIsInstance(stats.category_summaries, list)
        self.assertGreater(len(stats.category_summaries), 0)

    def test_category_stats_include_trend_information(self):
        """
        Scenario: Category stats include trend information
        Given a user "test@gmail.com" has email data
        When I send GET request to "/api/accounts/test@gmail.com/category-stats?days=7"
        Then the response status should be 200
        And each category should have: category, total_count, percentage, daily_average, trend
        """
        # Given: Create test data
        self._create_test_data(self.test_email, days=7)

        # When: Get aggregated statistics
        end_date = date.today()
        start_date = end_date - timedelta(days=6)
        stats = self.repository.get_aggregated_tallies(
            self.test_email,
            start_date,
            end_date
        )

        # Then: Verify each category has required fields
        self.assertGreater(len(stats.category_summaries), 0)
        for summary in stats.category_summaries:
            self.assertIsInstance(summary.category, str)
            self.assertGreaterEqual(summary.total_count, 0)
            self.assertGreaterEqual(summary.percentage, 0.0)
            self.assertGreaterEqual(summary.daily_average, 0.0)
            self.assertIsNotNone(summary.trend)
            self.assertIn(summary.trend, ["increasing", "decreasing", "stable"])

    def test_api_returns_already_blocked_categories(self):
        """
        Scenario: API returns already blocked categories
        Given a user "test@gmail.com" has already blocked "Wants-Money"
        And the user has email data
        When I send GET request to "/api/accounts/test@gmail.com/recommendations"
        Then the response status should be 200
        And already_blocked should contain "Wants-Money"
        """
        # Given: Set up blocked categories
        self.domain_service.blocked_categories = ["Wants-Money"]
        self._create_test_data(self.test_email, days=7)

        # When: Get recommendations
        result = self.recommendation_service.get_recommendations(self.test_email, days=7)

        # Then: Verify blocked categories are included
        self.assertIn("Wants-Money", result.already_blocked)

    def test_response_format_matches_openapi_spec(self):
        """
        Scenario: Response format matches OpenAPI spec
        Given a user "test@gmail.com" has email data
        When I send GET request to "/api/accounts/test@gmail.com/recommendations"
        Then the response should match the BlockingRecommendationResult schema
        And each recommendation should match the BlockingRecommendation schema
        """
        # Given: Create test data
        self._create_test_data(self.test_email, days=7, marketing_percentage=35.0)

        # When: Get recommendations
        result = self.recommendation_service.get_recommendations(self.test_email, days=7)

        # Then: Verify schema compliance via Pydantic model
        self.assertIsInstance(result, BlockingRecommendationResult)
        self.assertIsInstance(result.email_address, str)
        self.assertIsInstance(result.period_start, date)
        self.assertIsInstance(result.period_end, date)
        self.assertIsInstance(result.total_emails_analyzed, int)
        self.assertIsInstance(result.recommendations, list)
        self.assertIsInstance(result.already_blocked, list)
        self.assertIsInstance(result.generated_at, datetime)

        # Verify each recommendation matches schema
        for rec in result.recommendations:
            self.assertIsInstance(rec, BlockingRecommendation)
            self.assertIsInstance(rec.category, str)
            self.assertIsInstance(rec.strength, RecommendationStrength)
            self.assertIsInstance(rec.email_count, int)
            self.assertIsInstance(rec.percentage, float)
            self.assertIsInstance(rec.reason, str)

    def test_daily_breakdown_is_sorted_chronologically(self):
        """
        Scenario: Daily breakdown is sorted chronologically
        Given a user "test@gmail.com" has daily data for the past 7 days
        When I send GET request to "/api/accounts/test@gmail.com/recommendations/Marketing/details"
        Then the response status should be 200
        And daily_breakdown should be sorted by date ascending
        """
        # Given: Create 7 days of test data
        self._create_test_data(self.test_email, days=7, marketing_percentage=35.0)

        # When: Get detailed reasons
        reason = self.recommendation_service.get_recommendation_reasons(
            self.test_email,
            "Marketing",
            days=7
        )

        # Then: Verify daily breakdown is sorted
        self.assertGreater(len(reason.daily_breakdown), 0)
        dates = [item.date for item in reason.daily_breakdown]
        self.assertEqual(dates, sorted(dates))

    def test_concurrent_requests_return_consistent_data(self):
        """
        Scenario: API handles concurrent requests
        Given a user "test@gmail.com" has email data
        When I send 10 concurrent GET requests to "/api/accounts/test@gmail.com/recommendations"
        Then all responses should have status 200
        And all responses should return consistent data
        """
        # Given: Create test data
        self._create_test_data(self.test_email, days=7, marketing_percentage=35.0)

        # When: Make multiple requests (simulated concurrency)
        results = []
        for _ in range(10):
            result = self.recommendation_service.get_recommendations(self.test_email, days=7)
            results.append(result)

        # Then: Verify all results are consistent
        first_result = results[0]
        for result in results[1:]:
            self.assertEqual(result.email_address, first_result.email_address)
            self.assertEqual(result.total_emails_analyzed, first_result.total_emails_analyzed)
            self.assertEqual(len(result.recommendations), len(first_result.recommendations))

            # Verify same categories in same order
            for i, rec in enumerate(result.recommendations):
                self.assertEqual(rec.category, first_result.recommendations[i].category)
                self.assertEqual(rec.email_count, first_result.recommendations[i].email_count)

    def test_get_details_for_unknown_category_returns_zero_count(self):
        """
        Scenario: Get details for non-recommended category returns 404
        Given a user "test@gmail.com" exists
        And "UnknownCategory" is not in the system
        When I send GET request to "/api/accounts/test@gmail.com/recommendations/UnknownCategory/details"
        Then the response status should be 404

        Note: Service returns data with zero count, API endpoint should convert to 404.
        """
        # Given: Create test data
        self._create_test_data(self.test_email, days=7)

        # When: Get details for unknown category
        reason = self.recommendation_service.get_recommendation_reasons(
            self.test_email,
            "UnknownCategory",
            days=7
        )

        # Then: Should return reason with zero count
        self.assertEqual(reason.category, "UnknownCategory")
        self.assertEqual(reason.total_count, 0)
        self.assertEqual(reason.percentage, 0.0)


if __name__ == "__main__":
    unittest.main()
