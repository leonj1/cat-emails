"""
Service class for complex statistical calculations.
Extracted from SimpleCalculator.calculate_complex method.
"""
from typing import Dict, List, Union


class SimpleCalculatorCalculateComplexService:
    """Service for performing complex statistical calculations on numbers."""

    def __init__(self):
        """Initialize the service with no external dependencies."""
        pass

    def calculate_complex(self, numbers: List[Union[int, float]]) -> Dict:
        """
        Perform comprehensive statistical calculations on a list of numbers.

        Args:
            numbers: List of numeric values to analyze

        Returns:
            Dictionary containing statistical metrics or error information
        """
        # Validate input
        validation_error = self._validate_input(numbers)
        if validation_error:
            return validation_error

        # Perform calculations
        total_sum = sum(numbers)
        average = self._calculate_average(total_sum, len(numbers))
        minimum = min(numbers)
        maximum = max(numbers)
        median = self._calculate_median(numbers)
        variance = self._calculate_variance(numbers, average)
        std_dev = variance ** 0.5

        # Build result
        result = self._build_result(
            total_sum, average, minimum, maximum,
            median, variance, std_dev, len(numbers)
        )

        return result

    def _validate_input(self, numbers: List) -> Union[Dict, None]:
        """Validate input numbers list."""
        if not numbers:
            return {"error": "No numbers provided"}

        if not all(isinstance(n, (int, float)) for n in numbers):
            return {"error": "All inputs must be numbers"}

        return None

    def _calculate_average(self, total: float, count: int) -> float:
        """Calculate average from total and count."""
        return total / count

    def _calculate_median(self, numbers: List[Union[int, float]]) -> float:
        """Calculate median value from list of numbers."""
        sorted_nums = sorted(numbers)
        mid = len(sorted_nums) // 2

        if len(sorted_nums) % 2 == 0:
            return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2
        else:
            return sorted_nums[mid]

    def _calculate_variance(
        self, numbers: List[Union[int, float]], average: float
    ) -> float:
        """Calculate variance from numbers and their average."""
        return sum((x - average) ** 2 for x in numbers) / len(numbers)

    def _build_result(
        self, total_sum: float, average: float, minimum: float,
        maximum: float, median: float, variance: float,
        std_dev: float, count: int
    ) -> Dict:
        """Build the result dictionary."""
        return {
            "sum": total_sum,
            "average": average,
            "min": minimum,
            "max": maximum,
            "median": median,
            "variance": variance,
            "std_dev": std_dev,
            "count": count
        }
