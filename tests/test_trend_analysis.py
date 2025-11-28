"""
Tests for Category Trend Analysis feature.

Based on BDD scenarios from prompts/003-bdd-trend-analysis.md:
- Scenario: Increasing trend is detected
- Scenario: Decreasing trend is detected
- Scenario: Stable trend is detected when variation is within threshold
- Scenario: Trend is stable with minimal data
- Scenario: Trend handles zero counts in first half
- Scenario: Recommendation includes trend information
- Scenario: Detailed recommendation reasons include daily breakdown
- Scenario: Comparable categories are included in detailed reasons
- Scenario: Recommendation factors are clearly listed

Trend Classification Rules (from spec section 4.4):
- Increasing: Second half average >= 15% higher than first half
- Decreasing: Second half average <= 15% lower than first half
- Stable: Change between -15% and +15%

These tests follow TDD Red phase - they will fail until the trend analysis
functions and models are implemented.
"""
import unittest
from datetime import date
from typing import List


class TestIncreasingTrendIsDetected(unittest.TestCase):
    """
    Scenario: Increasing trend is detected

    Given a user "test@gmail.com" has daily tallies for "Marketing":
      | date       | count |
      | 2025-11-22 | 20    |
      | 2025-11-23 | 22    |
      | 2025-11-24 | 25    |
      | 2025-11-25 | 35    |
      | 2025-11-26 | 40    |
      | 2025-11-27 | 45    |
      | 2025-11-28 | 50    |
    When the trend is calculated for "Marketing"
    Then the trend direction should be "increasing"
    And the trend percentage change should be positive

    The implementation should:
    - Compare first half average (20+22+25)/3 = 22.33 vs second half (35+40+45+50)/4 = 42.5
    - Percentage change = ((42.5 - 22.33) / 22.33) * 100 = 90.3%
    - Since 90.3% > 15%, classify as "increasing"
    """

    def test_increasing_trend_direction(self):
        """
        Test that trend direction is "increasing" for data with second half
        significantly higher than first half.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=20),
            DailyBreakdown(date=date(2025, 11, 23), count=22),
            DailyBreakdown(date=date(2025, 11, 24), count=25),
            DailyBreakdown(date=date(2025, 11, 25), count=35),
            DailyBreakdown(date=date(2025, 11, 26), count=40),
            DailyBreakdown(date=date(2025, 11, 27), count=45),
            DailyBreakdown(date=date(2025, 11, 28), count=50),
        ]

        # Act
        trend_direction = calculate_trend(daily_breakdown)

        # Assert
        self.assertEqual(
            trend_direction,
            "increasing",
            f"Expected trend direction 'increasing', got '{trend_direction}'"
        )

    def test_increasing_trend_percentage_change_is_positive(self):
        """
        Test that trend percentage change is positive for increasing trend.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend_percentage_change

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=20),
            DailyBreakdown(date=date(2025, 11, 23), count=22),
            DailyBreakdown(date=date(2025, 11, 24), count=25),
            DailyBreakdown(date=date(2025, 11, 25), count=35),
            DailyBreakdown(date=date(2025, 11, 26), count=40),
            DailyBreakdown(date=date(2025, 11, 27), count=45),
            DailyBreakdown(date=date(2025, 11, 28), count=50),
        ]

        # Act
        percentage_change = calculate_trend_percentage_change(daily_breakdown)

        # Assert
        self.assertGreater(
            percentage_change,
            0.0,
            f"Expected positive percentage change, got {percentage_change}"
        )


