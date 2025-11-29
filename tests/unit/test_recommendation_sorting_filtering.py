"""
Tests for Recommendation Sorting, Filtering, and Response Structure (TDD Red Phase).

This module tests the enhanced recommendation features including:
1. RecommendationSummary data model with proper structure
2. Sorting by count descending then alphabetically
3. Filtering of blocked and non-qualifying domains
4. Complete response structure for notification integration

Based on Gherkin scenarios from the Blocking Recommendations Email Notification feature.
These tests follow TDD Red phase - they will fail until implementation is complete.
"""
import unittest
from typing import Set, List, Dict


# ============================================================================
# SECTION 1: RecommendationSummary Data Model Tests
# ============================================================================

class TestRecommendationSummaryModelExists(unittest.TestCase):
    """
    Tests that RecommendationSummary model exists with correct structure.

    The model should:
    - Be defined in models/domain_recommendation_models.py
    - Have recommendations (List[DomainRecommendation]), total_count (int)
    - Have domain_count property derived from len(recommendations)
    - Have to_dict() method for response serialization
    """

    def test_recommendation_summary_model_exists(self):
        """
        Test that RecommendationSummary model exists.

        The model should be defined in:
        models/domain_recommendation_models.py
        """
        # Act & Assert
        from models.domain_recommendation_models import RecommendationSummary

        self.assertTrue(
            hasattr(RecommendationSummary, '__dataclass_fields__') or
            callable(RecommendationSummary),
            "RecommendationSummary should be a dataclass or class"
        )

    def test_recommendation_summary_has_recommendations_field(self):
        """
        Test that RecommendationSummary has recommendations field.

        The recommendations field should be a List[DomainRecommendation].
        """
        from models.domain_recommendation_models import RecommendationSummary

        self.assertTrue(
            hasattr(RecommendationSummary, '__dataclass_fields__'),
            "RecommendationSummary should be a dataclass"
        )

        self.assertIn(
            'recommendations',
            RecommendationSummary.__dataclass_fields__,
            "RecommendationSummary should have 'recommendations' field"
        )

    def test_recommendation_summary_has_total_count_field(self):
        """
        Test that RecommendationSummary has total_count field of type int.

        This represents total_emails_matched across all recommendations.
        """
        from models.domain_recommendation_models import RecommendationSummary

        self.assertIn(
            'total_count',
            RecommendationSummary.__dataclass_fields__,
            "RecommendationSummary should have 'total_count' field"
        )

        field = RecommendationSummary.__dataclass_fields__['total_count']
        self.assertEqual(
            field.type,
            int,
            "total_count field should be of type int"
        )

    def test_recommendation_summary_can_be_created(self):
        """
        Test that RecommendationSummary can be instantiated with valid data.

        Scenario: Response includes complete recommendation summary
        Given the blocked domains list is empty
        And the inbox contains 10 emails from "spam@example.com" categorized as "Marketing"
        """
        from models.domain_recommendation_models import (
            RecommendationSummary,
            DomainRecommendation
        )

        # Arrange
        recommendations = [
            DomainRecommendation(
                domain="example.com",
                category="Marketing",
                count=10
            )
        ]
        total_count = 10

        # Act
        summary = RecommendationSummary(
            recommendations=recommendations,
            total_count=total_count
        )

        # Assert
        self.assertIsNotNone(summary)
        self.assertEqual(len(summary.recommendations), 1)
        self.assertEqual(summary.total_count, 10)


