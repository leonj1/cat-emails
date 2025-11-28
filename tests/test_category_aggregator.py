"""
Tests for Category Aggregator Service.

Based on BDD scenarios from prompts/002-bdd-category-aggregation.md:
- Scenario: Record a single email categorization
- Scenario: Record multiple categories for the same account on the same day
- Scenario: Record batch of category counts
- Scenario: Buffer flushes when size limit is reached
- Scenario: Flush merges with existing daily tally
- Scenario: Categories accumulate across multiple processing runs
- Scenario: Separate tallies are maintained for different accounts
- Scenario: Separate tallies are maintained for different days

These tests follow TDD Red phase - they will fail until the CategoryAggregator
service is implemented.
"""
import unittest
from datetime import datetime, date
from typing import Dict, Optional, List
from unittest.mock import Mock, call

from repositories.category_tally_repository_interface import ICategoryTallyRepository
from models.category_tally_models import DailyCategoryTally


class FakeCategoryTallyRepository:
    """
    Fake implementation of ICategoryTallyRepository for testing.

    This fake stores tallies in memory and allows inspection of saved data.
    It follows the mock-at-boundaries pattern from testing standards.
    """

    def __init__(self):
        """Initialize with empty storage."""
        self._tallies: Dict[str, DailyCategoryTally] = {}
        self._save_calls: List[Dict] = []

    def _make_key(self, email_address: str, tally_date: date) -> str:
        """Create a unique key for email/date combination."""
        return f"{email_address}_{tally_date.isoformat()}"

    def save_daily_tally(
        self,
        email_address: str,
        tally_date: date,
        category_counts: dict,
        total_emails: int
    ) -> DailyCategoryTally:
        """Save or update a daily tally."""
        self._save_calls.append({
            "email_address": email_address,
            "tally_date": tally_date,
            "category_counts": category_counts.copy(),
            "total_emails": total_emails
        })

        key = self._make_key(email_address, tally_date)
        now = datetime.utcnow()

        # Get existing tally if any
        existing = self._tallies.get(key)
        if existing:
            # Merge category counts
            merged_counts = existing.category_counts.copy()
            for cat, count in category_counts.items():
                merged_counts[cat] = merged_counts.get(cat, 0) + count

            tally = DailyCategoryTally(
                id=existing.id,
                email_address=email_address,
                tally_date=tally_date,
                category_counts=merged_counts,
                total_emails=total_emails,
                created_at=existing.created_at,
                updated_at=now
            )
        else:
            tally = DailyCategoryTally(
                id=len(self._tallies) + 1,
                email_address=email_address,
                tally_date=tally_date,
                category_counts=category_counts.copy(),
                total_emails=total_emails,
                created_at=now,
                updated_at=now
            )

        self._tallies[key] = tally
        return tally

    def get_tally(
        self,
        email_address: str,
        tally_date: date
    ) -> Optional[DailyCategoryTally]:
        """Retrieve a single daily tally."""
        key = self._make_key(email_address, tally_date)
        return self._tallies.get(key)

    def get_tallies_for_period(
        self,
        email_address: str,
        start_date: date,
        end_date: date
    ) -> List[DailyCategoryTally]:
        """Retrieve tallies for a period."""
        result = []
        for key, tally in self._tallies.items():
            if (tally.email_address == email_address and
                start_date <= tally.tally_date <= end_date):
                result.append(tally)
        return sorted(result, key=lambda t: t.tally_date)

    def get_aggregated_tallies(self, email_address, start_date, end_date):
        """Not needed for aggregator tests."""
        pass

    def delete_tallies_before(self, email_address, cutoff_date):
        """Not needed for aggregator tests."""
        pass

    def get_save_call_count(self) -> int:
        """Return number of times save_daily_tally was called."""
        return len(self._save_calls)

    def clear_storage(self):
        """Clear all stored tallies."""
        self._tallies.clear()
        self._save_calls.clear()


