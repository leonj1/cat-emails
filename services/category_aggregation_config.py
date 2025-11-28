"""
Category Aggregation Configuration Implementation.

Provides configuration values for email category aggregation and
blocking recommendations with sensible defaults.
"""
from typing import List

from services.interfaces.category_aggregation_config_interface import (
    ICategoryAggregationConfig
)


class CategoryAggregationConfig(ICategoryAggregationConfig):
    """
    Implementation of category aggregation configuration.

    Provides configurable thresholds and exclusions with default values
    per the BDD specification (section 8).

    Default values:
    - threshold_percentage: 10.0
    - minimum_count: 10
    - excluded_categories: ["Personal", "Work-related", "Financial-Notification"]
    - retention_days: 30
    """

    def __init__(
        self,
        threshold_percentage: float = 10.0,
        minimum_count: int = 10,
        excluded_categories: List[str] | None = None,
        retention_days: int = 30
    ):
        """
        Initialize configuration with custom or default values.

        Args:
            threshold_percentage: Minimum percentage for recommendations (default: 10.0)
            minimum_count: Minimum email count for recommendations (default: 10)
            excluded_categories: Categories to never recommend (default: Personal, Work-related, Financial-Notification)
            retention_days: Data retention period in days (default: 30)
        """
        self._threshold_percentage = threshold_percentage
        self._minimum_count = minimum_count
        self._excluded_categories = excluded_categories or [
            "Personal",
            "Work-related",
            "Financial-Notification"
        ]
        self._retention_days = retention_days

    def get_recommendation_threshold_percentage(self) -> float:
        """
        Get the minimum percentage threshold for recommendations.

        Returns:
            Threshold percentage (default: 10.0)
        """
        return self._threshold_percentage

    def get_minimum_email_count(self) -> int:
        """
        Get the minimum email count for recommendations.

        Returns:
            Minimum email count threshold (default: 10)
        """
        return self._minimum_count

    def get_excluded_categories(self) -> List[str]:
        """
        Get the list of categories excluded from blocking recommendations.

        Returns:
            List of excluded category names
        """
        return self._excluded_categories.copy()

    def get_retention_days(self) -> int:
        """
        Get the data retention period in days.

        Returns:
            Retention period in days (default: 30)
        """
        return self._retention_days
