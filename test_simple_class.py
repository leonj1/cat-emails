"""
Simple test class for quick validation of refactoring agent.
"""


class SimpleCalculator:
    """A simple calculator with one large function."""

    def __init__(self):
        self.history = []

    def calculate_complex(self, numbers: list) -> dict:
        """
        Main calculation function - this is large (>30 lines).
        This should be identified as the primary function.
        """
        # Validate input
        if not numbers:
            return {"error": "No numbers provided"}

        if not all(isinstance(n, (int, float)) for n in numbers):
            return {"error": "All inputs must be numbers"}

        # Calculate sum
        total_sum = sum(numbers)

        # Calculate average
        average = total_sum / len(numbers)

        # Find min and max
        minimum = min(numbers)
        maximum = max(numbers)

        # Calculate median
        sorted_nums = sorted(numbers)
        mid = len(sorted_nums) // 2
        if len(sorted_nums) % 2 == 0:
            median = (sorted_nums[mid - 1] + sorted_nums[mid]) / 2
        else:
            median = sorted_nums[mid]

        # Calculate variance
        variance = sum((x - average) ** 2 for x in numbers) / len(numbers)

        # Calculate standard deviation
        std_dev = variance ** 0.5

        # Store in history
        result = {
            "sum": total_sum,
            "average": average,
            "min": minimum,
            "max": maximum,
            "median": median,
            "variance": variance,
            "std_dev": std_dev,
            "count": len(numbers)
        }

        self.history.append(result)

        return result
