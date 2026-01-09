---
executor: bdd
source_feature: ./tests/bdd/oauth-state-init.feature
---

<objective>
Implement the OAuth State Init Endpoint feature as defined by the BDD scenarios below.
The implementation must make all 29 Gherkin scenarios pass.

This endpoint enables popup-based OAuth flows by allowing frontends to pre-register
client-generated state tokens with the backend for CSRF protection and state correlation.
</objective>

<gherkin>
Feature: OAuth State Init Endpoint
  As a frontend application
  I want to pre-register a client-generated OAuth state token
  So that I can implement popup-based OAuth flows with state correlation

  Background:
    Given the OAuth state init endpoint is available
    And the OAuth state storage is accessible

  # === HAPPY PATHS ===

  Scenario: Successful state token registration with valid inputs
    Given a valid state token "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 200
    And the response should contain success true
    And the response should contain the registered state token
    And the response should contain an expiration timestamp

  Scenario: Response includes correct expiration timestamp
    Given a valid state token "valid-state-token-1234567890"
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 200
    And the expiration timestamp should be approximately 10 minutes from now
    And the expiration timestamp should be in ISO 8601 format

  Scenario: State token with minimum valid length is accepted
    Given a state token exactly 16 characters long "abcdefghij123456"
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 200
    And the response should contain success true

  Scenario: State token with maximum valid length is accepted
    Given a state token exactly 64 characters long
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 200
    And the response should contain success true

  Scenario: HTTP localhost redirect URI is accepted for development
    Given a valid state token "dev-state-token-12345678"
    And a redirect URI "http://localhost:3000/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 200
    And the response should contain success true

  Scenario: HTTP 127.0.0.1 redirect URI is accepted for development
    Given a valid state token "dev-state-token-12345678"
    And a redirect URI "http://127.0.0.1:8080/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 200
    And the response should contain success true

  # === STATE TOKEN VALIDATION ===

  Scenario: State token too short is rejected
    Given a state token "short12345" that is only 10 characters
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_state_token"
    And the response should contain message "State token must be at least 16 characters"

  Scenario: State token too long is rejected
    Given a state token that is 65 characters long
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_state_token"
    And the response should contain message "State token must not exceed 64 characters"

  Scenario: State token with spaces is rejected
    Given a state token "invalid state token 123"
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_state_token"
    And the response should contain message "State token must contain only alphanumeric characters and dashes"

  Scenario: State token with special characters is rejected
    Given a state token "invalid!@#$%token123456"
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_state_token"
    And the response should contain message "State token must contain only alphanumeric characters and dashes"

  Scenario: State token with underscores is rejected
    Given a state token "invalid_underscore_123456"
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_state_token"
    And the response should contain message "State token must contain only alphanumeric characters and dashes"

  Scenario: Empty state token is rejected
    Given an empty state token ""
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_state_token"
    And the response should contain message "State token is required"

  Scenario: Missing state token field is rejected
    Given a request body without a state_token field
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_request"
    And the response should contain message "State token is required"

  Scenario: Whitespace-only state token is rejected
    Given a state token "                " containing only spaces
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_state_token"
    And the response should contain message "State token is required"

  # === REDIRECT URI VALIDATION ===

  Scenario: Empty redirect URI is rejected
    Given a valid state token "valid-state-token-1234567890"
    And an empty redirect URI ""
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_redirect_uri"
    And the response should contain message "Redirect URI is required"

  Scenario: Missing redirect URI field is rejected
    Given a valid state token "valid-state-token-1234567890"
    And a request body without a redirect_uri field
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_request"
    And the response should contain message "Redirect URI is required"

  Scenario: Invalid URL format is rejected
    Given a valid state token "valid-state-token-1234567890"
    And a redirect URI "not-a-valid-url"
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_redirect_uri"
    And the response should contain message "Redirect URI must be a valid URL"

  Scenario: Malformed URL is rejected
    Given a valid state token "valid-state-token-1234567890"
    And a redirect URI "https://[invalid"
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_redirect_uri"
    And the response should contain message "Redirect URI must be a valid URL"

  Scenario: HTTP non-localhost redirect URI is rejected
    Given a valid state token "valid-state-token-1234567890"
    And a redirect URI "http://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_redirect_uri"
    And the response should contain message "Redirect URI must use HTTPS (or HTTP for localhost)"

  Scenario: FTP scheme redirect URI is rejected
    Given a valid state token "valid-state-token-1234567890"
    And a redirect URI "ftp://myapp.example.com/oauth/callback"
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_redirect_uri"
    And the response should contain message "Redirect URI must use HTTPS (or HTTP for localhost)"

  Scenario: Redirect URI exceeding maximum length is rejected
    Given a valid state token "valid-state-token-1234567890"
    And a redirect URI that exceeds 2048 characters
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_redirect_uri"
    And the response should contain message "Redirect URI must not exceed 2048 characters"

  # === SECURITY ===

  Scenario: Rate limiting rejects excessive requests from same IP
    Given a valid state token "rate-limit-test-12345678"
    And a valid redirect URI "https://myapp.example.com/oauth/callback"
    And 10 state token registrations have been made from the same IP in the last minute
    When the frontend requests state token registration
    Then the response should have status 429
    And the response should contain error "rate_limit_exceeded"
    And the response should contain message "Too many state token registration requests. Try again later."

  Scenario: Rate limit resets after time window
    Given 10 state token registrations were made from the same IP
    And the rate limit time window has elapsed
    When the frontend requests state token registration with a valid token
    Then the response should have status 200
    And the response should contain success true

  Scenario: Duplicate state token registration overwrites previous registration
    Given a state token "duplicate-token-123456789012" was previously registered
    And a valid redirect URI "https://newapp.example.com/oauth/callback"
    When the frontend requests state token registration with the same token
    Then the response should have status 200
    And the response should contain success true
    And the new redirect URI should be associated with the state token

  Scenario: Invalid JSON request body is rejected
    Given a request body with invalid JSON
    When the frontend requests state token registration
    Then the response should have status 400
    And the response should contain error "invalid_request"
    And the response should contain message "Invalid JSON body"

  # === INTEGRATION ===

  Scenario: Registered state token is found by callback endpoint
    Given a state token "integration-test-123456789" is pre-registered
    And the redirect URI "https://myapp.example.com/oauth/callback" is associated
    When the OAuth callback endpoint validates the state token
    Then the state token should be recognized as valid
    And the associated redirect URI should be returned

  Scenario: State token expires after 10 minutes
    Given a state token "expiring-token-123456789012" was registered 11 minutes ago
    When the OAuth callback endpoint validates the state token
    Then the state token should be recognized as expired
    And the validation should fail

  Scenario: State token is valid within 10 minute window
    Given a state token "valid-window-123456789012" was registered 9 minutes ago
    When the OAuth callback endpoint validates the state token
    Then the state token should be recognized as valid

  Scenario: Unregistered state token is rejected by callback
    Given a state token "never-registered-1234567890" was never registered
    When the OAuth callback endpoint validates the state token
    Then the state token should be recognized as invalid
    And the validation should fail
