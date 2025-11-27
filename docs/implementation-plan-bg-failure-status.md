# Implementation Plan: Expose Background Processing Failure Status to Frontend

## Problem Statement

When background email processing fails (e.g., Gmail authentication errors), the error is logged but the frontend has no way to:
1. Know that processing failed
2. See the specific reason for failure
3. Display actionable error messages to users

**Example error from logs:**
```log
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
from datetime import datetime
from typing import Optional
from fastapi import Query, Header
from models.processing_current_status_response import (
    ProcessingCurrentStatusResponse,
    ProcessingRunDetails,
    CurrentProcessingStatus,
    ProcessingFailureSummary
)

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
    verify_api_key(x_api_key)

    # Get current processing status
    is_processing = processing_status_manager.is_processing()
    current_status_dict = processing_status_manager.get_current_status()

    # Convert dict to typed model
    current_status = None
    if current_status_dict:
        current_status = CurrentProcessingStatus(**current_status_dict)

    # Get recent runs and convert to typed models
    recent_runs = None
    if include_recent:
        recent_runs_dicts = processing_status_manager.get_recent_runs(limit=recent_limit)
        recent_runs = [ProcessingRunDetails(**run) for run in recent_runs_dicts]

    # Get statistics if requested
    statistics = None
    if include_stats:
        statistics = processing_status_manager.get_statistics()

    # Build failure summary from typed models
    failure_summary = None
    if include_failure_summary and recent_runs:
        failures = [run for run in recent_runs if run.final_state == 'ERROR']
        failure_summary = ProcessingFailureSummary(
            has_recent_failures=len(failures) > 0,
            failure_count=len(failures),
            most_recent_failure=failures[0] if failures else None
        )

    # Check if WebSocket is available
    websocket_available = websocket_manager is not None

    response = ProcessingCurrentStatusResponse(
        is_processing=is_processing,
        current_status=current_status,
        recent_runs=recent_runs,
        statistics=statistics,
        timestamp=datetime.now().isoformat(),
        websocket_available=websocket_available,
        failure_summary=failure_summary  # NEW
    )

    return response
```

### Phase 3: Error Classification System

**File: `models/error_classification.py`** (NEW)

Create an extensible error classification system:

**Python Version Requirement**: This implementation uses Python 3.9+ type hint syntax (`list[str]`, `dict[...]`). If the project uses Python 3.8 or earlier, replace with `typing.List`, `typing.Dict`, etc.

