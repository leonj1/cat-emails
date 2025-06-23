from enum import Enum, auto
from difflib import get_close_matches

class EmailCategory(Enum):
    FINANCIAL = auto()
    ADMINISTRATIVE = auto()
    HEALTH_WELLNESS = auto()
    EDUCATION = auto()
    PERSONAL_COMMITMENTS = auto()
    HOME_MANAGEMENT = auto()
    WORK_RELATED = auto()
    CONSUMER_ACTION = auto()
    SUBSCRIPTIONS_MEMBERSHIPS = auto()
    PERSONAL_CORRESPONDENCE = auto()

    @classmethod
    def from_string(cls, category_string: str, fuzzy_match: bool = False) -> 'EmailCategory':
        """
        Convert a string to an EmailCategory enum.
        The conversion is case-insensitive and ignores spaces and underscores.
        If fuzzy_match is True, it will return the closest matching category.
        """
        category_string = category_string.lower().replace(' ', '').replace('_', '')
        for category in cls:
            if category.name.lower().replace('_', '') == category_string:
                return category
        
        if fuzzy_match:
            return cls.fuzzy_match(category_string)
        
        raise ValueError(f"'{category_string}' is not a valid EmailCategory")

    @classmethod
    def fuzzy_match(cls, category_string: str) -> 'EmailCategory':
        """
        Find the closest matching EmailCategory for the given string.
        """
        valid_categories = [category.name.lower().replace('_', '') for category in cls]
        matches = get_close_matches(category_string, valid_categories, n=1, cutoff=0.6)
        
        if matches:
            for category in cls:
                if category.name.lower().replace('_', '') == matches[0]:
                    return category
        
        raise ValueError(f"No close match found for '{category_string}'")

    @classmethod
    def all_categories(cls, separator: str = ", ") -> str:
        """
        Return all category names as a single joined string.
        """
        return separator.join(category.name for category in cls)

# # Example usage
# if __name__ == "__main__":
#     # Using the enum
#     print(EmailCategory.FINANCIAL)
#     print(EmailCategory.HEALTH_WELLNESS)

#     # Converting strings to enums
#     print(EmailCategory.from_string("Financial"))
#     print(EmailCategory.from_string("Health Wellness"))
#     print(EmailCategory.from_string("personal_commitments"))

#     # Using fuzzy matching
#     print(EmailCategory.from_string("finance", fuzzy_match=True))
#     print(EmailCategory.from_string("health", fuzzy_match=True))
#     print(EmailCategory.from_string("education stuff", fuzzy_match=True))

#     # Get all categories as a string
#     print("\nAll categories:")
#     print(EmailCategory.all_categories())

#     # Get all categories with a custom separator
#     print("\nAll categories (custom separator):")
#     print(EmailCategory.all_categories(" | "))

#     # This will raise a ValueError
#     # print(EmailCategory.from_string("Invalid Category"))

#     # This will also raise a ValueError (no close match)
#     # print(EmailCategory.from_string("xyz", fuzzy_match=True))