class TestRecordSingleEmailCategorization(unittest.TestCase):
    """
    Scenario: Record a single email categorization

    Given a user "test@gmail.com" exists in the system
    When the system records category "Marketing" for "test@gmail.com" at "2025-11-28 10:00:00"
    Then the buffer should contain 1 record for "test@gmail.com"
    And the category "Marketing" count should be 1 in the buffer

    The implementation should:
    - Accept email_address, category, and timestamp
    - Buffer the categorization in memory
    - Track count per category per account per day
    """

    def setUp(self):
        """Set up test fixtures."""
        self.repository = FakeCategoryTallyRepository()

    def test_record_single_category_creates_buffer_entry(self):
        """
        Test that recording a single category creates a buffer entry.

        Given a user exists
        When a category is recorded
        Then the buffer should contain 1 record for the user
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        aggregator = CategoryAggregator(self.repository, 100)
        email_address = "test@gmail.com"
        category = "Marketing"
        timestamp = datetime(2025, 11, 28, 10, 0, 0)

        # Act
        aggregator.record_category(email_address, category, timestamp)

        # Assert
        buffer_count = aggregator.get_buffer_count_for_account(email_address)
        self.assertEqual(
            buffer_count,
            1,
            f"Buffer should contain 1 record for {email_address}, got {buffer_count}"
        )

    def test_record_single_category_sets_count_to_one(self):
        """
        Test that recording a single category sets its count to 1.

        When a category is recorded
        Then the category count should be 1 in the buffer
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        aggregator = CategoryAggregator(self.repository, 100)
        email_address = "test@gmail.com"
        category = "Marketing"
        timestamp = datetime(2025, 11, 28, 10, 0, 0)

        # Act
        aggregator.record_category(email_address, category, timestamp)

        # Assert
        buffer_contents = aggregator.get_buffer_contents()
        tally_date = date(2025, 11, 28)
        key = (email_address, tally_date)

        self.assertIn(key, buffer_contents, f"Buffer should have entry for {key}")
        self.assertEqual(
            buffer_contents[key].get("Marketing", 0),
            1,
            "Marketing count should be 1"
        )


class TestRecordMultipleCategoriesSameAccountSameDay(unittest.TestCase):
    """
    Scenario: Record multiple categories for the same account on the same day

    Given a user "test@gmail.com" exists in the system
    When the system records the following categories for "test@gmail.com" on "2025-11-28":
      | category    | count |
      | Marketing   | 5     |
      | Advertising | 3     |
      | Personal    | 2     |
    Then the buffer should aggregate to 10 total emails for "test@gmail.com" on "2025-11-28"

    The implementation should:
    - Aggregate multiple category recordings
    - Calculate total emails across categories
    - Maintain separate counts per category
    """

    def setUp(self):
        """Set up test fixtures."""
        self.repository = FakeCategoryTallyRepository()

    def test_multiple_categories_aggregate_to_total(self):
        """
        Test that multiple categories aggregate to correct total.

        When multiple categories are recorded
        Then the buffer should show correct total emails
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        aggregator = CategoryAggregator(self.repository, 100)
        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)

        # Act - Record categories matching the Gherkin table
        categories_to_record = [
            ("Marketing", 5),
            ("Advertising", 3),
            ("Personal", 2)
        ]
        for category, count in categories_to_record:
            for _ in range(count):
                timestamp = datetime.combine(tally_date, datetime.min.time())
                aggregator.record_category(email_address, category, timestamp)

        # Assert
        total = aggregator.get_buffer_total_for_account_date(email_address, tally_date)
        self.assertEqual(
            total,
            10,
            f"Buffer should aggregate to 10 total emails, got {total}"
        )

    def test_multiple_categories_maintain_individual_counts(self):
        """
        Test that individual category counts are maintained correctly.

        When multiple categories are recorded
        Then each category should have correct individual count
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        aggregator = CategoryAggregator(self.repository, 100)
        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)

        # Act
        categories_to_record = [
            ("Marketing", 5),
            ("Advertising", 3),
            ("Personal", 2)
        ]
        for category, count in categories_to_record:
            for _ in range(count):
                timestamp = datetime.combine(tally_date, datetime.min.time())
                aggregator.record_category(email_address, category, timestamp)

        # Assert
        buffer_contents = aggregator.get_buffer_contents()
        key = (email_address, tally_date)

        self.assertEqual(
            buffer_contents[key]["Marketing"],
            5,
            "Marketing count should be 5"
        )
        self.assertEqual(
            buffer_contents[key]["Advertising"],
            3,
            "Advertising count should be 3"
        )
        self.assertEqual(
            buffer_contents[key]["Personal"],
            2,
            "Personal count should be 2"
        )