class TestDecreasingTrendIsDetected(unittest.TestCase):
    """
    Scenario: Decreasing trend is detected

    Given a user "test@gmail.com" has daily tallies for "Marketing":
      | date       | count |
      | 2025-11-22 | 50    |
      | 2025-11-23 | 45    |
      | 2025-11-24 | 40    |
      | 2025-11-25 | 30    |
      | 2025-11-26 | 25    |
      | 2025-11-27 | 22    |
      | 2025-11-28 | 20    |
    When the trend is calculated for "Marketing"
    Then the trend direction should be "decreasing"
    And the trend percentage change should be negative

    The implementation should:
    - Compare first half average (50+45+40)/3 = 45 vs second half (30+25+22+20)/4 = 24.25
    - Percentage change = ((24.25 - 45) / 45) * 100 = -46.1%
    - Since -46.1% < -15%, classify as "decreasing"
    """

    def test_decreasing_trend_direction(self):
        """
        Test that trend direction is "decreasing" for data with second half
        significantly lower than first half.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=50),
            DailyBreakdown(date=date(2025, 11, 23), count=45),
            DailyBreakdown(date=date(2025, 11, 24), count=40),
            DailyBreakdown(date=date(2025, 11, 25), count=30),
            DailyBreakdown(date=date(2025, 11, 26), count=25),
            DailyBreakdown(date=date(2025, 11, 27), count=22),
            DailyBreakdown(date=date(2025, 11, 28), count=20),
        ]

        # Act
        trend_direction = calculate_trend(daily_breakdown)

        # Assert
        self.assertEqual(
            trend_direction,
            "decreasing",
            f"Expected trend direction 'decreasing', got '{trend_direction}'"
        )

    def test_decreasing_trend_percentage_change_is_negative(self):
        """
        Test that trend percentage change is negative for decreasing trend.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend_percentage_change

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=50),
            DailyBreakdown(date=date(2025, 11, 23), count=45),
            DailyBreakdown(date=date(2025, 11, 24), count=40),
            DailyBreakdown(date=date(2025, 11, 25), count=30),
            DailyBreakdown(date=date(2025, 11, 26), count=25),
            DailyBreakdown(date=date(2025, 11, 27), count=22),
            DailyBreakdown(date=date(2025, 11, 28), count=20),
        ]

        # Act
        percentage_change = calculate_trend_percentage_change(daily_breakdown)

        # Assert
        self.assertLess(
            percentage_change,
            0.0,
            f"Expected negative percentage change, got {percentage_change}"
        )


class TestStableTrendWithinThreshold(unittest.TestCase):
    """
    Scenario: Stable trend is detected when variation is within threshold

    Given a user "test@gmail.com" has daily tallies for "Marketing":
      | date       | count |
      | 2025-11-22 | 30    |
      | 2025-11-23 | 32    |
      | 2025-11-24 | 28    |
      | 2025-11-25 | 31    |
      | 2025-11-26 | 29    |
      | 2025-11-27 | 30    |
      | 2025-11-28 | 31    |
    When the trend is calculated for "Marketing"
    Then the trend direction should be "stable"
    And the trend percentage change should be between -15 and 15 percent

    The implementation should:
    - Compare first half average (30+32+28)/3 = 30 vs second half (31+29+30+31)/4 = 30.25
    - Percentage change = ((30.25 - 30) / 30) * 100 = 0.83%
    - Since 0.83% is between -15% and 15%, classify as "stable"
    """

    def test_stable_trend_direction(self):
        """
        Test that trend direction is "stable" when variation is within threshold.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=30),
            DailyBreakdown(date=date(2025, 11, 23), count=32),
            DailyBreakdown(date=date(2025, 11, 24), count=28),
            DailyBreakdown(date=date(2025, 11, 25), count=31),
            DailyBreakdown(date=date(2025, 11, 26), count=29),
            DailyBreakdown(date=date(2025, 11, 27), count=30),
            DailyBreakdown(date=date(2025, 11, 28), count=31),
        ]

        # Act
        trend_direction = calculate_trend(daily_breakdown)

        # Assert
        self.assertEqual(
            trend_direction,
            "stable",
            f"Expected trend direction 'stable', got '{trend_direction}'"
        )

    def test_stable_trend_percentage_change_within_threshold(self):
        """
        Test that percentage change is between -15 and 15 percent for stable trend.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend_percentage_change

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=30),
            DailyBreakdown(date=date(2025, 11, 23), count=32),
            DailyBreakdown(date=date(2025, 11, 24), count=28),
            DailyBreakdown(date=date(2025, 11, 25), count=31),
            DailyBreakdown(date=date(2025, 11, 26), count=29),
            DailyBreakdown(date=date(2025, 11, 27), count=30),
            DailyBreakdown(date=date(2025, 11, 28), count=31),
        ]

        # Act
        percentage_change = calculate_trend_percentage_change(daily_breakdown)

        # Assert
        self.assertGreaterEqual(
            percentage_change,
            -15.0,
            f"Expected percentage change >= -15, got {percentage_change}"
        )
        self.assertLessEqual(
            percentage_change,
            15.0,
            f"Expected percentage change <= 15, got {percentage_change}"
        )