</gherkin>

<requirements>
Based on the 29 Gherkin scenarios, implement:

## 1. POST /api/auth/gmail/init Endpoint

Create a new FastAPI endpoint that accepts:
- Request Body: `{"state_token": "string", "redirect_uri": "string"}`
- Returns: `{"success": true, "expires_at": "ISO8601", "state_token": "string"}`

## 2. State Token Validation

Implement validation rules:
- Length: 16-64 characters
- Characters: alphanumeric and dashes only (`^[a-zA-Z0-9-]+$`)
- Required: non-empty, non-whitespace
- Error code: `invalid_state_token`

## 3. Redirect URI Validation

Implement validation rules:
- Required: non-empty
- Maximum length: 2048 characters
- Must be valid URL format
- Must use HTTPS (except localhost/127.0.0.1 for development)
- Error code: `invalid_redirect_uri`

## 4. Rate Limiting

Implement IP-based rate limiting:
- Limit: 10 requests per IP per minute
- Sliding window algorithm
- Error code: `rate_limit_exceeded`
- HTTP status: 429

## 5. State Token Storage

Extend OAuthStateRepository for:
- Upsert behavior (duplicate tokens overwrite)
- 10-minute expiration
- Store redirect_uri association

## 6. Error Response Format

Consistent error responses:
```json
{
  "error": "error_code",
  "message": "Human-readable message"
}
```

