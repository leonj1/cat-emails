"""Mock ell module for testing."""

def init(**kwargs):
    pass

def simple(*args, **kwargs):
    def decorator(func):
        def wrapper(*args, **kwargs):
            return "Newsletter"  # Default category for testing
        return wrapper
    return decorator
