"""
Tests for Category Tally Pydantic models.

Based on requirements in:
- prompts/001-bdd-repository-operations.md

These tests verify the Pydantic models that represent:
- DailyCategoryTally: Daily tally data
- AggregatedCategoryTally: Aggregated data across date range
- CategorySummaryItem: Summary for a single category

The implementation should:
- Create models in models/category_tally_models.py
- Follow existing Pydantic model patterns from models/account_models.py
"""
import unittest
from datetime import datetime, date


class TestDailyCategoryTallyModel(unittest.TestCase):
    """
    Tests for the DailyCategoryTally Pydantic model.

    The model should have fields:
    - id: Optional[int]
    - email_address: str
    - tally_date: date
    - category_counts: Dict[str, int]
    - total_emails: int
    - created_at: datetime
    - updated_at: datetime
    """

    def test_model_accepts_valid_data(self):
        """Test that model accepts valid data."""
        from models.category_tally_models import DailyCategoryTally

        tally = DailyCategoryTally(
            email_address="test@gmail.com",
            tally_date=date(2025, 11, 28),
            category_counts={"Marketing": 45, "Personal": 12},
            total_emails=57,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.assertEqual(tally.email_address, "test@gmail.com")
        self.assertEqual(tally.tally_date, date(2025, 11, 28))
        self.assertEqual(tally.total_emails, 57)
        self.assertEqual(tally.category_counts["Marketing"], 45)

    def test_model_has_required_fields(self):
        """Test that model has all required fields."""
        from models.category_tally_models import DailyCategoryTally

        # Get model field names
        field_names = DailyCategoryTally.model_fields.keys()

        required_fields = [
            'email_address',
            'tally_date',
            'category_counts',
            'total_emails',
            'created_at',
            'updated_at'
        ]

        for field in required_fields:
            self.assertIn(field, field_names,
                         f"DailyCategoryTally should have '{field}' field")

    def test_model_accepts_empty_category_counts(self):
        """Test that model accepts empty category_counts."""
        from models.category_tally_models import DailyCategoryTally

        tally = DailyCategoryTally(
            email_address="test@gmail.com",
            tally_date=date(2025, 11, 28),
            category_counts={},
            total_emails=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.assertEqual(len(tally.category_counts), 0)
        self.assertEqual(tally.total_emails, 0)

    def test_model_optional_id_field(self):
        """Test that id field is optional (None for new records)."""
        from models.category_tally_models import DailyCategoryTally

        # Create without id
        tally = DailyCategoryTally(
            email_address="test@gmail.com",
            tally_date=date(2025, 11, 28),
            category_counts={"Marketing": 45},
            total_emails=45,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # id should be None or not set
        self.assertTrue(
            not hasattr(tally, 'id') or tally.id is None,
            "id should be optional/None for new records"
        )


class TestCategorySummaryItemModel(unittest.TestCase):
    """
    Tests for the CategorySummaryItem Pydantic model.

    The model should have fields:
    - category: str
    - total_count: int
    - percentage: float
    - daily_average: float
    - trend: Optional[str]
    """

    def test_category_summary_item_accepts_valid_data(self):
        """Test that CategorySummaryItem accepts valid data."""
        from models.category_tally_models import CategorySummaryItem

        summary = CategorySummaryItem(
            category="Marketing",
            total_count=245,
            percentage=66.6,
            daily_average=35.0,
            trend=None
        )

        self.assertEqual(summary.category, "Marketing")
        self.assertEqual(summary.total_count, 245)
        self.assertEqual(summary.percentage, 66.6)
        self.assertEqual(summary.daily_average, 35.0)

    def test_category_summary_item_has_required_fields(self):
        """Test that CategorySummaryItem has all required fields."""
        from models.category_tally_models import CategorySummaryItem

        field_names = CategorySummaryItem.model_fields.keys()

        required_fields = [
            'category',
            'total_count',
            'percentage',
            'daily_average'
        ]

        for field in required_fields:
            self.assertIn(field, field_names,
                         f"CategorySummaryItem should have '{field}' field")

    def test_category_summary_item_trend_is_optional(self):
        """Test that trend field is optional."""
        from models.category_tally_models import CategorySummaryItem

        # Create without trend
        summary = CategorySummaryItem(
            category="Marketing",
            total_count=245,
            percentage=66.6,
            daily_average=35.0
        )

        # trend should be None or not required
        self.assertTrue(
            not hasattr(summary, 'trend') or summary.trend is None,
            "trend should be optional"
        )


class TestAggregatedCategoryTallyModel(unittest.TestCase):
    """
    Tests for the AggregatedCategoryTally Pydantic model.

    The model should have fields:
    - email_address: str
    - start_date: date
    - end_date: date
    - total_emails: int
    - days_with_data: int
    - category_summaries: List[CategorySummaryItem]
    """

    def test_model_accepts_valid_aggregation_data(self):
        """Test that AggregatedCategoryTally accepts valid data."""
        from models.category_tally_models import (
            AggregatedCategoryTally,
            CategorySummaryItem
        )

        summary_item = CategorySummaryItem(
            category="Marketing",
            total_count=245,
            percentage=66.6,
            daily_average=35.0,
            trend=None
        )

        aggregation = AggregatedCategoryTally(
            email_address="test@gmail.com",
            start_date=date(2025, 11, 22),
            end_date=date(2025, 11, 28),
            total_emails=368,
            days_with_data=7,
            category_summaries=[summary_item]
        )

        self.assertEqual(aggregation.email_address, "test@gmail.com")
        self.assertEqual(aggregation.total_emails, 368)
        self.assertEqual(aggregation.days_with_data, 7)
        self.assertEqual(len(aggregation.category_summaries), 1)

    def test_aggregated_model_has_required_fields(self):
        """Test that AggregatedCategoryTally has all required fields."""
        from models.category_tally_models import AggregatedCategoryTally

        field_names = AggregatedCategoryTally.model_fields.keys()

        required_fields = [
            'email_address',
            'start_date',
            'end_date',
            'total_emails',
            'days_with_data',
            'category_summaries'
        ]

        for field in required_fields:
            self.assertIn(field, field_names,
                         f"AggregatedCategoryTally should have '{field}' field")

    def test_aggregated_model_accepts_empty_summaries(self):
        """Test that model accepts empty category_summaries."""
        from models.category_tally_models import AggregatedCategoryTally

        aggregation = AggregatedCategoryTally(
            email_address="empty@gmail.com",
            start_date=date(2025, 11, 22),
            end_date=date(2025, 11, 28),
            total_emails=0,
            days_with_data=0,
            category_summaries=[]
        )

        self.assertEqual(len(aggregation.category_summaries), 0)
        self.assertEqual(aggregation.total_emails, 0)
        self.assertEqual(aggregation.days_with_data, 0)


if __name__ == '__main__':
    unittest.main()
