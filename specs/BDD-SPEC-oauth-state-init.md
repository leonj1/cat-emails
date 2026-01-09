# BDD Specification: OAuth State Init Endpoint

## Overview

This specification defines the behavior of the `POST /api/auth/gmail/init` endpoint, which allows frontend applications to pre-register client-generated OAuth state tokens with the backend. This enables popup-based OAuth flows where the frontend needs to control the state token to correlate OAuth responses with the originating popup window.

## User Stories

- As a frontend application, I want to pre-register a client-generated OAuth state token so that I can implement popup-based OAuth flows with state correlation.
- As a security-conscious system, I want to validate state tokens and redirect URIs so that OAuth flows are protected from CSRF and injection attacks.
- As a system administrator, I want rate limiting on state token registration so that the system is protected from flooding attacks.

## Feature Files

| Feature File | Scenarios | Coverage |
|--------------|-----------|----------|
| oauth-state-init.feature | 29 | Happy paths, state token validation, redirect URI validation, security, integration |

## Scenarios Summary

### oauth-state-init.feature

#### Happy Paths (6 scenarios)
1. Successful state token registration with valid inputs
2. Response includes correct expiration timestamp
3. State token with minimum valid length is accepted
4. State token with maximum valid length is accepted
5. HTTP localhost redirect URI is accepted for development
6. HTTP 127.0.0.1 redirect URI is accepted for development

#### State Token Validation (8 scenarios)
7. State token too short is rejected
8. State token too long is rejected
9. State token with spaces is rejected
10. State token with special characters is rejected
11. State token with underscores is rejected
12. Empty state token is rejected
13. Missing state token field is rejected
14. Whitespace-only state token is rejected

#### Redirect URI Validation (7 scenarios)
15. Empty redirect URI is rejected
16. Missing redirect URI field is rejected
17. Invalid URL format is rejected
18. Malformed URL is rejected
19. HTTP non-localhost redirect URI is rejected
20. FTP scheme redirect URI is rejected
21. Redirect URI exceeding maximum length is rejected

#### Security (4 scenarios)
22. Rate limiting rejects excessive requests from same IP
23. Rate limit resets after time window
24. Duplicate state token registration overwrites previous registration
25. Invalid JSON request body is rejected

#### Integration (4 scenarios)
26. Registered state token is found by callback endpoint
27. State token expires after 10 minutes
28. State token is valid within 10 minute window
29. Unregistered state token is rejected by callback

## Acceptance Criteria

### Endpoint Behavior
- [ ] POST /api/auth/gmail/init returns 200 for valid requests
- [ ] Response includes `success`, `expires_at`, and `state_token` fields
- [ ] Expiration timestamp is 10 minutes from registration time
- [ ] Expiration timestamp is in ISO 8601 format

### State Token Validation
- [ ] State token must be 16-64 characters long
- [ ] State token must contain only alphanumeric characters and dashes
- [ ] Empty or whitespace-only state tokens are rejected
- [ ] Missing state_token field returns appropriate error

### Redirect URI Validation
- [ ] Redirect URI must be a valid URL
- [ ] Redirect URI must use HTTPS (except localhost/127.0.0.1)
- [ ] HTTP is allowed for localhost and 127.0.0.1 (development)
- [ ] Redirect URI must not exceed 2048 characters
- [ ] Empty or missing redirect_uri returns appropriate error

### Security
- [ ] Rate limit: 10 requests per IP per minute
- [ ] Rate limit exceeded returns 429 status
- [ ] Duplicate state tokens overwrite previous registrations
- [ ] Invalid JSON returns 400 with appropriate error message

### Integration
- [ ] Registered state tokens can be validated by callback endpoint
- [ ] State tokens expire after 10 minutes
- [ ] Unregistered state tokens are rejected by callback

## Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| invalid_request | 400 | Missing required field or invalid JSON |
| invalid_state_token | 400 | State token format validation failed |
| invalid_redirect_uri | 400 | Redirect URI validation failed |
| rate_limit_exceeded | 429 | Too many requests from same IP |

## Data Models

### Request
```json
{
  "state_token": "string (16-64 chars, alphanumeric + dashes)",
  "redirect_uri": "string (valid HTTPS URL, max 2048 chars)"
}
```

### Success Response (200)
```json
{
  "success": true,
  "expires_at": "2026-01-09T12:10:00Z",
  "state_token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### Error Response (400/429)
```json
{
  "error": "invalid_state_token",
  "message": "State token must be at least 16 characters"
}
```

## Related Documentation

- Draft Specification: `specs/DRAFT-oauth-state-init-endpoint.md`
- Feature File: `tests/bdd/oauth-state-init.feature`
- Existing OAuth State Repository: `repositories/oauth_state_repository.py`

## Next Steps

1. **gherkin-to-test**: Convert Gherkin scenarios to TDD test prompts
2. **test-creator**: Write unit and integration tests from scenarios
3. **coder**: Implement endpoint to pass all tests
