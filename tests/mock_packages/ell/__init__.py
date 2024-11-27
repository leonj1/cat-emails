"""Mock ELL package for testing."""
from unittest.mock import MagicMock

def init(*args, **kwargs):
    """Mock init function."""
    pass

def complete(*args, **kwargs):
    """Mock complete function."""
    return "Other"

# Create mock objects
mock_client = MagicMock()
mock_client.complete.return_value = "Other"

# Make the module itself callable
__call__ = MagicMock()
__call__.return_value = mock_client
