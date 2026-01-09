# Gap Analysis: OAuth State Init Endpoint

## Overview

This analysis identifies reuse opportunities and new components needed for implementing the `POST /api/auth/gmail/init` endpoint based on the BDD scenarios in `tests/bdd/oauth-state-init.feature`.

## Existing Code Reuse Opportunities

### 1. OAuthStateRepository (HIGH REUSE)

**Location**: `repositories/oauth_state_repository.py`

**Reusable Components**:
- `store_state(state_token, redirect_uri, metadata)` - Core storage function already exists
- `get_state(state_token)` - Retrieval and validation already exists
- `delete_state(state_token)` - Cleanup already exists
- `STATE_TTL_MINUTES = 10` - 10-minute expiration already configured
- `cleanup_expired_states()` - Housekeeping already exists

**Usage in New Endpoint**:
```python
oauth_state_repo = OAuthStateRepository()
oauth_state_repo.store_state(state_token, redirect_uri)
```

**Gap**: The `store_state` method currently does INSERT only. For "duplicate state token overwrites previous registration" scenario, we need INSERT ON DUPLICATE KEY UPDATE or a delete-before-insert pattern.

### 2. RateLimiterService (HIGH REUSE)

**Location**: `services/rate_limiter_service.py`

**Reusable Components**:
- `check_rate_limit(key, interval_seconds)` - Thread-safe rate limiting
- Already used by force_process endpoint
- Returns `(allowed: bool, seconds_until_allowed: float)`

**Usage in New Endpoint**:
```python
rate_limiter = RateLimiterService(default_interval_seconds=60)
allowed, wait_time = rate_limiter.check_rate_limit(client_ip, interval_seconds=6)  # 10 per minute
```

**Gap**: Current rate limiter tracks "last request time" per key. For "10 requests per IP per minute" we need a sliding window counter, not interval-based limiting.

### 3. API Service Patterns (HIGH REUSE)

**Location**: `api_service.py`

**Reusable Patterns**:
- FastAPI endpoint structure
- `Request` object for IP extraction
- JSON error response format: `{"error": "code", "message": "description"}`
- CORS configuration already supports localhost origins
- Pydantic models for request/response validation

**Example Pattern** (from force_process endpoint):
```python
@app.post("/api/endpoint", response_model=ResponseModel)
async def endpoint_handler(request: Request, body: RequestModel):
    client_ip = request.client.host
    # validation and processing
    return JSONResponse(status_code=200, content={...})
```

### 4. OAuth Models (MEDIUM REUSE)

**Location**: `models/oauth_models.py`

**Existing Models**:
- `OAuthCallbackRequest` - Request body pattern
- `OAuthCallbackResponse` - Response structure

**New Models Needed**:
- `OAuthStateInitRequest` - state_token, redirect_uri
- `OAuthStateInitResponse` - success, expires_at, state_token
- `OAuthStateInitErrorResponse` - error, message

### 5. Integration Test Patterns (HIGH REUSE)

**Location**: `tests/integration/test_oauth_state_repository.py`

**Reusable Patterns**:
- Pytest fixtures for repository setup
- Database cleanup fixtures
- Test patterns for store/retrieve/delete
- Expiration testing patterns

## New Components Needed

### 1. State Token Validator

**Purpose**: Validate state token format (16-64 chars, alphanumeric + dashes)

**Location**: `validators/state_token_validator.py` or inline in endpoint

**Implementation**:
```python
import re

def validate_state_token(token: str) -> tuple[bool, str | None]:
    """Validate state token format.

    Returns:
        (is_valid, error_message or None)
    """
    if not token or not token.strip():
        return False, "State token is required"
    if len(token) < 16:
        return False, "State token must be at least 16 characters"
    if len(token) > 64:
        return False, "State token must not exceed 64 characters"
    if not re.match(r'^[a-zA-Z0-9-]+$', token):
        return False, "State token must contain only alphanumeric characters and dashes"
    return True, None
```

### 2. Redirect URI Validator

**Purpose**: Validate redirect URI format and security requirements

**Location**: `validators/redirect_uri_validator.py` or inline in endpoint

**Implementation**:
```python
from urllib.parse import urlparse

def validate_redirect_uri(uri: str) -> tuple[bool, str | None]:
    """Validate redirect URI format and security.

    Returns:
        (is_valid, error_message or None)
    """
    if not uri or not uri.strip():
        return False, "Redirect URI is required"
    if len(uri) > 2048:
        return False, "Redirect URI must not exceed 2048 characters"

    try:
        parsed = urlparse(uri)
    except Exception:
        return False, "Redirect URI must be a valid URL"

    if not parsed.scheme or not parsed.netloc:
        return False, "Redirect URI must be a valid URL"

    is_localhost = parsed.netloc.startswith(('localhost', '127.0.0.1'))

    if parsed.scheme == 'http' and not is_localhost:
        return False, "Redirect URI must use HTTPS (or HTTP for localhost)"

    if parsed.scheme not in ('http', 'https'):
        return False, "Redirect URI must use HTTPS (or HTTP for localhost)"

    return True, None
```

### 3. IP-Based Rate Limiter (Sliding Window)

**Purpose**: Rate limit based on IP with sliding window (10 requests per minute)

**Location**: Extend `services/rate_limiter_service.py` or new `services/ip_rate_limiter.py`

**Implementation Approach**:
- Track list of timestamps per IP
- On check: remove timestamps older than window, count remaining
- If count >= limit, deny; else allow and record

### 4. Request/Response Models

**Location**: `models/oauth_state_init_models.py`

```python
from pydantic import BaseModel
from typing import Optional

class OAuthStateInitRequest(BaseModel):
    state_token: str
    redirect_uri: str

class OAuthStateInitResponse(BaseModel):
    success: bool
    expires_at: str  # ISO 8601 format
    state_token: str

class OAuthStateInitErrorResponse(BaseModel):
    error: str
    message: str
```

### 5. Endpoint Handler

**Location**: `api_service.py` (add new endpoint)

**Endpoint**: `POST /api/auth/gmail/init`

## Database Schema

The existing `oauth_state` table should work:
```sql
CREATE TABLE oauth_state (
    state_token VARCHAR(255) PRIMARY KEY,
    redirect_uri TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    metadata JSON
);
```

**Potential Change**: Ensure `state_token` has UNIQUE constraint for upsert behavior.

## Summary

| Component | Status | Action |
|-----------|--------|--------|
| OAuthStateRepository | EXISTS | Modify `store_state` for upsert |
| RateLimiterService | EXISTS | Add sliding window variant |
| State Token Validator | NEW | Create validation function |
| Redirect URI Validator | NEW | Create validation function |
| Request/Response Models | NEW | Create Pydantic models |
| Endpoint Handler | NEW | Add to api_service.py |
| Integration Tests | PATTERN EXISTS | Create new tests |

## Refactoring Recommendation

**Recommendation**: Proceed with implementation (GO)

**Rationale**:
1. Core infrastructure exists (OAuthStateRepository, rate limiter patterns)
2. Changes are additive (new endpoint, new validators)
3. Minor modification to store_state for upsert behavior
4. No breaking changes to existing functionality

**Risk Level**: LOW - additive changes only