class TestTrendStableWithMinimalData(unittest.TestCase):
    """
    Scenario: Trend is stable with minimal data

    Given a user "test@gmail.com" has daily tallies for "Marketing":
      | date       | count |
      | 2025-11-28 | 30    |
    When the trend is calculated for "Marketing"
    Then the trend direction should be "stable"

    The implementation should:
    - Handle single data point gracefully
    - Return "stable" when insufficient data for trend calculation
    """

    def test_single_data_point_returns_stable(self):
        """
        Test that a single data point returns "stable" trend.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 28), count=30),
        ]

        # Act
        trend_direction = calculate_trend(daily_breakdown)

        # Assert
        self.assertEqual(
            trend_direction,
            "stable",
            f"Expected trend direction 'stable' for single data point, got '{trend_direction}'"
        )

    def test_empty_data_returns_stable(self):
        """
        Test that empty data returns "stable" trend.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend

        daily_breakdown: List[DailyBreakdown] = []

        # Act
        trend_direction = calculate_trend(daily_breakdown)

        # Assert
        self.assertEqual(
            trend_direction,
            "stable",
            f"Expected trend direction 'stable' for empty data, got '{trend_direction}'"
        )

    def test_two_data_points_calculates_trend(self):
        """
        Test that two data points can calculate a trend.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend

        # Two points with significant increase (first half: 10, second half: 100)
        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 27), count=10),
            DailyBreakdown(date=date(2025, 11, 28), count=100),
        ]

        # Act
        trend_direction = calculate_trend(daily_breakdown)

        # Assert - Should detect increasing trend (900% increase)
        self.assertEqual(
            trend_direction,
            "increasing",
            f"Expected 'increasing' for two points with large increase, got '{trend_direction}'"
        )


class TestTrendHandlesZeroCountsInFirstHalf(unittest.TestCase):
    """
    Scenario: Trend handles zero counts in first half

    Given a user "test@gmail.com" has daily tallies for "Marketing":
      | date       | count |
      | 2025-11-22 | 0     |
      | 2025-11-23 | 0     |
      | 2025-11-24 | 0     |
      | 2025-11-25 | 10    |
      | 2025-11-26 | 15    |
      | 2025-11-27 | 20    |
      | 2025-11-28 | 25    |
    When the trend is calculated for "Marketing"
    Then the trend direction should be "increasing"

    The implementation should:
    - Handle zero average in first half without division by zero
    - Recognize that going from 0 to any positive value is an increase
    """

    def test_zero_first_half_returns_increasing(self):
        """
        Test that zero counts in first half returns "increasing" when
        second half has positive counts.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=0),
            DailyBreakdown(date=date(2025, 11, 23), count=0),
            DailyBreakdown(date=date(2025, 11, 24), count=0),
            DailyBreakdown(date=date(2025, 11, 25), count=10),
            DailyBreakdown(date=date(2025, 11, 26), count=15),
            DailyBreakdown(date=date(2025, 11, 27), count=20),
            DailyBreakdown(date=date(2025, 11, 28), count=25),
        ]

        # Act
        trend_direction = calculate_trend(daily_breakdown)

        # Assert
        self.assertEqual(
            trend_direction,
            "increasing",
            f"Expected trend direction 'increasing' for zero->positive, got '{trend_direction}'"
        )

    def test_zero_first_half_does_not_raise_error(self):
        """
        Test that zero counts in first half does not raise division by zero.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend_percentage_change

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=0),
            DailyBreakdown(date=date(2025, 11, 23), count=0),
            DailyBreakdown(date=date(2025, 11, 24), count=0),
            DailyBreakdown(date=date(2025, 11, 25), count=10),
            DailyBreakdown(date=date(2025, 11, 26), count=15),
            DailyBreakdown(date=date(2025, 11, 27), count=20),
            DailyBreakdown(date=date(2025, 11, 28), count=25),
        ]

        # Act - Should not raise exception
        percentage_change = calculate_trend_percentage_change(daily_breakdown)

        # Assert - Result should be some positive number (implementation-defined)
        self.assertIsInstance(
            percentage_change,
            float,
            f"Expected float result, got {type(percentage_change)}"
        )


class TestRecommendationIncludesTrendInformation(unittest.TestCase):
    """
    Scenario: Recommendation includes trend information

    Given a user "test@gmail.com" has daily tallies for "Marketing" showing an increasing trend
    And "Marketing" qualifies for a recommendation
    When the user requests blocking recommendations
    Then the recommendation for "Marketing" should mention the trend
    And the reason should indicate the category is "trending upward"

    The implementation should:
    - Include trend in CategorySummary
    - Include trend in recommendation reason text
    """

    def test_category_summary_includes_trend_field(self):
        """
        Test that CategorySummaryItem model has trend field.
        """
        # Arrange
        from models.category_tally_models import CategorySummaryItem

        # Act
        summary = CategorySummaryItem(
            category="Marketing",
            total_count=245,
            percentage=35.2,
            daily_average=35.0,
            trend="increasing"
        )

        # Assert
        self.assertEqual(
            summary.trend,
            "increasing",
            f"Expected trend 'increasing', got '{summary.trend}'"
        )

    def test_recommendation_reason_mentions_trend(self):
        """
        Test that recommendation reason includes trend information.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown, RecommendationReason

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=20),
            DailyBreakdown(date=date(2025, 11, 23), count=25),
            DailyBreakdown(date=date(2025, 11, 24), count=30),
            DailyBreakdown(date=date(2025, 11, 25), count=35),
            DailyBreakdown(date=date(2025, 11, 26), count=40),
            DailyBreakdown(date=date(2025, 11, 27), count=45),
            DailyBreakdown(date=date(2025, 11, 28), count=50),
        ]

        # Act
        reason = RecommendationReason(
            category="Marketing",
            total_count=245,
            percentage=35.2,
            daily_breakdown=daily_breakdown,
            trend_direction="increasing",
            trend_percentage_change=90.3,
            comparable_categories={"Advertising": 22.4},
            recommendation_factors=["High volume: 245 emails in 7 days"]
        )

        # Assert
        self.assertEqual(
            reason.trend_direction,
            "increasing",
            f"Expected trend_direction 'increasing', got '{reason.trend_direction}'"
        )

    def test_recommendation_factor_includes_trend_upward(self):
        """
        Test that recommendation factors mention "trending upward" for increasing trend.
        """
        # Arrange
        from services.trend_calculator import generate_trend_factor

        # Act
        trend_factor = generate_trend_factor("increasing", 90.3)

        # Assert
        self.assertIn(
            "trending upward",
            trend_factor.lower(),
            f"Expected 'trending upward' in factor, got '{trend_factor}'"
        )


