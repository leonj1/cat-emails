"""
Tests for Blocking Recommendations feature.

Based on BDD scenarios in tests/bdd/blocking-recommendations.feature.
Tests follow TDD approach - written before implementation.
"""
import unittest
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from models.recommendation_models import (
    BlockingRecommendation,
    BlockingRecommendationResult,
    RecommendationStrength
)
from services.blocking_recommendation_service import BlockingRecommendationService
from services.category_aggregation_config import CategoryAggregationConfig
from repositories.category_tally_repository_interface import ICategoryTallyRepository
from models.category_tally_models import DailyCategoryTally


class MockCategoryTallyRepository(ICategoryTallyRepository):
    """Mock repository for testing blocking recommendations."""

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
            # Merge counts
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
    ) -> Optional[DailyCategoryTally]:
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

    def get_aggregated_tallies(self, email_address: str, start_date: date, end_date: date):
        # Not needed for blocking recommendations tests
        pass

    def delete_tallies_before(self, email_address: str, cutoff_date: date) -> int:
        # Not needed for blocking recommendations tests
        pass


class MockBlockedCategory:
    """Mock BlockedCategory for testing."""
    def __init__(self, category: str, reason: str):
        self.category = category
        self.reason = reason


class MockDomainService:
    """Mock domain service for testing."""

    def __init__(self):
        self.blocked_categories = []

    def fetch_blocked_categories(self):
        return [MockBlockedCategory(category=cat, reason="Test blocked") for cat in self.blocked_categories]