Error codes:
- `invalid_request` - Missing required field or invalid JSON
- `invalid_state_token` - State token format validation failed
- `invalid_redirect_uri` - Redirect URI validation failed
- `rate_limit_exceeded` - Too many requests

## Edge Cases to Handle

- Empty string state token
- Whitespace-only state token
- Missing state_token field in request
- State token with spaces, special chars, underscores
- State token at boundary lengths (16 and 64 chars)
- Empty redirect URI
- Missing redirect_uri field
- Malformed URLs
- HTTP on non-localhost domains
- Non-HTTP/HTTPS schemes (ftp)
- Redirect URI over 2048 characters
- Invalid JSON body
- Rate limit at boundary (10th vs 11th request)
- Duplicate state token registration
- Expired state tokens
- Never-registered state tokens

</requirements>

<context>
BDD Specification: specs/BDD-SPEC-oauth-state-init.md
Gap Analysis: specs/GAP-ANALYSIS-oauth-state-init.md
Draft Specification: specs/DRAFT-oauth-state-init-endpoint.md

## Reuse Opportunities (from gap analysis)

### OAuthStateRepository (repositories/oauth_state_repository.py)
- `store_state(state_token, redirect_uri, metadata)` - Core storage
- `get_state(state_token)` - Retrieval and validation
- `STATE_TTL_MINUTES = 10` - Expiration already configured
- Modify for upsert behavior (delete + insert or ON DUPLICATE KEY UPDATE)

### RateLimiterService (services/rate_limiter_service.py)
- Existing rate limiter pattern
- Need sliding window variant for "10 per minute" vs interval-based
- Or create new IPRateLimiter class

### API Patterns (api_service.py)
- FastAPI endpoint structure
- Request object for client IP extraction
- JSON error response format
- CORS already supports localhost

### Test Patterns (tests/integration/test_oauth_state_repository.py)
- Pytest fixtures for repository setup
- Database cleanup fixtures
- Expiration testing patterns

## New Components Needed

1. **State Token Validator** - validation function for token format
2. **Redirect URI Validator** - validation function for URI format/security
3. **IP Rate Limiter** - sliding window rate limiter by IP address
4. **Request/Response Models** - Pydantic models for the endpoint
5. **Endpoint Handler** - FastAPI route handler

</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

## Architecture Guidelines

- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Maintain consistency with project structure

## Suggested File Structure

```
models/
  oauth_state_init_models.py    # Request/Response Pydantic models

validators/
  state_token_validator.py      # State token validation
  redirect_uri_validator.py     # Redirect URI validation

services/
  ip_rate_limiter.py           # Sliding window rate limiter (or extend rate_limiter_service.py)

api_service.py                 # Add new endpoint handler

tests/
  unit/
    test_state_token_validator.py
    test_redirect_uri_validator.py
    test_ip_rate_limiter.py
  integration/
    test_oauth_state_init_endpoint.py
```

## Implementation Order

1. Create Pydantic models for request/response
2. Implement state token validator with unit tests
3. Implement redirect URI validator with unit tests
4. Implement/extend rate limiter for IP-based sliding window
5. Modify OAuthStateRepository for upsert behavior
6. Create endpoint handler in api_service.py
7. Write integration tests for endpoint

## Key Implementation Details

