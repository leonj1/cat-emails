# Force Process Endpoint Implementation

## Overview

Successfully implemented a new REST API endpoint that allows force initiating email processing for a specific Gmail account on-demand.

**Endpoint:** `POST /api/accounts/{email_address}/process`

## Implementation Summary

### ✅ Files Created

1. **`models/force_process_response.py`**
   - Pydantic response model for the force process endpoint
   - Includes `ForceProcessResponse` and `ProcessingInfo` models
   - Supports success, error, and already_processing states

2. **`services/rate_limiter_service.py`**
   - Thread-safe rate limiting service
   - Default 5-minute cooldown between requests per account
   - Prevents abuse of resource-intensive operations
   - Methods: `check_rate_limit()`, `reset_key()`, `clear_all()`, `get_stats()`

3. **`tests/test_force_process_endpoint.py`**
   - Comprehensive unit test suite
   - Tests for: success, 404, 409, 429, 400, authentication, custom hours
   - Tests for RateLimiterService functionality

4. **`test_force_process_simple.py`**
   - Simple verification script to test basic functionality
   - Validates imports, models, rate limiter, and status manager

### ✅ Files Modified

1. **`api_service.py`**
   - Added new `/api/accounts/{email_address}/process` endpoint
   - Integrated rate limiting (429 Too Many Requests)
   - Concurrency protection (409 Conflict if already processing)
   - Async background processing (202 Accepted response)
   - Custom lookback hours support (`hours` query parameter, 1-168)
   - Updated root endpoint documentation

2. **`services/processing_status_manager.py`**
   - Added `is_processing_account(email_address: str)` method
   - Thread-safe check for specific account processing status
   - Case-insensitive email comparison

3. **`CLAUDE.md`**
   - Added comprehensive API Service section
   - Documented all API endpoints
   - Included force processing usage examples
   - Added environment variables documentation
   - Explained force processing vs background processing
   - Updated security notes

## Features Implemented

### ✅ Core Features (MVP)

- ✅ **Force processing endpoint** - `POST /api/accounts/{email_address}/process`
- ✅ **Concurrency protection** - Returns 409 if account is already processing
- ✅ **Async execution** - Returns 202 Accepted immediately
- ✅ **Custom lookback hours** - Optional `hours` query parameter (1-168)
- ✅ **Rate limiting** - Max 1 request per account every 5 minutes (429 response)
- ✅ **Error handling** - Proper HTTP status codes (400, 401, 404, 409, 429, 500)
- ✅ **API authentication** - Supports X-API-Key header
- ✅ **OpenAPI documentation** - Comprehensive endpoint docs with examples

### ✅ Advanced Features

- ✅ **Thread-safe operations** - All shared state protected with locks
- ✅ **Real-time status monitoring** - Integration with existing WebSocket `/ws/status`
- ✅ **Detailed logging** - All operations logged with context
- ✅ **Comprehensive tests** - Unit tests for all scenarios
- ✅ **Documentation** - Updated CLAUDE.md with usage examples

## API Endpoint Details

### Request

```http
POST /api/accounts/{email_address}/process?hours={lookback_hours}
X-API-Key: your-api-key
```

**Path Parameters:**
- `email_address` (required): Gmail address to process

**Query Parameters:**
- `hours` (optional): Lookback hours (1-168, default from settings)

### Response Codes

| Code | Meaning | Scenario |
|------|---------|----------|
| 202 | Accepted | Processing started successfully |
| 400 | Bad Request | Invalid email format or parameters |
| 401 | Unauthorized | Missing or invalid API key |
| 404 | Not Found | Account not found in database |
| 409 | Conflict | Account already being processed |
| 429 | Too Many Requests | Rate limit exceeded (< 5 min since last) |
| 500 | Internal Server Error | Processing failed to start |

### Example Responses

**Success (202):**
```json
{
  "status": "success",
  "message": "Email processing started for user@gmail.com",
  "email_address": "user@gmail.com",
  "timestamp": "2025-10-07T10:30:00Z",
  "processing_info": {
    "hours": 2,
    "status_url": "/api/processing/current-status",
    "websocket_url": "/ws/status"
  }
}
```

**Already Processing (409):**
```json
{
  "status": "already_processing",
  "message": "Account user@gmail.com is currently being processed",
  "email_address": "user@gmail.com",
  "timestamp": "2025-10-07T10:30:00Z",
  "processing_info": {
    "state": "PROCESSING",
    "current_step": "Processing email 5 of 20",
    "status_url": "/api/processing/current-status",
    "websocket_url": "/ws/status"
  }
}
```

