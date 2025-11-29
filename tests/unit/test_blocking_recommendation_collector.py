"""
Tests for BlockingRecommendationCollector component (TDD Red Phase).

This component is responsible for:
1. Collecting domains during email processing that are candidates for blocking
2. Filtering by qualifying categories: Marketing, Advertising, Wants-Money
3. Excluding already-blocked domains
4. Aggregating counts per domain+category pair
5. Providing sorted recommendations

Based on Gherkin scenarios from the Blocking Recommendations Email Notification feature.
These tests follow TDD Red phase - they will fail until implementation is complete.
"""
import unittest
from dataclasses import dataclass
from typing import List, Set, Dict, Protocol
from abc import ABC, abstractmethod


# ============================================================================
# SECTION 1: Interface Tests
# ============================================================================

class TestIBlockingRecommendationCollectorInterface(unittest.TestCase):
    """
    Tests to verify the IBlockingRecommendationCollector interface exists
    and has the correct methods.

    The interface should define:
    - collect(sender_domain, category, blocked_domains) -> None
    - get_recommendations() -> List[DomainRecommendation]
    - clear() -> None
    """

    def test_interface_exists(self):
        """
        Test that IBlockingRecommendationCollector interface exists.

        The implementation should define an interface in:
        services/interfaces/blocking_recommendation_collector_interface.py
        """
        # Act & Assert
        from services.interfaces.blocking_recommendation_collector_interface import (
            IBlockingRecommendationCollector
        )

        # Verify it's an abstract class or protocol
        import inspect
        self.assertTrue(
            inspect.isabstract(IBlockingRecommendationCollector) or
            hasattr(IBlockingRecommendationCollector, '__protocol_attrs__'),
            "IBlockingRecommendationCollector should be an abstract class or Protocol"
        )

    def test_interface_has_collect_method(self):
        """
        Test that interface defines collect method.

        The collect method should:
        - Accept sender_domain (str), category (str), blocked_domains (Set[str])
        - Return None
        - Record the domain if it qualifies for blocking recommendations
        """
        from services.interfaces.blocking_recommendation_collector_interface import (
            IBlockingRecommendationCollector
        )
        import inspect

        methods = [name for name, _ in inspect.getmembers(
            IBlockingRecommendationCollector,
            predicate=inspect.isfunction
        )]
        self.assertIn(
            "collect",
            methods,
            "IBlockingRecommendationCollector should have collect method"
        )

    def test_interface_has_get_recommendations_method(self):
        """
        Test that interface defines get_recommendations method.

        The get_recommendations method should:
        - Accept no arguments
        - Return List[DomainRecommendation]
        """
        from services.interfaces.blocking_recommendation_collector_interface import (
            IBlockingRecommendationCollector
        )
        import inspect

        methods = [name for name, _ in inspect.getmembers(
            IBlockingRecommendationCollector,
            predicate=inspect.isfunction
        )]
        self.assertIn(
            "get_recommendations",
            methods,
            "IBlockingRecommendationCollector should have get_recommendations method"
        )

    def test_interface_has_clear_method(self):
        """
        Test that interface defines clear method.

        The clear method should:
        - Accept no arguments
        - Return None
        - Reset the collector's internal state
        """
        from services.interfaces.blocking_recommendation_collector_interface import (
            IBlockingRecommendationCollector
        )
        import inspect

        methods = [name for name, _ in inspect.getmembers(
            IBlockingRecommendationCollector,
            predicate=inspect.isfunction
        )]
        self.assertIn(
            "clear",
            methods,
            "IBlockingRecommendationCollector should have clear method"
        )


# ============================================================================
# SECTION 2: Data Model Tests
# ============================================================================

