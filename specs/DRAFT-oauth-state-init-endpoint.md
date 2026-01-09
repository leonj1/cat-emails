# DRAFT Specification: OAuth State Init Endpoint

> **Status**: DRAFT
> **Task**: Create POST /api/auth/gmail/init endpoint for popup-based OAuth flow
> **Author**: Feature Spec Architect
> **Date**: 2026-01-09

## Overview

This specification defines a new API endpoint that allows frontend applications to pre-register client-generated OAuth state tokens with the backend. This enables popup-based OAuth flows where the frontend needs to control the state token to correlate OAuth responses with the originating popup window.

## Problem Statement

The current OAuth flow generates state tokens server-side in `/api/auth/gmail/authorize`. This approach does not support popup-based OAuth flows where:
1. The frontend opens a popup window for OAuth
2. The popup navigates to Google's OAuth consent screen
3. Google redirects back to the callback URL
4. The frontend popup needs to communicate the result back to the parent window

In popup flows, the frontend needs to control the state token to:
- Correlate the OAuth response with the specific popup window
- Validate that the response came from an expected OAuth flow
- Pass context between the popup and parent window

## Solution: Pre-Registration Endpoint

Create a new endpoint `POST /api/auth/gmail/init` that allows the frontend to:
1. Generate a state token client-side (e.g., `crypto.randomUUID()`)
2. Pre-register that state token with the backend
3. Construct the OAuth authorization URL using the pre-registered state
4. Complete the OAuth flow via popup
5. Backend validates the state during callback (existing flow)

---

## Interfaces Needed

### 1. IOAuthStateInitRequest (Input Interface)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class OAuthStateInitRequest:
    """Request to pre-register a client-generated OAuth state token."""
    state_token: str    # Client-generated state token (16-64 chars)
    redirect_uri: str   # OAuth redirect URI for callback
```

### 2. IOAuthStateInitResponse (Output Interface)

```python
@dataclass
class OAuthStateInitResponse:
    """Response confirming state token registration."""
    success: bool           # Whether registration succeeded
    expires_at: str         # ISO 8601 timestamp when token expires
    state_token: str        # Echo back the registered token (for confirmation)
```

### 3. IOAuthStateInitValidator (Validation Interface)

```python
class IOAuthStateInitValidator(ABC):
    """Validates OAuth state init requests."""

    @abstractmethod
    def validate_state_token(self, state_token: str) -> tuple[bool, str | None]:
        """
        Validate state token format.

        Args:
            state_token: The client-provided state token

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid.
        """
        pass

    @abstractmethod
    def validate_redirect_uri(self, redirect_uri: str) -> tuple[bool, str | None]:
        """
        Validate redirect URI is allowed.

        Args:
            redirect_uri: The requested redirect URI

        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid.
        """
        pass
```

### 4. IOAuthStateRepository (Storage Interface - Existing)

```python
class IOAuthStateRepository(ABC):
    """Repository for OAuth state token storage."""

    @abstractmethod
    def store_state(self, state_token: str, redirect_uri: str, ttl_seconds: int) -> None:
        """
        Store a state token with associated redirect URI.

        Args:
            state_token: The state token to store
            redirect_uri: The associated redirect URI
            ttl_seconds: Time-to-live in seconds
        """
        pass

    @abstractmethod
    def validate_state(self, state_token: str) -> str | None:
        """
        Validate and consume a state token.

        Args:
            state_token: The state token to validate

        Returns:
            The associated redirect_uri if valid, None otherwise
        """
        pass
```

### 5. IOAuthStateInitService (Business Logic Interface)

```python
class IOAuthStateInitService(ABC):
    """Service for handling OAuth state initialization."""

    @abstractmethod
    def init_oauth_state(self, request: OAuthStateInitRequest) -> OAuthStateInitResponse:
        """
        Initialize (pre-register) a client-generated OAuth state token.

        Args:
            request: The state init request

        Returns:
            Response with registration result

        Raises:
            ValidationError: If request validation fails
            RateLimitError: If rate limit exceeded
        """
        pass