class TestRecommendationSummaryDomainCountProperty(unittest.TestCase):
    """
    Tests for the domain_count property which returns unique_domains_count.

    Scenario: Response includes complete recommendation summary
    Then the response should include:
      | field                          | expected_value |
      | unique_domains_count           | 1              |
    """

    def test_domain_count_returns_number_of_recommendations(self):
        """
        Test that domain_count property returns len(recommendations).

        This provides unique_domains_count for the response.
        """
        from models.domain_recommendation_models import (
            RecommendationSummary,
            DomainRecommendation
        )

        # Arrange
        recommendations = [
            DomainRecommendation(domain="domain1.com", category="Marketing", count=5),
            DomainRecommendation(domain="domain2.com", category="Advertising", count=3),
            DomainRecommendation(domain="domain3.com", category="Wants-Money", count=1),
        ]

        summary = RecommendationSummary(
            recommendations=recommendations,
            total_count=9
        )

        # Act
        domain_count = summary.domain_count

        # Assert
        self.assertEqual(
            domain_count,
            3,
            f"domain_count should be 3, got {domain_count}"
        )

    def test_domain_count_returns_zero_for_empty_recommendations(self):
        """
        Test that domain_count returns 0 when recommendations list is empty.

        Scenario: No recommendations when all domains are already blocked
        Then the "unique_domains_count" should be 0
        """
        from models.domain_recommendation_models import RecommendationSummary

        # Arrange
        summary = RecommendationSummary(
            recommendations=[],
            total_count=0
        )

        # Act
        domain_count = summary.domain_count

        # Assert
        self.assertEqual(
            domain_count,
            0,
            f"domain_count should be 0 for empty recommendations, got {domain_count}"
        )


class TestRecommendationSummaryToDict(unittest.TestCase):
    """
    Tests for RecommendationSummary.to_dict() method.

    Scenario: Response includes complete recommendation summary
    Then the response should include:
      | field                          | expected_value |
      | recommended_domains_to_block   | list           |
      | total_emails_matched           | 10             |
      | unique_domains_count           | 1              |
    """

    def test_to_dict_returns_complete_structure(self):
        """
        Test that to_dict() returns all required fields for response.
        """
        from models.domain_recommendation_models import (
            RecommendationSummary,
            DomainRecommendation
        )

        # Arrange
        recommendations = [
            DomainRecommendation(domain="example.com", category="Marketing", count=10)
        ]
        summary = RecommendationSummary(
            recommendations=recommendations,
            total_count=10
        )

        # Act
        result = summary.to_dict()

        # Assert - Check structure
        expected = {
            "recommended_domains_to_block": [
                {"domain": "example.com", "category": "Marketing", "count": 10}
            ],
            "total_emails_matched": 10,
            "unique_domains_count": 1
        }

        self.assertEqual(
            result,
            expected,
            f"to_dict() should return {expected}, got {result}"
        )

    def test_to_dict_empty_recommendations(self):
        """
        Test that to_dict() handles empty recommendations correctly.

        Scenario: No recommendations when all domains are already blocked
        Then the "recommended_domains_to_block" should be an empty list
        And the "unique_domains_count" should be 0
        """
        from models.domain_recommendation_models import RecommendationSummary

        # Arrange
        summary = RecommendationSummary(
            recommendations=[],
            total_count=0
        )

        # Act
        result = summary.to_dict()

        # Assert
        expected = {
            "recommended_domains_to_block": [],
            "total_emails_matched": 0,
            "unique_domains_count": 0
        }

        self.assertEqual(
            result,
            expected,
            f"to_dict() should return {expected}, got {result}"
        )

    def test_to_dict_multiple_recommendations(self):
        """
        Test that to_dict() correctly serializes multiple recommendations.

        Scenario: Multiple domains with different categories and counts
        """
        from models.domain_recommendation_models import (
            RecommendationSummary,
            DomainRecommendation
        )

        # Arrange
        recommendations = [
            DomainRecommendation(domain="marketing-spam.com", category="Marketing", count=12),
            DomainRecommendation(domain="ads-network.io", category="Advertising", count=8),
            DomainRecommendation(domain="pay-now.biz", category="Wants-Money", count=3),
        ]
        summary = RecommendationSummary(
            recommendations=recommendations,
            total_count=23
        )

        # Act
        result = summary.to_dict()

        # Assert
        self.assertEqual(len(result["recommended_domains_to_block"]), 3)
        self.assertEqual(result["total_emails_matched"], 23)
        self.assertEqual(result["unique_domains_count"], 3)


