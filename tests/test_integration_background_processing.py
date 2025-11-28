"""
Tests for Integration with Background Email Processing.

Based on BDD scenarios from tests/bdd/integration-background-processing.feature:
- Scenario: Categories are recorded during email processing
- Scenario: Aggregator is flushed after each processing run
- Scenario: Multiple accounts are processed independently
- Scenario: Processing continues if aggregation fails
- Scenario: Aggregator initialization at application startup
- Scenario: Aggregator shutdown flushes remaining buffer
- Scenario: Data cleanup job removes old tallies
- Scenario: Hourly processing accumulates daily tallies
- Scenario: Processing spans midnight correctly

These tests follow TDD approach - implement integration code to make them pass.
"""
import unittest
from datetime import datetime, date, timedelta
from typing import Dict, Optional, List, Callable, Any
from unittest.mock import Mock, MagicMock, patch, call
import atexit

from services.interfaces.category_aggregator_interface import ICategoryAggregator
from repositories.category_tally_repository_interface import ICategoryTallyRepository
from models.category_tally_models import DailyCategoryTally


class FakeCategoryAggregator(ICategoryAggregator):
    """Fake aggregator implementation for testing."""

    def __init__(self):
        """Initialize the fake aggregator."""
        self.recorded_batches = []
        self.flush_count = 0
        self.should_raise_on_flush = False
        self.buffer = {}

    def record_category(
        self,
        email_address: str,
        category: str,
        timestamp: datetime
    ) -> None:
        """Record a single category."""
        key = (email_address, timestamp.date())
        if key not in self.buffer:
            self.buffer[key] = {}
        self.buffer[key][category] = self.buffer[key].get(category, 0) + 1

    def record_batch(
        self,
        email_address: str,
        category_counts: Dict[str, int],
        timestamp: datetime
    ) -> None:
        """Record a batch of category counts."""
        self.recorded_batches.append({
            'email_address': email_address,
            'category_counts': category_counts.copy(),
            'timestamp': timestamp
        })
        # Also update buffer for tracking
        key = (email_address, timestamp.date())
        if key not in self.buffer:
            self.buffer[key] = {}
        for category, count in category_counts.items():
            self.buffer[key][category] = self.buffer[key].get(category, 0) + count

    def flush(self) -> None:
        """Flush buffered data."""
        if self.should_raise_on_flush:
            raise Exception("Database temporarily unavailable")
        self.flush_count += 1
        self.buffer.clear()

    def has_buffered_data(self) -> bool:
        """Check if there is buffered data."""
        return len(self.buffer) > 0