```

---

## Data Models

### OAuthStateInitRequest

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| state_token | string | 16-64 chars, alphanumeric + dashes | Client-generated state token |
| redirect_uri | string | Valid URL, max 2048 chars | OAuth callback redirect URI |

### OAuthStateInitResponse

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether registration succeeded |
| expires_at | string (ISO 8601) | Token expiration timestamp |
| state_token | string | Echo of registered token |

### Error Response

| Field | Type | Description |
|-------|------|-------------|
| error | string | Error code |
| message | string | Human-readable error message |

---

## Logic Flow

### Endpoint Handler Pseudocode

```
FUNCTION handle_oauth_init(request_body):
    // 1. Parse and validate request
    request = parse_json(request_body)
    IF request is None:
        RETURN error_response(400, "invalid_request", "Invalid JSON body")

    // 2. Validate state token format
    (valid, error) = validator.validate_state_token(request.state_token)
    IF NOT valid:
        RETURN error_response(400, "invalid_state_token", error)

    // 3. Validate redirect URI
    (valid, error) = validator.validate_redirect_uri(request.redirect_uri)
    IF NOT valid:
        RETURN error_response(400, "invalid_redirect_uri", error)

    // 4. Check rate limit (by IP or session)
    IF rate_limiter.is_exceeded(client_ip):
        RETURN error_response(429, "rate_limit_exceeded", "Too many requests")

    // 5. Calculate expiration (10 minutes from now)
    TTL_SECONDS = 600
    expires_at = current_time() + TTL_SECONDS

    // 6. Store state token (reuse existing repository)
    state_repository.store_state(
        state_token=request.state_token,
        redirect_uri=request.redirect_uri,
        ttl_seconds=TTL_SECONDS
    )

    // 7. Return success response
    RETURN success_response(
        success=True,
        expires_at=expires_at.iso_format(),
        state_token=request.state_token
    )
```

### State Token Validation Pseudocode

```
FUNCTION validate_state_token(state_token):
    // Check non-empty
    IF state_token is None OR state_token.strip() == "":
        RETURN (False, "State token is required")

    // Check length (16-64 characters)
    IF len(state_token) < 16:
        RETURN (False, "State token must be at least 16 characters")
    IF len(state_token) > 64:
        RETURN (False, "State token must not exceed 64 characters")

    // Check character set (alphanumeric + dashes only)
    ALLOWED_PATTERN = /^[a-zA-Z0-9\-]+$/
    IF NOT state_token.matches(ALLOWED_PATTERN):
        RETURN (False, "State token must contain only alphanumeric characters and dashes")

    RETURN (True, None)
```

### Redirect URI Validation Pseudocode

```
FUNCTION validate_redirect_uri(redirect_uri):
    // Check non-empty
    IF redirect_uri is None OR redirect_uri.strip() == "":
        RETURN (False, "Redirect URI is required")

    // Check max length
    IF len(redirect_uri) > 2048:
        RETURN (False, "Redirect URI must not exceed 2048 characters")

    // Check valid URL format
    parsed = parse_url(redirect_uri)
    IF parsed is None:
        RETURN (False, "Redirect URI must be a valid URL")

    // Check scheme is https (or http for localhost)
    IF parsed.scheme != "https":
        IF NOT (parsed.scheme == "http" AND parsed.host IN ["localhost", "127.0.0.1"]):
            RETURN (False, "Redirect URI must use HTTPS (or HTTP for localhost)")

    RETURN (True, None)