### State Token Validator
```python
import re

def validate_state_token(token: str | None) -> tuple[str | None, str | None]:
    """Returns (error_code, error_message) or (None, None) if valid."""
    if token is None:
        return "invalid_request", "State token is required"
    if not token.strip():
        return "invalid_state_token", "State token is required"
    if len(token) < 16:
        return "invalid_state_token", "State token must be at least 16 characters"
    if len(token) > 64:
        return "invalid_state_token", "State token must not exceed 64 characters"
    if not re.match(r'^[a-zA-Z0-9-]+$', token):
        return "invalid_state_token", "State token must contain only alphanumeric characters and dashes"
    return None, None
```

### Redirect URI Validator
```python
from urllib.parse import urlparse

def validate_redirect_uri(uri: str | None) -> tuple[str | None, str | None]:
    """Returns (error_code, error_message) or (None, None) if valid."""
    if uri is None:
        return "invalid_request", "Redirect URI is required"
    if not uri.strip():
        return "invalid_redirect_uri", "Redirect URI is required"
    if len(uri) > 2048:
        return "invalid_redirect_uri", "Redirect URI must not exceed 2048 characters"

    try:
        parsed = urlparse(uri)
        if not parsed.scheme or not parsed.netloc:
            return "invalid_redirect_uri", "Redirect URI must be a valid URL"
    except Exception:
        return "invalid_redirect_uri", "Redirect URI must be a valid URL"

    is_localhost = parsed.netloc.startswith(('localhost', '127.0.0.1'))
    if parsed.scheme not in ('http', 'https'):
        return "invalid_redirect_uri", "Redirect URI must use HTTPS (or HTTP for localhost)"
    if parsed.scheme == 'http' and not is_localhost:
        return "invalid_redirect_uri", "Redirect URI must use HTTPS (or HTTP for localhost)"

    return None, None
```

### OAuthStateRepository Upsert
Modify `store_state` to handle duplicates:
```python
def store_state(self, state_token, redirect_uri, metadata=None):
    # Delete existing if present
    self.delete_state(state_token)
    # Then insert new
    # ... existing insert logic
```
</implementation>

<verification>
All Gherkin scenarios must pass:

### Happy Paths (6 scenarios)
- [ ] Scenario: Successful state token registration with valid inputs
- [ ] Scenario: Response includes correct expiration timestamp
- [ ] Scenario: State token with minimum valid length is accepted
- [ ] Scenario: State token with maximum valid length is accepted
- [ ] Scenario: HTTP localhost redirect URI is accepted for development
- [ ] Scenario: HTTP 127.0.0.1 redirect URI is accepted for development

### State Token Validation (8 scenarios)
- [ ] Scenario: State token too short is rejected
- [ ] Scenario: State token too long is rejected
- [ ] Scenario: State token with spaces is rejected
- [ ] Scenario: State token with special characters is rejected
- [ ] Scenario: State token with underscores is rejected
- [ ] Scenario: Empty state token is rejected
- [ ] Scenario: Missing state token field is rejected
- [ ] Scenario: Whitespace-only state token is rejected

### Redirect URI Validation (7 scenarios)
- [ ] Scenario: Empty redirect URI is rejected
- [ ] Scenario: Missing redirect URI field is rejected
- [ ] Scenario: Invalid URL format is rejected
- [ ] Scenario: Malformed URL is rejected
- [ ] Scenario: HTTP non-localhost redirect URI is rejected
- [ ] Scenario: FTP scheme redirect URI is rejected
- [ ] Scenario: Redirect URI exceeding maximum length is rejected

### Security (4 scenarios)
- [ ] Scenario: Rate limiting rejects excessive requests from same IP
- [ ] Scenario: Rate limit resets after time window
- [ ] Scenario: Duplicate state token registration overwrites previous registration
- [ ] Scenario: Invalid JSON request body is rejected

### Integration (4 scenarios)
- [ ] Scenario: Registered state token is found by callback endpoint
- [ ] Scenario: State token expires after 10 minutes
- [ ] Scenario: State token is valid within 10 minute window
- [ ] Scenario: Unregistered state token is rejected by callback
</verification>

<success_criteria>
- All 29 Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- POST /api/auth/gmail/init endpoint is functional
- Rate limiting protects against abuse
- State tokens integrate with existing OAuth callback flow
- Error responses follow consistent format
</success_criteria>
