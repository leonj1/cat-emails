"""Mock email scanner consumer module for testing."""
import mock_ell as ell
import unittest.mock as mock

# Mock openai module
openai = mock.MagicMock()
openai.Client = mock.MagicMock()

def categorize_email_ell_marketing(contents: str):
    """Mock categorization function."""
    if not contents:
        return None
    return "Newsletter"

def categorize_email_ell_marketing2(contents: str):
    """Mock second categorization function."""
    if not contents:
        return None
    # For testing long category names
    if len(contents) > 30:
        return "Newsletter"
    return None
