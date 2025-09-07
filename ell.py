# Minimal stub for the 'ell' library used in gmail_fetcher.py during tests.
# Provides no-op init and a pass-through decorator for @ell.simple.

def init(verbose=False, store=None):
    return None

def simple(model=None, temperature=None):
    def decorator(func):
        return func
    return decorator