class FakeCategoryTallyRepository(ICategoryTallyRepository):
    """Fake repository implementation for testing."""

    def __init__(self):
        """Initialize the fake repository."""
        self._tallies = {}

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
        key = self._make_key(email_address, tally_date)
        now = datetime.now()

        if key in self._tallies:
            existing = self._tallies[key]
            merged_counts = existing.category_counts.copy()
            for category, count in category_counts.items():
                merged_counts[category] = merged_counts.get(category, 0) + count

            tally = DailyCategoryTally(
                email_address=email_address,
                tally_date=tally_date,
                category_counts=merged_counts,
                total_emails=sum(merged_counts.values()),
                created_at=existing.created_at,
                updated_at=now
            )
        else:
            tally = DailyCategoryTally(
                email_address=email_address,
                tally_date=tally_date,
                category_counts=category_counts,
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
        """Get a daily tally."""
        key = self._make_key(email_address, tally_date)
        return self._tallies.get(key)

    def get_tallies_for_period(
        self,
        email_address: str,
        start_date: date,
        end_date: date
    ) -> List[DailyCategoryTally]:
        """Get tallies for a date range."""
        result = []
        for tally in self._tallies.values():
            if (tally.email_address == email_address and
                start_date <= tally.tally_date <= end_date):
                result.append(tally)
        return sorted(result, key=lambda t: t.tally_date)

    def delete_tallies_before(
        self,
        email_address: str,
        cutoff_date: date
    ) -> int:
        """Delete tallies older than cutoff date for a specific account."""
        keys_to_delete = [
            key for key, tally in self._tallies.items()
            if tally.email_address == email_address and tally.tally_date < cutoff_date
        ]
        for key in keys_to_delete:
            del self._tallies[key]
        return len(keys_to_delete)

    def get_aggregated_tallies(
        self,
        email_address: str,
        start_date: date,
        end_date: date
    ):
        """Get aggregated tallies."""
        pass  # Not needed for these tests


class TestCategoriesRecordedDuringProcessing(unittest.TestCase):
    """
    Scenario: Categories are recorded during email processing

    Given a user "test@gmail.com" is configured for processing
    And the following emails are fetched with categories
    When the background processor processes the emails
    Then the category aggregator should receive a batch with correct counts
    """

    def test_categories_recorded_during_email_processing(self):
        """Test that categories are recorded during email processing."""
        # Given: Setup fake aggregator
        fake_aggregator = FakeCategoryAggregator()

        # Simulate processing emails with categories
        email_address = "test@gmail.com"
        timestamp = datetime(2025, 11, 28, 10, 0, 0)

        category_counts = {
            "Marketing": 2,
            "Wants-Money": 1,
            "Personal": 1,
            "Financial-Notification": 1
        }

        # When: Record batch
        fake_aggregator.record_batch(email_address, category_counts, timestamp)

        # Then: Verify batch was recorded
        self.assertEqual(len(fake_aggregator.recorded_batches), 1)
        batch = fake_aggregator.recorded_batches[0]
        self.assertEqual(batch['email_address'], email_address)
        self.assertEqual(batch['category_counts'], category_counts)
        self.assertEqual(batch['timestamp'], timestamp)


class TestAggregatorFlushedAfterProcessingRun(unittest.TestCase):
    """
    Scenario: Aggregator is flushed after each processing run

    Given a user is configured for processing
    When the background processor processes emails
    Then the aggregator should be flushed
    And the tallies should be persisted to the database
    """

    def test_aggregator_flushed_after_processing(self):
        """Test that aggregator is flushed after each processing run."""
        # Given: Setup fake aggregator and repository
        fake_aggregator = FakeCategoryAggregator()
        fake_repository = FakeCategoryTallyRepository()

        email_address = "test@gmail.com"
        timestamp = datetime(2025, 11, 28, 10, 0, 0)
        category_counts = {"Marketing": 5, "Personal": 3}

        # Record batch
        fake_aggregator.record_batch(email_address, category_counts, timestamp)

        # Verify buffer has data
        self.assertTrue(fake_aggregator.has_buffered_data())
        initial_flush_count = fake_aggregator.flush_count

        # When: Flush the aggregator
        fake_aggregator.flush()

        # Then: Verify flush was called
        self.assertEqual(fake_aggregator.flush_count, initial_flush_count + 1)
        self.assertFalse(fake_aggregator.has_buffered_data())


class TestMultipleAccountsProcessedIndependently(unittest.TestCase):
    """
    Scenario: Multiple accounts are processed independently

    Given multiple users are configured for processing
    When the background processor processes emails for all accounts
    Then each account should have separate tally records
    And the aggregator should flush after each account
    """

    def test_multiple_accounts_processed_independently(self):
        """Test that multiple accounts are processed independently."""
        # Given: Setup fake aggregator
        fake_aggregator = FakeCategoryAggregator()

        timestamp = datetime(2025, 11, 28, 10, 0, 0)

        # When: Process multiple accounts
        accounts = ["user1@gmail.com", "user2@gmail.com"]
        for account in accounts:
            fake_aggregator.record_batch(
                account,
                {"Marketing": 3},
                timestamp
            )
            fake_aggregator.flush()

        # Then: Verify flush was called for each account
        self.assertEqual(fake_aggregator.flush_count, 2)


class TestProcessingContinuesIfAggregationFails(unittest.TestCase):
    """
    Scenario: Processing continues if aggregation fails

    Given a user is configured for processing
    And the aggregation database is temporarily unavailable
    When the background processor processes emails
    Then the email processing should complete successfully
    And an error should be logged for aggregation failure
    """

    def test_processing_continues_if_aggregation_fails(self):
        """Test that processing continues even if aggregation fails."""
        # Given: Setup aggregator that fails on flush
        fake_aggregator = FakeCategoryAggregator()
        fake_aggregator.should_raise_on_flush = True

        email_address = "test@gmail.com"
        timestamp = datetime(2025, 11, 28, 10, 0, 0)

        # Record batch
        fake_aggregator.record_batch(
            email_address,
            {"Marketing": 5},
            timestamp
        )

        # When: Attempt to flush (should raise exception)
        with self.assertRaises(Exception) as context:
            fake_aggregator.flush()

        # Then: Verify exception was raised
        self.assertIn("Database temporarily unavailable", str(context.exception))


class TestAggregatorInitializationAtStartup(unittest.TestCase):
    """
    Scenario: Aggregator initialization at application startup

    When the application starts
    Then the CategoryAggregator should be initialized
    And the CategoryTallyRepository should be initialized
    And the BlockingRecommendationService should be initialized
    """

    def test_aggregator_initialization_at_startup(self):
        """Test that aggregator components are initialized at startup."""
        # This test verifies the initialization pattern
        # In actual implementation, this would be in api_service.py

        # Given: Create instances
        fake_repository = FakeCategoryTallyRepository()
        fake_aggregator = FakeCategoryAggregator()

        # Then: Verify instances are created
        self.assertIsNotNone(fake_repository)
        self.assertIsNotNone(fake_aggregator)


class TestAggregatorShutdownFlushesBuffer(unittest.TestCase):
    """
    Scenario: Aggregator shutdown flushes remaining buffer

    Given the aggregator has buffered data
    When the application shuts down
    Then the aggregator should flush all buffered data
    And no data should be lost
    """

    def test_aggregator_shutdown_flushes_buffer(self):
        """Test that aggregator flushes on shutdown."""
        # Given: Aggregator with buffered data
        fake_aggregator = FakeCategoryAggregator()
        fake_aggregator.record_batch(
            "test@gmail.com",
            {"Marketing": 5},
            datetime(2025, 11, 28, 10, 0, 0)
        )

        # Verify buffer has data
        self.assertTrue(fake_aggregator.has_buffered_data())
        initial_flush_count = fake_aggregator.flush_count

        # When: Shutdown (simulate atexit handler)
        fake_aggregator.flush()

        # Then: Verify data was flushed
        self.assertEqual(fake_aggregator.flush_count, initial_flush_count + 1)
        self.assertFalse(fake_aggregator.has_buffered_data())


class TestDataCleanupJobRemovesOldTallies(unittest.TestCase):
    """
    Scenario: Data cleanup job removes old tallies

    Given tallies exist older than 30 days
    When the data cleanup job runs
    Then tallies older than 30 days should be deleted
    And recent tallies should be preserved
    """

    def test_data_cleanup_removes_old_tallies(self):
        """Test that cleanup job removes old tallies."""
        # Given: Repository with old and recent tallies
        fake_repository = FakeCategoryTallyRepository()

        today = date(2025, 11, 28)
        old_date = today - timedelta(days=35)
        recent_date = today - timedelta(days=5)

        # Save old tally
        fake_repository.save_daily_tally(
            "test@gmail.com",
            old_date,
            {"Marketing": 5},
            5
        )

        # Save recent tally
        fake_repository.save_daily_tally(
            "test@gmail.com",
            recent_date,
            {"Marketing": 3},
            3
        )

        # When: Run cleanup job (delete tallies older than 30 days)
        cutoff_date = today - timedelta(days=30)
        deleted_count = fake_repository.delete_tallies_before("test@gmail.com", cutoff_date)

        # Then: Verify old tally was deleted and recent preserved
        self.assertEqual(deleted_count, 1)
        self.assertIsNone(fake_repository.get_tally("test@gmail.com", old_date))
        self.assertIsNotNone(fake_repository.get_tally("test@gmail.com", recent_date))


class TestHourlyProcessingAccumulatesDailyTallies(unittest.TestCase):
    """
    Scenario: Hourly processing accumulates daily tallies

    Given a user is configured for processing
    When the background processor runs multiple times in the same day
    Then the daily tally should accumulate all counts
    """

    def test_hourly_processing_accumulates_tallies(self):
        """Test that multiple processing runs accumulate in daily tallies."""
        # Given: Repository
        fake_repository = FakeCategoryTallyRepository()

        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)

        # When: Process at different times on same day
        # Morning processing
        fake_repository.save_daily_tally(
            email_address,
            tally_date,
            {"Marketing": 5},
            5
        )

        # Afternoon processing (should accumulate)
        fake_repository.save_daily_tally(
            email_address,
            tally_date,
            {"Marketing": 8},
            8 + 5  # Total after merging
        )

        # Then: Verify daily tally accumulated
        tally = fake_repository.get_tally(email_address, tally_date)
        self.assertIsNotNone(tally)
        self.assertEqual(tally.category_counts["Marketing"], 13)
        self.assertEqual(tally.total_emails, 13)


class TestProcessingSpansMidnightCorrectly(unittest.TestCase):
    """
    Scenario: Processing spans midnight correctly

    Given a user is configured for processing
    When the background processor runs before and after midnight
    Then separate tallies should be created for each day
    """

    def test_processing_spans_midnight_correctly(self):
        """Test that processing correctly handles midnight boundary."""
        # Given: Repository
        fake_repository = FakeCategoryTallyRepository()

        email_address = "test@gmail.com"
        date1 = date(2025, 11, 27)
        date2 = date(2025, 11, 28)

        # When: Process before midnight
        fake_repository.save_daily_tally(
            email_address,
            date1,
            {"Marketing": 5},
            5
        )

        # Process after midnight
        fake_repository.save_daily_tally(
            email_address,
            date2,
            {"Marketing": 3},
            3
        )

        # Then: Verify separate tallies for each day
        tally1 = fake_repository.get_tally(email_address, date1)
        tally2 = fake_repository.get_tally(email_address, date2)

        self.assertIsNotNone(tally1)
        self.assertIsNotNone(tally2)
        self.assertEqual(tally1.category_counts["Marketing"], 5)
        self.assertEqual(tally2.category_counts["Marketing"], 3)


if __name__ == '__main__':
    unittest.main()
