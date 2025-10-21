# Logs Collector API Error Details Display Enhancement

## Summary
Enhanced error handling in the logs-collector integration to display detailed error information from the API when requests fail. This helps developers immediately understand the root cause of API errors.

## Changes Made

### 1. `services/logs_collector_service.py`
- Updated error handling to specifically catch `HTTPError` exceptions
- Extract and display the `details` field from API error responses
- Print error details to stdout with "ERROR:" prefix for visibility
- Fallback to `message` or `error` fields if `details` is not available
- Show raw response text (truncated) if response is not valid JSON

### 2. `clients/logs_collector_client.py`
- Added similar error handling for `HTTPError` exceptions
- Extract and display error details from API responses
- Print detailed error information to stdout
- Graceful handling of non-JSON responses

### 3. Test Coverage
- Added `test_send_log_http_error_with_details` test to verify details extraction
- Added `test_send_log_http_error_without_details` test for fallback behavior
- Created comprehensive test suite in `tests/test_logs_collector_client.py`
- All tests passing successfully

## Benefits
- **Immediate Visibility**: Developers see the exact error reason in stdout
- **Better Debugging**: No need to inspect network traffic or logs to understand API errors
- **Graceful Fallback**: Works even if API response format changes
- **Comprehensive Coverage**: Both service implementations updated and tested

## Example Output
When the API returns an error with details:
```
ERROR: Logs collector API error details: Invalid trace_id format: must be a valid UUID
Failed to send log to collector: 400 Client Error - Details: Invalid trace_id format: must be a valid UUID
```

This makes it immediately clear what the problem is and how to fix it.