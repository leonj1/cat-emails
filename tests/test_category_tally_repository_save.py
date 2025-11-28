"""
Tests for Category Tally Repository - Save and Update operations.

Based on BDD scenarios:
- Scenario: Save a new daily tally
- Scenario: Update an existing daily tally

Tests are derived from Gherkin scenarios in:
- tests/bdd/repository-operations.feature
- prompts/001-bdd-repository-operations.md
"""
import unittest
import tempfile
import os
import time
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base


class TestSaveNewDailyTally(unittest.TestCase):
    """
    Scenario: Save a new daily tally

    Given no tally exists for "test@gmail.com" on "2025-11-28"
    When a daily tally is saved with specific category counts
    Then the tally should be persisted in the database
    And retrieving the tally should return the saved data

    The implementation should create a save_daily_tally method that:
    - Accepts email_address, tally_date, category_counts, and total_emails
    - Persists the data to the database
    - Returns the created tally
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

    def test_save_new_daily_tally_persists_data(self):
        """
        Test that a new daily tally is persisted correctly.

        Given no tally exists for the email and date
        When a daily tally is saved
        Then the tally should be persisted in the database
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)
        category_counts = {
            "Marketing": 45,
            "Advertising": 32,
            "Personal": 12
        }
        total_emails = 89

        # Act
        result = repository.save_daily_tally(
            email_address,
            tally_date,
            category_counts,
            total_emails
        )

        # Assert
        self.assertIsNotNone(result, "save_daily_tally should return the created tally")
        self.assertEqual(result.email_address, email_address)
        self.assertEqual(result.tally_date, tally_date)
        self.assertEqual(result.total_emails, total_emails)
        self.assertIsNotNone(result.id, "Persisted tally should have an id")

    def test_save_new_daily_tally_stores_category_counts(self):
        """
        Test that category counts are stored correctly.

        When a daily tally is saved with category counts
        Then retrieving the tally should return the saved category data
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)
        category_counts = {
            "Marketing": 45,
            "Advertising": 32,
            "Personal": 12
        }
        total_emails = 89

        # Act
        repository.save_daily_tally(
            email_address,
            tally_date,
            category_counts,
            total_emails
        )

        # Retrieve and verify
        retrieved = repository.get_tally(email_address, tally_date)

        # Assert
        self.assertIsNotNone(retrieved, "Retrieved tally should not be None")
        self.assertEqual(retrieved.category_counts["Marketing"], 45)
        self.assertEqual(retrieved.category_counts["Advertising"], 32)
        self.assertEqual(retrieved.category_counts["Personal"], 12)


class TestUpdateExistingDailyTally(unittest.TestCase):
    """
    Scenario: Update an existing daily tally

    Given a tally exists for "test@gmail.com" on "2025-11-28"
    When the tally is updated with new category counts
    Then the tally should reflect the updated values
    And the updated_at timestamp should be newer than created_at

    The implementation should handle upsert semantics for tallies.
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

    def test_update_existing_tally_reflects_new_values(self):
        """
        Test that updating an existing tally replaces values.

        Given a tally exists with Marketing=20
        When the tally is updated with Marketing=45, Personal=10
        Then the tally should reflect the updated values
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)

        # Create initial tally
        initial_counts = {"Marketing": 20}
        repository.save_daily_tally(
            email_address,
            tally_date,
            initial_counts,
            20
        )

        # Act - Update with new values
        updated_counts = {"Marketing": 45, "Personal": 10}
        repository.save_daily_tally(
            email_address,
            tally_date,
            updated_counts,
            55
        )

        # Assert
        retrieved = repository.get_tally(email_address, tally_date)
        self.assertEqual(retrieved.category_counts["Marketing"], 45,
                        "Marketing count should be updated to 45")
        self.assertEqual(retrieved.category_counts["Personal"], 10,
                        "Personal count should be added as 10")
        self.assertEqual(retrieved.total_emails, 55,
                        "Total emails should be updated to 55")

    def test_update_tally_updates_timestamp(self):
        """
        Test that the updated_at timestamp is newer than created_at after update.

        Given a tally exists
        When the tally is updated
        Then updated_at should be newer than created_at
        """
        # Arrange
        from repositories.category_tally_repository import CategoryTallyRepository

        repository = CategoryTallyRepository(self.session)
        email_address = "test@gmail.com"
        tally_date = date(2025, 11, 28)

        # Create initial tally
        repository.save_daily_tally(
            email_address,
            tally_date,
            {"Marketing": 20},
            20
        )

        # Get created_at timestamp
        initial_tally = repository.get_tally(email_address, tally_date)
        created_at = initial_tally.created_at

        # Small delay to ensure timestamp difference
        time.sleep(0.1)

        # Act - Update the tally
        repository.save_daily_tally(
            email_address,
            tally_date,
            {"Marketing": 45},
            45
        )

        # Assert
        updated_tally = repository.get_tally(email_address, tally_date)
        self.assertGreater(
            updated_tally.updated_at,
            created_at,
            "updated_at timestamp should be newer than created_at after update"
        )


if __name__ == '__main__':
    unittest.main()