class TestDomainRecommendationModel(unittest.TestCase):
    """
    Tests for DomainRecommendation data model.

    Scenario: DomainRecommendation contains required fields
    Given the blocked domains list is empty
    And the inbox contains emails from "spam@test.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then each recommendation object should contain:
      | field    | type   |
      | domain   | string |
      | category | string |
      | count    | integer|

    The model should be an immutable dataclass with to_dict() method.
    """

    def test_domain_recommendation_model_exists(self):
        """
        Test that DomainRecommendation model exists.

        The model should be defined in:
        models/domain_recommendation_models.py
        """
        # Act & Assert
        from models.domain_recommendation_models import DomainRecommendation

        self.assertTrue(
            hasattr(DomainRecommendation, '__dataclass_fields__'),
            "DomainRecommendation should be a dataclass"
        )

    def test_domain_recommendation_has_domain_field(self):
        """
        Test that DomainRecommendation has domain field of type string.
        """
        from models.domain_recommendation_models import DomainRecommendation

        self.assertIn(
            'domain',
            DomainRecommendation.__dataclass_fields__,
            "DomainRecommendation should have 'domain' field"
        )

        field = DomainRecommendation.__dataclass_fields__['domain']
        self.assertEqual(
            field.type,
            str,
            "domain field should be of type str"
        )

    def test_domain_recommendation_has_category_field(self):
        """
        Test that DomainRecommendation has category field of type string.
        """
        from models.domain_recommendation_models import DomainRecommendation

        self.assertIn(
            'category',
            DomainRecommendation.__dataclass_fields__,
            "DomainRecommendation should have 'category' field"
        )

        field = DomainRecommendation.__dataclass_fields__['category']
        self.assertEqual(
            field.type,
            str,
            "category field should be of type str"
        )

    def test_domain_recommendation_has_count_field(self):
        """
        Test that DomainRecommendation has count field of type integer.
        """
        from models.domain_recommendation_models import DomainRecommendation

        self.assertIn(
            'count',
            DomainRecommendation.__dataclass_fields__,
            "DomainRecommendation should have 'count' field"
        )

        field = DomainRecommendation.__dataclass_fields__['count']
        self.assertEqual(
            field.type,
            int,
            "count field should be of type int"
        )

    def test_domain_recommendation_can_be_created_with_valid_data(self):
        """
        Test that DomainRecommendation can be instantiated with valid data.
        """
        from models.domain_recommendation_models import DomainRecommendation

        # Arrange
        domain = "marketing-spam.com"
        category = "Marketing"
        count = 5

        # Act
        recommendation = DomainRecommendation(
            domain=domain,
            category=category,
            count=count
        )

        # Assert
        self.assertEqual(recommendation.domain, domain)
        self.assertEqual(recommendation.category, category)
        self.assertEqual(recommendation.count, count)

    def test_domain_recommendation_has_to_dict_method(self):
        """
        Test that DomainRecommendation has to_dict() method.

        The to_dict() method should return a dictionary representation
        of the recommendation object.
        """
        from models.domain_recommendation_models import DomainRecommendation

        recommendation = DomainRecommendation(
            domain="test.com",
            category="Marketing",
            count=3
        )

        # Assert method exists
        self.assertTrue(
            hasattr(recommendation, 'to_dict'),
            "DomainRecommendation should have to_dict method"
        )

        # Assert it returns expected structure
        result = recommendation.to_dict()
        expected = {
            "domain": "test.com",
            "category": "Marketing",
            "count": 3
        }
        self.assertEqual(
            result,
            expected,
            f"to_dict() should return {expected}, got {result}"
        )

    def test_domain_recommendation_is_immutable(self):
        """
        Test that DomainRecommendation is immutable (frozen dataclass).

        Once created, the fields should not be modifiable.
        """
        from models.domain_recommendation_models import DomainRecommendation

        recommendation = DomainRecommendation(
            domain="test.com",
            category="Marketing",
            count=3
        )

        # Act & Assert - trying to modify should raise an error
        with self.assertRaises(AttributeError):
            recommendation.domain = "other.com"

        with self.assertRaises(AttributeError):
            recommendation.count = 10


