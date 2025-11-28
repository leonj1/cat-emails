"""
Category Aggregation Configuration Interface.

This interface defines the contract for configuration values used in
email category aggregation and blocking recommendations.
"""
from abc import ABC, abstractmethod
from typing import List


class ICategoryAggregationConfig(ABC):
    """
    Abstract interface for category aggregation configuration.

    Provides configuration values for thresholds, minimums, and exclusions
    used in the blocking recommendation algorithm.
    """

    @abstractmethod
    def get_recommendation_threshold_percentage(self) -> float:
        """
        Get the minimum percentage threshold for recommendations.

        Categories below this percentage of total emails will not be
        recommended for blocking (unless they meet higher strength thresholds).

        Returns:
            Threshold percentage (e.g., 10.0 for 10%)
        """
        pass

    @abstractmethod
    def get_minimum_email_count(self) -> int:
        """
        Get the minimum email count for recommendations.

        Categories with fewer emails than this threshold will not be
        recommended for blocking, regardless of percentage.

        Returns:
            Minimum email count threshold
        """
        pass

    @abstractmethod
    def get_excluded_categories(self) -> List[str]:
        """
        Get the list of categories excluded from blocking recommendations.

        These categories will never be recommended for blocking, regardless
        of their volume or percentage (e.g., Personal, Work-related).

        Returns:
            List of excluded category names
        """
        pass

    @abstractmethod
    def get_retention_days(self) -> int:
        """
        Get the data retention period in days.

        Defines how long to keep historical tally data before cleanup.

        Returns:
            Retention period in days
        """
        pass
