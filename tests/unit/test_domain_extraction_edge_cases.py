"""
Tests for Domain Extraction Edge Cases (TDD Red Phase).

This module tests edge cases for domain extraction from email addresses
and multi-category domain tracking. These are critical for accurate
blocking recommendations.

Based on Gherkin scenarios:
- Scenario: Single email generates recommendation
- Scenario: Domain with special characters in sender email
- Scenario: Same domain appears with different categories
- Scenario: Very long domain name handling
- Scenario: International domain names

These tests follow TDD Red phase - they will fail until implementation is complete.
"""
import unittest
from typing import Set


# ============================================================================
# SECTION 1: Domain Extraction Utility Tests
# ============================================================================

class TestDomainExtractorExists(unittest.TestCase):
    """
    Tests that a domain extraction utility exists.

    The utility should:
    - Be importable from utils/domain_extractor.py or services/domain_extractor.py
    - Have an extract_domain function
    - Handle various email address formats
    """

    def test_domain_extractor_module_exists(self):
        """
        Test that domain extractor utility exists.

        The implementation should define a domain extraction utility in:
        utils/domain_extractor.py OR services/domain_extractor.py
        """
        # Act & Assert - Try to import from utils first, then services
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        self.assertTrue(
            callable(extract_domain),
            "extract_domain should be a callable function"
        )

    def test_extract_domain_function_signature(self):
        """
        Test that extract_domain accepts an email address and returns a string.

        The function signature should be:
        def extract_domain(email_address: str) -> str
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        import inspect
        sig = inspect.signature(extract_domain)

        # Should have exactly one required parameter
        params = list(sig.parameters.values())
        required_params = [p for p in params if p.default is inspect.Parameter.empty]

        self.assertGreaterEqual(
            len(required_params),
            1,
            "extract_domain should have at least one required parameter"
        )


class TestExtractDomainBasicFunctionality(unittest.TestCase):
    """
    Basic domain extraction tests.

    Algorithm:
    1. Split email by '@'
    2. Return the part after '@' in lowercase
    3. Handle invalid formats with ValueError
    """

    def test_extract_domain_simple_email(self):
        """
        Test basic domain extraction from simple email address.

        Given: user@example.com
        Then: extract_domain should return "example.com"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "user@example.com"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "example.com",
            f"Expected 'example.com', got '{result}'"
        )

    def test_extract_domain_normalizes_to_lowercase(self):
        """
        Test that domain extraction normalizes to lowercase.

        Given: USER@EXAMPLE.COM
        Then: extract_domain should return "example.com"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "USER@EXAMPLE.COM"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "example.com",
            f"Domain should be lowercase, got '{result}'"
        )

    def test_extract_domain_invalid_no_at_symbol(self):
        """
        Test that extract_domain raises ValueError for invalid email without @.

        Given: invalid-email
        Then: extract_domain should raise ValueError
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "invalid-email"

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            extract_domain(email)

        self.assertIn(
            "Invalid email",
            str(context.exception),
            f"Error message should mention 'Invalid email', got '{context.exception}'"
        )


# ============================================================================
# SECTION 2: Plus Addressing (user+tag@domain.com)
# ============================================================================