class TestDetailedRecommendationReasonsIncludeDailyBreakdown(unittest.TestCase):
    """
    Scenario: Detailed recommendation reasons include daily breakdown

    Given a user "test@gmail.com" has daily tallies for "Marketing":
      | date       | count |
      | 2025-11-22 | 32    |
      | 2025-11-23 | 38    |
      | 2025-11-24 | 35    |
      | 2025-11-25 | 30    |
      | 2025-11-26 | 42    |
      | 2025-11-27 | 36    |
      | 2025-11-28 | 32    |
    When the user requests detailed reasons for "Marketing" recommendation
    Then the response should include daily_breakdown with 7 entries
    And each entry should have a date and count
    And the trend_direction should be provided
    And the trend_percentage_change should be provided
    """

    def test_recommendation_reason_has_daily_breakdown_with_seven_entries(self):
        """
        Test that daily breakdown contains 7 entries.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown, RecommendationReason

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=32),
            DailyBreakdown(date=date(2025, 11, 23), count=38),
            DailyBreakdown(date=date(2025, 11, 24), count=35),
            DailyBreakdown(date=date(2025, 11, 25), count=30),
            DailyBreakdown(date=date(2025, 11, 26), count=42),
            DailyBreakdown(date=date(2025, 11, 27), count=36),
            DailyBreakdown(date=date(2025, 11, 28), count=32),
        ]

        # Act
        reason = RecommendationReason(
            category="Marketing",
            total_count=245,
            percentage=35.2,
            daily_breakdown=daily_breakdown,
            trend_direction="stable",
            trend_percentage_change=2.5,
            comparable_categories={"Advertising": 22.4},
            recommendation_factors=["High volume"]
        )

        # Assert
        self.assertEqual(
            len(reason.daily_breakdown),
            7,
            f"Expected 7 entries in daily_breakdown, got {len(reason.daily_breakdown)}"
        )

    def test_each_daily_breakdown_entry_has_date_and_count(self):
        """
        Test that each daily breakdown entry has date and count fields.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown

        entry = DailyBreakdown(date=date(2025, 11, 22), count=32)

        # Assert
        self.assertEqual(
            entry.date,
            date(2025, 11, 22),
            f"Expected date 2025-11-22, got {entry.date}"
        )
        self.assertEqual(
            entry.count,
            32,
            f"Expected count 32, got {entry.count}"
        )

    def test_recommendation_reason_has_trend_direction(self):
        """
        Test that RecommendationReason includes trend_direction field.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown, RecommendationReason

        daily_breakdown = [DailyBreakdown(date=date(2025, 11, 28), count=32)]

        # Act
        reason = RecommendationReason(
            category="Marketing",
            total_count=245,
            percentage=35.2,
            daily_breakdown=daily_breakdown,
            trend_direction="stable",
            trend_percentage_change=2.5,
            comparable_categories={},
            recommendation_factors=[]
        )

        # Assert
        self.assertIsNotNone(
            reason.trend_direction,
            "trend_direction should not be None"
        )
        self.assertIn(
            reason.trend_direction,
            ["increasing", "decreasing", "stable"],
            f"trend_direction should be one of 'increasing', 'decreasing', 'stable', got '{reason.trend_direction}'"
        )

    def test_recommendation_reason_has_trend_percentage_change(self):
        """
        Test that RecommendationReason includes trend_percentage_change field.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown, RecommendationReason

        daily_breakdown = [DailyBreakdown(date=date(2025, 11, 28), count=32)]

        # Act
        reason = RecommendationReason(
            category="Marketing",
            total_count=245,
            percentage=35.2,
            daily_breakdown=daily_breakdown,
            trend_direction="stable",
            trend_percentage_change=2.5,
            comparable_categories={},
            recommendation_factors=[]
        )

        # Assert
        self.assertIsNotNone(
            reason.trend_percentage_change,
            "trend_percentage_change should not be None"
        )
        self.assertIsInstance(
            reason.trend_percentage_change,
            float,
            f"trend_percentage_change should be float, got {type(reason.trend_percentage_change)}"
        )