# ============================================================================
# SECTION 3: BlockingRecommendationCollector Implementation Tests
# ============================================================================

class TestBlockingRecommendationCollectorCreation(unittest.TestCase):
    """
    Tests for BlockingRecommendationCollector instantiation.
    """

    def test_collector_class_exists(self):
        """
        Test that BlockingRecommendationCollector class exists.

        The implementation should be in:
        services/blocking_recommendation_collector.py
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        self.assertTrue(
            callable(BlockingRecommendationCollector),
            "BlockingRecommendationCollector should be a callable class"
        )

    def test_collector_can_be_instantiated(self):
        """
        Test that BlockingRecommendationCollector can be instantiated.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Act
        collector = BlockingRecommendationCollector()

        # Assert
        self.assertIsNotNone(collector)

    def test_collector_implements_interface(self):
        """
        Test that BlockingRecommendationCollector implements IBlockingRecommendationCollector.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )
        from services.interfaces.blocking_recommendation_collector_interface import (
            IBlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()

        self.assertIsInstance(
            collector,
            IBlockingRecommendationCollector,
            "BlockingRecommendationCollector should implement IBlockingRecommendationCollector"
        )


class TestCollectMarketingDomain(unittest.TestCase):
    """
    Scenario: Generate recommendations for unblocked Marketing domain

    Given the blocked domains list is empty
    And the inbox contains emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "marketing-spam.com" with category "Marketing"
    """

    def test_collect_marketing_domain_adds_to_recommendations(self):
        """
        Test that collecting a Marketing domain adds it to recommendations.

        Given the blocked domains list is empty
        And an email from "marketing-spam.com" categorized as "Marketing"
        When collect is called
        Then get_recommendations should include the domain
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        sender_domain = "marketing-spam.com"
        category = "Marketing"
        blocked_domains: Set[str] = set()

        # Act
        collector.collect(sender_domain, category, blocked_domains)
        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(
            len(recommendations),
            1,
            f"Should have 1 recommendation, got {len(recommendations)}"
        )
        self.assertEqual(
            recommendations[0].domain,
            "marketing-spam.com",
            f"Domain should be 'marketing-spam.com', got '{recommendations[0].domain}'"
        )
        self.assertEqual(
            recommendations[0].category,
            "Marketing",
            f"Category should be 'Marketing', got '{recommendations[0].category}'"
        )


class TestCollectAdvertisingDomain(unittest.TestCase):
    """
    Scenario: Generate recommendations for unblocked Advertising domain

    Given the blocked domains list is empty
    And the inbox contains emails from "ads@ads-network.io" categorized as "Advertising"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "ads-network.io" with category "Advertising"
    """

    def test_collect_advertising_domain_adds_to_recommendations(self):
        """
        Test that collecting an Advertising domain adds it to recommendations.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        sender_domain = "ads-network.io"
        category = "Advertising"
        blocked_domains: Set[str] = set()

        # Act
        collector.collect(sender_domain, category, blocked_domains)
        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].domain, "ads-network.io")
        self.assertEqual(recommendations[0].category, "Advertising")


class TestCollectWantsMoneyDomain(unittest.TestCase):
    """
    Scenario: Generate recommendations for unblocked Wants-Money domain

    Given the blocked domains list is empty
    And the inbox contains emails from "donate@pay-now.biz" categorized as "Wants-Money"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "pay-now.biz" with category "Wants-Money"
    """

    def test_collect_wants_money_domain_adds_to_recommendations(self):
        """
        Test that collecting a Wants-Money domain adds it to recommendations.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        sender_domain = "pay-now.biz"
        category = "Wants-Money"
        blocked_domains: Set[str] = set()

        # Act
        collector.collect(sender_domain, category, blocked_domains)
        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].domain, "pay-now.biz")
        self.assertEqual(recommendations[0].category, "Wants-Money")


