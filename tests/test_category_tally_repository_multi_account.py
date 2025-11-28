"""
Tests for Category Tally Repository - Multi-account and edge case operations.

Based on BDD scenarios:
- Scenario: Handle multiple accounts independently
- Scenario: Empty aggregation for account with no data

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


class TestHandleMultipleAccountsIndependently(unittest.TestCase):
    """
    Scenario: Handle multiple accounts independently

    Given tallies exist for different accounts
    When aggregated tallies are requested for each account
    Then each account's data should be independent

    The implementation should properly filter by email_address.
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

    def test_user1_totals_independent_from_user2(self):
        """
        Test that user1's totals don't include user2's data.

        Given user1 has Marketing=100 and user2 has Marketing=200
        When aggregated tallies are requested for user1
        Then total_emails should be 100
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        tally_date = date(2025, 11, 28)

        # Create tallies for two different users
        repository.save_daily_tally(
            "user1@gmail.com",
            tally_date,
            {"Marketing": 100},
            100
        )
        repository.save_daily_tally(
            "user2@gmail.com",
            tally_date,
            {"Marketing": 200},
            200
        )

        # Act - Get aggregated tallies for user1
        result = repository.get_aggregated_tallies(
            "user1@gmail.com",
            tally_date,
            tally_date
        )

        # Assert
        self.assertEqual(result.total_emails, 100,
                        "user1 total_emails should be 100 (not including user2's data)")

    def test_user2_totals_independent_from_user1(self):
        """
        Test that user2's totals don't include user1's data.

        Given user1 has Marketing=100 and user2 has Marketing=200
        When aggregated tallies are requested for user2
        Then total_emails should be 200
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        tally_date = date(2025, 11, 28)

        # Create tallies for two different users
        repository.save_daily_tally(
            "user1@gmail.com",
            tally_date,
            {"Marketing": 100},
            100
        )
        repository.save_daily_tally(
            "user2@gmail.com",
            tally_date,
            {"Marketing": 200},
            200
        )

        # Act - Get aggregated tallies for user2
        result = repository.get_aggregated_tallies(
            "user2@gmail.com",
            tally_date,
            tally_date
        )

        # Assert
        self.assertEqual(result.total_emails, 200,
                        "user2 total_emails should be 200 (not including user1's data)")


class TestEmptyAggregationForAccountWithNoData(unittest.TestCase):
    """
    Scenario: Empty aggregation for account with no data

    Given no tallies exist for "empty@gmail.com"
    When aggregated tallies are requested
    Then total_emails should be 0
    And days_with_data should be 0
    And category_summaries should be empty

    The implementation should handle empty data gracefully.
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

    def test_empty_account_has_zero_total_emails(self):
        """
        Test that an account with no data has total_emails=0.

        Given no tallies exist for "empty@gmail.com"
        When aggregated tallies are requested
        Then total_emails should be 0
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)

        # Act - Request aggregation for account with no data
        result = repository.get_aggregated_tallies(
            "empty@gmail.com",
            date(2025, 11, 22),
            date(2025, 11, 28)
        )

        # Assert
        self.assertEqual(result.total_emails, 0,
                        "total_emails should be 0 for account with no data")

    def test_empty_account_has_zero_days_with_data(self):
        """
        Test that an account with no data has days_with_data=0.

        Given no tallies exist for "empty@gmail.com"
        When aggregated tallies are requested
        Then days_with_data should be 0
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)

        # Act
        result = repository.get_aggregated_tallies(
            "empty@gmail.com",
            date(2025, 11, 22),
            date(2025, 11, 28)
        )

        # Assert
        self.assertEqual(result.days_with_data, 0,
                        "days_with_data should be 0 for account with no data")

    def test_empty_account_has_empty_category_summaries(self):
        """
        Test that an account with no data has empty category_summaries.

        Given no tallies exist for "empty@gmail.com"
        When aggregated tallies are requested
        Then category_summaries should be empty
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)

        # Act
        result = repository.get_aggregated_tallies(
            "empty@gmail.com",
            date(2025, 11, 22),
            date(2025, 11, 28)
        )

        # Assert
        self.assertEqual(len(result.category_summaries), 0,
                        "category_summaries should be empty for account with no data")


if __name__ == '__main__':
    unittest.main()