```python
from enum import Enum
from typing import Optional, Pattern, List, Dict, Tuple
import re
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Categorization of processing errors"""
    AUTHENTICATION = "authentication"
    CONNECTION = "connection"
    ACCOUNT_NOT_FOUND = "account_not_found"
    CONFIGURATION = "configuration"
    RATE_LIMIT = "rate_limit"
    GMAIL_SERVICE = "gmail_service"
    UNKNOWN = "unknown"


class ErrorPattern(BaseModel):
    """Pattern matching configuration for error classification"""
    category: ErrorCategory
    patterns: List[str] = Field(..., description="Regex patterns to match")
    suggested_action: str = Field(..., description="User-friendly remediation guidance")
    priority: int = Field(default=100, description="Lower number = higher priority when multiple matches")
    retry_strategy: Optional[str] = Field(None, description="Recommended retry strategy (e.g., 'exponential_backoff')")


# Error classification rules (ordered by priority)
ERROR_CLASSIFICATION_RULES = [
    ErrorPattern(
        category=ErrorCategory.AUTHENTICATION,
        patterns=[
            r"AUTHENTICATIONFAILED",
            r"Invalid credentials",
            r"authentication failed",
            r"LOGIN error",
            r"credentials.*invalid"
        ],
        suggested_action="Verify that the Gmail App Password is correct (16 characters, no spaces) and that 2-Step Verification is enabled on the Gmail account. Generate a new App Password if needed.",
        priority=10
    ),
    ErrorPattern(
        category=ErrorCategory.ACCOUNT_NOT_FOUND,
        patterns=[
            r"Account.*not found",
            r"No account found",
            r"account.*does not exist"
        ],
        suggested_action="The account may have been deleted or deactivated. Re-register the account via POST /api/accounts.",
        priority=20
    ),
    ErrorPattern(
        category=ErrorCategory.CONNECTION,
        patterns=[
            r"connection.*refused",
            r"connection.*timeout",
            r"network.*error",
            r"failed to connect",
            r"socket.*error"
        ],
        suggested_action="Check network connectivity. Gmail's IMAP service may be temporarily unavailable. Retry in a few minutes.",
        priority=30
    ),
    ErrorPattern(
        category=ErrorCategory.CONFIGURATION,
        patterns=[
            r"No app password",
            r"missing.*password",
            r"configuration.*error",
            r"invalid.*configuration"
        ],
        suggested_action="Account configuration is incomplete. Update the account with a valid Gmail App Password via POST /api/accounts.",
        priority=15
    ),
    ErrorPattern(
        category=ErrorCategory.RATE_LIMIT,
        patterns=[
            r"rate limit",
            r"too many requests",
            r"quota exceeded",
            r"429"
        ],
        suggested_action="Gmail API rate limit reached. Processing will automatically retry after the rate limit window expires.",
        priority=25,
        retry_strategy="exponential_backoff"  # Recommended: start with 60s, double each retry, max 3600s
    ),
    ErrorPattern(
        category=ErrorCategory.GMAIL_SERVICE,
        patterns=[
            r"IMAP.*unavailable",
            r"Gmail.*service.*error",
            r"temporary.*failure",
            r"503.*Service Unavailable"
        ],
        suggested_action="Gmail IMAP service is temporarily unavailable. This is usually temporary; processing will retry automatically.",
        priority=40
    )
]


class ErrorClassifier:
    """
    Classifier for processing error messages.

    Retry Strategy Recommendations:
    - RATE_LIMIT errors: Use exponential backoff (60s, 120s, 240s, max 3600s)
    - CONNECTION errors: Use exponential backoff with jitter (5s, 10s, 20s, max 300s)
    - GMAIL_SERVICE errors: Linear backoff (60s intervals, max 5 retries)
    - AUTHENTICATION errors: Do not retry automatically (requires user intervention)

    Logging Best Practices:
    - Avoid logging full error messages containing PII (email addresses, passwords)
    - Use structured logging with sanitized fields
    - Log error categories and patterns matched instead of raw messages when possible
    """

    def __init__(self, rules: List[ErrorPattern] = None):
        """
        Initialize error classifier with rules.

        Args:
            rules: List of ErrorPattern rules (defaults to ERROR_CLASSIFICATION_RULES)
        """
        self.rules = rules or ERROR_CLASSIFICATION_RULES
        # Sort by priority (lower number first)
        self.rules.sort(key=lambda r: r.priority)

        # Compile regex patterns for performance
        self._compiled_patterns: Dict[ErrorCategory, List[Pattern]] = {}
        for rule in self.rules:
            self._compiled_patterns[rule.category] = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in rule.patterns
            ]

    def classify(self, error_message: str) -> Tuple[ErrorCategory, str]:
        """
        Classify an error message and return category with suggested action.

        Args:
            error_message: The error message to classify

        Returns:
            Tuple of (ErrorCategory, suggested_action)
        """
        if not error_message:
            return ErrorCategory.UNKNOWN, "No error message provided. Contact support."

        # Check each rule in priority order
        for rule in self.rules:
            patterns = self._compiled_patterns[rule.category]
            for pattern in patterns:
                if pattern.search(error_message):
                    return rule.category, rule.suggested_action

        # No match found - log for pattern improvement (sanitize PII first)
        # Only log first 100 chars to avoid PII leakage
        sanitized_msg = error_message[:100] + "..." if len(error_message) > 100 else error_message
        logger.warning(
            f"Unclassified error pattern detected",
            extra={"error_preview": sanitized_msg, "category": "UNKNOWN"}
        )
        return ErrorCategory.UNKNOWN, "An unexpected error occurred. Review the error details and contact support if the issue persists."

    def is_authentication_error(self, error_message: str) -> bool:
        """Check if error is authentication-related"""
        category, _ = self.classify(error_message)
        return category == ErrorCategory.AUTHENTICATION

    def is_retryable_error(self, error_message: str) -> bool:
        """Check if error is likely to be resolved by retrying"""
        category, _ = self.classify(error_message)
        return category in {
            ErrorCategory.CONNECTION,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.GMAIL_SERVICE
        }


# Global classifier instance
_error_classifier = ErrorClassifier()


def classify_error(error_message: str) -> Tuple[ErrorCategory, str]:
    """
    Convenience function to classify an error using the global classifier.

    Args:
        error_message: The error message to classify

    Returns:
        Tuple of (ErrorCategory, suggested_action)
    """
    return _error_classifier.classify(error_message)


def is_authentication_error(error_message: str) -> bool:
    """Convenience function to check if error is authentication-related"""
    return _error_classifier.is_authentication_error(error_message)


def is_retryable_error(error_message: str) -> bool:
    """Convenience function to check if error is retryable"""
    return _error_classifier.is_retryable_error(error_message)
```