class TestAggregateCountForMultipleEmails(unittest.TestCase):
    """
    Scenario: Aggregate count for multiple emails from same domain

    Given the blocked domains list is empty
    And the inbox contains 5 emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include domain "marketing-spam.com" with count 5
    And the "total_emails_matched" should be 5
    And the "unique_domains_count" should be 1
    """

    def test_multiple_emails_from_same_domain_aggregates_count(self):
        """
        Test that multiple emails from the same domain aggregate the count.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        sender_domain = "marketing-spam.com"
        category = "Marketing"
        blocked_domains: Set[str] = set()

        # Act - Collect 5 emails from the same domain
        for _ in range(5):
            collector.collect(sender_domain, category, blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(
            len(recommendations),
            1,
            f"Should have 1 recommendation (aggregated), got {len(recommendations)}"
        )
        self.assertEqual(
            recommendations[0].count,
            5,
            f"Count should be 5, got {recommendations[0].count}"
        )

    def test_get_total_emails_matched_returns_correct_count(self):
        """
        Test that get_total_emails_matched returns the total count across all domains.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act - Collect 5 Marketing emails from one domain
        for _ in range(5):
            collector.collect("marketing-spam.com", "Marketing", blocked_domains)

        total = collector.get_total_emails_matched()

        # Assert
        self.assertEqual(
            total,
            5,
            f"total_emails_matched should be 5, got {total}"
        )

    def test_get_unique_domains_count_returns_correct_count(self):
        """
        Test that get_unique_domains_count returns the count of unique domains.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act - Collect 5 emails from the same domain
        for _ in range(5):
            collector.collect("marketing-spam.com", "Marketing", blocked_domains)

        unique_count = collector.get_unique_domains_count()

        # Assert
        self.assertEqual(
            unique_count,
            1,
            f"unique_domains_count should be 1, got {unique_count}"
        )


class TestCollectorClearedBetweenRuns(unittest.TestCase):
    """
    Scenario: Collector is cleared between processing runs

    Given the blocked domains list is empty
    And account "user@gmail.com" was previously processed with recommendations
    When the process_account function runs again for "user@gmail.com"
    Then the recommendations should only reflect the current processing run
    And previous recommendations should not be carried over
    """

    def test_clear_removes_all_recommendations(self):
        """
        Test that clear() removes all previously collected recommendations.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # First run - collect some domains
        collector.collect("spam1.com", "Marketing", blocked_domains)
        collector.collect("spam2.com", "Advertising", blocked_domains)

        # Verify we have recommendations
        self.assertEqual(len(collector.get_recommendations()), 2)

        # Act - Clear the collector
        collector.clear()

        # Assert
        recommendations = collector.get_recommendations()
        self.assertEqual(
            len(recommendations),
            0,
            f"After clear(), should have 0 recommendations, got {len(recommendations)}"
        )

    def test_clear_resets_total_emails_matched(self):
        """
        Test that clear() resets the total_emails_matched counter.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Collect some domains
        collector.collect("spam1.com", "Marketing", blocked_domains)
        collector.collect("spam1.com", "Marketing", blocked_domains)

        # Act
        collector.clear()

        # Assert
        self.assertEqual(
            collector.get_total_emails_matched(),
            0,
            "After clear(), total_emails_matched should be 0"
        )

    def test_clear_resets_unique_domains_count(self):
        """
        Test that clear() resets the unique_domains_count counter.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Collect some domains
        collector.collect("spam1.com", "Marketing", blocked_domains)
        collector.collect("spam2.com", "Advertising", blocked_domains)

        # Act
        collector.clear()

        # Assert
        self.assertEqual(
            collector.get_unique_domains_count(),
            0,
            "After clear(), unique_domains_count should be 0"
        )

    def test_new_run_after_clear_only_reflects_current_data(self):
        """
        Test that after clear(), a new run only contains current run's data.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # First run
        collector.collect("old-spam.com", "Marketing", blocked_domains)
        collector.collect("old-spam.com", "Marketing", blocked_domains)
        collector.collect("old-spam.com", "Marketing", blocked_domains)

        # Clear for new run
        collector.clear()

        # Second run - new data
        collector.collect("new-spam.com", "Advertising", blocked_domains)

        # Assert
        recommendations = collector.get_recommendations()
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].domain, "new-spam.com")
        self.assertEqual(recommendations[0].count, 1)


class TestOnlyQualifyingCategoriesTracked(unittest.TestCase):
    """
    Scenario: Collector only tracks qualifying categories

    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email         | category      |
      | spam@junk.com        | Marketing     |
      | work@company.com     | Work          |
      | promo@ads.com        | Advertising   |
      | friend@personal.com  | Personal      |
      | donate@charity.com   | Wants-Money   |
      | news@updates.com     | Newsletter    |
    When the process_account function runs for "user@gmail.com"
    Then only domains from "Marketing", "Advertising", and "Wants-Money" categories should be recommended
    And "Work", "Personal", and "Newsletter" domains should not appear
    """

    def test_marketing_is_qualifying_category(self):
        """
        Test that Marketing is a qualifying category.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        collector.collect("junk.com", "Marketing", blocked_domains)
        recommendations = collector.get_recommendations()

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].domain, "junk.com")

    def test_advertising_is_qualifying_category(self):
        """
        Test that Advertising is a qualifying category.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        collector.collect("ads.com", "Advertising", blocked_domains)
        recommendations = collector.get_recommendations()

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].domain, "ads.com")

    def test_wants_money_is_qualifying_category(self):
        """
        Test that Wants-Money is a qualifying category.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        collector.collect("charity.com", "Wants-Money", blocked_domains)
        recommendations = collector.get_recommendations()

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].domain, "charity.com")

    def test_work_is_not_qualifying_category(self):
        """
        Test that Work category is NOT tracked.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        collector.collect("company.com", "Work", blocked_domains)
        recommendations = collector.get_recommendations()

        self.assertEqual(
            len(recommendations),
            0,
            f"Work category should not be tracked, got {len(recommendations)} recommendations"
        )

    def test_personal_is_not_qualifying_category(self):
        """
        Test that Personal category is NOT tracked.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        collector.collect("personal.com", "Personal", blocked_domains)
        recommendations = collector.get_recommendations()

        self.assertEqual(
            len(recommendations),
            0,
            f"Personal category should not be tracked, got {len(recommendations)} recommendations"
        )

    def test_newsletter_is_not_qualifying_category(self):
        """
        Test that Newsletter category is NOT tracked.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        collector.collect("updates.com", "Newsletter", blocked_domains)
        recommendations = collector.get_recommendations()

        self.assertEqual(
            len(recommendations),
            0,
            f"Newsletter category should not be tracked, got {len(recommendations)} recommendations"
        )

    def test_mixed_categories_only_tracks_qualifying(self):
        """
        Test that when multiple categories are collected, only qualifying ones are tracked.

        This is the complete scenario from the Gherkin.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Collect emails from the Gherkin table
        collector.collect("junk.com", "Marketing", blocked_domains)      # Should be tracked
        collector.collect("company.com", "Work", blocked_domains)        # Should NOT be tracked
        collector.collect("ads.com", "Advertising", blocked_domains)     # Should be tracked
        collector.collect("personal.com", "Personal", blocked_domains)   # Should NOT be tracked
        collector.collect("charity.com", "Wants-Money", blocked_domains) # Should be tracked
        collector.collect("updates.com", "Newsletter", blocked_domains)  # Should NOT be tracked

        recommendations = collector.get_recommendations()

        # Assert only qualifying categories are in recommendations
        self.assertEqual(
            len(recommendations),
            3,
            f"Should have 3 recommendations (Marketing, Advertising, Wants-Money), got {len(recommendations)}"
        )

        domains = {r.domain for r in recommendations}
        self.assertEqual(
            domains,
            {"junk.com", "ads.com", "charity.com"},
            f"Expected domains from qualifying categories, got {domains}"
        )

        # Assert non-qualifying categories are NOT in recommendations
        non_qualifying_domains = {"company.com", "personal.com", "updates.com"}
        for domain in non_qualifying_domains:
            self.assertNotIn(
                domain,
                domains,
                f"Domain {domain} from non-qualifying category should not be in recommendations"
            )


