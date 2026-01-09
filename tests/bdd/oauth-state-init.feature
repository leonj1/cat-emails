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