# ============================================================================
# SECTION 2: Sorting Tests (Count DESC, Domain Alpha)
# ============================================================================

class TestRecommendationsSortedByCountDescending(unittest.TestCase):
    """
    Scenario: Multiple domains with different categories and counts

    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email                    | category      | count |
      | spam@marketing-spam.com         | Marketing     | 12    |
      | promo@ads-network.io            | Advertising   | 8     |
      | donate@pay-now.biz              | Wants-Money   | 3     |
      | news@legit-news.com             | Personal      | 5     |
    Then the recommendations should be sorted by count in descending order
    And the first recommendation should have count 12
    And the last recommendation should have count 3
    """

    def test_recommendations_sorted_by_count_descending(self):
        """
        Test that recommendations are sorted by count in descending order.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Add domains with different counts (matching Gherkin scenario)
        for _ in range(12):
            collector.collect("marketing-spam.com", "Marketing", blocked_domains)
        for _ in range(8):
            collector.collect("ads-network.io", "Advertising", blocked_domains)
        for _ in range(3):
            collector.collect("pay-now.biz", "Wants-Money", blocked_domains)
        for _ in range(5):
            collector.collect("legit-news.com", "Personal", blocked_domains)  # Should be filtered

        # Act
        recommendations = collector.get_recommendations()

        # Assert - Should have 3 recommendations (Personal filtered out)
        self.assertEqual(
            len(recommendations),
            3,
            f"Should have 3 recommendations (Personal filtered), got {len(recommendations)}"
        )

        # First should be highest count
        self.assertEqual(
            recommendations[0].count,
            12,
            f"First recommendation should have count 12, got {recommendations[0].count}"
        )
        self.assertEqual(recommendations[0].domain, "marketing-spam.com")

        # Last should be lowest count
        self.assertEqual(
            recommendations[2].count,
            3,
            f"Last recommendation should have count 3, got {recommendations[2].count}"
        )
        self.assertEqual(recommendations[2].domain, "pay-now.biz")

    def test_total_emails_matched_excludes_non_qualifying(self):
        """
        Test that total_emails_matched only counts qualifying emails.

        And the "total_emails_matched" should be 23
        And domain "legit-news.com" should not be in recommendations
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Add emails matching the Gherkin scenario
        for _ in range(12):
            collector.collect("marketing-spam.com", "Marketing", blocked_domains)
        for _ in range(8):
            collector.collect("ads-network.io", "Advertising", blocked_domains)
        for _ in range(3):
            collector.collect("pay-now.biz", "Wants-Money", blocked_domains)
        for _ in range(5):
            collector.collect("legit-news.com", "Personal", blocked_domains)

        # Act
        total = collector.get_total_emails_matched()
        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(
            total,
            23,
            f"total_emails_matched should be 23 (12+8+3), got {total}"
        )

        # Personal domain should not be in recommendations
        domains = {r.domain for r in recommendations}
        self.assertNotIn(
            "legit-news.com",
            domains,
            "legit-news.com (Personal) should not be in recommendations"
        )