class TestComparableCategoriesIncludedInDetailedReasons(unittest.TestCase):
    """
    Scenario: Comparable categories are included in detailed reasons

    Given a user "test@gmail.com" has category tallies:
      | category        | percentage |
      | Marketing       | 35.2       |
      | Advertising     | 22.4       |
      | Service-Updates | 12.1       |
    When the user requests detailed reasons for "Marketing" recommendation
    Then the response should include comparable_categories
    And comparable_categories should include "Advertising" with 22.4 percent
    And comparable_categories should include "Service-Updates" with 12.1 percent
    """

    def test_recommendation_reason_has_comparable_categories(self):
        """
        Test that RecommendationReason includes comparable_categories field.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown, RecommendationReason

        daily_breakdown = [DailyBreakdown(date=date(2025, 11, 28), count=32)]
        comparable = {
            "Advertising": 22.4,
            "Service-Updates": 12.1
        }

        # Act
        reason = RecommendationReason(
            category="Marketing",
            total_count=245,
            percentage=35.2,
            daily_breakdown=daily_breakdown,
            trend_direction="stable",
            trend_percentage_change=2.5,
            comparable_categories=comparable,
            recommendation_factors=[]
        )

        # Assert
        self.assertIsNotNone(
            reason.comparable_categories,
            "comparable_categories should not be None"
        )
        self.assertIsInstance(
            reason.comparable_categories,
            dict,
            f"comparable_categories should be dict, got {type(reason.comparable_categories)}"
        )

    def test_comparable_categories_includes_advertising(self):
        """
        Test that comparable_categories includes Advertising with 22.4 percent.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown, RecommendationReason

        daily_breakdown = [DailyBreakdown(date=date(2025, 11, 28), count=32)]
        comparable = {
            "Advertising": 22.4,
            "Service-Updates": 12.1
        }

        # Act
        reason = RecommendationReason(
            category="Marketing",
            total_count=245,
            percentage=35.2,
            daily_breakdown=daily_breakdown,
            trend_direction="stable",
            trend_percentage_change=2.5,
            comparable_categories=comparable,
            recommendation_factors=[]
        )

        # Assert
        self.assertIn(
            "Advertising",
            reason.comparable_categories,
            "comparable_categories should include 'Advertising'"
        )
        self.assertEqual(
            reason.comparable_categories["Advertising"],
            22.4,
            f"Advertising percentage should be 22.4, got {reason.comparable_categories.get('Advertising')}"
        )

    def test_comparable_categories_includes_service_updates(self):
        """
        Test that comparable_categories includes Service-Updates with 12.1 percent.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown, RecommendationReason

        daily_breakdown = [DailyBreakdown(date=date(2025, 11, 28), count=32)]
        comparable = {
            "Advertising": 22.4,
            "Service-Updates": 12.1
        }

        # Act
        reason = RecommendationReason(
            category="Marketing",
            total_count=245,
            percentage=35.2,
            daily_breakdown=daily_breakdown,
            trend_direction="stable",
            trend_percentage_change=2.5,
            comparable_categories=comparable,
            recommendation_factors=[]
        )

        # Assert
        self.assertIn(
            "Service-Updates",
            reason.comparable_categories,
            "comparable_categories should include 'Service-Updates'"
        )
        self.assertEqual(
            reason.comparable_categories["Service-Updates"],
            12.1,
            f"Service-Updates percentage should be 12.1, got {reason.comparable_categories.get('Service-Updates')}"
        )


class TestRecommendationFactorsAreClearlyListed(unittest.TestCase):
    """
    Scenario: Recommendation factors are clearly listed

    Given a user "test@gmail.com" has "Marketing" category with:
      | metric           | value      |
      | total_count      | 245        |
      | percentage       | 35.2       |
      | daily_average    | 35         |
      | trend            | increasing |
      | trend_change     | 8.5        |
    When the user requests detailed reasons for "Marketing" recommendation
    Then the recommendation_factors should include "High volume: 245 emails in 7 days"
    And the recommendation_factors should include "Significant percentage: 35.2% of total inbox"
    And the recommendation_factors should include information about the trend
    """

    def test_recommendation_factors_include_high_volume(self):
        """
        Test that recommendation_factors includes high volume message.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown, RecommendationReason

        daily_breakdown = [DailyBreakdown(date=date(2025, 11, 28), count=32)]
        factors = [
            "High volume: 245 emails in 7 days",
            "Significant percentage: 35.2% of total inbox",
            "Trending upward: 8.5% increase over period"
        ]

        # Act
        reason = RecommendationReason(
            category="Marketing",
            total_count=245,
            percentage=35.2,
            daily_breakdown=daily_breakdown,
            trend_direction="increasing",
            trend_percentage_change=8.5,
            comparable_categories={},
            recommendation_factors=factors
        )

        # Assert
        high_volume_found = any(
            "High volume: 245 emails" in factor
            for factor in reason.recommendation_factors
        )
        self.assertTrue(
            high_volume_found,
            f"Expected 'High volume: 245 emails' in factors, got {reason.recommendation_factors}"
        )

    def test_recommendation_factors_include_significant_percentage(self):
        """
        Test that recommendation_factors includes significant percentage message.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown, RecommendationReason

        daily_breakdown = [DailyBreakdown(date=date(2025, 11, 28), count=32)]
        factors = [
            "High volume: 245 emails in 7 days",
            "Significant percentage: 35.2% of total inbox",
            "Trending upward: 8.5% increase over period"
        ]

        # Act
        reason = RecommendationReason(
            category="Marketing",
            total_count=245,
            percentage=35.2,
            daily_breakdown=daily_breakdown,
            trend_direction="increasing",
            trend_percentage_change=8.5,
            comparable_categories={},
            recommendation_factors=factors
        )

        # Assert
        percentage_found = any(
            "Significant percentage: 35.2%" in factor
            for factor in reason.recommendation_factors
        )
        self.assertTrue(
            percentage_found,
            f"Expected 'Significant percentage: 35.2%' in factors, got {reason.recommendation_factors}"
        )

    def test_recommendation_factors_include_trend_information(self):
        """
        Test that recommendation_factors includes trend information.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown, RecommendationReason

        daily_breakdown = [DailyBreakdown(date=date(2025, 11, 28), count=32)]
        factors = [
            "High volume: 245 emails in 7 days",
            "Significant percentage: 35.2% of total inbox",
            "Trending upward: 8.5% increase over period"
        ]

        # Act
        reason = RecommendationReason(
            category="Marketing",
            total_count=245,
            percentage=35.2,
            daily_breakdown=daily_breakdown,
            trend_direction="increasing",
            trend_percentage_change=8.5,
            comparable_categories={},
            recommendation_factors=factors
        )

        # Assert
        trend_found = any(
            "trend" in factor.lower()
            for factor in reason.recommendation_factors
        )
        self.assertTrue(
            trend_found,
            f"Expected trend information in factors, got {reason.recommendation_factors}"
        )