class TestRecordBatchOfCategoryCounts(unittest.TestCase):
    """
    Scenario: Record batch of category counts

    Given a user "test@gmail.com" exists in the system
    When the system records a batch with the following counts for "test@gmail.com":
      | category           | count |
      | Marketing          | 45    |
      | Advertising        | 32    |
      | Personal           | 12    |
      | Work-related       | 8     |
      | Financial-Notification | 3 |
    Then the total emails recorded should be 100

    The implementation should:
    - Support batch recording of multiple categories at once
    - Calculate correct total from batch
    """

    def setUp(self):
        """Set up test fixtures."""
        self.repository = FakeCategoryTallyRepository()

    def test_record_batch_calculates_correct_total(self):
        """
        Test that batch recording calculates correct total.

        When a batch of category counts is recorded
        Then the total should match the sum of all counts
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        aggregator = CategoryAggregator(self.repository, 200)
        email_address = "test@gmail.com"
        timestamp = datetime(2025, 11, 28, 10, 0, 0)

        batch_counts = {
            "Marketing": 45,
            "Advertising": 32,
            "Personal": 12,
            "Work-related": 8,
            "Financial-Notification": 3
        }

        # Act
        aggregator.record_batch(email_address, batch_counts, timestamp)

        # Assert
        tally_date = date(2025, 11, 28)
        total = aggregator.get_buffer_total_for_account_date(email_address, tally_date)
        self.assertEqual(
            total,
            100,
            f"Total emails recorded should be 100, got {total}"
        )

    def test_record_batch_stores_all_categories(self):
        """
        Test that batch recording stores all category counts.

        When a batch is recorded
        Then all categories should be in the buffer with correct counts
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        aggregator = CategoryAggregator(self.repository, 200)
        email_address = "test@gmail.com"
        timestamp = datetime(2025, 11, 28, 10, 0, 0)

        batch_counts = {
            "Marketing": 45,
            "Advertising": 32,
            "Personal": 12,
            "Work-related": 8,
            "Financial-Notification": 3
        }

        # Act
        aggregator.record_batch(email_address, batch_counts, timestamp)

        # Assert
        buffer_contents = aggregator.get_buffer_contents()
        tally_date = date(2025, 11, 28)
        key = (email_address, tally_date)

        self.assertEqual(buffer_contents[key]["Marketing"], 45)
        self.assertEqual(buffer_contents[key]["Advertising"], 32)
        self.assertEqual(buffer_contents[key]["Personal"], 12)
        self.assertEqual(buffer_contents[key]["Work-related"], 8)
        self.assertEqual(buffer_contents[key]["Financial-Notification"], 3)


