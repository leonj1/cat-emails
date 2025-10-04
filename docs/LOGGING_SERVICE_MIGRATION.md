# Logging Service Migration Guide

This guide explains how to migrate from direct `logging` usage to the new `CentralLoggingService` with `LogsCollectorClient` interface.

## What Changed

The `CentralLoggingService` now requires a `LogsCollectorClient` interface in its constructor, making it more testable and flexible:

**Before:**
```python
from services.logging_service import CentralLoggingService

# Old way - reads env vars internally
logger = CentralLoggingService(
    logger_name="my-app",
    enable_remote=True
)
```

**After:**
```python
from services.logging_factory import create_logging_service

# New way - uses factory function
logger = create_logging_service(
    logger_name="my-app",
    enable_remote=True
)
```

## Migration Options

### Option 1: Use the Factory Function (Recommended)

The easiest migration path is to use `create_logging_service()`:

```python
from services.logging_factory import create_logging_service

# Simple usage
logger = create_logging_service()

# With custom configuration
logger = create_logging_service(
    logger_name="my-service",
    log_level=logging.DEBUG,
    enable_remote=True
)
```

### Option 2: Inject Client Manually

For more control, create and inject the client yourself:

```python
from services.logging_service import CentralLoggingService
from clients.logs_collector_client import RemoteLogsCollectorClient
import os

# Create client
client = RemoteLogsCollectorClient(
    logs_collector_url=os.getenv("LOGS_COLLECTOR_API"),
    application_name="my-app",
    logs_collector_token=os.getenv("LOGS_COLLECTOR_TOKEN")
)

# Create service with client
logger = CentralLoggingService(
    logs_collector_client=client,
    logger_name="my-app"
)
```

### Option 3: Testing with Fake Client

For tests, use the `FakeLogsCollectorClient`:

```python
from services.logging_service import CentralLoggingService
from clients.logs_collector_client import FakeLogsCollectorClient

# Create fake client for testing
fake_client = FakeLogsCollectorClient(
    logs_collector_url="http://localhost",
    application_name="test-app",
    logs_collector_token="fake-token"
)

# Use in tests
logger = CentralLoggingService(
    logs_collector_client=fake_client,
    enable_remote=False  # Optional: disable queue
)
```

## Example Migration

### Before (Old Code)

```python
import logging

# Standard logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)

logger.info("Processing email")
logger.error("Failed to connect")
```

### After (New Code)

```python
from services.logging_factory import create_logging_service

# Create centralized logger
logger = create_logging_service(
    logger_name=__name__,
    log_level=logging.INFO
)

# Same interface, but logs go to both stdout and remote collector
logger.info("Processing email")
logger.error("Failed to connect")
```

## Environment Variables

Make sure these environment variables are set:

```bash
# Required for remote logging
export LOGS_COLLECTOR_API="https://logs-collector-production.up.railway.app"
export LOGS_COLLECTOR_TOKEN="your-bearer-token"

# Optional
export APP_NAME="cat-emails"
export APP_VERSION="1.0.0"
export APP_ENVIRONMENT="production"
```

## Files to Update

Search for these patterns in your codebase:

1. **Direct logging usage:**
   ```python
   logger = logging.getLogger(__name__)
   ```
   Replace with:
   ```python
   from services.logging_factory import create_logging_service
   logger = create_logging_service(logger_name=__name__)
   ```

2. **Old CentralLoggingService usage:**
   ```python
   from services.logging_service import CentralLoggingService
   logger = CentralLoggingService()
   ```
   Replace with:
   ```python
   from services.logging_factory import create_logging_service
   logger = create_logging_service()
   ```

## Benefits

1. **Testability**: Easy to inject fake clients in tests
2. **Flexibility**: Swap implementations without changing code
3. **Consistency**: Unified logging across the codebase
4. **Remote logging**: Automatic log forwarding to central collector
5. **Trace IDs**: Built-in support for distributed tracing

## Example Files

- **Factory usage**: `services/logging_factory.py`
- **Client interface**: `clients/logs_collector_client.py`
- **Examples**: `examples/logging_service_example.py`
- **Tests**: `tests/test_logging_service.py`

## Quick Reference

```python
# Import
from services.logging_factory import create_logging_service

# Create logger
logger = create_logging_service(logger_name="my-service")

# Use it
logger.debug("Debug message")
logger.info("Info message", trace_id="req-123")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")

# Generic log method
logger.log(logging.INFO, "Custom level", trace_id="trace-456")
```
