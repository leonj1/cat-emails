from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TypedDict, Union


class SimpleEmailCategory(str, Enum):
    """Three basic categories for commercial email classification."""
    ADVERTISING = "Advertising"
    MARKETING = "Marketing"
    WANTS_MONEY = "Wants-Money"


class CategoryError(TypedDict):
    """Typed error response for categorization failures (using typing.TypedDict)."""
    error: str
    detail: str


# Result type for the categorization operation
CategoryResult = Union[SimpleEmailCategory, CategoryError]


class CategorizeEmails(ABC):
    """
    Interface for categorizing an email's contents into one of three categories.

    Implementations should return a SimpleEmailCategory value on success. If the
    categorization cannot be performed (e.g., model error, invalid input), they
    should return a CategoryError typed response rather than raise.
    """

    @abstractmethod
    def category(self, email_contents: str) -> CategoryResult:  # pragma: no cover - interface only
        """
        Determine an email category from the provided contents.

        Args:
            email_contents: Raw email contents as a string.

        Returns:
            - SimpleEmailCategory: one of "Advertising", "Marketing", or "Wants-Money".
            - CategoryError: a typed error response if categorization fails.
        """
        ...