class TestDailyBreakdownModel(unittest.TestCase):
    """
    Tests for the DailyBreakdown Pydantic model.

    The model should have fields:
    - date: date
    - count: int
    """

    def test_daily_breakdown_model_accepts_valid_data(self):
        """
        Test that DailyBreakdown model accepts valid data.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown

        # Act
        breakdown = DailyBreakdown(
            date=date(2025, 11, 28),
            count=32
        )

        # Assert
        self.assertEqual(breakdown.date, date(2025, 11, 28))
        self.assertEqual(breakdown.count, 32)

    def test_daily_breakdown_model_has_required_fields(self):
        """
        Test that DailyBreakdown model has all required fields.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown

        # Act
        field_names = list(DailyBreakdown.model_fields.keys())

        # Assert
        self.assertIn("date", field_names, "DailyBreakdown should have 'date' field")
        self.assertIn("count", field_names, "DailyBreakdown should have 'count' field")

    def test_daily_breakdown_accepts_zero_count(self):
        """
        Test that DailyBreakdown accepts zero count.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown

        # Act
        breakdown = DailyBreakdown(
            date=date(2025, 11, 22),
            count=0
        )

        # Assert
        self.assertEqual(breakdown.count, 0)


class TestRecommendationReasonModel(unittest.TestCase):
    """
    Tests for the RecommendationReason Pydantic model.

    The model should have fields:
    - category: str
    - total_count: int
    - percentage: float
    - daily_breakdown: List[DailyBreakdown]
    - trend_direction: str
    - trend_percentage_change: float
    - comparable_categories: Dict[str, float]
    - recommendation_factors: List[str]
    """

    def test_recommendation_reason_model_has_all_required_fields(self):
        """
        Test that RecommendationReason model has all required fields.
        """
        # Arrange
        from models.recommendation_models import RecommendationReason

        # Act
        field_names = list(RecommendationReason.model_fields.keys())

        # Assert
        required_fields = [
            "category",
            "total_count",
            "percentage",
            "daily_breakdown",
            "trend_direction",
            "trend_percentage_change",
            "comparable_categories",
            "recommendation_factors"
        ]

        for field in required_fields:
            self.assertIn(
                field,
                field_names,
                f"RecommendationReason should have '{field}' field"
            )

    def test_recommendation_reason_model_accepts_valid_data(self):
        """
        Test that RecommendationReason model accepts valid data.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown, RecommendationReason

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=32),
            DailyBreakdown(date=date(2025, 11, 23), count=38),
        ]

        # Act
        reason = RecommendationReason(
            category="Marketing",
            total_count=245,
            percentage=35.2,
            daily_breakdown=daily_breakdown,
            trend_direction="increasing",
            trend_percentage_change=8.5,
            comparable_categories={"Advertising": 22.4},
            recommendation_factors=["High volume: 245 emails in 7 days"]
        )

        # Assert
        self.assertEqual(reason.category, "Marketing")
        self.assertEqual(reason.total_count, 245)
        self.assertEqual(reason.percentage, 35.2)
        self.assertEqual(len(reason.daily_breakdown), 2)
        self.assertEqual(reason.trend_direction, "increasing")
        self.assertEqual(reason.trend_percentage_change, 8.5)
        self.assertEqual(reason.comparable_categories["Advertising"], 22.4)
        self.assertEqual(len(reason.recommendation_factors), 1)


