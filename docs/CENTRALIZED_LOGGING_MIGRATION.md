# Centralized Logging Migration Guide

## Overview
The Cat-Emails project now uses a centralized logging system via `CentralLoggingService`. This ensures all logs are sent to both stdout and a remote logging service (when configured).

## Benefits
✅ **Dual Output**: All logs go to both stdout AND remote logging service  
✅ **Single Configuration Point**: Configure logging once for the entire application  
✅ **Third-party Library Capture**: Even logs from external libraries are captured  
✅ **Drop-in Replacement**: Minimal code changes needed  
✅ **Async Remote Logging**: Doesn't block the application  
✅ **Automatic Retry & Queue Management**: Handles network issues gracefully

## Migration Steps

### For Main Entry Points (e.g., api_service.py, gmail_fetcher.py)

**OLD CODE:**
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

**NEW CODE:**
```python
import logging
from utils.logger import initialize_central_logging, get_logger, shutdown_logging

# Initialize central logging at application startup
initialize_central_logging(
    log_level=logging.INFO,
    enable_remote=True  # Enable sending to remote collector if configured
)

# Get logger instance - same API as before
logger = get_logger(__name__)

# Optional: Add graceful shutdown (e.g., in FastAPI shutdown event)
@app.on_event("shutdown")
async def shutdown_event():
    shutdown_logging(timeout=5.0)
```

### For Service/Module Files

**OLD CODE:**
```python
import logging

logger = logging.getLogger(__name__)
```

**NEW CODE:**
```python
from utils.logger import get_logger

logger = get_logger(__name__)
```

That's it! The `get_logger` function will automatically use the centralized logging system.

## Environment Configuration

To enable remote logging, set these environment variables:

```bash
# Remote logging collector configuration
export LOGS_COLLECTOR_API="http://your-logging-api.example.com"
export LOGS_COLLECTOR_TOKEN="your-auth-token"

# Application metadata
export APP_NAME="cat-emails"
export APP_VERSION="1.0.0"
export APP_ENVIRONMENT="production"
```

If these aren't set, logging will only go to stdout (useful for development).

## Testing Your Migration

Run the test script to verify centralized logging works:

```bash
python3 test_centralized_logging.py
```

Run the example to see the difference:

```bash
python3 examples/centralized_logging_example.py
```

## Important Notes

1. **Initialize Once**: Call `initialize_central_logging()` only once at application startup
2. **Auto-initialization**: If not explicitly initialized, it will auto-initialize with defaults on first use
3. **Backward Compatibility**: Standard `logging.getLogger()` calls are automatically captured
4. **Performance**: Remote logging is async and won't block your application
5. **Graceful Degradation**: If remote logging fails, stdout logging continues working

## Implementation Details

The centralized logging system:
- Uses `CentralLoggingService` from `services/logging_service.py`
- Creates logs via `LogsCollectorClient` for remote sending
- Configures the root logger to capture all Python logging
- Provides a simple `get_logger()` function as a drop-in replacement

## Files Updated in This Migration

1. **Created:**
   - `/utils/logger.py` - Central logger configuration module
   - `/examples/centralized_logging_example.py` - Usage examples
   - `/test_centralized_logging.py` - Test suite

2. **Updated:**
   - `/api_service.py` - Updated to use centralized logging

## Next Steps

To complete the migration across the entire project:

1. Update all main entry points (gmail_fetcher.py, etc.) to use `initialize_central_logging()`
2. Replace `logging.getLogger()` with `get_logger()` in service files
3. Add `shutdown_logging()` to graceful shutdown handlers
4. Configure environment variables for remote logging in production

## Questions?

See the example files or test suite for more detailed usage patterns.