class TestRecommendationsSortedAlphabeticallyForSameCount(unittest.TestCase):
    """
    Scenario: Recommendations sorted by count descending then alphabetically

    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email                | category   | count |
      | spam@zebra-ads.com          | Marketing  | 5     |
      | ads@alpha-marketing.com     | Marketing  | 5     |
      | promo@beta-promo.com        | Marketing  | 3     |
    Then the recommendations should be sorted by count descending
    And for domains with equal count they should be sorted alphabetically
    And the recommendation order should be "alpha-marketing.com", "zebra-ads.com", "beta-promo.com"
    """

    def test_same_count_sorted_alphabetically(self):
        """
        Test that domains with same count are sorted alphabetically.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Add emails with same count for some domains
        for _ in range(5):
            collector.collect("zebra-ads.com", "Marketing", blocked_domains)
        for _ in range(5):
            collector.collect("alpha-marketing.com", "Marketing", blocked_domains)
        for _ in range(3):
            collector.collect("beta-promo.com", "Marketing", blocked_domains)

        # Act
        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(len(recommendations), 3)

        # Expected order: alpha-marketing.com (5), zebra-ads.com (5), beta-promo.com (3)
        # For count=5, alpha comes before zebra alphabetically
        domain_order = [r.domain for r in recommendations]
        expected_order = ["alpha-marketing.com", "zebra-ads.com", "beta-promo.com"]

        self.assertEqual(
            domain_order,
            expected_order,
            f"Expected order {expected_order}, got {domain_order}"
        )

    def test_multiple_domains_with_equal_counts_sorted_alphabetically(self):
        """
        Test that multiple domains with equal counts are sorted alphabetically.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # All have count 1
        collector.collect("zulu.com", "Marketing", blocked_domains)
        collector.collect("alpha.com", "Marketing", blocked_domains)
        collector.collect("charlie.com", "Marketing", blocked_domains)
        collector.collect("bravo.com", "Advertising", blocked_domains)

        # Act
        recommendations = collector.get_recommendations()

        # Assert - Should be in alphabetical order
        domain_order = [r.domain for r in recommendations]
        expected_order = ["alpha.com", "bravo.com", "charlie.com", "zulu.com"]

        self.assertEqual(
            domain_order,
            expected_order,
            f"Expected alphabetical order {expected_order}, got {domain_order}"
        )


# ============================================================================
# SECTION 3: Filtering Tests (Blocked Domains, Non-Qualifying Categories)
# ============================================================================

class TestNoRecommendationsWhenAllDomainsBlocked(unittest.TestCase):
    """
    Scenario: No recommendations when all domains are already blocked

    Given the blocked domains list contains:
      | domain              |
      | marketing-spam.com  |
      | ads-network.io      |
    And the inbox contains emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    And the inbox contains emails from "promo@ads-network.io" categorized as "Advertising"
    Then the "recommended_domains_to_block" should be an empty list
    And the "unique_domains_count" should be 0
    """

    def test_all_blocked_domains_returns_empty_recommendations(self):
        """
        Test that when all qualifying domains are blocked, recommendations is empty.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = {"marketing-spam.com", "ads-network.io"}

        # Act
        collector.collect("marketing-spam.com", "Marketing", blocked_domains)
        collector.collect("ads-network.io", "Advertising", blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(
            recommendations,
            [],
            f"Should be empty list when all domains blocked, got {recommendations}"
        )

    def test_unique_domains_count_is_zero_when_all_blocked(self):
        """
        Test that unique_domains_count is 0 when all domains are blocked.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = {"marketing-spam.com", "ads-network.io"}

        # Act
        collector.collect("marketing-spam.com", "Marketing", blocked_domains)
        collector.collect("ads-network.io", "Advertising", blocked_domains)

        unique_count = collector.get_unique_domains_count()

        # Assert
        self.assertEqual(
            unique_count,
            0,
            f"unique_domains_count should be 0, got {unique_count}"
        )


