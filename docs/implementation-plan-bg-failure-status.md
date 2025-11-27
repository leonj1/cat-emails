# Implementation Plan: Expose Background Processing Failure Status to Frontend

## Problem Statement

When background email processing fails (e.g., Gmail authentication errors), the error is logged but the frontend has no way to:
1. Know that processing failed
2. See the specific reason for failure
3. Display actionable error messages to users

**Example error from logs:**
```
Processing error for public.test@gmail.com: Processing failed: Failed to connect to Gmail:
[AUTHENTICATIONFAILED] Invalid credentials (Failure); LOGIN error: b'[AUTHENTICATIONFAILED]
Invalid credentials (Failure)'. Gmail authentication failed. Ensure GMAIL_PASSWORD is a
Gmail App Password (not your regular password), 16 characters, no spaces, and that
2-Step Verification is enabled.
```

## Current Architecture Analysis

### Components Involved

1. **ProcessingStatusManager** (`services/processing_status_manager.py`)
   - Already captures `error_message` field in `AccountStatus` dataclass (line 66)
   - `update_status()` accepts `error_message` parameter (line 138)
   - Stores `error_message` in archived runs (line 207)
   - **Status**: Already stores error data correctly

2. **AccountEmailProcessorService** (`services/account_email_processor_service.py`)
   - Properly calls `update_status()` with `error_message` on failures (lines 106-110, 127-131, 330-334)
   - **Status**: Already propagates errors correctly

3. **API Endpoints** (`api_service.py`)
   - `/api/processing/status` - Returns current status (line 832)
   - `/api/processing/history` - Returns recent runs with error info (line 853)
   - `/api/processing/current-status` - Comprehensive status (line 895)
   - **Status**: Endpoints exist but error info may not be prominently exposed

4. **Response Models** (`models/`)
   - `ProcessingCurrentStatusResponse` - Uses generic `Dict` types (line 8-12)
   - No explicit error fields in response schemas
   - **Status**: Needs enhancement for explicit error exposure

5. **WebSocket Handler** (`services/websocket_handler.py`)
   - Broadcasts status updates via `broadcast_status()` (line 190)
   - Already includes `recent_runs` which contains error info
   - **Status**: Already broadcasts error data

## Gap Analysis

| Component | Error Data Captured | Error Data Exposed | Gap |
|-----------|---------------------|-------------------|-----|
| ProcessingStatusManager | ✅ Yes | ✅ Yes (via methods) | None |
| AccountEmailProcessorService | ✅ Yes | N/A | None |
| REST API Endpoints | ✅ Via history/status | ⚠️ Implicit | Needs explicit error fields |
| Response Models | ⚠️ Generic Dict | ⚠️ No typed error fields | Needs typed response |
| WebSocket | ✅ In recent_runs | ⚠️ Implicit | Could be more explicit |
| Frontend | N/A | ❌ No display | Needs implementation |

## Proposed Solution

### Phase 1: Enhance Response Models

**File: `models/processing_current_status_response.py`**

Add explicit error fields to make failures immediately visible:

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


class ProcessingRunDetails(BaseModel):
    """Detailed information about a processing run"""
    email_address: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    final_state: str  # "COMPLETED", "ERROR", etc.
    final_step: Optional[str] = None
    error_message: Optional[str] = Field(
        None,
        description="Error message if processing failed. Contains actionable information for users."
    )
    final_progress: Optional[Dict[str, Any]] = None


class CurrentProcessingStatus(BaseModel):
    """Current processing status with explicit error handling"""
    email_address: str
    state: str  # Processing state enum as string
    current_step: str
    progress: Optional[Dict[str, Any]] = None
    start_time: Optional[str] = None
    last_updated: Optional[str] = None
    error_message: Optional[str] = Field(
        None,
        description="Error message if current processing is in error state"
    )


class ProcessingFailureSummary(BaseModel):
    """Summary of recent processing failures for quick frontend display"""
    has_recent_failures: bool = Field(
        ...,
        description="True if there are any failed runs in recent history"
    )
    failure_count: int = Field(
        ...,
        description="Number of failed runs in recent history"
    )
    most_recent_failure: Optional[ProcessingRunDetails] = Field(
        None,
        description="Details of the most recent failure, if any"
    )


class ProcessingCurrentStatusResponse(BaseModel):
    """Enhanced response model for current processing status endpoint"""
    is_processing: bool
    current_status: Optional[CurrentProcessingStatus] = None
    recent_runs: Optional[List[ProcessingRunDetails]] = None
    statistics: Optional[Dict[str, Any]] = None
    timestamp: str
    websocket_available: bool

    # NEW: Explicit failure information
    failure_summary: Optional[ProcessingFailureSummary] = Field(
        None,
        description="Summary of recent processing failures for easy frontend consumption"
    )
