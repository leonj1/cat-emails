"""
Fake implementation of EmailCategorizerInterface for testing purposes.

This mock class allows testing email categorization logic without requiring
actual LLM model calls or external service dependencies.
"""
from services.email_categorizer_interface import EmailCategorizerInterface


class FakeEmailCategorizer(EmailCategorizerInterface):
    """Fake email categorizer for testing that returns predefined categories."""

    def __init__(self, default_category: str = "Other"):
        """
        Initialize the fake email categorizer.

        Args:
            default_category: The default category to return for all emails
        """
        self.default_category = default_category
        self.categorization_calls: list[tuple[str, str]] = []  # (contents, model)
        self.category_mappings: dict[str, str] = {}  # maps content keywords to categories

    def categorize(self, contents: str, model: str) -> str:
        """
        Categorize email content using predefined rules.

        Args:
            contents: The email content to categorize
            model: The model identifier (tracked but not used in fake)

        Returns:
            str: The category name based on configured mappings or default
        """
        # Track the call
        self.categorization_calls.append((contents, model))

        # Check if we have a specific mapping for this content
        for keyword, category in self.category_mappings.items():
            if keyword.lower() in contents.lower():
                return category

        # Return default category
        return self.default_category

    def set_category_mapping(self, keyword: str, category: str) -> None:
        """
        Configure a keyword-to-category mapping for testing.

        Args:
            keyword: A keyword to search for in email contents
            category: The category to return when keyword is found
        """
        self.category_mappings[keyword] = category

    def clear_category_mappings(self) -> None:
        """Clear all keyword-to-category mappings."""
        self.category_mappings.clear()

    def get_categorization_count(self) -> int:
        """
        Get the number of times categorize() was called.

        Returns:
            int: Number of categorization calls made
        """
        return len(self.categorization_calls)

    def get_last_categorization_call(self) -> tuple[str, str] | None:
        """
        Get the arguments from the last categorize() call.

        Returns:
            tuple of (contents, model) or None if no calls have been made
        """
        if self.categorization_calls:
            return self.categorization_calls[-1]
        return None

    def clear_tracking(self) -> None:
        """Clear all tracking data (categorization calls)."""
        self.categorization_calls.clear()