### Phase 4: Add Dedicated Failure Endpoint

**File: `models/processing_failure_detail.py`** (NEW)

Create a detailed failure response model:

```python
from pydantic import BaseModel, Field
from typing import Optional
from models.error_classification import ErrorCategory


class ProcessingFailureDetail(BaseModel):
    """Detailed information about a processing failure"""
    email_address: str = Field(..., description="Email address that failed processing")
    error_message: str = Field(..., description="Full error message")
    error_time: Optional[str] = Field(None, description="ISO timestamp when error occurred")
    failed_step: Optional[str] = Field(None, description="Processing step where failure occurred")
    duration_seconds: Optional[float] = Field(None, description="Duration before failure (seconds)")

    # Classification fields
    error_category: ErrorCategory = Field(..., description="Classified error category")
    is_auth_error: bool = Field(..., description="True if authentication-related error")
    is_retryable: bool = Field(..., description="True if error may be resolved by retrying")
    suggested_action: str = Field(..., description="User-friendly remediation guidance")
```

**File: `api_service.py`**

Add a new endpoint specifically for querying processing failures:

```python
from datetime import datetime
from typing import Optional
from fastapi import Query, Header
from models.processing_failure_detail import ProcessingFailureDetail
from models.error_classification import classify_error, is_authentication_error, is_retryable_error

@app.get("/api/processing/failures", tags=["processing-status"])
async def get_processing_failures(
    email_address: Optional[str] = Query(None, description="Filter by specific email address"),
    limit: int = Query(10, ge=1, le=100, description="Maximum failures to return"),
    x_api_key: Optional[str] = Header(None)
):
    """
    Get recent processing failures with detailed error information

    Returns:
        List of failed processing runs with error messages, classification, and remediation guidance

    Use Cases:
        - Display error notifications in frontend dashboard
        - Diagnose authentication issues for specific accounts
        - Generate error reports for system administrators
        - Determine if errors are retryable or require manual intervention
    """
    verify_api_key(x_api_key)

    # Get recent runs (fetch more than needed to allow filtering)
    recent_runs_dicts = processing_status_manager.get_recent_runs(limit=limit * 2)

    failures = []
    for run_dict in recent_runs_dicts:
        if run_dict.get('final_state') == 'ERROR':
            # Filter by email address if specified
            if email_address and run_dict.get('email_address', '').lower() != email_address.lower():
                continue

            # Classify the error
            error_msg = run_dict.get('error_message', '')
            error_category, suggested_action = classify_error(error_msg)

            # Build typed failure detail
            failure = ProcessingFailureDetail(
                email_address=run_dict.get('email_address', 'unknown'),
                error_message=error_msg,
                error_time=run_dict.get('end_time'),
                failed_step=run_dict.get('final_step'),
                duration_seconds=run_dict.get('duration_seconds'),
                error_category=error_category,
                is_auth_error=is_authentication_error(error_msg),
                is_retryable=is_retryable_error(error_msg),
                suggested_action=suggested_action
            )

            failures.append(failure)

            if len(failures) >= limit:
                break

    return {
        'failures': [f.model_dump() for f in failures],
        'total_failures': len(failures),
        'timestamp': datetime.now().isoformat()
    }
```

### Phase 5: Enhance WebSocket Updates

**File: `services/websocket_handler.py`**

Update `broadcast_status()` to include explicit failure notification:

