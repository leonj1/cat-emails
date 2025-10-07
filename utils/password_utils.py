"""
Password utility functions for the Cat-Emails project.
"""
from typing import Optional


def mask_password(password: Optional[str]) -> Optional[str]:
    """
    Mask a password showing only first 2 and last 2 characters.

    Args:
        password: The password to mask

    Returns:
        Masked password string or None if password is None/empty
    """
    if not password:
        return None

    # If password is too short, return all asterisks
    if len(password) <= 4:
        return "*" * len(password)

    # Show first 2, asterisks in middle, last 2
    first_two = password[:2]
    last_two = password[-2:]
    middle_stars = "*" * (len(password) - 4)

    return f"{first_two}{middle_stars}{last_two}"