```

---

## API Specification

### Endpoint

```
POST /api/auth/gmail/init
Content-Type: application/json
```

### Request Body

```json
{
    "state_token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "redirect_uri": "https://myapp.example.com/oauth/callback"
}
```

### Success Response (200 OK)

```json
{
    "success": true,
    "expires_at": "2026-01-09T12:10:00Z",
    "state_token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### Error Response (400 Bad Request)

```json
{
    "error": "invalid_state_token",
    "message": "State token must be at least 16 characters"
}
```

### Error Response (429 Too Many Requests)

```json
{
    "error": "rate_limit_exceeded",
    "message": "Too many state token registration requests. Try again later."
}
```

---

## Security Considerations

### 1. State Token Format Validation
- **Minimum length**: 16 characters (prevents guessable tokens)
- **Maximum length**: 64 characters (prevents DoS via oversized tokens)
- **Character set**: Alphanumeric + dashes only (prevents injection attacks)

### 2. Rate Limiting
- Limit: 10 requests per IP per minute
- Prevents state token flooding attacks
- Returns 429 status code when exceeded

### 3. Time-to-Live (TTL)
- Same as server-generated tokens: 10 minutes
- Prevents stale token accumulation
- Automatically cleaned up by existing TTL mechanism

### 4. Redirect URI Validation
- Must be valid URL
- Must use HTTPS (except localhost for development)
- Maximum length 2048 characters

### 5. No Authentication Required
- This endpoint is intentionally unauthenticated
- Authentication happens after OAuth callback
- State token provides CSRF protection during flow

---

## Integration Points

### Existing Components (Reused)
1. **OAuthStateRepository.store_state()** - Used to store the pre-registered state
2. **OAuth callback endpoint** - Validates any registered state token (no changes needed)
3. **State table TTL cleanup** - Existing mechanism cleans expired tokens

### New Components
1. **POST /api/auth/gmail/init endpoint** - New endpoint handler
2. **OAuthStateInitValidator** - New validation class
3. **OAuthStateInitRequest/Response models** - New data models
4. **Rate limiter** - New or reused rate limiting mechanism

### Frontend Flow (Reference)

```javascript
// 1. Generate state token client-side
const stateToken = crypto.randomUUID();

// 2. Pre-register with backend
const initResponse = await fetch('/api/auth/gmail/init', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        state_token: stateToken,
        redirect_uri: window.location.origin + '/oauth/callback'
    })
});

// 3. Construct OAuth URL with registered state
const oauthUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
    `client_id=${CLIENT_ID}&` +
    `redirect_uri=${encodeURIComponent(REDIRECT_URI)}&` +
    `scope=${encodeURIComponent(SCOPES)}&` +
    `state=${stateToken}&` +
    `response_type=code&` +
    `access_type=offline&` +
    `prompt=consent`;

// 4. Open popup
const popup = window.open(oauthUrl, 'oauth', 'width=500,height=600');

// 5. Listen for callback message
window.addEventListener('message', (event) => {
    if (event.data.type === 'oauth_callback') {
        // Verify state matches
        if (event.data.state === stateToken) {
            // Continue with authenticated flow
        }
    }
});
```

---

## Context Budget

| Category | Estimate |
|----------|----------|
| Files to read | 3 (~150 lines) |
| New code to write | ~80 lines |
| Test code to write | ~120 lines |
| **Estimated context usage** | **15%** |

### Breakdown

**New Code (~80 lines)**:
- Endpoint handler: 30 lines
- Validator class: 25 lines
- Request/Response models: 15 lines
- Rate limiter integration: 10 lines

**Test Code (~120 lines)**:
- Happy path tests: 20 lines
- State token validation tests: 40 lines
- Redirect URI validation tests: 30 lines
- Rate limiting tests: 20 lines
- Error handling tests: 10 lines

---

## Acceptance Criteria

1. **Endpoint Exists**: POST /api/auth/gmail/init returns 200 for valid requests
2. **State Token Validation**: Rejects tokens < 16 or > 64 characters
3. **State Token Storage**: Token can be validated by existing callback endpoint
4. **TTL Applied**: Stored token expires after 10 minutes
5. **Rate Limiting**: Returns 429 after 10 requests/minute from same IP
6. **Error Responses**: Returns appropriate error codes and messages
7. **Integration**: Popup flow works end-to-end with pre-registered state

---

## Test Scenarios

### Unit Tests

1. **Valid state token accepted** - 36-char UUID is valid
2. **Short state token rejected** - 15-char token returns error
3. **Long state token rejected** - 65-char token returns error
4. **Invalid characters rejected** - Token with spaces/special chars fails
5. **Empty state token rejected** - Empty string returns error
6. **Valid redirect URI accepted** - HTTPS URL is valid
7. **HTTP localhost accepted** - http://localhost:3000 is valid
8. **HTTP non-localhost rejected** - http://example.com fails
9. **Invalid URL rejected** - Malformed URL fails
10. **Rate limit enforced** - 11th request in 1 minute returns 429

### Integration Tests

1. **Pre-registered state validates in callback** - Full flow works
2. **Expired state rejected in callback** - 11-minute-old token fails
3. **Unregistered state rejected** - Random token fails callback

---

## Open Questions

1. **Rate limit configuration**: Should rate limit be configurable via environment variable?
2. **Metrics/Logging**: Should we log state registrations for audit purposes?
3. **Redirect URI allowlist**: Should we maintain an allowlist of valid redirect URIs?
