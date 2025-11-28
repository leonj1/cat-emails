"""
Tests for Category Tally Repository - Retrieve operations.

Based on BDD scenarios:
- Scenario: Retrieve tallies for a date range
- Scenario: Retrieve single tally by account and date
- Scenario: Return None for non-existent tally

Tests are derived from Gherkin scenarios in:
- tests/bdd/repository-operations.feature
- prompts/001-bdd-repository-operations.md
"""
import unittest
import tempfile
import os
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base


class TestRetrieveTalliesForDateRange(unittest.TestCase):
    """
    Scenario: Retrieve tallies for a date range

    Given tallies exist for "test@gmail.com" for multiple dates
    When tallies are retrieved for a date range
    Then all tallies within the range should be returned
    And each tally should contain the correct category counts

    The implementation should provide get_tallies_for_period method.
    """

    def setUp(self):
        """Set up test fixtures with in-memory database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        self.engine = create_engine(f'sqlite:///{self.temp_db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        """Clean up test fixtures."""
        self.session.close()
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_retrieve_tallies_returns_all_in_range(self):
        """
        Test that all tallies within a date range are returned.

        Given 7 tallies exist for consecutive dates
        When tallies are retrieved for "2025-11-22" to "2025-11-28"
        Then 7 daily tallies should be returned
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"

        # Create 7 days of tallies
        test_data = [
            (date(2025, 11, 22), {"Marketing": 30, "Personal": 10}),
            (date(2025, 11, 23), {"Marketing": 35, "Personal": 12}),
            (date(2025, 11, 24), {"Marketing": 28, "Personal": 8}),
            (date(2025, 11, 25), {"Marketing": 40, "Personal": 15}),
            (date(2025, 11, 26), {"Marketing": 32, "Personal": 11}),
            (date(2025, 11, 27), {"Marketing": 38, "Personal": 9}),
            (date(2025, 11, 28), {"Marketing": 42, "Personal": 13}),
        ]

        for tally_date, counts in test_data:
            total = sum(counts.values())
            repository.save_daily_tally(email_address, tally_date, counts, total)

        # Act
        start_date = date(2025, 11, 22)
        end_date = date(2025, 11, 28)
        results = repository.get_tallies_for_period(
            email_address,
            start_date,
            end_date
        )

        # Assert
        self.assertEqual(len(results), 7, "Should return 7 daily tallies for the range")

    def test_retrieve_tallies_contains_correct_counts(self):
        """
        Test that each retrieved tally contains the correct category counts.

        Given tallies exist with specific category counts
        When tallies are retrieved
        Then each tally should contain the correct category counts
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"

        # Create test data
        tally_date = date(2025, 11, 28)
        expected_counts = {"Marketing": 42, "Personal": 13}
        repository.save_daily_tally(
            email_address,
            tally_date,
            expected_counts,
            sum(expected_counts.values())
        )

        # Act
        results = repository.get_tallies_for_period(
            email_address,
            tally_date,
            tally_date
        )

        # Assert
        self.assertEqual(len(results), 1, "Should return 1 tally for single date range")
        tally = results[0]
        self.assertEqual(tally.category_counts["Marketing"], 42,
                        "Marketing count should be 42")
        self.assertEqual(tally.category_counts["Personal"], 13,
                        "Personal count should be 13")


class TestRetrieveSingleTallyByAccountAndDate(unittest.TestCase):
    """
    Scenario: Retrieve single tally by account and date

    Given a tally exists for "test@gmail.com" on "2025-11-28"
    When the tally is retrieved for that account and date
    Then the tally should be returned
    And the category_counts should match the stored data

    The implementation should provide get_tally method.
    """

    def setUp(self):
        """Set up test fixtures with in-memory database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        self.engine = create_engine(f'sqlite:///{self.temp_db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        """Clean up test fixtures."""
        self.session.close()
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_retrieve_single_tally_returns_data(self):
        """
        Test that retrieving a tally by account and date returns the tally.

        Given a tally exists for "test@gmail.com" on "2025-11-28"
        When the tally is retrieved
        Then the tally should be returned
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)

        repository.save_daily_tally(
            email_address,
            tally_date,
            {"Marketing": 50},
            50
        )

        # Act
        result = repository.get_tally(email_address, tally_date)

        # Assert
        self.assertIsNotNone(result, "get_tally should return the tally")
        self.assertEqual(result.email_address, email_address)
        self.assertEqual(result.tally_date, tally_date)

    def test_retrieve_single_tally_category_counts_match(self):
        """
        Test that retrieved tally has correct category_counts.

        Given a tally exists with Marketing=50
        When the tally is retrieved
        Then category_counts should match the stored data
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)
        expected_counts = {"Marketing": 50}

        repository.save_daily_tally(
            email_address,
            tally_date,
            expected_counts,
            50
        )

        # Act
        result = repository.get_tally(email_address, tally_date)

        # Assert
        self.assertEqual(
            result.category_counts,
            expected_counts,
            "category_counts should match the stored data"
        )


class TestReturnNoneForNonExistentTally(unittest.TestCase):
    """
    Scenario: Return None for non-existent tally

    Given no tally exists for "unknown@gmail.com" on "2025-11-28"
    When the tally is retrieved
    Then the result should be None

    The implementation should return None for missing tallies.
    """

    def setUp(self):
        """Set up test fixtures with in-memory database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        self.engine = create_engine(f'sqlite:///{self.temp_db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        """Clean up test fixtures."""
        self.session.close()
        if hasattr(self, 'temp_db_path') and os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_non_existent_tally_returns_none(self):
        """
        Test that retrieving a non-existent tally returns None.

        Given no tally exists for "unknown@gmail.com" on "2025-11-28"
        When the tally is retrieved
        Then the result should be None
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)

        # Act - Try to retrieve a tally that doesn't exist
        result = repository.get_tally("unknown@gmail.com", date(2025, 11, 28))

        # Assert
        self.assertIsNone(result, "get_tally should return None for non-existent tally")


if __name__ == '__main__':
    unittest.main()
