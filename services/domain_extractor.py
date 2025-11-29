"""
Domain extraction utility for email addresses.

This module provides functionality to extract and normalize domain names
from email addresses, handling various edge cases including:
- Plus addressing (user+tag@domain.com)
- Subdomains (mail.example.com)
- International TLDs (.co.jp, .co.uk, etc.)
- Long domain names
- Case normalization
"""


def extract_domain(email_address: str) -> str:
    """
    Extract domain from email address.

    Args:
        email_address: Full email address (e.g., "user@example.com")

    Returns:
        Domain part in lowercase (e.g., "example.com")

    Raises:
        ValueError: If email_address is invalid

    Examples:
        - user@example.com -> example.com
        - user+tag@sub.domain-name.co.uk -> sub.domain-name.co.uk
        - USER@DOMAIN.COM -> domain.com
    """
    # Strip leading/trailing whitespace
    email_address = email_address.strip()

    # Validate not empty
    if not email_address:
        raise ValueError("Invalid email address: cannot be empty")

    # Count @ symbols
    at_count = email_address.count("@")

    # Validate exactly one @ symbol
    if at_count == 0:
        raise ValueError("Invalid email address: missing @ symbol")

    if at_count > 1:
        raise ValueError("Invalid email address: multiple @ symbols")

    # Split on @ and extract domain
    parts = email_address.split("@")
    local_part = parts[0]
    domain = parts[1]

    # Validate domain is not empty
    if not domain:
        raise ValueError("Invalid email address: no domain after @")

    # Validate local part is not empty
    if not local_part:
        raise ValueError("Invalid email address: no local part before @")

    # Normalize to lowercase
    return domain.lower()