class TestBlockingRecommendations(unittest.TestCase):
    """Test blocking recommendation scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.repository = MockCategoryTallyRepository()
        self.domain_service = MockDomainService()
        self.config = CategoryAggregationConfig(
            threshold_percentage=10.0,
            minimum_count=10,
            excluded_categories=["Personal", "Work-related", "Financial-Notification"]
        )
        self.service = BlockingRecommendationService(
            repository=self.repository,
            config=self.config,
            domain_service=self.domain_service
        )
        self.email_address = "test@gmail.com"

    def _populate_tallies(self, category_counts: Dict[str, int], days: int = 7):
        """Helper to populate repository with test data."""
        today = date.today()
        # Distribute counts evenly across days
        for i in range(days):
            tally_date = today - timedelta(days=i)
            daily_counts = {
                category: count // days + (1 if i < count % days else 0)
                for category, count in category_counts.items()
            }
            total = sum(daily_counts.values())
            self.repository.save_daily_tally(
                self.email_address,
                tally_date,
                daily_counts,
                total
            )

    def test_high_strength_recommendation_for_dominant_category(self):
        """
        Scenario: User receives high-strength recommendation for dominant category

        Given category tallies with Marketing at 250/700 (35.7%)
        When user requests recommendations
        Then they should receive HIGH strength for Marketing
        """
        # Given
        self._populate_tallies({
            "Marketing": 250,
            "Advertising": 150,
            "Personal": 100,
            "Other": 200
        })

        # When
        result = self.service.get_recommendations(self.email_address, days=7)

        # Then
        self.assertEqual(result.email_address, self.email_address)
        self.assertEqual(result.total_emails_analyzed, 700)

        # Find Marketing recommendation
        marketing_rec = next(
            (r for r in result.recommendations if r.category == "Marketing"),
            None
        )
        self.assertIsNotNone(marketing_rec, "Marketing recommendation should exist")
        self.assertEqual(marketing_rec.strength, RecommendationStrength.HIGH)
        self.assertEqual(marketing_rec.email_count, 250)
        self.assertAlmostEqual(marketing_rec.percentage, 35.7, places=0)
        # Check that reason contains percentage (35 or 36 due to rounding)
        self.assertTrue("35" in marketing_rec.reason or "36" in marketing_rec.reason)
        self.assertIn("250", marketing_rec.reason)

    def test_medium_strength_recommendation(self):
        """
        Scenario: User receives medium-strength recommendation

        Given category tallies with Advertising at 150/1000 (15%)
        When user requests recommendations
        Then they should receive MEDIUM strength for Advertising
        """
        # Given
        self._populate_tallies({
            "Marketing": 100,
            "Advertising": 150,
            "Personal": 300,
            "Other": 450
        })

        # When
        result = self.service.get_recommendations(self.email_address, days=7)

        # Then
        advertising_rec = next(
            (r for r in result.recommendations if r.category == "Advertising"),
            None
        )
        self.assertIsNotNone(advertising_rec)
        self.assertEqual(advertising_rec.strength, RecommendationStrength.MEDIUM)
        self.assertAlmostEqual(advertising_rec.percentage, 15.0, places=1)

    def test_low_strength_recommendation(self):
        """
        Scenario: User receives low-strength recommendation

        Given category tallies with Marketing at 60/600 (10%)
        When user requests recommendations
        Then they should receive LOW strength for Marketing
        """
        # Given
        self._populate_tallies({
            "Marketing": 60,
            "Advertising": 40,
            "Personal": 200,
            "Service-Updates": 100,
            "Other": 200
        })

        # When
        result = self.service.get_recommendations(self.email_address, days=7)

        # Then
        marketing_rec = next(
            (r for r in result.recommendations if r.category == "Marketing"),
            None
        )
        self.assertIsNotNone(marketing_rec)
        self.assertEqual(marketing_rec.strength, RecommendationStrength.LOW)
        self.assertAlmostEqual(marketing_rec.percentage, 10.0, places=1)

    def test_personal_emails_never_recommended(self):
        """
        Scenario: Personal emails are never recommended for blocking

        Given Personal category has high volume
        When user requests recommendations
        Then Personal should not appear in recommendations
        """
        # Given
        self._populate_tallies({
            "Personal": 400,
            "Marketing": 50,
            "Other": 50
        })

        # When
        result = self.service.get_recommendations(self.email_address, days=7)

        # Then
        personal_in_recs = any(r.category == "Personal" for r in result.recommendations)
        self.assertFalse(personal_in_recs, "Personal should not be recommended")

    def test_work_related_emails_never_recommended(self):
        """
        Scenario: Work-related emails are never recommended for blocking

        Given Work-related category has high volume
        When user requests recommendations
        Then Work-related should not appear in recommendations
        """
        # Given
        self._populate_tallies({
            "Work-related": 350,
            "Marketing": 100,
            "Other": 50
        })

        # When
        result = self.service.get_recommendations(self.email_address, days=7)

        # Then
        work_in_recs = any(r.category == "Work-related" for r in result.recommendations)
        self.assertFalse(work_in_recs, "Work-related should not be recommended")

    def test_financial_notifications_never_recommended(self):
        """
        Scenario: Financial notifications are never recommended for blocking

        Given Financial-Notification category has high volume
        When user requests recommendations
        Then Financial-Notification should not appear in recommendations
        """
        # Given
        self._populate_tallies({
            "Financial-Notification": 300,
            "Marketing": 100,
            "Other": 100
        })

        # When
        result = self.service.get_recommendations(self.email_address, days=7)

        # Then
        financial_in_recs = any(
            r.category == "Financial-Notification" for r in result.recommendations
        )
        self.assertFalse(financial_in_recs, "Financial-Notification should not be recommended")

    def test_low_volume_categories_not_recommended(self):
        """
        Scenario: Low volume categories are not recommended

        Given category with count below minimum threshold (< 10)
        When user requests recommendations
        Then that category should not appear in recommendations
        """
        # Given
        self._populate_tallies({
            "Marketing": 200,
            "Appointment-Reminder": 5,  # Below threshold of 10
            "Other": 295
        })

        # When
        result = self.service.get_recommendations(self.email_address, days=7)

        # Then
        appointment_in_recs = any(
            r.category == "Appointment-Reminder" for r in result.recommendations
        )
        self.assertFalse(appointment_in_recs, "Low volume category should not be recommended")

    def test_below_percentage_threshold_not_recommended(self):
        """
        Scenario: Categories below percentage threshold are not recommended

        Given category with percentage below threshold (< 10%)
        When user requests recommendations
        Then that category should not appear in recommendations
        """
        # Given
        self._populate_tallies({
            "Marketing": 30,      # 3% of 1000
            "Advertising": 20,    # 2% of 1000
            "Personal": 450,
            "Other": 500
        })

        # When
        result = self.service.get_recommendations(self.email_address, days=7)

        # Then
        marketing_in_recs = any(r.category == "Marketing" for r in result.recommendations)
        self.assertFalse(marketing_in_recs, "Below threshold category should not be recommended")

    def test_recommendations_sorted_by_count_descending(self):
        """
        Scenario: Multiple recommendations are sorted by strength and count

        Given multiple categories meeting recommendation criteria
        When user requests recommendations
        Then recommendations should be ordered by count descending
        """
        # Given
        self._populate_tallies({
            "Marketing": 280,
            "Advertising": 180,
            "Service-Updates": 120,
            "Personal": 100,
            "Other": 120
        })

        # When
        result = self.service.get_recommendations(self.email_address, days=7)

        # Then
        self.assertGreaterEqual(len(result.recommendations), 3)
        self.assertEqual(result.recommendations[0].category, "Marketing")
        self.assertEqual(result.recommendations[1].category, "Advertising")
        # Service-Updates and Other both have 120, order may vary
        categories = {r.category for r in result.recommendations[:3]}
        self.assertIn("Service-Updates", categories)

    def test_recommendations_show_already_blocked(self):
        """
        Scenario: Recommendations show already blocked categories

        Given user has already blocked some categories
        When user requests recommendations
        Then response should include blocked categories in already_blocked list
        """
        # Given
        self.domain_service.blocked_categories = ["Wants-Money"]
        self._populate_tallies({
            "Marketing": 200,
            "Wants-Money": 50,
            "Other": 250
        })

        # When
        result = self.service.get_recommendations(self.email_address, days=7)

        # Then
        self.assertIn("Wants-Money", result.already_blocked)

    def test_no_recommendations_when_no_data(self):
        """
        Scenario: No recommendations when no email data exists

        Given user has no email data
        When user requests recommendations
        Then total_emails_analyzed should be 0 and recommendations empty
        """
        # Given - no data populated

        # When
        result = self.service.get_recommendations(self.email_address, days=7)

        # Then
        self.assertEqual(result.total_emails_analyzed, 0)
        self.assertEqual(len(result.recommendations), 0)

    def test_custom_rolling_window_period(self):
        """
        Scenario: Custom rolling window period

        Given user has data over 14 days
        When user requests recommendations with days=14
        Then analysis should include all 14 days
        """
        # Given
        self._populate_tallies(
            {"Marketing": 280, "Personal": 140, "Other": 280},
            days=14
        )

        # When
        result = self.service.get_recommendations(self.email_address, days=14)

        # Then
        today = date.today()
        expected_start = today - timedelta(days=13)  # 14 days inclusive
        self.assertEqual(result.period_start, expected_start)
        self.assertEqual(result.period_end, today)
        self.assertEqual(result.total_emails_analyzed, 700)


if __name__ == "__main__":
    unittest.main()
