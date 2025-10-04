# Central Logging Service

A robust logging service that logs to both stdout and a central logging collector API.

## Features

- **Dual Output**: Logs to both stdout (via Python's logging module) and a remote logging API
- **Automatic Failover**: Gracefully degrades to local-only logging if remote service is unavailable
- **Distributed Tracing**: Support for trace IDs to correlate logs across services
- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Type-Safe**: Uses Pydantic models for request/response validation
- **Non-Blocking**: Remote logging failures don't interrupt application flow
- **Configurable**: Environment variable based configuration

## Installation

The service requires the following packages (already in requirements.txt):
```bash
pip install requests pydantic
```

## Configuration

Configure the service using environment variables:

### Required Variables (for remote logging)
```bash
export LOGS_COLLECTOR_API="https://logs-collector-production.up.railway.app"
export LOGS_COLLECTOR_TOKEN="your-bearer-token-here"
```

### Optional Variables
```bash
export APP_NAME="cat-emails"           # Default: "cat-emails"
export APP_VERSION="1.0.0"             # Default: "1.0.0"
export APP_ENVIRONMENT="production"     # Default: "production"
```

## Usage

### Basic Usage

```python
from services.logging_service import CentralLoggingService

# Initialize the service
logger = CentralLoggingService()

# Log at different levels
logger.debug("Debugging information")
logger.info("Informational message")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical failure")
```

### With Trace IDs (Distributed Tracing)

```python
from services.logging_service import CentralLoggingService

logger = CentralLoggingService()

# Use trace IDs to correlate related log messages
request_id = "req-12345"
logger.info("Processing started", trace_id=request_id)
logger.info("Database query executed", trace_id=request_id)
logger.info("Processing complete", trace_id=request_id)
```

### Local-Only Logging

```python
from services.logging_service import CentralLoggingService

# Disable remote logging (useful for development/testing)
logger = CentralLoggingService(enable_remote=False)
logger.info("This only goes to stdout")
```

### Custom Logger Name and Level

```python
import logging
from services.logging_service import CentralLoggingService

logger = CentralLoggingService(
    logger_name="my-service",
    log_level=logging.DEBUG
)
```

## API Integration

The service sends logs to the central logging collector with the following payload:

```json
{
  "application_name": "cat-emails",
  "environment": "production",
  "hostname": "server-hostname",
  "level": "info",
  "message": "User logged in successfully",
  "timestamp": "2024-01-15T14:30:00Z",
  "trace_id": "abc123xyz",
  "version": "1.0.0"
}
```

### API Endpoint
- **URL**: `POST /logs`
- **Authentication**: Bearer token in `Authorization` header
- **Success Response**: HTTP 202 Accepted
- **Content-Type**: application/json

## Error Handling

The service handles various error scenarios gracefully:

1. **Missing Configuration**: Falls back to local-only logging
2. **Network Timeouts**: Logs warning and continues (5-second timeout)
3. **API Errors**: Logs warning and continues
4. **Invalid Responses**: Logs warning and continues

All errors in remote logging are logged locally but don't interrupt application flow.

## Testing

Run the unit tests:

```bash
# Using Docker (recommended)
make test

# Or directly with Python
python -m unittest tests.test_logging_service
```

Run the example script:

```bash
# Without remote logging
python examples/logging_service_example.py

# With remote logging
export LOGS_COLLECTOR_API="https://logs-collector-production.up.railway.app"
export LOGS_COLLECTOR_TOKEN="your-token"
python examples/logging_service_example.py
```

## Models

### LogLevel Enum
```python
class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
```

### LogPayload
```python
class LogPayload(BaseModel):
    application_name: str
    environment: str
    hostname: str
    level: LogLevel
    message: str
    timestamp: str  # ISO 8601 format
    trace_id: str
    version: str
```

## Integration with Existing Code

To integrate with existing code using standard Python logging:

```python
from services.logging_service import CentralLoggingService
import logging

# Initialize central logger
central_logger = CentralLoggingService(logger_name="my-app")

# Use it like standard Python logging
central_logger.info("Application started")
central_logger.error("An error occurred")

# Or use the generic log() method
central_logger.log(logging.WARNING, "Custom warning message")
```

## Best Practices

1. **Use Trace IDs**: Always provide trace IDs for request-scoped logs to enable correlation
2. **Appropriate Log Levels**: Use DEBUG for verbose info, INFO for normal operations, WARNING for unexpected but handled situations, ERROR for errors, CRITICAL for severe failures
3. **Structured Messages**: Keep log messages clear and searchable
4. **Don't Log Sensitive Data**: Never log passwords, tokens, or PII
5. **Single Instance**: Create one CentralLoggingService instance per application and reuse it

## Troubleshooting

### Remote logging not working?

Check the following:

1. **Environment variables set?**
   ```bash
   echo $LOGS_COLLECTOR_API
   echo $LOGS_COLLECTOR_TOKEN
   ```

2. **Check logs for warnings**:
   - "LOGS_COLLECTOR_API not set. Remote logging disabled."
   - "LOGS_COLLECTOR_TOKEN not set. Remote logging disabled."
   - "Failed to send log to remote collector: HTTP XXX"
   - "Timeout sending log to remote collector"

3. **Test API connectivity**:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        -H "Content-Type: application/json" \
        -X POST \
        https://logs-collector-production.up.railway.app/logs \
        -d '{"application_name":"test","environment":"test","hostname":"test","level":"info","message":"test","timestamp":"2024-01-01T00:00:00Z","trace_id":"test","version":"1.0.0"}'
   ```

## Architecture

```
┌─────────────────────┐
│  Your Application   │
│  (uses logger.info) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ CentralLoggingService│
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌────────┐  ┌────────────┐
│ stdout │  │ Remote API │
│(local) │  │ (optional) │
└────────┘  └────────────┘
```

## Files

- `services/logging_service.py` - Main service implementation
- `models/log_models.py` - Pydantic models for logs
- `tests/test_logging_service.py` - Comprehensive unit tests
- `examples/logging_service_example.py` - Usage examples
- `services/LOGGING_SERVICE_README.md` - This file

## License

Part of the Cat-Emails project.