class TestExcludesBlockedDomains(unittest.TestCase):
    """
    Test that already-blocked domains are excluded from recommendations.
    """

    def test_blocked_domain_is_not_added(self):
        """
        Test that a domain already in blocked_domains is not added to recommendations.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = {"already-blocked.com"}

        # Act
        collector.collect("already-blocked.com", "Marketing", blocked_domains)
        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(
            len(recommendations),
            0,
            "Already blocked domains should not be added to recommendations"
        )

    def test_unblocked_domain_is_added_when_others_blocked(self):
        """
        Test that unblocked domains are still added when other domains are blocked.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = {"blocked1.com", "blocked2.com"}

        # Act
        collector.collect("not-blocked.com", "Marketing", blocked_domains)
        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].domain, "not-blocked.com")

    def test_mixed_blocked_and_unblocked_domains(self):
        """
        Test with a mix of blocked and unblocked domains.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = {"blocked.com"}

        # Act
        collector.collect("blocked.com", "Marketing", blocked_domains)    # Should be excluded
        collector.collect("unblocked1.com", "Marketing", blocked_domains) # Should be added
        collector.collect("unblocked2.com", "Advertising", blocked_domains) # Should be added

        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(len(recommendations), 2)
        domains = {r.domain for r in recommendations}
        self.assertEqual(domains, {"unblocked1.com", "unblocked2.com"})
        self.assertNotIn("blocked.com", domains)


class TestRecommendationsSorting(unittest.TestCase):
    """
    Test that recommendations are sorted correctly.

    Recommendations should be sorted by:
    1. Count descending (most emails first)
    2. Domain alphabetically (for same count)
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

        # Add domains with different counts
        for _ in range(3):
            collector.collect("low.com", "Marketing", blocked_domains)
        for _ in range(10):
            collector.collect("high.com", "Marketing", blocked_domains)
        for _ in range(5):
            collector.collect("medium.com", "Marketing", blocked_domains)

        # Act
        recommendations = collector.get_recommendations()

        # Assert - should be sorted by count descending
        self.assertEqual(len(recommendations), 3)
        self.assertEqual(
            recommendations[0].domain,
            "high.com",
            f"First should be 'high.com' with count 10, got '{recommendations[0].domain}'"
        )
        self.assertEqual(recommendations[0].count, 10)
        self.assertEqual(
            recommendations[1].domain,
            "medium.com",
            f"Second should be 'medium.com' with count 5, got '{recommendations[1].domain}'"
        )
        self.assertEqual(recommendations[1].count, 5)
        self.assertEqual(
            recommendations[2].domain,
            "low.com",
            f"Third should be 'low.com' with count 3, got '{recommendations[2].domain}'"
        )
        self.assertEqual(recommendations[2].count, 3)

    def test_recommendations_sorted_alphabetically_for_same_count(self):
        """
        Test that domains with the same count are sorted alphabetically.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Add domains with same count
        collector.collect("zebra.com", "Marketing", blocked_domains)
        collector.collect("alpha.com", "Marketing", blocked_domains)
        collector.collect("middle.com", "Marketing", blocked_domains)

        # Act
        recommendations = collector.get_recommendations()

        # Assert - should be sorted alphabetically for same count
        self.assertEqual(len(recommendations), 3)
        domains_in_order = [r.domain for r in recommendations]
        self.assertEqual(
            domains_in_order,
            ["alpha.com", "middle.com", "zebra.com"],
            f"Expected alphabetical order, got {domains_in_order}"
        )


class TestMultipleCategoriesForSameDomain(unittest.TestCase):
    """
    Test handling of the same domain appearing in multiple qualifying categories.
    """

    def test_same_domain_different_categories_creates_separate_recommendations(self):
        """
        Test that the same domain with different categories creates separate recommendations.

        If example.com sends both Marketing and Advertising emails, they should be
        tracked separately per category.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act - Same domain, different categories
        collector.collect("spammer.com", "Marketing", blocked_domains)
        collector.collect("spammer.com", "Marketing", blocked_domains)
        collector.collect("spammer.com", "Advertising", blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert - Should have 2 separate recommendations (one per category)
        self.assertEqual(
            len(recommendations),
            2,
            f"Should have 2 recommendations (Marketing + Advertising), got {len(recommendations)}"
        )

        # Find the recommendations by category
        marketing_rec = next(
            (r for r in recommendations if r.category == "Marketing"),
            None
        )
        advertising_rec = next(
            (r for r in recommendations if r.category == "Advertising"),
            None
        )

        self.assertIsNotNone(marketing_rec, "Should have Marketing recommendation")
        self.assertEqual(marketing_rec.count, 2)
        self.assertEqual(marketing_rec.domain, "spammer.com")

        self.assertIsNotNone(advertising_rec, "Should have Advertising recommendation")
        self.assertEqual(advertising_rec.count, 1)
        self.assertEqual(advertising_rec.domain, "spammer.com")


class TestEdgeCases(unittest.TestCase):
    """
    Test edge cases and boundary conditions.
    """

    def test_empty_collector_returns_empty_list(self):
        """
        Test that a new collector with no data returns empty list.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()
        recommendations = collector.get_recommendations()

        self.assertEqual(
            recommendations,
            [],
            f"Empty collector should return empty list, got {recommendations}"
        )

    def test_empty_collector_returns_zero_total(self):
        """
        Test that a new collector returns 0 for total_emails_matched.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()
        total = collector.get_total_emails_matched()

        self.assertEqual(total, 0)

    def test_empty_collector_returns_zero_unique_domains(self):
        """
        Test that a new collector returns 0 for unique_domains_count.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()
        count = collector.get_unique_domains_count()

        self.assertEqual(count, 0)

    def test_case_insensitive_domain_matching(self):
        """
        Test that domain matching is case-insensitive.

        "SPAM.COM" and "spam.com" should be treated as the same domain.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act - Same domain, different cases
        collector.collect("SPAM.COM", "Marketing", blocked_domains)
        collector.collect("spam.com", "Marketing", blocked_domains)
        collector.collect("Spam.Com", "Marketing", blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert - Should be aggregated as one
        self.assertEqual(
            len(recommendations),
            1,
            f"Different cases should be aggregated, got {len(recommendations)} recommendations"
        )
        self.assertEqual(recommendations[0].count, 3)

    def test_blocked_domain_case_insensitive(self):
        """
        Test that blocked domain matching is case-insensitive.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = {"BLOCKED.COM"}

        # Act
        collector.collect("blocked.com", "Marketing", blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(
            len(recommendations),
            0,
            "Case-insensitive blocked domain check should exclude 'blocked.com'"
        )


class TestGetQualifyingCategories(unittest.TestCase):
    """
    Test the list of qualifying categories is accessible.
    """

    def test_get_qualifying_categories_returns_correct_list(self):
        """
        Test that get_qualifying_categories returns the expected categories.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        collector = BlockingRecommendationCollector()

        # The method may be a class method or static method
        qualifying = collector.get_qualifying_categories()

        self.assertIsInstance(qualifying, (list, set, tuple))
        self.assertIn("Marketing", qualifying)
        self.assertIn("Advertising", qualifying)
        self.assertIn("Wants-Money", qualifying)
        self.assertEqual(
            len(qualifying),
            3,
            f"Should have exactly 3 qualifying categories, got {len(qualifying)}"
        )


if __name__ == '__main__':
    unittest.main()