```

### Phase 2: Enhance API Endpoint

**File: `api_service.py`**

Update `get_current_processing_status()` endpoint to include failure summary:

```python
@app.get("/api/processing/current-status", response_model=ProcessingCurrentStatusResponse, tags=["processing-status"])
async def get_current_processing_status(
    include_recent: bool = Query(True, description="Include recent processing runs"),
    recent_limit: int = Query(5, ge=1, le=50, description="Number of recent runs to return (1-50)"),
    include_stats: bool = Query(False, description="Include processing statistics"),
    include_failure_summary: bool = Query(True, description="Include failure summary"),
    x_api_key: Optional[str] = Header(None)
):
    """
    Get comprehensive current processing status with explicit failure information
    """
    # ... existing code ...

    # Build failure summary
    failure_summary = None
    if include_failure_summary and recent_runs:
        failures = [run for run in recent_runs if run.get('final_state') == 'ERROR']
        failure_summary = ProcessingFailureSummary(
            has_recent_failures=len(failures) > 0,
            failure_count=len(failures),
            most_recent_failure=ProcessingRunDetails(**failures[0]) if failures else None
        )

    response = ProcessingCurrentStatusResponse(
        is_processing=is_processing,
        current_status=current_status,
        recent_runs=recent_runs,
        statistics=statistics,
        timestamp=datetime.now().isoformat(),
        websocket_available=websocket_available,
        failure_summary=failure_summary  # NEW
    )
```

### Phase 3: Add Dedicated Failure Endpoint

**File: `api_service.py`**

Add a new endpoint specifically for querying processing failures:

```python
@app.get("/api/processing/failures", tags=["processing-status"])
async def get_processing_failures(
    email_address: Optional[str] = Query(None, description="Filter by specific email address"),
    limit: int = Query(10, ge=1, le=100, description="Maximum failures to return"),
    x_api_key: Optional[str] = Header(None)
):
    """
    Get recent processing failures with detailed error information

    Returns:
        List of failed processing runs with error messages and context

    Use Cases:
        - Display error notifications in frontend dashboard
        - Diagnose authentication issues for specific accounts
        - Generate error reports for system administrators
    """
    verify_api_key(x_api_key)

    recent_runs = processing_status_manager.get_recent_runs(limit=limit * 2)  # Get more to filter

    failures = []
    for run in recent_runs:
        if run.get('final_state') == 'ERROR':
            if email_address and run.get('email_address', '').lower() != email_address.lower():
                continue
            failures.append({
                'email_address': run.get('email_address'),
                'error_message': run.get('error_message'),
                'error_time': run.get('end_time'),
                'failed_step': run.get('final_step'),
                'duration_seconds': run.get('duration_seconds'),
                'is_auth_error': _is_authentication_error(run.get('error_message', '')),
                'suggested_action': _get_suggested_action(run.get('error_message', ''))
            })
            if len(failures) >= limit:
                break

    return {
        'failures': failures,
        'total_failures': len(failures),
        'timestamp': datetime.now().isoformat()
    }


def _is_authentication_error(error_message: str) -> bool:
    """Check if error is related to authentication"""
    auth_keywords = ['AUTHENTICATIONFAILED', 'Invalid credentials', 'authentication failed', 'LOGIN error']
    return any(keyword.lower() in error_message.lower() for keyword in auth_keywords)


def _get_suggested_action(error_message: str) -> str:
    """Provide user-friendly suggested action based on error type"""
    if _is_authentication_error(error_message):
        return "Verify that the Gmail App Password is correct (16 characters, no spaces) and that 2-Step Verification is enabled on the Gmail account."
    elif 'not found' in error_message.lower():
        return "The account may have been deleted or deactivated. Re-register the account."
    elif 'connection' in error_message.lower():
        return "Check network connectivity. Gmail's IMAP service may be temporarily unavailable."
    else:
        return "Review the error details and contact support if the issue persists."