```python
from datetime import datetime, timezone
import time

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
- [ ] Convert dict responses to typed models (ProcessingRunDetails, CurrentProcessingStatus)
- [ ] Build failure summary from typed recent runs
- [ ] Update OpenAPI documentation
- [ ] Add integration tests

### Task 3: Create Error Classification System
- [ ] Create `ErrorCategory` enum with error types
- [ ] Create `ErrorPattern` model for classification rules
- [ ] Implement `ErrorClassifier` class with regex pattern matching
- [ ] Define `ERROR_CLASSIFICATION_RULES` with priorities
- [ ] Add convenience functions: `classify_error()`, `is_authentication_error()`, `is_retryable_error()`
- [ ] Add unit tests for error classification edge cases
- [ ] Add logger statement when errors don't match known patterns

### Task 4: Add Failures Endpoint with Typed Models
- [ ] Create `ProcessingFailureDetail` model extending ProcessingRunDetails
- [ ] Create `/api/processing/failures` endpoint
- [ ] Integrate error classification into endpoint
- [ ] Convert dict runs to ProcessingFailureDetail typed models
- [ ] Add endpoint to route documentation
- [ ] Add unit and integration tests

### Task 5: Enhance WebSocket Handler
- [ ] Update `broadcast_status()` with failure info
- [ ] Add failure notification message type
- [ ] Update WebSocket documentation
- [ ] Add WebSocket tests for failure scenarios

### Task 6: Frontend Integration (Out of Scope)
- [ ] Display failure notifications in dashboard
- [ ] Show actionable error messages with `suggested_action`
- [ ] Add "Verify Password" action button for auth errors
- [ ] Display error category badges (authentication, connection, etc.)

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
      "error_message": "Failed to connect to Gmail: [AUTHENTICATIONFAILED] Invalid credentials (Failure); LOGIN error: b'[AUTHENTICATIONFAILED] Invalid credentials (Failure)'. Gmail authentication failed. Ensure GMAIL_PASSWORD is a Gmail App Password (not your regular password), 16 characters, no spaces, and that 2-Step Verification is enabled.",
      "error_time": "2025-11-27T22:16:03.971000+00:00",
      "failed_step": "Processing failed: Failed to connect to Gmail",
      "duration_seconds": 3.97,
      "error_category": "authentication",
      "is_auth_error": true,
      "is_retryable": false,
      "suggested_action": "Verify that the Gmail App Password is correct (16 characters, no spaces) and that 2-Step Verification is enabled on the Gmail account. Generate a new App Password if needed."
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

## Backward Compatibility Matrix

| Component | Change | Existing Clients | New Clients | Notes |
|-----------|--------|------------------|-------------|-------|
| `ProcessingCurrentStatusResponse` | Added `failure_summary` field | ✅ Compatible | ✅ Enhanced | Optional field, defaults to `None` |
| `GET /api/processing/current-status` | Added `include_failure_summary` param | ✅ Compatible | ✅ Enhanced | Optional param, defaults to `True` |
| `ProcessingRunDetails` | Changed from `Dict` to typed model | ✅ Compatible | ✅ Enhanced | Pydantic auto-converts dicts to models |
| `CurrentProcessingStatus` | Changed from `Dict` to typed model | ✅ Compatible | ✅ Enhanced | Pydantic auto-converts dicts to models |
| WebSocket `status_update` | Added `has_failures`, `failure_count`, `most_recent_failure` | ✅ Compatible | ✅ Enhanced | Additive fields, existing fields unchanged |
| `GET /api/processing/failures` | New endpoint | N/A | ✅ New | No impact on existing clients |

**Pydantic Version Compatibility:**
- **Pydantic v2**: Use `.model_dump()` for serialization
- **Pydantic v1**: Use `.dict()` for serialization
- Code examples in this plan use Pydantic v2 syntax

**Python Version Compatibility:**
- **Python 3.9+**: Modern type hints (`list[str]`, `dict[...]`) work natively
- **Python 3.8 and earlier**: Replace with `typing.List`, `typing.Dict`, `typing.Tuple`

## Migration Notes

- All changes are backward compatible
- Existing API consumers will continue to work without modification
- New fields are optional with sensible defaults (`None` or `False`)
- Frontend can progressively adopt new failure fields
- No breaking changes to request/response contracts
- WebSocket clients can ignore new fields they don't recognize

## Success Criteria

1. Frontend can display processing failures with specific error messages
2. Authentication errors show actionable guidance to users
3. WebSocket updates include failure status in real-time
4. REST API provides dedicated failure querying capability
5. All existing functionality remains unchanged
