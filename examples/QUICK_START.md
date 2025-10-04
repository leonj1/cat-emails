# Logging Service Quick Start Guide

## 1. Configuration (Required)

```bash
export LOGS_COLLECTOR_API="https://logs-collector-production.up.railway.app"
export LOGS_COLLECTOR_TOKEN="your-bearer-token-here"
```

## 2. Basic Usage

```python
from services.logging_service import CentralLoggingService

# Create logger instance
logger = CentralLoggingService()

# Log messages
logger.debug("Detailed debugging information")
logger.info("Application started successfully")
logger.warning("Memory usage is high")
logger.error("Failed to connect to database")
logger.critical("System is shutting down")
```

## 3. With Trace IDs (Recommended)

```python
from services.logging_service import CentralLoggingService

logger = CentralLoggingService()

# Use trace IDs to correlate related logs
trace_id = "request-12345"
logger.info("Processing email", trace_id=trace_id)
logger.info("Email categorized", trace_id=trace_id)
logger.info("Label applied", trace_id=trace_id)
```

## 4. Payload Sent to API

```json
{
  "application_name": "cat-emails",
  "environment": "production",
  "hostname": "your-hostname",
  "level": "info",
  "message": "Your log message",
  "timestamp": "2024-01-15T14:30:00.123456Z",
  "trace_id": "auto-generated-or-provided",
  "version": "1.0.0"
}
```

## 5. Verify It Works

Run the test to see the actual payload:
```bash
python tests/test_payload_example.py
```

Run all tests:
```bash
make test
```

## 6. Features

✅ Logs to stdout (always)
✅ Logs to remote API (if configured)
✅ Auto-failover to local-only if remote unavailable
✅ Distributed tracing with trace IDs
✅ Non-blocking error handling
✅ Type-safe with Pydantic models

## 7. Troubleshooting

**Logs not appearing in remote collector?**

1. Check environment variables are set:
   ```bash
   echo $LOGS_COLLECTOR_API
   echo $LOGS_COLLECTOR_TOKEN
   ```

2. Look for warnings in stdout:
   - "LOGS_COLLECTOR_API not set. Remote logging disabled."
   - "Failed to send log to remote collector: HTTP XXX"

3. Verify API connectivity:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        https://logs-collector-production.up.railway.app/logs
   ```

## 8. Optional Configuration

```bash
# Customize app metadata
export APP_NAME="my-custom-app"
export APP_VERSION="2.0.0"
export APP_ENVIRONMENT="staging"
```

## 9. Local-Only Mode (Testing)

```python
# Disable remote logging
logger = CentralLoggingService(enable_remote=False)
logger.info("Only goes to stdout")
```

## 10. Run Examples

```bash
python examples/logging_service_example.py
```

---

**Need more details?** See `services/LOGGING_SERVICE_README.md`