```

### Phase 4: Enhance WebSocket Updates

**File: `services/websocket_handler.py`**

Update `broadcast_status()` to include explicit failure notification:

```python
async def broadcast_status(self) -> None:
    """Broadcast current processing status to all connected clients."""
    # ... existing code ...

    # Check for failures in recent runs
    recent_runs = self.status_manager.get_recent_runs(limit=5)
    failures = [r for r in recent_runs if r.get('final_state') == 'ERROR']

    message = {
        "type": "status_update",
        "data": {
            "current_processing": current_status,
            "recent_runs": recent_runs,
            "statistics": statistics,
            "client_count": len(self.clients),
            # NEW: Explicit failure information
            "has_failures": len(failures) > 0,
            "failure_count": len(failures),
            "most_recent_failure": failures[0] if failures else None
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "server_time": time.time()
    }
```

## Implementation Tasks

### Task 1: Update Response Models
- [ ] Create `ProcessingRunDetails` model
- [ ] Create `CurrentProcessingStatus` model
- [ ] Create `ProcessingFailureSummary` model
- [ ] Update `ProcessingCurrentStatusResponse` model
- [ ] Add unit tests for new models

### Task 2: Enhance Current Status Endpoint
- [ ] Add `include_failure_summary` query parameter
- [ ] Build failure summary from recent runs
- [ ] Map Dict responses to typed models
- [ ] Update OpenAPI documentation
- [ ] Add integration tests

### Task 3: Add Failures Endpoint
- [ ] Create `/api/processing/failures` endpoint
- [ ] Implement `_is_authentication_error()` helper
- [ ] Implement `_get_suggested_action()` helper
- [ ] Add endpoint to route documentation
- [ ] Add unit and integration tests

### Task 4: Enhance WebSocket Handler
- [ ] Update `broadcast_status()` with failure info
- [ ] Add failure notification message type
- [ ] Update WebSocket documentation
- [ ] Add WebSocket tests for failure scenarios

### Task 5: Frontend Integration (Out of Scope)
- [ ] Display failure notifications in dashboard
- [ ] Show actionable error messages
- [ ] Add "Verify Password" action button for auth errors

## API Response Examples

### Success Response (No Failures)
```json
{
  "is_processing": false,
  "current_status": null,
  "recent_runs": [
    {
      "email_address": "user@gmail.com",
      "final_state": "COMPLETED",
      "final_step": "Successfully processed 25 emails",
      "error_message": null
    }
  ],
  "failure_summary": {
    "has_recent_failures": false,
    "failure_count": 0,
    "most_recent_failure": null
  },
  "timestamp": "2025-11-27T22:30:00Z",
  "websocket_available": true
}
```

### Failure Response (Authentication Error)
```json
{
  "is_processing": false,
  "current_status": null,
  "recent_runs": [
    {
      "email_address": "public.test@gmail.com",
      "final_state": "ERROR",
      "final_step": "Processing failed: Failed to connect to Gmail",
      "error_message": "Failed to connect to Gmail: [AUTHENTICATIONFAILED] Invalid credentials (Failure). Gmail authentication failed. Ensure GMAIL_PASSWORD is a Gmail App Password (not your regular password), 16 characters, no spaces, and that 2-Step Verification is enabled.",
      "start_time": "2025-11-27T22:16:00Z",
      "end_time": "2025-11-27T22:16:03Z"
    }
  ],
  "failure_summary": {
    "has_recent_failures": true,
    "failure_count": 1,
    "most_recent_failure": {
      "email_address": "public.test@gmail.com",
      "final_state": "ERROR",
      "error_message": "Failed to connect to Gmail: [AUTHENTICATIONFAILED] Invalid credentials (Failure). Gmail authentication failed. Ensure GMAIL_PASSWORD is a Gmail App Password (not your regular password), 16 characters, no spaces, and that 2-Step Verification is enabled."
    }
  },
  "timestamp": "2025-11-27T22:30:00Z",
  "websocket_available": true
}
```

### Failures Endpoint Response
```json
{
  "failures": [
    {
      "email_address": "public.test@gmail.com",
      "error_message": "Failed to connect to Gmail: [AUTHENTICATIONFAILED] Invalid credentials...",
      "error_time": "2025-11-27T22:16:03Z",
      "failed_step": "Processing failed: Failed to connect to Gmail",
      "duration_seconds": 3.2,
      "is_auth_error": true,
      "suggested_action": "Verify that the Gmail App Password is correct (16 characters, no spaces) and that 2-Step Verification is enabled on the Gmail account."
    }
  ],
  "total_failures": 1,
  "timestamp": "2025-11-27T22:30:00Z"
}
```

## WebSocket Message Format

### Status Update with Failure Info
```json
{
  "type": "status_update",
  "data": {
    "current_processing": null,
    "recent_runs": [...],
    "statistics": {...},
    "client_count": 2,
    "has_failures": true,
    "failure_count": 1,
    "most_recent_failure": {
      "email_address": "public.test@gmail.com",
      "final_state": "ERROR",
      "error_message": "Failed to connect to Gmail: [AUTHENTICATIONFAILED]..."
    }
  },
  "timestamp": "2025-11-27T22:30:00.000Z"
}
```

## Testing Strategy

1. **Unit Tests**: Test new model classes and helper functions
2. **Integration Tests**: Test API endpoints with mocked failures
3. **E2E Tests**: Test WebSocket failure broadcasts
4. **Manual Testing**: Trigger actual auth failures and verify frontend display

## Migration Notes

- All changes are backward compatible
- Existing API consumers will continue to work
- New fields are optional with sensible defaults
- Frontend can progressively adopt new failure fields

## Success Criteria

1. Frontend can display processing failures with specific error messages
2. Authentication errors show actionable guidance to users
3. WebSocket updates include failure status in real-time
4. REST API provides dedicated failure querying capability
5. All existing functionality remains unchanged
