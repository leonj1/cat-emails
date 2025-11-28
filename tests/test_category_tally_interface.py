"""
Tests for Category Tally Repository Interface.

Based on requirements in:
- prompts/001-bdd-repository-operations.md

These tests verify the ICategoryTallyRepository interface contract.

The implementation should:
- Create interface in repositories/category_tally_repository_interface.py
- Follow existing DatabaseRepositoryInterface pattern
- Define abstract methods for all repository operations
"""
import unittest


class TestCategoryTallyRepositoryInterface(unittest.TestCase):
    """
    Tests to verify the ICategoryTallyRepository interface contract.

    The interface should define:
    - save_daily_tally(email_address, tally_date, category_counts, total_emails)
    - get_tally(email_address, tally_date)
    - get_tallies_for_period(email_address, start_date, end_date)
    - get_aggregated_tallies(email_address, start_date, end_date)
    - delete_tallies_before(email_address, cutoff_date)
    """

    def test_interface_exists(self):
        """Test that the interface module can be imported."""
        from repositories.category_tally_repository_interface import ICategoryTallyRepository

        self.assertIsNotNone(ICategoryTallyRepository,
                            "ICategoryTallyRepository should be importable")

    def test_interface_defines_save_daily_tally(self):
        """Test that the interface defines save_daily_tally method."""
        from repositories.category_tally_repository_interface import ICategoryTallyRepository

        self.assertTrue(
            hasattr(ICategoryTallyRepository, 'save_daily_tally'),
            "ICategoryTallyRepository should define save_daily_tally method"
        )

    def test_interface_defines_get_tally(self):
        """Test that the interface defines get_tally method."""
        from repositories.category_tally_repository_interface import ICategoryTallyRepository

        self.assertTrue(
            hasattr(ICategoryTallyRepository, 'get_tally'),
            "ICategoryTallyRepository should define get_tally method"
        )

    def test_interface_defines_get_tallies_for_period(self):
        """Test that the interface defines get_tallies_for_period method."""
        from repositories.category_tally_repository_interface import ICategoryTallyRepository

        self.assertTrue(
            hasattr(ICategoryTallyRepository, 'get_tallies_for_period'),
            "ICategoryTallyRepository should define get_tallies_for_period method"
        )

    def test_interface_defines_get_aggregated_tallies(self):
        """Test that the interface defines get_aggregated_tallies method."""
        from repositories.category_tally_repository_interface import ICategoryTallyRepository

        self.assertTrue(
            hasattr(ICategoryTallyRepository, 'get_aggregated_tallies'),
            "ICategoryTallyRepository should define get_aggregated_tallies method"
        )

    def test_interface_defines_delete_tallies_before(self):
        """Test that the interface defines delete_tallies_before method."""
        from repositories.category_tally_repository_interface import ICategoryTallyRepository

        self.assertTrue(
            hasattr(ICategoryTallyRepository, 'delete_tallies_before'),
            "ICategoryTallyRepository should define delete_tallies_before method"
        )

    def test_interface_is_abstract(self):
        """Test that the interface is an abstract class (Protocol or ABC)."""
        from repositories.category_tally_repository_interface import ICategoryTallyRepository
        from abc import ABC
        from typing import Protocol

        # Interface should be either ABC or Protocol
        is_protocol_or_abc = (
            isinstance(ICategoryTallyRepository, type) and
            (issubclass(ICategoryTallyRepository, ABC) or
             hasattr(ICategoryTallyRepository, '_is_protocol'))
        )

        self.assertTrue(
            is_protocol_or_abc or hasattr(ICategoryTallyRepository, '__abstractmethods__'),
            "ICategoryTallyRepository should be an abstract class (ABC or Protocol)"
        )


if __name__ == '__main__':
    unittest.main()