class TestPlusAddressingDomainExtraction(unittest.TestCase):
    """
    Scenario: Domain with special characters in sender email

    Given the blocked domains list is empty
    And the inbox contains emails from "user+tag@sub.domain-name.co.uk" categorized as "Advertising"
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include domain "sub.domain-name.co.uk"
    And the domain should be correctly extracted from the sender email
    """

    def test_extract_domain_plus_addressing(self):
        """
        Test domain extraction handles plus addressing.

        Plus addressing format: user+tag@domain.com
        The '+tag' is part of the local part, not the domain.

        Given: user+tag@example.com
        Then: extract_domain should return "example.com"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "user+tag@example.com"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "example.com",
            f"Plus addressing should not affect domain extraction, got '{result}'"
        )

    def test_extract_domain_plus_addressing_with_subdomain(self):
        """
        Test domain extraction with plus addressing and subdomain.

        Given: user+newsletter@sub.domain-name.co.uk
        Then: extract_domain should return "sub.domain-name.co.uk"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "user+newsletter@sub.domain-name.co.uk"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "sub.domain-name.co.uk",
            f"Expected 'sub.domain-name.co.uk', got '{result}'"
        )

    def test_extract_domain_multiple_plus_signs(self):
        """
        Test domain extraction with multiple plus signs in local part.

        Given: user+tag+filter@example.com
        Then: extract_domain should return "example.com"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "user+tag+filter@example.com"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "example.com",
            f"Multiple plus signs should not affect domain extraction, got '{result}'"
        )


# ============================================================================
# SECTION 3: Subdomain Handling
# ============================================================================

class TestSubdomainExtraction(unittest.TestCase):
    """
    Tests for handling subdomains with multiple levels.

    The entire domain part after @ should be preserved, including all subdomains.
    """

    def test_extract_domain_single_subdomain(self):
        """
        Test domain extraction with single subdomain.

        Given: user@mail.example.com
        Then: extract_domain should return "mail.example.com"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "user@mail.example.com"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "mail.example.com",
            f"Expected 'mail.example.com', got '{result}'"
        )

    def test_extract_domain_multiple_subdomains(self):
        """
        Test domain extraction with multiple nested subdomains.

        Given: user@deep.sub.domain.example.com
        Then: extract_domain should return "deep.sub.domain.example.com"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "user@deep.sub.domain.example.com"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "deep.sub.domain.example.com",
            f"Expected full subdomain chain, got '{result}'"
        )

    def test_extract_domain_subdomain_with_hyphen(self):
        """
        Test domain extraction with hyphenated subdomain.

        Given: user@sub.domain-name.co.uk
        Then: extract_domain should return "sub.domain-name.co.uk"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "user@sub.domain-name.co.uk"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "sub.domain-name.co.uk",
            f"Expected 'sub.domain-name.co.uk', got '{result}'"
        )


# ============================================================================
# SECTION 4: International TLDs
# ============================================================================

class TestInternationalDomainExtraction(unittest.TestCase):
    """
    Scenario: International domain names

    Given the blocked domains list is empty
    And the inbox contains emails from "spam@example.co.jp" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include domain "example.co.jp"
    """

    def test_extract_domain_japanese_tld(self):
        """
        Test domain extraction for Japanese TLD (.co.jp).

        Given: spam@example.co.jp
        Then: extract_domain should return "example.co.jp"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "spam@example.co.jp"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "example.co.jp",
            f"Expected 'example.co.jp', got '{result}'"
        )

    def test_extract_domain_uk_tld(self):
        """
        Test domain extraction for UK TLD (.co.uk).

        Given: user@company.co.uk
        Then: extract_domain should return "company.co.uk"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "user@company.co.uk"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "company.co.uk",
            f"Expected 'company.co.uk', got '{result}'"
        )

    def test_extract_domain_brazilian_tld(self):
        """
        Test domain extraction for Brazilian TLD (.com.br).

        Given: user@empresa.com.br
        Then: extract_domain should return "empresa.com.br"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "user@empresa.com.br"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "empresa.com.br",
            f"Expected 'empresa.com.br', got '{result}'"
        )

    def test_extract_domain_german_tld(self):
        """
        Test domain extraction for German TLD (.de).

        Given: user@firma.de
        Then: extract_domain should return "firma.de"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "user@firma.de"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "firma.de",
            f"Expected 'firma.de', got '{result}'"
        )

    def test_extract_domain_australian_tld(self):
        """
        Test domain extraction for Australian TLD (.com.au).

        Given: user@company.com.au
        Then: extract_domain should return "company.com.au"
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "user@company.com.au"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "company.com.au",
            f"Expected 'company.com.au', got '{result}'"
        )


# ============================================================================
# SECTION 5: Long Domain Names
# ============================================================================

class TestLongDomainExtraction(unittest.TestCase):
    """
    Scenario: Very long domain name handling

    Given the blocked domains list is empty
    And the inbox contains emails from "user@very-long-subdomain.extremely-long-domain-name-that-tests-limits.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the domain should be correctly processed
    And the recommendation should include the full domain name
    """

    def test_extract_domain_very_long_name(self):
        """
        Test domain extraction for very long domain names.

        Long domain names should be preserved without truncation.
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        long_domain = "very-long-subdomain.extremely-long-domain-name-that-tests-limits.com"
        email = f"user@{long_domain}"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            long_domain,
            f"Long domain should not be truncated, got '{result}'"
        )

    def test_extract_domain_max_length_63_chars_per_label(self):
        """
        Test domain extraction with maximum length labels (63 chars each).

        DNS allows up to 63 characters per label. We should handle this.
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange - 63 character label
        long_label = "a" * 63
        domain = f"{long_label}.example.com"
        email = f"user@{domain}"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            domain,
            f"Max length label should be handled, got '{result}'"
        )

    def test_extract_domain_253_char_total_length(self):
        """
        Test domain extraction with maximum total domain length (253 chars).

        DNS allows up to 253 characters for the full domain name.
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange - Create a 253 character domain
        # Use multiple labels to stay within 63 char per label limit
        labels = []
        remaining = 253
        while remaining > 4:  # Need room for ".com"
            label_len = min(63, remaining - 5)  # -5 for ".com" and separator
            if label_len > 0:
                labels.append("a" * label_len)
                remaining -= label_len + 1  # +1 for the dot
            else:
                break
        labels.append("com")
        domain = ".".join(labels)

        email = f"user@{domain}"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            domain.lower(),
            f"Long domain should be preserved, expected length {len(domain)}, got length {len(result)}"
        )


