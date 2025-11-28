"""
Tests for Category Tally Repository - Aggregation operations.

Based on BDD scenarios:
- Scenario: Get aggregated tallies across date range
- Scenario: Calculate percentages correctly in aggregation
- Scenario: Calculate daily averages in aggregation

Tests are derived from Gherkin scenarios in:
- tests/bdd/repository-operations.feature
- prompts/001-bdd-repository-operations.md
"""
import unittest
import tempfile
import os
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base


class TestGetAggregatedTallies(unittest.TestCase):
    """
    Scenario: Get aggregated tallies across date range

    Given tallies exist for multiple dates
    When aggregated tallies are requested for a date range
    Then total_emails should be the sum of all tallies
    And days_with_data should equal the number of days with tallies
    And category_summaries should include totals for each category
    And category_summaries should include percentages for each category

    The implementation should provide get_aggregated_tallies method.
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

    def test_aggregated_tallies_calculates_total_emails(self):
        """
        Test that total_emails is calculated correctly across date range.

        Given tallies exist with total counts summing to 368
        When aggregated tallies are requested
        Then total_emails should be 368
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"

        # Create 7 days of tallies (total should be 368)
        test_data = [
            (date(2025, 11, 22), {"Marketing": 30, "Personal": 10, "Other": 5}),
            (date(2025, 11, 23), {"Marketing": 35, "Personal": 12, "Other": 8}),
            (date(2025, 11, 24), {"Marketing": 28, "Personal": 8, "Other": 4}),
            (date(2025, 11, 25), {"Marketing": 40, "Personal": 15, "Other": 10}),
            (date(2025, 11, 26), {"Marketing": 32, "Personal": 11, "Other": 7}),
            (date(2025, 11, 27), {"Marketing": 38, "Personal": 9, "Other": 6}),
            (date(2025, 11, 28), {"Marketing": 42, "Personal": 13, "Other": 5}),
        ]  # Total: 368

        for tally_date, counts in test_data:
            total = sum(counts.values())
            repository.save_daily_tally(email_address, tally_date, counts, total)

        # Act
        result = repository.get_aggregated_tallies(
            email_address,
            date(2025, 11, 22),
            date(2025, 11, 28)
        )

        # Assert
        self.assertEqual(result.total_emails, 368,
                        "total_emails should be 368 (sum of all daily totals)")

    def test_aggregated_tallies_counts_days_with_data(self):
        """
        Test that days_with_data is calculated correctly.

        Given 7 days of tallies exist
        When aggregated tallies are requested
        Then days_with_data should be 7
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"

        # Create 7 days of tallies
        for i in range(7):
            tally_date = date(2025, 11, 22) + timedelta(days=i)
            repository.save_daily_tally(
                email_address,
                tally_date,
                {"Marketing": 30},
                30
            )

        # Act
        result = repository.get_aggregated_tallies(
            email_address,
            date(2025, 11, 22),
            date(2025, 11, 28)
        )

        # Assert
        self.assertEqual(result.days_with_data, 7,
                        "days_with_data should be 7")

    def test_aggregated_tallies_includes_category_totals(self):
        """
        Test that category_summaries includes correct totals.

        Given tallies with Marketing totaling 245 and Personal totaling 78
        When aggregated tallies are requested
        Then category_summaries should include Marketing with total_count 245
        And category_summaries should include Personal with total_count 78
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"

        # Marketing totals: 30+35+28+40+32+38+42 = 245
        # Personal totals: 10+12+8+15+11+9+13 = 78
        test_data = [
            (date(2025, 11, 22), {"Marketing": 30, "Personal": 10, "Other": 5}),
            (date(2025, 11, 23), {"Marketing": 35, "Personal": 12, "Other": 8}),
            (date(2025, 11, 24), {"Marketing": 28, "Personal": 8, "Other": 4}),
            (date(2025, 11, 25), {"Marketing": 40, "Personal": 15, "Other": 10}),
            (date(2025, 11, 26), {"Marketing": 32, "Personal": 11, "Other": 7}),
            (date(2025, 11, 27), {"Marketing": 38, "Personal": 9, "Other": 6}),
            (date(2025, 11, 28), {"Marketing": 42, "Personal": 13, "Other": 5}),
        ]

        for tally_date, counts in test_data:
            total = sum(counts.values())
            repository.save_daily_tally(email_address, tally_date, counts, total)

        # Act
        result = repository.get_aggregated_tallies(
            email_address,
            date(2025, 11, 22),
            date(2025, 11, 28)
        )

        # Assert - Find Marketing and Personal in category_summaries
        marketing_summary = next(
            (s for s in result.category_summaries if s.category == "Marketing"),
            None
        )
        personal_summary = next(
            (s for s in result.category_summaries if s.category == "Personal"),
            None
        )

        self.assertIsNotNone(marketing_summary, "Marketing should be in summaries")
        self.assertEqual(marketing_summary.total_count, 245,
                        "Marketing total_count should be 245")

        self.assertIsNotNone(personal_summary, "Personal should be in summaries")
        self.assertEqual(personal_summary.total_count, 78,
                        "Personal total_count should be 78")

    def test_aggregated_tallies_includes_percentages(self):
        """
        Test that category_summaries includes percentages.

        Given tallies exist
        When aggregated tallies are requested
        Then category_summaries should include percentages for each category
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"

        # Create test data
        test_data = [
            (date(2025, 11, 22), {"Marketing": 30, "Personal": 10, "Other": 5}),
        ]

        for tally_date, counts in test_data:
            total = sum(counts.values())
            repository.save_daily_tally(email_address, tally_date, counts, total)

        # Act
        result = repository.get_aggregated_tallies(
            email_address,
            date(2025, 11, 22),
            date(2025, 11, 22)
        )

        # Assert - All category_summaries should have percentage field
        for summary in result.category_summaries:
            self.assertTrue(
                hasattr(summary, 'percentage'),
                f"Category {summary.category} should have percentage attribute"
            )
            self.assertIsNotNone(
                summary.percentage,
                f"Category {summary.category} percentage should not be None"
            )
            self.assertGreaterEqual(
                summary.percentage,
                0.0,
                f"Category {summary.category} percentage should be >= 0"
            )
            self.assertLessEqual(
                summary.percentage,
                100.0,
                f"Category {summary.category} percentage should be <= 100"
            )


class TestCalculatePercentagesCorrectly(unittest.TestCase):
    """
    Scenario: Calculate percentages correctly in aggregation

    Given tallies with Marketing=70 and Personal=30 (total 100)
    When aggregated tallies are requested
    Then Marketing percentage should be 70.0
    And Personal percentage should be 30.0

    The implementation should calculate accurate percentages.
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

    def test_percentage_calculation_accuracy(self):
        """
        Test that percentages are calculated correctly.

        Given tallies with Marketing=70, Personal=30 (100 total)
        When aggregated tallies are requested
        Then Marketing percentage should be 70.0
        And Personal percentage should be 30.0
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)

        # Create tally with 70/30 split
        category_counts = {"Marketing": 70, "Personal": 30}
        repository.save_daily_tally(
            email_address,
            tally_date,
            category_counts,
            100
        )

        # Act
        result = repository.get_aggregated_tallies(
            email_address,
            tally_date,
            tally_date
        )

        # Assert
        marketing_summary = next(
            (s for s in result.category_summaries if s.category == "Marketing"),
            None
        )
        personal_summary = next(
            (s for s in result.category_summaries if s.category == "Personal"),
            None
        )

        self.assertIsNotNone(marketing_summary, "Marketing should be in summaries")
        self.assertEqual(marketing_summary.percentage, 70.0,
                        "Marketing percentage should be exactly 70.0")

        self.assertIsNotNone(personal_summary, "Personal should be in summaries")
        self.assertEqual(personal_summary.percentage, 30.0,
                        "Personal percentage should be exactly 30.0")


class TestCalculateDailyAverages(unittest.TestCase):
    """
    Scenario: Calculate daily averages in aggregation

    Given tallies exist with Marketing counts 30, 40, 50, 60 over 4 days
    When aggregated tallies are requested
    Then Marketing daily_average should be 45.0

    The implementation should calculate daily averages for each category.
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

    def test_daily_average_calculation(self):
        """
        Test that daily averages are calculated correctly.

        Given Marketing counts of 30, 40, 50, 60 over 4 days
        When aggregated tallies are requested
        Then Marketing daily_average should be 45.0 ((30+40+50+60)/4)
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"

        # Create 4 days of tallies: 30, 40, 50, 60 (average = 45)
        test_data = [
            (date(2025, 11, 25), {"Marketing": 30}),
            (date(2025, 11, 26), {"Marketing": 40}),
            (date(2025, 11, 27), {"Marketing": 50}),
            (date(2025, 11, 28), {"Marketing": 60}),
        ]

        for tally_date, counts in test_data:
            total = sum(counts.values())
            repository.save_daily_tally(email_address, tally_date, counts, total)

        # Act
        result = repository.get_aggregated_tallies(
            email_address,
            date(2025, 11, 25),
            date(2025, 11, 28)
        )

        # Assert
        marketing_summary = next(
            (s for s in result.category_summaries if s.category == "Marketing"),
            None
        )

        self.assertIsNotNone(marketing_summary, "Marketing should be in summaries")
        self.assertEqual(marketing_summary.daily_average, 45.0,
                        "Marketing daily_average should be 45.0")


if __name__ == '__main__':
    unittest.main()
