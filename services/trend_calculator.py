"""
Trend calculation utilities for email category analysis.

Pure functions for calculating trends from daily email counts,
following the trend classification rules from the BDD specification.

Trend Classification Rules (from spec section 4.4):
- Increasing: Second half average >= 15% higher than first half
- Decreasing: Second half average <= 15% lower than first half
- Stable: Change between -15% and +15%

Edge Cases Handled:
- Single/empty data: return 'stable'
- Zero first half average: if second half > 0 return 'increasing', else 'stable'
- Odd data points: split so first half is smaller (e.g., 7 points → first 3, second 4)
"""
from typing import List


def calculate_trend(daily_breakdown: List) -> str:
    """
    Calculate trend direction from daily breakdown data.

    Compares the average of the first half to the average of the second half
    to determine if the trend is increasing, decreasing, or stable.

    Args:
        daily_breakdown: List of DailyBreakdown objects with date and count fields

    Returns:
        str: One of 'increasing', 'decreasing', or 'stable'

    Example:
        >>> from models.recommendation_models import DailyBreakdown
        >>> from datetime import date
        >>> data = [
        ...     DailyBreakdown(date=date(2025, 11, 22), count=20),
        ...     DailyBreakdown(date=date(2025, 11, 23), count=40)
        ... ]
        >>> calculate_trend(data)
        'increasing'
    """
    # Edge case: empty or single data point
    if len(daily_breakdown) <= 1:
        return "stable"

    # Split data into first half and second half
    # For odd numbers, first half is smaller (e.g., 7 points → 3 and 4)
    midpoint = len(daily_breakdown) // 2
    first_half = daily_breakdown[:midpoint]
    second_half = daily_breakdown[midpoint:]

    # Calculate averages
    first_half_avg = sum(item.count for item in first_half) / len(first_half)
    second_half_avg = sum(item.count for item in second_half) / len(second_half)

    # Handle zero first half average edge case
    if first_half_avg == 0:
        if second_half_avg > 0:
            return "increasing"
        else:
            return "stable"

    # Calculate percentage change
    percentage_change = ((second_half_avg - first_half_avg) / first_half_avg) * 100

    # Apply threshold rules: >= 15% or <= -15%
    if percentage_change >= 15.0:
        return "increasing"
    elif percentage_change <= -15.0:
        return "decreasing"
    else:
        return "stable"


def calculate_trend_percentage_change(daily_breakdown: List) -> float:
    """
    Calculate the percentage change between first half and second half.

    Args:
        daily_breakdown: List of DailyBreakdown objects with date and count fields

    Returns:
        float: Percentage change (positive or negative)

    Example:
        >>> from models.recommendation_models import DailyBreakdown
        >>> from datetime import date
        >>> data = [
        ...     DailyBreakdown(date=date(2025, 11, 22), count=100),
        ...     DailyBreakdown(date=date(2025, 11, 23), count=150)
        ... ]
        >>> calculate_trend_percentage_change(data)
        50.0
    """
    # Edge case: empty or single data point
    if len(daily_breakdown) <= 1:
        return 0.0

    # Split data into first half and second half
    midpoint = len(daily_breakdown) // 2
    first_half = daily_breakdown[:midpoint]
    second_half = daily_breakdown[midpoint:]

    # Calculate averages
    first_half_avg = sum(item.count for item in first_half) / len(first_half)
    second_half_avg = sum(item.count for item in second_half) / len(second_half)

    # Handle zero first half average edge case
    if first_half_avg == 0:
        # If second half is also zero, no change
        if second_half_avg == 0:
            return 0.0
        # If second half has values, we can't calculate percentage but it's clearly an increase
        # Return a large positive number to indicate significant increase
        return 100.0

    # Calculate and return percentage change
    percentage_change = ((second_half_avg - first_half_avg) / first_half_avg) * 100
    return percentage_change


def generate_trend_factor(trend_direction: str, percentage_change: float) -> str:
    """
    Generate a human-readable trend factor message.

    Args:
        trend_direction: One of 'increasing', 'decreasing', or 'stable'
        percentage_change: The percentage change value

    Returns:
        str: Human-readable trend description

    Example:
        >>> generate_trend_factor("increasing", 45.2)
        'Trending upward: 45.2% increase over period'
    """
    if trend_direction == "increasing":
        return f"Trending upward: {abs(percentage_change):.1f}% increase over period"
    elif trend_direction == "decreasing":
        return f"Trending downward: {abs(percentage_change):.1f}% decrease over period"
    else:
        return f"Stable trend: {abs(percentage_change):.1f}% variation over period"
