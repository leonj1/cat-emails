"""Mock ELL package for testing."""
from unittest.mock import MagicMock
from functools import wraps

def init(*args, **kwargs):
    """Mock init function."""
    pass

def complete(*args, **kwargs):
    """Mock complete function."""
    # Check if the prompt contains specific keywords to determine the category
    prompt = kwargs.get('prompt', '')
    if 'categorize_email_ell_marketing' in prompt:
        return "Other"
    elif 'categorize_email_ell_generic' in prompt:
        return "Other"
    else:
        return "Other"

def simple(model=None, temperature=None):
    """Mock simple decorator."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return "Other"
        return wrapper
    return decorator

# Create mock objects
mock_client = MagicMock()
mock_client.complete.side_effect = complete

# Make the module itself callable
__call__ = MagicMock()
__call__.return_value = mock_client
