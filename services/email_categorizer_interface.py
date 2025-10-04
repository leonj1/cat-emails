from abc import ABC, abstractmethod


class EmailCategorizerInterface(ABC):
    """Interface for email categorization services."""

    @abstractmethod
    def categorize(self, contents: str, model: str) -> str:
        """
        Categorize email content using an LLM model.

        Args:
            contents: The email content to categorize
            model: The model identifier to use for categorization

        Returns:
            str: The category name (e.g., "Marketing", "Personal", "Other", etc.)
        """
        pass