class TestBufferFlushesWhenSizeLimitReached(unittest.TestCase):
    """
    Scenario: Buffer flushes when size limit is reached

    Given a user "test@gmail.com" exists in the system
    And the buffer size limit is set to 50
    When the system records 50 individual categorization events
    Then the buffer should automatically flush to the database
    And the buffer should be empty after flush

    The implementation should:
    - Track total buffer size (sum of all counts)
    - Automatically flush when limit is reached
    - Clear buffer after flush
    """

    def setUp(self):
        """Set up test fixtures."""
        self.repository = FakeCategoryTallyRepository()

    def test_buffer_auto_flushes_at_limit(self):
        """
        Test that buffer automatically flushes when size limit is reached.

        Given buffer size limit is 50
        When 50 events are recorded
        Then the buffer should automatically flush
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        buffer_size_limit = 50
        aggregator = CategoryAggregator(self.repository, buffer_size_limit)
        email_address = "test@gmail.com"

        # Act - Record exactly 50 events
        for i in range(50):
            timestamp = datetime(2025, 11, 28, 10, 0, i)
            aggregator.record_category(email_address, "Marketing", timestamp)

        # Assert - Repository should have received the flush
        self.assertGreater(
            self.repository.get_save_call_count(),
            0,
            "Repository should have received at least one save call after flush"
        )

    def test_buffer_empty_after_auto_flush(self):
        """
        Test that buffer is empty after automatic flush.

        When buffer limit is reached and auto-flush occurs
        Then the buffer should be empty
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        buffer_size_limit = 50
        aggregator = CategoryAggregator(self.repository, buffer_size_limit)
        email_address = "test@gmail.com"

        # Act - Record 50 events to trigger flush
        for i in range(50):
            timestamp = datetime(2025, 11, 28, 10, 0, i)
            aggregator.record_category(email_address, "Marketing", timestamp)

        # Assert
        buffer_contents = aggregator.get_buffer_contents()
        self.assertEqual(
            len(buffer_contents),
            0,
            f"Buffer should be empty after flush, but has {len(buffer_contents)} entries"
        )

    def test_flush_triggered_at_exact_limit(self):
        """
        Test that flush is triggered exactly when limit is reached.

        Given buffer size limit is 50
        When 49 events are recorded, flush should NOT occur
        When 50th event is recorded, flush should occur
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        buffer_size_limit = 50
        aggregator = CategoryAggregator(self.repository, buffer_size_limit)
        email_address = "test@gmail.com"

        # Act - Record 49 events (should NOT trigger flush)
        for i in range(49):
            timestamp = datetime(2025, 11, 28, 10, 0, i)
            aggregator.record_category(email_address, "Marketing", timestamp)

        # Assert - No flush yet
        self.assertEqual(
            self.repository.get_save_call_count(),
            0,
            "Repository should NOT have received save call before limit"
        )

        # Act - Record 50th event (should trigger flush)
        timestamp = datetime(2025, 11, 28, 10, 0, 49)
        aggregator.record_category(email_address, "Marketing", timestamp)

        # Assert - Flush occurred
        self.assertGreater(
            self.repository.get_save_call_count(),
            0,
            "Repository should have received save call at limit"
        )


class TestFlushMergesWithExistingDailyTally(unittest.TestCase):
    """
    Scenario: Flush merges with existing daily tally

    Given a user "test@gmail.com" exists in the system
    And a daily tally exists for "test@gmail.com" on "2025-11-28" with:
      | category  | count |
      | Marketing | 20    |
      | Personal  | 5     |
    When the system records and flushes:
      | category  | count |
      | Marketing | 10    |
      | Advertising | 15  |
    Then the daily tally for "test@gmail.com" on "2025-11-28" should show:
      | category    | count |
      | Marketing   | 30    |
      | Personal    | 5     |
      | Advertising | 15    |

    The implementation should:
    - Retrieve existing tally before flush
    - Merge new counts with existing counts
    - Save merged result
    """

    def setUp(self):
        """Set up test fixtures."""
        self.repository = FakeCategoryTallyRepository()

    def test_flush_merges_marketing_count(self):
        """
        Test that flush merges Marketing count correctly.

        Given existing Marketing=20
        When flushing Marketing=10
        Then result should be Marketing=30
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)

        # Set up existing tally in repository
        self.repository.save_daily_tally(
            email_address,
            tally_date,
            {"Marketing": 20, "Personal": 5},
            25
        )
        # Clear save calls from setup
        self.repository._save_calls.clear()

        aggregator = CategoryAggregator(self.repository, 100)

        # Act - Record new counts and flush
        timestamp = datetime.combine(tally_date, datetime.min.time())
        aggregator.record_batch(
            email_address,
            {"Marketing": 10, "Advertising": 15},
            timestamp
        )
        aggregator.flush()

        # Assert
        result = self.repository.get_tally(email_address, tally_date)
        self.assertEqual(
            result.category_counts["Marketing"],
            30,
            f"Marketing should be 30 (20 + 10), got {result.category_counts.get('Marketing')}"
        )

    def test_flush_preserves_existing_categories(self):
        """
        Test that flush preserves categories not in new batch.

        Given existing Personal=5
        When flushing without Personal
        Then result should still have Personal=5
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)

        # Set up existing tally
        self.repository.save_daily_tally(
            email_address,
            tally_date,
            {"Marketing": 20, "Personal": 5},
            25
        )
        self.repository._save_calls.clear()

        aggregator = CategoryAggregator(self.repository, 100)

        # Act
        timestamp = datetime.combine(tally_date, datetime.min.time())
        aggregator.record_batch(
            email_address,
            {"Marketing": 10, "Advertising": 15},
            timestamp
        )
        aggregator.flush()

        # Assert
        result = self.repository.get_tally(email_address, tally_date)
        self.assertEqual(
            result.category_counts.get("Personal"),
            5,
            f"Personal should be preserved as 5, got {result.category_counts.get('Personal')}"
        )

    def test_flush_adds_new_categories(self):
        """
        Test that flush adds new categories not in existing tally.

        Given no Advertising in existing
        When flushing Advertising=15
        Then result should have Advertising=15
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)

        # Set up existing tally (no Advertising)
        self.repository.save_daily_tally(
            email_address,
            tally_date,
            {"Marketing": 20, "Personal": 5},
            25
        )
        self.repository._save_calls.clear()

        aggregator = CategoryAggregator(self.repository, 100)

        # Act
        timestamp = datetime.combine(tally_date, datetime.min.time())
        aggregator.record_batch(
            email_address,
            {"Marketing": 10, "Advertising": 15},
            timestamp
        )
        aggregator.flush()

        # Assert
        result = self.repository.get_tally(email_address, tally_date)
        self.assertEqual(
            result.category_counts.get("Advertising"),
            15,
            f"Advertising should be 15, got {result.category_counts.get('Advertising')}"
        )