# ============================================================================
# SECTION 6: Single Email Count Handling
# ============================================================================

class TestSingleEmailRecommendation(unittest.TestCase):
    """
    Scenario: Single email generates recommendation

    Given the blocked domains list is empty
    And the inbox contains exactly 1 email from "spam@single-sender.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include domain "single-sender.com" with count 1
    And a notification email should be sent
    """

    def test_single_email_generates_recommendation_with_count_one(self):
        """
        Test that a single email generates a recommendation with count=1.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act - Single email
        collector.collect("single-sender.com", "Marketing", blocked_domains)
        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(
            len(recommendations),
            1,
            f"Should have 1 recommendation, got {len(recommendations)}"
        )
        self.assertEqual(
            recommendations[0].domain,
            "single-sender.com",
            f"Domain should be 'single-sender.com', got '{recommendations[0].domain}'"
        )
        self.assertEqual(
            recommendations[0].count,
            1,
            f"Count should be 1 for single email, got {recommendations[0].count}"
        )

    def test_single_email_total_emails_matched_is_one(self):
        """
        Test that a single email results in total_emails_matched=1.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act
        collector.collect("single-sender.com", "Marketing", blocked_domains)
        total = collector.get_total_emails_matched()

        # Assert
        self.assertEqual(
            total,
            1,
            f"total_emails_matched should be 1, got {total}"
        )

    def test_single_email_unique_domains_count_is_one(self):
        """
        Test that a single email results in unique_domains_count=1.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act
        collector.collect("single-sender.com", "Marketing", blocked_domains)
        unique = collector.get_unique_domains_count()

        # Assert
        self.assertEqual(
            unique,
            1,
            f"unique_domains_count should be 1, got {unique}"
        )


# ============================================================================
# SECTION 7: Multi-Category Domain Tracking
# ============================================================================

class TestSameDomainDifferentCategories(unittest.TestCase):
    """
    Scenario: Same domain appears with different categories

    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email              | category      |
      | marketing@multi.com       | Marketing     |
      | ads@multi.com             | Advertising   |
      | money@multi.com           | Wants-Money   |
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include separate entries for each category
    And domain "multi.com" should appear 3 times with different categories
    """

    def test_same_domain_different_categories_creates_three_entries(self):
        """
        Test that same domain with 3 different categories creates 3 entries.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act - Same domain, different categories
        collector.collect("multi.com", "Marketing", blocked_domains)
        collector.collect("multi.com", "Advertising", blocked_domains)
        collector.collect("multi.com", "Wants-Money", blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(
            len(recommendations),
            3,
            f"Should have 3 recommendations for 3 categories, got {len(recommendations)}"
        )

        # Verify all categories are present
        categories = {r.category for r in recommendations}
        expected_categories = {"Marketing", "Advertising", "Wants-Money"}

        self.assertEqual(
            categories,
            expected_categories,
            f"Expected categories {expected_categories}, got {categories}"
        )

    def test_same_domain_different_categories_all_have_domain_multi_com(self):
        """
        Test that all 3 entries have domain "multi.com".
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act
        collector.collect("multi.com", "Marketing", blocked_domains)
        collector.collect("multi.com", "Advertising", blocked_domains)
        collector.collect("multi.com", "Wants-Money", blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert
        for rec in recommendations:
            self.assertEqual(
                rec.domain,
                "multi.com",
                f"All recommendations should have domain 'multi.com', got '{rec.domain}'"
            )

    def test_same_domain_different_categories_each_has_count_one(self):
        """
        Test that each category entry has count=1 when only one email per category.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act
        collector.collect("multi.com", "Marketing", blocked_domains)
        collector.collect("multi.com", "Advertising", blocked_domains)
        collector.collect("multi.com", "Wants-Money", blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert
        for rec in recommendations:
            self.assertEqual(
                rec.count,
                1,
                f"Each category should have count 1, {rec.category} has {rec.count}"
            )

    def test_same_domain_multiple_emails_per_category(self):
        """
        Test aggregation when same domain has multiple emails per category.

        Given:
        - multi.com Marketing x 5
        - multi.com Advertising x 3
        - multi.com Wants-Money x 1

        Then:
        - Marketing entry has count 5
        - Advertising entry has count 3
        - Wants-Money entry has count 1
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act - Different counts per category
        for _ in range(5):
            collector.collect("multi.com", "Marketing", blocked_domains)
        for _ in range(3):
            collector.collect("multi.com", "Advertising", blocked_domains)
        collector.collect("multi.com", "Wants-Money", blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert - Find each category's recommendation
        marketing_rec = next(
            (r for r in recommendations if r.category == "Marketing"),
            None
        )
        advertising_rec = next(
            (r for r in recommendations if r.category == "Advertising"),
            None
        )
        wants_money_rec = next(
            (r for r in recommendations if r.category == "Wants-Money"),
            None
        )

        self.assertIsNotNone(marketing_rec, "Should have Marketing recommendation")
        self.assertEqual(marketing_rec.count, 5)

        self.assertIsNotNone(advertising_rec, "Should have Advertising recommendation")
        self.assertEqual(advertising_rec.count, 3)

        self.assertIsNotNone(wants_money_rec, "Should have Wants-Money recommendation")
        self.assertEqual(wants_money_rec.count, 1)

    def test_total_emails_matched_sums_across_categories(self):
        """
        Test that total_emails_matched sums counts across all categories.

        Given: 5 + 3 + 1 = 9 total emails for multi.com
        Then: total_emails_matched should be 9
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act
        for _ in range(5):
            collector.collect("multi.com", "Marketing", blocked_domains)
        for _ in range(3):
            collector.collect("multi.com", "Advertising", blocked_domains)
        collector.collect("multi.com", "Wants-Money", blocked_domains)

        total = collector.get_total_emails_matched()

        # Assert
        self.assertEqual(
            total,
            9,
            f"Total should be 9 (5+3+1), got {total}"
        )


# ============================================================================
# SECTION 8: Case Insensitivity Edge Cases
# ============================================================================

class TestCaseInsensitivityEdgeCases(unittest.TestCase):
    """
    Additional case insensitivity tests for edge cases.
    """

    def test_mixed_case_in_same_domain_different_categories(self):
        """
        Test that MULTI.COM, multi.com, and Multi.Com are treated as same domain.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act - Same domain with different cases and categories
        collector.collect("MULTI.COM", "Marketing", blocked_domains)
        collector.collect("multi.com", "Advertising", blocked_domains)
        collector.collect("Multi.Com", "Wants-Money", blocked_domains)

        recommendations = collector.get_recommendations()

        # Assert - Should have 3 entries (one per category), all with normalized domain
        self.assertEqual(
            len(recommendations),
            3,
            f"Should have 3 recommendations (one per category), got {len(recommendations)}"
        )

        # All domains should be lowercase
        for rec in recommendations:
            self.assertEqual(
                rec.domain,
                "multi.com",
                f"Domain should be lowercase 'multi.com', got '{rec.domain}'"
            )

    def test_plus_addressing_case_normalization(self):
        """
        Test case normalization with plus addressing.
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "USER+TAG@EXAMPLE.COM"

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "example.com",
            f"Domain should be normalized to lowercase, got '{result}'"
        )


# ============================================================================
# SECTION 9: Integration with BlockingRecommendationCollector
# ============================================================================

class TestCollectorWithExtractedDomains(unittest.TestCase):
    """
    Integration tests for BlockingRecommendationCollector with domain extraction.

    These tests verify that the collector correctly handles domains extracted
    from various email address formats.
    """

    def test_collector_with_plus_addressed_email_domain(self):
        """
        Test that collector correctly tracks domain from plus-addressed email.

        When collecting from email "user+tag@sub.domain-name.co.uk",
        the domain "sub.domain-name.co.uk" should be tracked.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # The domain extracted from "user+tag@sub.domain-name.co.uk"
        domain = "sub.domain-name.co.uk"

        # Act
        collector.collect(domain, "Advertising", blocked_domains)
        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(
            recommendations[0].domain,
            "sub.domain-name.co.uk",
            f"Domain should be 'sub.domain-name.co.uk', got '{recommendations[0].domain}'"
        )

    def test_collector_with_international_domain(self):
        """
        Test that collector correctly tracks international domain.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        # Act
        collector.collect("example.co.jp", "Marketing", blocked_domains)
        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(
            recommendations[0].domain,
            "example.co.jp",
            f"Domain should be 'example.co.jp', got '{recommendations[0].domain}'"
        )

    def test_collector_with_long_domain(self):
        """
        Test that collector correctly tracks very long domain names.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()
        long_domain = "very-long-subdomain.extremely-long-domain-name-that-tests-limits.com"

        # Act
        collector.collect(long_domain, "Marketing", blocked_domains)
        recommendations = collector.get_recommendations()

        # Assert
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(
            recommendations[0].domain,
            long_domain,
            f"Long domain should be fully preserved, got '{recommendations[0].domain}'"
        )


# ============================================================================
# SECTION 10: Error Handling Edge Cases
# ============================================================================

class TestDomainExtractionErrorHandling(unittest.TestCase):
    """
    Error handling tests for domain extraction edge cases.
    """

    def test_extract_domain_empty_string(self):
        """
        Test that extract_domain raises ValueError for empty string.
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            extract_domain("")

        self.assertIn(
            "Invalid email",
            str(context.exception),
            f"Should mention 'Invalid email', got '{context.exception}'"
        )

    def test_extract_domain_only_at_symbol(self):
        """
        Test that extract_domain raises ValueError for just '@'.
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            extract_domain("@")

        self.assertIn(
            "Invalid email",
            str(context.exception),
            f"Should mention 'Invalid email', got '{context.exception}'"
        )

    def test_extract_domain_multiple_at_symbols(self):
        """
        Test that extract_domain raises ValueError for multiple @ symbols.

        Email addresses with multiple @ are invalid.
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            extract_domain("user@domain@example.com")

        self.assertIn(
            "Invalid email",
            str(context.exception),
            f"Should mention 'Invalid email', got '{context.exception}'"
        )

    def test_extract_domain_whitespace_handling(self):
        """
        Test that domain extraction handles emails with whitespace.

        Leading/trailing whitespace should be trimmed.
        """
        try:
            from utils.domain_extractor import extract_domain
        except ImportError:
            from services.domain_extractor import extract_domain

        # Arrange
        email = "  user@example.com  "

        # Act
        result = extract_domain(email)

        # Assert
        self.assertEqual(
            result,
            "example.com",
            f"Whitespace should be trimmed, got '{result}'"
        )


# ============================================================================
# SECTION 11: Summary Integration Tests
# ============================================================================

class TestDomainExtractionInSummary(unittest.TestCase):
    """
    Tests for domain extraction edge cases in get_summary().
    """

    def test_summary_with_single_email(self):
        """
        Test get_summary() with single email recommendation.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        collector.collect("single-sender.com", "Marketing", blocked_domains)

        # Act
        summary = collector.get_summary()
        summary_dict = summary.to_dict()

        # Assert
        self.assertEqual(summary.domain_count, 1)
        self.assertEqual(summary.total_count, 1)
        self.assertEqual(len(summary_dict["recommended_domains_to_block"]), 1)
        self.assertEqual(summary_dict["recommended_domains_to_block"][0]["count"], 1)

    def test_summary_with_multi_category_domain(self):
        """
        Test get_summary() with same domain across multiple categories.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        collector.collect("multi.com", "Marketing", blocked_domains)
        collector.collect("multi.com", "Advertising", blocked_domains)
        collector.collect("multi.com", "Wants-Money", blocked_domains)

        # Act
        summary = collector.get_summary()

        # Assert
        self.assertEqual(
            summary.domain_count,
            3,
            f"Should have 3 domain+category pairs, got {summary.domain_count}"
        )
        self.assertEqual(
            summary.total_count,
            3,
            f"Total count should be 3, got {summary.total_count}"
        )

    def test_summary_to_dict_with_international_domain(self):
        """
        Test that to_dict() correctly serializes international domains.
        """
        from services.blocking_recommendation_collector import (
            BlockingRecommendationCollector
        )

        # Arrange
        collector = BlockingRecommendationCollector()
        blocked_domains: Set[str] = set()

        collector.collect("example.co.jp", "Marketing", blocked_domains)

        # Act
        summary = collector.get_summary()
        result = summary.to_dict()

        # Assert
        expected = {
            "recommended_domains_to_block": [
                {"domain": "example.co.jp", "category": "Marketing", "count": 1}
            ],
            "total_emails_matched": 1,
            "unique_domains_count": 1
        }

        self.assertEqual(
            result,
            expected,
            f"Expected {expected}, got {result}"
        )


if __name__ == '__main__':
    unittest.main()
