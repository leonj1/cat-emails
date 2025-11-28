"""
Tests for Category Tally Repository - Delete operations.

Based on BDD scenarios:
- Scenario: Delete tallies older than cutoff date

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


class TestDeleteTalliesOlderThanCutoff(unittest.TestCase):
    """
    Scenario: Delete tallies older than cutoff date

    Given tallies exist for dates before and after a cutoff
    When tallies before the cutoff are deleted
    Then only tallies before cutoff should be removed
    And tallies on or after cutoff should still exist

    The implementation should provide delete_tallies_before method.
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

    def test_delete_tallies_before_cutoff_date(self):
        """
        Test that tallies before cutoff date are deleted.

        Given tallies exist for 2025-10-01, 2025-10-15, 2025-11-01, 2025-11-28
        When tallies before "2025-11-01" are deleted
        Then 2 tallies should be deleted (2025-10-01 and 2025-10-15)
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"

        # Create tallies on different dates
        test_dates = [
            date(2025, 10, 1),   # Should be deleted
            date(2025, 10, 15),  # Should be deleted
            date(2025, 11, 1),   # Should remain
            date(2025, 11, 28),  # Should remain
        ]

        for tally_date in test_dates:
            repository.save_daily_tally(
                email_address,
                tally_date,
                {"Marketing": 100},
                100
            )

        # Act
        cutoff_date = date(2025, 11, 1)
        deleted_count = repository.delete_tallies_before(email_address, cutoff_date)

        # Assert
        self.assertEqual(deleted_count, 2, "Should delete 2 tallies (before 2025-11-01)")

    def test_tallies_on_or_after_cutoff_remain(self):
        """
        Test that tallies on or after cutoff date remain.

        Given tallies exist for dates before and after cutoff
        When tallies before cutoff are deleted
        Then tallies for "2025-11-01" and "2025-11-28" should still exist
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"

        # Create tallies on different dates
        test_dates = [
            date(2025, 10, 1),
            date(2025, 10, 15),
            date(2025, 11, 1),
            date(2025, 11, 28),
        ]

        for tally_date in test_dates:
            repository.save_daily_tally(
                email_address,
                tally_date,
                {"Marketing": 100},
                100
            )

        # Act
        cutoff_date = date(2025, 11, 1)
        repository.delete_tallies_before(email_address, cutoff_date)

        # Assert - Check that tallies on/after cutoff still exist
        nov1_tally = repository.get_tally(email_address, date(2025, 11, 1))
        nov28_tally = repository.get_tally(email_address, date(2025, 11, 28))

        self.assertIsNotNone(nov1_tally, "Tally for 2025-11-01 should still exist")
        self.assertIsNotNone(nov28_tally, "Tally for 2025-11-28 should still exist")

        # Verify tallies before cutoff are gone
        oct1_tally = repository.get_tally(email_address, date(2025, 10, 1))
        oct15_tally = repository.get_tally(email_address, date(2025, 10, 15))

        self.assertIsNone(oct1_tally, "Tally for 2025-10-01 should be deleted")
        self.assertIsNone(oct15_tally, "Tally for 2025-10-15 should be deleted")


if __name__ == '__main__':
    unittest.main()