class TestCategoriesAccumulateAcrossMultipleRuns(unittest.TestCase):
    """
    Scenario: Categories accumulate across multiple processing runs

    Given a user "test@gmail.com" exists in the system
    When the system processes run 1 with categories:
      | category  | count |
      | Marketing | 15    |
    And the system processes run 2 with categories:
      | category  | count |
      | Marketing | 25    |
    And both runs are flushed
    Then the daily total for "Marketing" should be 40

    The implementation should:
    - Support multiple processing runs
    - Accumulate counts across runs
    """

    def setUp(self):
        """Set up test fixtures."""
        self.repository = FakeCategoryTallyRepository()

    def test_categories_accumulate_across_runs(self):
        """
        Test that categories accumulate across multiple processing runs.

        When run 1 records Marketing=15 and run 2 records Marketing=25
        Then total Marketing should be 40
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)

        # Act - Run 1
        aggregator1 = CategoryAggregator(self.repository, 100)
        timestamp = datetime.combine(tally_date, datetime.min.time())
        aggregator1.record_batch(email_address, {"Marketing": 15}, timestamp)
        aggregator1.flush()

        # Act - Run 2
        aggregator2 = CategoryAggregator(self.repository, 100)
        aggregator2.record_batch(email_address, {"Marketing": 25}, timestamp)
        aggregator2.flush()

        # Assert
        result = self.repository.get_tally(email_address, tally_date)
        self.assertEqual(
            result.category_counts["Marketing"],
            40,
            f"Marketing should be 40 (15 + 25), got {result.category_counts.get('Marketing')}"
        )

    def test_multiple_runs_update_total_emails(self):
        """
        Test that total emails is updated correctly across runs.

        When run 1 records 15 emails and run 2 records 25 emails
        Then total emails should reflect latest save
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)

        # Act - Run 1
        aggregator1 = CategoryAggregator(self.repository, 100)
        timestamp = datetime.combine(tally_date, datetime.min.time())
        aggregator1.record_batch(email_address, {"Marketing": 15}, timestamp)
        aggregator1.flush()

        # Act - Run 2
        aggregator2 = CategoryAggregator(self.repository, 100)
        aggregator2.record_batch(email_address, {"Marketing": 25}, timestamp)
        aggregator2.flush()

        # Assert
        result = self.repository.get_tally(email_address, tally_date)
        self.assertEqual(
            result.total_emails,
            40,
            f"Total emails should be 40, got {result.total_emails}"
        )