**Rate Limited (429):**
```json
{
  "error": "Rate limit exceeded",
  "message": "Please wait 3.5 minutes before processing user@gmail.com again",
  "seconds_remaining": 210.0,
  "retry_after": 210
}
```

## Usage Examples

### cURL

```bash
# Basic force processing
curl -X POST "http://localhost:8001/api/accounts/user@gmail.com/process" \
  -H "X-API-Key: your-api-key"

# With custom lookback hours (24 hours)
curl -X POST "http://localhost:8001/api/accounts/user@gmail.com/process?hours=24" \
  -H "X-API-Key: your-api-key"
```

### Python

```python
import requests

url = "http://localhost:8001/api/accounts/user@gmail.com/process"
headers = {"X-API-Key": "your-api-key"}
params = {"hours": 24}  # Optional

response = requests.post(url, headers=headers, params=params)

if response.status_code == 202:
    data = response.json()
    print(f"Processing started: {data['message']}")
    print(f"Monitor at: {data['processing_info']['status_url']}")
elif response.status_code == 409:
    print("Already processing - check current status")
elif response.status_code == 429:
    data = response.json()
    print(f"Rate limited: {data['detail']['message']}")
```

### JavaScript

```javascript
const response = await fetch(
  'http://localhost:8001/api/accounts/user@gmail.com/process?hours=24',
  {
    method: 'POST',
    headers: {
      'X-API-Key': 'your-api-key'
    }
  }
);

const data = await response.json();

if (response.status === 202) {
  console.log('Processing started:', data.message);
  // Connect to WebSocket for real-time updates
  const ws = new WebSocket(data.processing_info.websocket_url);
  ws.onmessage = (event) => console.log('Status:', JSON.parse(event.data));
}
```

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install fastapi pytest

# Run tests
python -m pytest tests/test_force_process_endpoint.py -v

# Or with unittest
python -m unittest tests.test_force_process_endpoint -v
```

### Manual Testing

1. **Start the API service:**
   ```bash
   export API_KEY="test-key"
   export REQUESTYAI_API_KEY="your-llm-key"
   python api_service.py
   ```

2. **Create a test account:**
   ```bash
   curl -X POST "http://localhost:8001/api/accounts" \
     -H "X-API-Key: test-key" \
     -H "Content-Type: application/json" \
     -d '{
       "email_address": "test@gmail.com",
       "app_password": "your-gmail-app-password"
     }'
   ```

3. **Force process the account:**
   ```bash
   curl -X POST "http://localhost:8001/api/accounts/test@gmail.com/process" \
     -H "X-API-Key: test-key"
   ```

4. **Try again immediately (should be rate limited):**
   ```bash
   curl -X POST "http://localhost:8001/api/accounts/test@gmail.com/process" \
     -H "X-API-Key: test-key"
   # Should return 429 Too Many Requests
   ```

5. **Monitor processing status:**
   ```bash
   curl "http://localhost:8001/api/processing/current-status" \
     -H "X-API-Key: test-key"
   ```

## Architecture

### Thread Safety

All components are thread-safe:
- `ProcessingStatusManager`: Uses `threading.RLock()` for all operations
- `RateLimiterService`: Uses `threading.RLock()` for rate limit tracking
- Background processing: Daemon thread separate from force processing

### Concurrency Model

```
┌─────────────────────────────────────────────────────────────┐
│                     API Request                              │
│                 POST /process                                │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │  Rate Limit Check   │
         │  (5 min cooldown)   │
         └─────────┬───────────┘
                   │ OK
                   ▼
         ┌─────────────────────┐
         │ Concurrency Check   │
         │ (is_processing?)    │
         └─────────┬───────────┘
                   │ Not Processing
                   ▼
         ┌─────────────────────┐
         │ Return 202 Accepted │
         └─────────┬───────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │  Background Thread  │──────► Process emails
         │  (async execution)  │──────► Update status via
         └─────────────────────┘        ProcessingStatusManager
                                        │
                                        ▼
                              ┌──────────────────────┐
                              │  WebSocket Broadcast │
                              │  Real-time Updates   │
                              └──────────────────────┘
```

### Rate Limiting Algorithm

```python
# Per-account rate limiting
if last_request_time exists:
    time_since_last = now - last_request_time
    if time_since_last < 300 seconds:  # 5 minutes
        deny_request(seconds_remaining)
    else:
        allow_request()
        update_last_request_time()