class TestNoRecommendationsWhenNoQualifyingCategories(unittest.TestCase):
    """
    Scenario: No recommendations when no emails match qualifying categories

    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email             | category     |
      | friend@personal.com      | Personal     |
      | work@company.com         | Work         |
      | news@newsletter.com      | Newsletter   |
    Then the "recommended_domains_to_block" should be an empty list
    """

    def test_no_qualifying_categories_returns_empty_recommendations(self):
        """
        Test that when no emails match qualifying categories, recommendations is empty.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act - Only non-qualifying categories
        collector.collect("personal.com", "Personal", blocked_domains)
        collector.collect("company.com", "Work", blocked_domains)
        collector.collect("newsletter.com", "Newsletter", blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(
            recommendations,
            [],
            f"Should be empty when no qualifying categories, got {len(recommendations)} recommendations"
        )


class TestNoRecommendationsWhenInboxEmpty(unittest.TestCase):
    """
    Scenario: No recommendations when inbox is empty

    Given the blocked domains list is empty
    And the inbox is empty
    Then the "recommended_domains_to_block" should be an empty list
    And the processing should complete successfully
    """

    def test_empty_inbox_returns_empty_recommendations(self):
        """
        Test that empty inbox returns empty recommendations.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()

        # Act - No emails collected
        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(
            recommendations,
            [],
            f"Should be empty for empty inbox, got {recommendations}"
        )

    def test_empty_inbox_total_emails_matched_is_zero(self):
        """
        Test that empty inbox has total_emails_matched of 0.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()

        # Act
        total = collector.get_total_emails_matched()

        # Assert
        self.assertEqual(total, 0)


class TestPartialBlocking(unittest.TestCase):
    """
    Scenario: Partial blocking - some domains blocked, some not

    Given the blocked domains list contains "marketing-spam.com"
    And the inbox contains:
      | sender_email                 | category   |
      | spam@marketing-spam.com      | Marketing  |
      | ads@new-ads-domain.com       | Advertising|
    Then the recommendations should include only domain "new-ads-domain.com"
    And domain "marketing-spam.com" should not be in recommendations
    """

    def test_partial_blocking_only_includes_unblocked(self):
        """
        Test that only unblocked domains appear in recommendations.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = {"marketing-spam.com"}

        # Act
        collector.collect("marketing-spam.com", "Marketing", blocked_domains)
        collector.collect("new-ads-domain.com", "Advertising", blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(
            recommendations[0].domain,
            "new-ads-domain.com",
            f"Should only include unblocked domain, got {recommendations[0].domain}"
        )

    def test_blocked_domain_not_in_recommendations(self):
        """
        Test that blocked domain is not in recommendations.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = {"marketing-spam.com"}

        # Act
        collector.collect("marketing-spam.com", "Marketing", blocked_domains)
        collector.collect("new-ads-domain.com", "Advertising", blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert
        domains = {r.domain for r in recommendations}
        self.assertNotIn(
            "marketing-spam.com",
            domains,
            "Blocked domain should not appear in recommendations"
        )


# ============================================================================
# SECTION 4: get_summary() Method Tests
# ============================================================================

class TestGetSummaryMethodExists(unittest.TestCase):
    """
    Tests that BlockingRecommendationCollector has get_summary() method.

    The method should return a RecommendationSummary object containing:
    - recommendations: List[DomainRecommendation]
    - total_count: int (total emails matched)
    """

    def test_get_summary_method_exists(self):
        """
        Test that BlockingRecommendationCollector has get_summary() method.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()

        # Assert method exists
        self.assertTrue(
            hasattr(collector, 'get_summary'),
            "BlockingRecommendationCollector should have get_summary method"
        )
        self.assertTrue(
            callable(getattr(collector, 'get_summary')),
            "get_summary should be callable"
        )

    def test_get_summary_returns_recommendation_summary(self):
        """
        Test that get_summary() returns a RecommendationSummary object.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )
        from models.domain_recommendation_models import RecommendationSummary

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()
        collector.collect("spam.com", "Marketing", blocked_domains)

        # Act
        summary = collector.get_summary()

        # Assert
        self.assertIsInstance(
            summary,
            RecommendationSummary,
            f"get_summary() should return RecommendationSummary, got {type(summary)}"
        )


class TestGetSummaryContainsCorrectData(unittest.TestCase):
    """
    Tests that get_summary() returns correct data matching the Gherkin scenarios.
    """

    def test_get_summary_contains_recommendations(self):
        """
        Test that get_summary() contains the recommendations list.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        collector.collect("spam.com", "Marketing", blocked_domains)
        collector.collect("spam.com", "Marketing", blocked_domains)
        collector.collect("ads.com", "Advertising", blocked_domains)

        # Act
        summary = collector.get_summary()

        # Assert
        self.assertEqual(len(summary.recommendations), 2)

    def test_get_summary_contains_total_count(self):
        """
        Test that get_summary() contains total_count matching total_emails_matched.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        for _ in range(12):
            collector.collect("marketing-spam.com", "Marketing", blocked_domains)
        for _ in range(8):
            collector.collect("ads-network.io", "Advertising", blocked_domains)
        for _ in range(3):
            collector.collect("pay-now.biz", "Wants-Money", blocked_domains)

        # Act
        summary = collector.get_summary()

        # Assert
        self.assertEqual(
            summary.total_count,
            23,
            f"total_count should be 23, got {summary.total_count}"
        )

    def test_get_summary_recommendations_sorted_correctly(self):
        """
        Test that get_summary().recommendations are sorted correctly.

        Sorted by count DESC, then domain ASC.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        for _ in range(5):
            collector.collect("zebra-ads.com", "Marketing", blocked_domains)
        for _ in range(5):
            collector.collect("alpha-marketing.com", "Marketing", blocked_domains)
        for _ in range(3):
            collector.collect("beta-promo.com", "Marketing", blocked_domains)

        # Act
        summary = collector.get_summary()

        # Assert
        domain_order = [r.domain for r in summary.recommendations]
        expected_order = ["alpha-marketing.com", "zebra-ads.com", "beta-promo.com"]

        self.assertEqual(
            domain_order,
            expected_order,
            f"Expected order {expected_order}, got {domain_order}"
        )

    def test_get_summary_to_dict_has_all_response_fields(self):
        """
        Test that get_summary().to_dict() has all fields needed for response.

        Scenario: Response includes complete recommendation summary
        Then the response should include:
          | field                          | expected_value |
          | recommended_domains_to_block   | list           |
          | total_emails_matched           | 10             |
          | unique_domains_count           | 1              |
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        for _ in range(10):
            collector.collect("example.com", "Marketing", blocked_domains)

        # Act
        summary = collector.get_summary()
        result = summary.to_dict()

        # Assert - Check all required fields exist
        required_fields = [
            "recommended_domains_to_block",
            "total_emails_matched",
            "unique_domains_count"
        ]
        for field in required_fields:
            self.assertIn(
                field,
                result,
                f"Response should include '{field}'"
            )

        # Check values
        self.assertEqual(result["total_emails_matched"], 10)
        self.assertEqual(result["unique_domains_count"], 1)
        self.assertIsInstance(result["recommended_domains_to_block"], list)


# ============================================================================
# SECTION 5: Response Structure for Integration Tests
# ============================================================================

class TestResponseMaintainsExistingFields(unittest.TestCase):
    """
    Scenario: Response maintains existing fields

    Given the blocked domains list is empty
    And the inbox contains 10 emails with 3 categorized as "Marketing" from unblocked domains
    Then the response should include all existing fields:
      | field                  |
      | account                |
      | emails_found           |
      | emails_processed       |
      | emails_categorized     |
      | processing_time_seconds|
      | timestamp              |
      | success                |
    And the response should also include new recommendation fields

    NOTE: This test documents the expected response structure for integration.
    The actual integration with process_account is tested elsewhere.
    """

    def test_recommendation_summary_to_dict_structure(self):
        """
        Test that RecommendationSummary.to_dict() provides correct structure
        for merging with existing response fields.
        """
        from models.domain_recommendation_models import (
            RecommendationSummary,
            DomainRecommendation
        )

        # Arrange
        recommendations = [
            DomainRecommendation(domain="spam.com", category="Marketing", count=3)
        ]
        summary = RecommendationSummary(
            recommendations=recommendations,
            total_count=3
        )

        # Act
        result = summary.to_dict()

        # Assert - Structure for merging with existing response
        self.assertIn("recommended_domains_to_block", result)
        self.assertIn("total_emails_matched", result)
        self.assertIn("unique_domains_count", result)

        # The recommendation fields should be a flat dict structure
        # that can be merged with existing process_account response
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result.keys()), 3)


class TestNotificationFields(unittest.TestCase):
    """
    Scenario: Response includes complete recommendation summary
    Then the response should include:
      | field                          | expected_value |
      | notification_sent              | true           |
      | notification_error             | null           |

    NOTE: notification_sent and notification_error are added by the
    notification service after sending. These tests document the expected
    structure but the actual fields are added at integration time.
    """

    def test_recommendation_summary_does_not_include_notification_fields(self):
        """
        Test that RecommendationSummary.to_dict() does NOT include notification fields.

        Notification fields are added by the notification service, not the summary.
        """
        from models.domain_recommendation_models import (
            RecommendationSummary,
            DomainRecommendation
        )

        # Arrange
        recommendations = [
            DomainRecommendation(domain="spam.com", category="Marketing", count=3)
        ]
        summary = RecommendationSummary(
            recommendations=recommendations,
            total_count=3
        )

        # Act
        result = summary.to_dict()

        # Assert - notification fields should NOT be in summary
        # They are added by notification service
        self.assertNotIn("notification_sent", result)
        self.assertNotIn("notification_error", result)


# ============================================================================
# SECTION 6: Edge Cases and Boundary Conditions
# ============================================================================

class TestEdgeCasesForSummary(unittest.TestCase):
    """
    Edge cases and boundary conditions for recommendation summary.
    """

    def test_get_summary_empty_collector(self):
        """
        Test get_summary() on empty collector.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()

        # Act
        summary = collector.get_summary()

        # Assert
        self.assertEqual(len(summary.recommendations), 0)
        self.assertEqual(summary.total_count, 0)
        self.assertEqual(summary.domain_count, 0)

    def test_get_summary_after_clear(self):
        """
        Test get_summary() after clear() returns empty summary.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        collector.collect("spam.com", "Marketing", blocked_domains)
        collector.collect("spam.com", "Marketing", blocked_domains)
        collector.clear()

        # Act
        summary = collector.get_summary()

        # Assert
        self.assertEqual(len(summary.recommendations), 0)
        self.assertEqual(summary.total_count, 0)

    def test_get_summary_large_dataset(self):
        """
        Test get_summary() with many domains and high counts.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Add 100 different domains with varying counts
        for i in range(100):
            domain = f"spam{i:03d}.com"
            count = (i % 20) + 1  # Counts from 1 to 20
            for _ in range(count):
                collector.collect(domain, "Marketing", blocked_domains)

        # Act
        summary = collector.get_summary()

        # Assert
        self.assertEqual(summary.domain_count, 100)
        self.assertEqual(
            summary.total_count,
            sum((i % 20) + 1 for i in range(100))
        )

        # First recommendation should have highest count (20)
        # Multiple domains have count=20, should be sorted alphabetically
        self.assertEqual(summary.recommendations[0].count, 20)


class TestCaseInsensitiveDomainHandling(unittest.TestCase):
    """
    Test case-insensitive domain handling in summary.
    """

    def test_case_insensitive_aggregation_in_summary(self):
        """
        Test that case-insensitive domain aggregation is reflected in summary.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        collector.collect("SPAM.COM", "Marketing", blocked_domains)
        collector.collect("spam.com", "Marketing", blocked_domains)
        collector.collect("Spam.Com", "Marketing", blocked_domains)

        # Act
        summary = collector.get_summary()

        # Assert - Should be aggregated as one
        self.assertEqual(summary.domain_count, 1)
        self.assertEqual(summary.total_count, 3)
        self.assertEqual(len(summary.recommendations), 1)
        self.assertEqual(summary.recommendations[0].count, 3)

    def test_case_insensitive_blocking_in_summary(self):
        """
        Test that case-insensitive blocked domain check is reflected in summary.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = {"BLOCKED.COM"}

        # Try to add with different cases
        collector.collect("blocked.com", "Marketing", blocked_domains)
        collector.collect("Blocked.Com", "Marketing", blocked_domains)

        # Act
        summary = collector.get_summary()

        # Assert - All should be blocked
        self.assertEqual(summary.domain_count, 0)
        self.assertEqual(summary.total_count, 0)
        self.assertEqual(len(summary.recommendations), 0)


if __name__ == '__main__':
    unittest.main()