class TestTrendCalculatorInterface(unittest.TestCase):
    """
    Tests to verify the trend calculator functions exist and have correct signatures.

    This ensures the interface contract is properly defined before implementation.
    """

    def test_calculate_trend_function_exists(self):
        """
        Test that calculate_trend function exists.
        """
        # Act & Assert
        from services.trend_calculator import calculate_trend
        import inspect

        self.assertTrue(
            callable(calculate_trend),
            "calculate_trend should be a callable function"
        )

    def test_calculate_trend_percentage_change_function_exists(self):
        """
        Test that calculate_trend_percentage_change function exists.
        """
        # Act & Assert
        from services.trend_calculator import calculate_trend_percentage_change
        import inspect

        self.assertTrue(
            callable(calculate_trend_percentage_change),
            "calculate_trend_percentage_change should be a callable function"
        )

    def test_generate_trend_factor_function_exists(self):
        """
        Test that generate_trend_factor function exists.
        """
        # Act & Assert
        from services.trend_calculator import generate_trend_factor
        import inspect

        self.assertTrue(
            callable(generate_trend_factor),
            "generate_trend_factor should be a callable function"
        )


class TestTrendBoundaryConditions(unittest.TestCase):
    """
    Additional tests for boundary conditions in trend calculation.

    These tests verify edge cases at exactly the threshold values.
    """

    def test_exactly_15_percent_increase_is_stable(self):
        """
        Test that exactly 14.99% increase is classified as stable.

        The threshold is >= 15%, so 14.99% should be "stable".
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend

        # First half avg = 100, second half avg needs to be ~114.99 for 14.99% increase
        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=100),
            DailyBreakdown(date=date(2025, 11, 23), count=100),
            DailyBreakdown(date=date(2025, 11, 24), count=114),
            DailyBreakdown(date=date(2025, 11, 25), count=115),
        ]

        # Act
        trend_direction = calculate_trend(daily_breakdown)

        # Assert
        # With first half = 100, second half = 114.5, change = 14.5% (stable)
        self.assertEqual(
            trend_direction,
            "stable",
            f"Expected 'stable' at boundary, got '{trend_direction}'"
        )

    def test_exactly_15_percent_decrease_is_stable(self):
        """
        Test that exactly 14.99% decrease is classified as stable.

        The threshold is <= -15%, so -14.99% should be "stable".
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend

        # First half avg = 100, second half avg = 85.5 for ~14.5% decrease
        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=100),
            DailyBreakdown(date=date(2025, 11, 23), count=100),
            DailyBreakdown(date=date(2025, 11, 24), count=85),
            DailyBreakdown(date=date(2025, 11, 25), count=86),
        ]

        # Act
        trend_direction = calculate_trend(daily_breakdown)

        # Assert
        self.assertEqual(
            trend_direction,
            "stable",
            f"Expected 'stable' at boundary, got '{trend_direction}'"
        )

    def test_all_zeros_returns_stable(self):
        """
        Test that all zero counts returns "stable" trend.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend

        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=0),
            DailyBreakdown(date=date(2025, 11, 23), count=0),
            DailyBreakdown(date=date(2025, 11, 24), count=0),
            DailyBreakdown(date=date(2025, 11, 25), count=0),
        ]

        # Act
        trend_direction = calculate_trend(daily_breakdown)

        # Assert
        self.assertEqual(
            trend_direction,
            "stable",
            f"Expected 'stable' for all zeros, got '{trend_direction}'"
        )

    def test_odd_number_of_data_points_splits_correctly(self):
        """
        Test that odd number of data points splits correctly.

        For 5 points, first half = first 2, second half = last 3.
        """
        # Arrange
        from models.recommendation_models import DailyBreakdown
        from services.trend_calculator import calculate_trend

        # First half (2 points): avg = (10+20)/2 = 15
        # Second half (3 points): avg = (100+110+120)/3 = 110
        # Change = ((110-15)/15)*100 = 633% -> increasing
        daily_breakdown = [
            DailyBreakdown(date=date(2025, 11, 22), count=10),
            DailyBreakdown(date=date(2025, 11, 23), count=20),
            DailyBreakdown(date=date(2025, 11, 24), count=100),
            DailyBreakdown(date=date(2025, 11, 25), count=110),
            DailyBreakdown(date=date(2025, 11, 26), count=120),
        ]

        # Act
        trend_direction = calculate_trend(daily_breakdown)

        # Assert
        self.assertEqual(
            trend_direction,
            "increasing",
            f"Expected 'increasing' for odd points with large increase, got '{trend_direction}'"
        )


if __name__ == '__main__':
    unittest.main()