else:
    allow_request()  # First request always allowed
    set_last_request_time()
```

## Configuration

### Environment Variables

```bash
# Rate limiting (optional, defaults shown)
FORCE_PROCESS_RATE_LIMIT_SECONDS=300  # 5 minutes (not implemented, hardcoded in code)

# API Configuration
API_KEY=your-secret-key           # Optional API key
API_HOST=0.0.0.0                  # Bind host
API_PORT=8001                     # Bind port

# Processing defaults
BACKGROUND_PROCESS_HOURS=2        # Default lookback hours
```

### Customizing Rate Limit

To change the rate limit interval, modify in `api_service.py`:

```python
# Global rate limiter for force processing endpoint
force_process_rate_limiter = RateLimiterService(
    default_interval_seconds=600  # Change to 10 minutes
)
```

## Security Considerations

### Implemented Protections

✅ **Rate Limiting**
- Prevents abuse/spam of expensive operations
- Per-account cooldown (5 minutes)
- Returns clear error with retry timing

✅ **Concurrency Protection**
- Only one account processed at a time
- Prevents resource exhaustion
- Clear conflict messages

✅ **Authentication**
- Optional API key support
- Header-based authentication
- Consistent with other endpoints

✅ **Input Validation**
- Email format validation
- Hours parameter validation (1-168)
- Account existence verification
- Password presence check

### Security Best Practices

1. **Always use API_KEY in production**
   ```bash
   export API_KEY="$(openssl rand -hex 32)"
   ```

2. **Use HTTPS in production**
   - Never expose API over plain HTTP
   - Use reverse proxy (nginx/caddy) with TLS

3. **Monitor rate limit abuse**
   - Check logs for 429 responses
   - Implement alerts for excessive failed attempts

4. **Protect Gmail app passwords**
   - Never log passwords
   - Encrypt at rest in database
   - Use environment variables

## Monitoring & Observability

### Logging

All operations are logged with context:

```
INFO - Force processing request for account: user@gmail.com
INFO - Rate limit check for 'user@gmail.com': ALLOWED (first request)
INFO - Started processing for account: user@gmail.com
INFO - Successfully started force processing for user@gmail.com
```

### Metrics to Monitor

- **Force process requests**: Total count
- **429 responses**: Rate limit hits
- **409 responses**: Concurrency conflicts
- **Average processing time**: Performance tracking
- **Success/failure rates**: Reliability metrics

### Health Checks

```bash
# Check API health
curl http://localhost:8001/api/health

# Check processing status
curl http://localhost:8001/api/processing/current-status \
  -H "X-API-Key: your-key"

# Check background processor
curl http://localhost:8001/api/background/status \
  -H "X-API-Key: your-key"
```

## Future Enhancements

### Potential Improvements

1. **Queue-based Processing**
   - Accept multiple concurrent requests
   - Process in queue with configurable concurrency
   - Better resource utilization

2. **Per-user Rate Limiting**
   - Different limits for different API keys
   - Tiered access levels

3. **Webhook Callbacks**
   - Notify on completion
   - POST results to callback URL

4. **Dry Run Mode**
   - Preview what would be processed
   - Testing without side effects

5. **Priority Processing**
   - Express lane for critical accounts
   - Queue jumping for admin requests

6. **Scheduled Processing**
   - Schedule processing for future time
   - Recurring schedules per account

7. **Batch Processing**
   - Process multiple accounts in one request
   - Bulk operations endpoint

## Troubleshooting

### Common Issues

**Problem:** Getting 409 "already processing" errors
- **Solution:** Wait for current processing to complete or check `/api/processing/status`

**Problem:** Getting 429 rate limit errors
- **Solution:** Wait 5 minutes between force process requests for same account

**Problem:** Getting 404 account not found
- **Solution:** Create account first using `POST /api/accounts`

**Problem:** Getting 400 no password configured
- **Solution:** Update account with Gmail app password via `POST /api/accounts`

**Problem:** Processing seems stuck
- **Solution:** Check `/api/processing/current-status` for detailed state

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Summary

The force process endpoint implementation is **production-ready** with:

- ✅ Complete functionality
- ✅ Comprehensive error handling
- ✅ Security protections (rate limiting, concurrency)
- ✅ Full documentation
- ✅ Unit tests
- ✅ OpenAPI/Swagger docs
- ✅ Real-time status monitoring
- ✅ Background async execution

The endpoint provides a robust, secure way to trigger on-demand email processing for specific Gmail accounts while protecting against abuse and resource exhaustion.
