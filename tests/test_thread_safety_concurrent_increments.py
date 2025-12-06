"""
Tests for thread safety and concurrent access to increment_categorized and increment_skipped.

Based on requirements for sub-task 1.6:
- Concurrent access safety
- Large count handling (1000+)
- Lock mechanism verification

These tests verify that:
1. Multiple threads can safely increment counts concurrently
2. Lock mechanism prevents race conditions
3. Final counts are accurate after concurrent operations
4. Large batch increments are handled correctly
5. No data loss occurs under concurrent load
"""
import threading
import unittest

from services.processing_status_manager import (
    ProcessingStatusManager,
    ProcessingState,
    AccountStatus,
)


class TestConcurrentCategorizedIncrements(unittest.TestCase):
    """
    Scenario: Multiple threads increment categorized count concurrently

    Given a ProcessingStatusManager with an active session
    When multiple threads increment emails_categorized concurrently
    Then the final count equals the sum of all increments
    And no race conditions occur
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)
        self.status_manager.start_processing("concurrent@example.com")

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_concurrent_single_increments_10_threads(self):
        """
        Test that 10 threads each incrementing by 1 results in count of 10.

        Verifies thread-safe operation under concurrent single increments.
        """
        num_threads = 10
        threads = []

        # Define worker function
        def increment_worker():
            self.status_manager.increment_categorized(1)

        # Create and start threads
        for _ in range(num_threads):
            thread = threading.Thread(target=increment_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert: Final count should be 10
        status = self.status_manager.get_current_status()
        self.assertEqual(
            status['emails_categorized'],
            num_threads,
            f"Expected {num_threads} after concurrent increments, got {status['emails_categorized']}"
        )

    def test_concurrent_batch_increments_10_threads(self):
        """
        Test that 10 threads each incrementing by 5 results in count of 50.

        Verifies thread-safe operation under concurrent batch increments.
        """
        num_threads = 10
        increment_size = 5
        expected_total = num_threads * increment_size
        threads = []

        # Define worker function
        def increment_worker():
            self.status_manager.increment_categorized(increment_size)

        # Create and start threads
        for _ in range(num_threads):
            thread = threading.Thread(target=increment_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert: Final count should be 50
        status = self.status_manager.get_current_status()
        self.assertEqual(
            status['emails_categorized'],
            expected_total,
            f"Expected {expected_total} after concurrent batch increments"
        )

    def test_concurrent_mixed_increment_sizes(self):
        """
        Test concurrent increments with varying sizes.

        Thread 1-5: increment by 1
        Thread 6-10: increment by 10
        Expected total: (5 * 1) + (5 * 10) = 55
        """
        threads = []
        expected_total = 55

        # Define worker functions
        def small_increment_worker():
            self.status_manager.increment_categorized(1)

        def large_increment_worker():
            self.status_manager.increment_categorized(10)

        # Create 5 threads with small increments
        for _ in range(5):
            thread = threading.Thread(target=small_increment_worker)
            threads.append(thread)

        # Create 5 threads with large increments
        for _ in range(5):
            thread = threading.Thread(target=large_increment_worker)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert: Final count should be 55
        status = self.status_manager.get_current_status()
        self.assertEqual(
            status['emails_categorized'],
            expected_total,
            "Mixed concurrent increments should sum correctly"
        )


class TestConcurrentSkippedIncrements(unittest.TestCase):
    """
    Scenario: Multiple threads increment skipped count concurrently

    Given a ProcessingStatusManager with an active session
    When multiple threads increment emails_skipped concurrently
    Then the final count equals the sum of all increments
    And no race conditions occur
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)
        self.status_manager.start_processing("concurrent2@example.com")

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_concurrent_skipped_increments_20_threads(self):
        """
        Test that 20 threads each incrementing skipped by 1 results in count of 20.

        Verifies thread-safe operation for skipped field under higher concurrency.
        """
        num_threads = 20
        threads = []

        # Define worker function
        def increment_worker():
            self.status_manager.increment_skipped(1)

        # Create and start threads
        for _ in range(num_threads):
            thread = threading.Thread(target=increment_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert: Final count should be 20
        status = self.status_manager.get_current_status()
        self.assertEqual(
            status['emails_skipped'],
            num_threads,
            f"Expected {num_threads} after concurrent increments"
        )


class TestConcurrentMixedIncrements(unittest.TestCase):
    """
    Scenario: Multiple threads increment both categorized and skipped concurrently

    Given a ProcessingStatusManager with an active session
    When multiple threads increment both fields concurrently
    Then both final counts are accurate
    And fields don't interfere with each other
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)
        self.status_manager.start_processing("mixed@example.com")

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_concurrent_mixed_field_increments(self):
        """
        Test concurrent increments to both categorized and skipped fields.

        10 threads increment categorized by 2 (expected: 20)
        10 threads increment skipped by 3 (expected: 30)
        """
        threads = []

        # Define worker functions
        def categorized_worker():
            self.status_manager.increment_categorized(2)

        def skipped_worker():
            self.status_manager.increment_skipped(3)

        # Create 10 threads for each field
        for _ in range(10):
            threads.append(threading.Thread(target=categorized_worker))
            threads.append(threading.Thread(target=skipped_worker))

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert: Both fields should have correct totals
        status = self.status_manager.get_current_status()
        self.assertEqual(
            status['emails_categorized'],
            20,
            "Categorized count should be 20"
        )
        self.assertEqual(
            status['emails_skipped'],
            30,
            "Skipped count should be 30"
        )

    def test_concurrent_alternating_increments(self):
        """
        Test threads alternating between categorized and skipped increments.

        Each thread increments both fields in sequence.
        20 threads: each increments categorized(1) then skipped(1)
        Expected: categorized=20, skipped=20
        """
        num_threads = 20
        threads = []

        # Define worker function that increments both
        def alternating_worker():
            self.status_manager.increment_categorized(1)
            self.status_manager.increment_skipped(1)

        # Create and start threads
        for _ in range(num_threads):
            thread = threading.Thread(target=alternating_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert: Both fields should equal num_threads
        status = self.status_manager.get_current_status()
        self.assertEqual(
            status['emails_categorized'],
            num_threads,
            "Categorized count should equal thread count"
        )
        self.assertEqual(
            status['emails_skipped'],
            num_threads,
            "Skipped count should equal thread count"
        )


class TestLargeCountHandling(unittest.TestCase):
    """
    Scenario: Large count increments are handled correctly

    Given a ProcessingStatusManager with an active session
    When large count values (1000+) are incremented
    Then the values are handled without overflow or data loss
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)
        self.status_manager.start_processing("largecounts@example.com")

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_single_large_increment_1000(self):
        """
        Test single large increment of 1000.

        Verifies large batch increments are handled correctly.
        """
        large_count = 1000
        self.status_manager.increment_categorized(large_count)

        status = self.status_manager.get_current_status()
        self.assertEqual(
            status['emails_categorized'],
            large_count,
            f"Large count {large_count} should be handled correctly"
        )

    def test_multiple_large_increments_total_10000(self):
        """
        Test multiple large increments totaling 10000.

        10 increments of 1000 each.
        Verifies cumulative large counts are handled correctly.
        """
        increment_size = 1000
        num_increments = 10
        expected_total = increment_size * num_increments

        for _ in range(num_increments):
            self.status_manager.increment_categorized(increment_size)

        status = self.status_manager.get_current_status()
        self.assertEqual(
            status['emails_categorized'],
            expected_total,
            f"Cumulative large count {expected_total} should be correct"
        )

    def test_concurrent_large_increments(self):
        """
        Test concurrent large increments.

        5 threads each increment by 500 (expected: 2500)
        Verifies thread safety with large increment sizes.
        """
        num_threads = 5
        increment_size = 500
        expected_total = num_threads * increment_size
        threads = []

        # Define worker function
        def large_increment_worker():
            self.status_manager.increment_categorized(increment_size)

        # Create and start threads
        for _ in range(num_threads):
            thread = threading.Thread(target=large_increment_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert: Final count should be 2500
        status = self.status_manager.get_current_status()
        self.assertEqual(
            status['emails_categorized'],
            expected_total,
            f"Concurrent large increments should total {expected_total}"
        )

    def test_very_large_single_increment_50000(self):
        """
        Test very large single increment (50000).

        Simulates high-volume email processing scenario.
        """
        very_large_count = 50000
        self.status_manager.increment_categorized(very_large_count)

        status = self.status_manager.get_current_status()
        self.assertEqual(
            status['emails_categorized'],
            very_large_count,
            f"Very large count {very_large_count} should be handled without overflow"
        )


class TestLockMechanismVerification(unittest.TestCase):
    """
    Scenario: Lock mechanism prevents race conditions

    Given a ProcessingStatusManager with thread-safe locking
    When multiple threads access shared state concurrently
    Then no race conditions occur
    And data integrity is maintained
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)
        self.status_manager.start_processing("locktest@example.com")

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_lock_prevents_race_condition_100_threads(self):
        """
        Test that lock prevents race conditions with 100 concurrent threads.

        Each thread increments by 1, final count should be exactly 100.
        This is a stress test to verify lock mechanism integrity.
        """
        num_threads = 100
        threads = []

        # Define worker function
        def increment_worker():
            self.status_manager.increment_categorized(1)

        # Create and start threads
        for _ in range(num_threads):
            thread = threading.Thread(target=increment_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert: Final count should be exactly 100 (no lost increments)
        status = self.status_manager.get_current_status()
        self.assertEqual(
            status['emails_categorized'],
            num_threads,
            f"Lock should prevent race conditions, expected {num_threads}"
        )

    def test_rapid_concurrent_increments_no_data_loss(self):
        """
        Test rapid concurrent increments don't lose data.

        50 threads each increment by 2 (expected: 100)
        Threads start immediately without delays.
        """
        num_threads = 50
        increment_size = 2
        expected_total = num_threads * increment_size
        threads = []

        # Define worker function
        def rapid_increment_worker():
            self.status_manager.increment_categorized(increment_size)

        # Create and start threads rapidly
        for _ in range(num_threads):
            thread = threading.Thread(target=rapid_increment_worker)
            threads.append(thread)
            thread.start()  # Start immediately

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert: No data loss occurred
        status = self.status_manager.get_current_status()
        self.assertEqual(
            status['emails_categorized'],
            expected_total,
            "Rapid concurrent increments should not lose data"
        )

    def test_mixed_operations_thread_safety(self):
        """
        Test mixed operations (start, increment, get_status) are thread-safe.

        Threads perform different operations concurrently:
        - Some increment categorized
        - Some increment skipped
        - Some call get_current_status (read operation)

        All operations should complete without deadlock or data corruption.
        """
        results = []
        threads = []
        num_increment_threads = 20

        # Define worker functions
        def increment_categorized_worker():
            self.status_manager.increment_categorized(1)

        def increment_skipped_worker():
            self.status_manager.increment_skipped(1)

        def read_status_worker():
            status = self.status_manager.get_current_status()
            results.append(status)

        # Create threads for different operations
        for _ in range(num_increment_threads):
            threads.append(threading.Thread(target=increment_categorized_worker))
            threads.append(threading.Thread(target=increment_skipped_worker))

        # Add some read operations
        for _ in range(10):
            threads.append(threading.Thread(target=read_status_worker))

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert: Final counts should be correct
        final_status = self.status_manager.get_current_status()
        self.assertEqual(
            final_status['emails_categorized'],
            num_increment_threads,
            "Categorized count should be correct despite mixed operations"
        )
        self.assertEqual(
            final_status['emails_skipped'],
            num_increment_threads,
            "Skipped count should be correct despite mixed operations"
        )
        # Assert: All read operations completed successfully
        self.assertEqual(
            len(results),
            10,
            "All read operations should complete"
        )


if __name__ == '__main__':
    unittest.main()