class TestSeparateTalliesForDifferentAccounts(unittest.TestCase):
    """
    Scenario: Separate tallies are maintained for different accounts

    Given the following users exist:
      | email           |
      | user1@gmail.com |
      | user2@gmail.com |
    When the system records "Marketing" count 50 for "user1@gmail.com"
    And the system records "Marketing" count 30 for "user2@gmail.com"
    And the buffer is flushed
    Then "user1@gmail.com" should have 50 "Marketing" emails
    And "user2@gmail.com" should have 30 "Marketing" emails

    The implementation should:
    - Maintain separate buffers per account
    - Not mix counts between accounts
    """

    def setUp(self):
        """Set up test fixtures."""
        self.repository = FakeCategoryTallyRepository()

    def test_user1_has_correct_marketing_count(self):
        """
        Test that user1 has correct Marketing count after flush.

        When user1 records 50 Marketing emails
        Then user1 should have 50 Marketing emails
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        aggregator = CategoryAggregator(self.repository, 200)
        user1 = "user1@gmail.com"
        user2 = "user2@gmail.com"
        timestamp = datetime(2025, 11, 28, 10, 0, 0)

        # Act
        aggregator.record_batch(user1, {"Marketing": 50}, timestamp)
        aggregator.record_batch(user2, {"Marketing": 30}, timestamp)
        aggregator.flush()

        # Assert
        tally_date = date(2025, 11, 28)
        result = self.repository.get_tally(user1, tally_date)
        self.assertEqual(
            result.category_counts["Marketing"],
            50,
            f"user1 should have 50 Marketing emails, got {result.category_counts.get('Marketing')}"
        )

    def test_user2_has_correct_marketing_count(self):
        """
        Test that user2 has correct Marketing count after flush.

        When user2 records 30 Marketing emails
        Then user2 should have 30 Marketing emails
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        aggregator = CategoryAggregator(self.repository, 200)
        user1 = "user1@gmail.com"
        user2 = "user2@gmail.com"
        timestamp = datetime(2025, 11, 28, 10, 0, 0)

        # Act
        aggregator.record_batch(user1, {"Marketing": 50}, timestamp)
        aggregator.record_batch(user2, {"Marketing": 30}, timestamp)
        aggregator.flush()

        # Assert
        tally_date = date(2025, 11, 28)
        result = self.repository.get_tally(user2, tally_date)
        self.assertEqual(
            result.category_counts["Marketing"],
            30,
            f"user2 should have 30 Marketing emails, got {result.category_counts.get('Marketing')}"
        )

    def test_accounts_do_not_affect_each_other(self):
        """
        Test that recording for one account does not affect another.

        When both users record different counts
        Then each user's count should be independent
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        aggregator = CategoryAggregator(self.repository, 200)
        user1 = "user1@gmail.com"
        user2 = "user2@gmail.com"
        timestamp = datetime(2025, 11, 28, 10, 0, 0)

        # Act
        aggregator.record_batch(user1, {"Marketing": 50}, timestamp)
        aggregator.record_batch(user2, {"Marketing": 30}, timestamp)
        aggregator.flush()

        # Assert - Verify total counts
        tally_date = date(2025, 11, 28)
        user1_result = self.repository.get_tally(user1, tally_date)
        user2_result = self.repository.get_tally(user2, tally_date)

        total = user1_result.category_counts["Marketing"] + user2_result.category_counts["Marketing"]
        self.assertEqual(
            total,
            80,
            f"Combined total should be 80 (50 + 30), got {total}"
        )


class TestSeparateTalliesForDifferentDays(unittest.TestCase):
    """
    Scenario: Separate tallies are maintained for different days

    Given a user "test@gmail.com" exists in the system
    When the system records "Marketing" count 20 on "2025-11-27"
    And the system records "Marketing" count 35 on "2025-11-28"
    And the buffer is flushed
    Then the tally for "2025-11-27" should show 20 "Marketing" emails
    And the tally for "2025-11-28" should show 35 "Marketing" emails

    The implementation should:
    - Maintain separate tallies per day
    - Use timestamp to determine the date
    """

    def setUp(self):
        """Set up test fixtures."""
        self.repository = FakeCategoryTallyRepository()

    def test_day1_has_correct_count(self):
        """
        Test that day 1 (2025-11-27) has correct Marketing count.

        When 20 Marketing emails are recorded on 2025-11-27
        Then 2025-11-27 should have 20 Marketing emails
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        aggregator = CategoryAggregator(self.repository, 200)
        email_address = "test@gmail.com"

        day1 = date(2025, 11, 27)
        day2 = date(2025, 11, 28)

        # Act
        timestamp1 = datetime.combine(day1, datetime.min.time())
        timestamp2 = datetime.combine(day2, datetime.min.time())

        aggregator.record_batch(email_address, {"Marketing": 20}, timestamp1)
        aggregator.record_batch(email_address, {"Marketing": 35}, timestamp2)
        aggregator.flush()

        # Assert
        result = self.repository.get_tally(email_address, day1)
        self.assertEqual(
            result.category_counts["Marketing"],
            20,
            f"2025-11-27 should have 20 Marketing emails, got {result.category_counts.get('Marketing')}"
        )

    def test_day2_has_correct_count(self):
        """
        Test that day 2 (2025-11-28) has correct Marketing count.

        When 35 Marketing emails are recorded on 2025-11-28
        Then 2025-11-28 should have 35 Marketing emails
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        aggregator = CategoryAggregator(self.repository, 200)
        email_address = "test@gmail.com"

        day1 = date(2025, 11, 27)
        day2 = date(2025, 11, 28)

        # Act
        timestamp1 = datetime.combine(day1, datetime.min.time())
        timestamp2 = datetime.combine(day2, datetime.min.time())

        aggregator.record_batch(email_address, {"Marketing": 20}, timestamp1)
        aggregator.record_batch(email_address, {"Marketing": 35}, timestamp2)
        aggregator.flush()

        # Assert
        result = self.repository.get_tally(email_address, day2)
        self.assertEqual(
            result.category_counts["Marketing"],
            35,
            f"2025-11-28 should have 35 Marketing emails, got {result.category_counts.get('Marketing')}"
        )

    def test_days_do_not_affect_each_other(self):
        """
        Test that tallies for different days are independent.

        When different counts are recorded on different days
        Then each day should have its own independent count
        """
        # Arrange
        from services.category_aggregator_service import CategoryAggregator

        aggregator = CategoryAggregator(self.repository, 200)
        email_address = "test@gmail.com"

        day1 = date(2025, 11, 27)
        day2 = date(2025, 11, 28)

        # Act
        timestamp1 = datetime.combine(day1, datetime.min.time())
        timestamp2 = datetime.combine(day2, datetime.min.time())

        aggregator.record_batch(email_address, {"Marketing": 20}, timestamp1)
        aggregator.record_batch(email_address, {"Marketing": 35}, timestamp2)
        aggregator.flush()

        # Assert
        day1_result = self.repository.get_tally(email_address, day1)
        day2_result = self.repository.get_tally(email_address, day2)

        self.assertNotEqual(
            day1_result.category_counts["Marketing"],
            day2_result.category_counts["Marketing"],
            "Day 1 and Day 2 should have different Marketing counts"
        )

        total = day1_result.category_counts["Marketing"] + day2_result.category_counts["Marketing"]
        self.assertEqual(
            total,
            55,
            f"Combined total should be 55 (20 + 35), got {total}"
        )


class TestCategoryAggregatorInterface(unittest.TestCase):
    """
    Tests to verify the ICategoryAggregator interface exists and has correct methods.

    This ensures the interface contract is properly defined before implementation.
    """

    def test_interface_exists(self):
        """
        Test that ICategoryAggregator interface exists.

        The implementation should define an interface for the aggregator.
        """
        # Act & Assert
        from services.interfaces.category_aggregator_interface import ICategoryAggregator

        # Verify it's an abstract class
        import inspect
        self.assertTrue(
            inspect.isabstract(ICategoryAggregator),
            "ICategoryAggregator should be an abstract class"
        )

    def test_interface_has_record_category_method(self):
        """
        Test that interface defines record_category method.
        """
        from services.interfaces.category_aggregator_interface import ICategoryAggregator
        import inspect

        methods = [name for name, _ in inspect.getmembers(ICategoryAggregator, predicate=inspect.isfunction)]
        self.assertIn(
            "record_category",
            methods,
            "ICategoryAggregator should have record_category method"
        )

    def test_interface_has_record_batch_method(self):
        """
        Test that interface defines record_batch method.
        """
        from services.interfaces.category_aggregator_interface import ICategoryAggregator
        import inspect

        methods = [name for name, _ in inspect.getmembers(ICategoryAggregator, predicate=inspect.isfunction)]
        self.assertIn(
            "record_batch",
            methods,
            "ICategoryAggregator should have record_batch method"
        )

    def test_interface_has_flush_method(self):
        """
        Test that interface defines flush method.
        """
        from services.interfaces.category_aggregator_interface import ICategoryAggregator
        import inspect

        methods = [name for name, _ in inspect.getmembers(ICategoryAggregator, predicate=inspect.isfunction)]
        self.assertIn(
            "flush",
            methods,
            "ICategoryAggregator should have flush method"
        )


if __name__ == '__main__':
    unittest.main()
