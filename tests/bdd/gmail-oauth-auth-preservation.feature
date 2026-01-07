Feature: Gmail OAuth Auth Method Preservation
  As an email management system
  I want to preserve OAuth authentication settings when processing OAuth accounts
  So that OAuth-connected accounts remain functional after processing runs

  Background:
    Given the email processing system is initialized
    And the account service is available

  # === HAPPY PATHS ===

  Scenario: OAuth account authentication method is not overwritten during processing
    Given an account "oauth-user@gmail.com" is connected via OAuth
    And the account has auth_method "oauth"
    When the Gmail fetcher is created with a connection service for "oauth-user@gmail.com"
    Then the account service should not update the auth_method
    And the account "oauth-user@gmail.com" should still have auth_method "oauth"

  Scenario: IMAP account authentication method is set correctly during processing
    Given an account "imap-user@gmail.com" is configured for IMAP
    When the Gmail fetcher is created without a connection service for "imap-user@gmail.com"
    And an app password "test-app-password" is provided
    Then the account service should set auth_method to "imap"
    And the account should have the app_password stored

  Scenario: OAuth account remains functional after multiple processing runs
    Given an account "oauth-user@gmail.com" is connected via OAuth
    And the account has auth_method "oauth"
    When the Gmail fetcher processes emails for "oauth-user@gmail.com" with OAuth connection
    And the Gmail fetcher processes emails for "oauth-user@gmail.com" with OAuth connection again
    Then the account "oauth-user@gmail.com" should still have auth_method "oauth"
    And the account should remain functional

  # === EDGE CASES ===

  Scenario: New IMAP account is created with correct auth method
    Given no account exists for "new-imap@gmail.com"
    When the Gmail fetcher is created without a connection service for "new-imap@gmail.com"
    And an app password "new-app-password" is provided
    Then a new account should be created for "new-imap@gmail.com"
    And the new account should have auth_method "imap"
    And the new account should have the app_password stored

  Scenario: Existing OAuth account is not modified when processing with OAuth
    Given an account "existing-oauth@gmail.com" exists with:
      | auth_method          | oauth                    |
      | oauth_refresh_token  | existing-refresh-token   |
    When the Gmail fetcher is created with a connection service for "existing-oauth@gmail.com"
    Then the account "existing-oauth@gmail.com" should retain:
      | auth_method          | oauth                    |
      | oauth_refresh_token  | existing-refresh-token   |

  Scenario: Account with both OAuth token and app password is treated as OAuth
    Given an account "hybrid@gmail.com" has:
      | auth_method          | oauth                    |
      | oauth_refresh_token  | valid-token              |
      | app_password         | legacy-password          |
    When the Gmail fetcher is created with a connection service for "hybrid@gmail.com"
    Then the account should be treated as an OAuth account
    And the auth_method should remain "oauth"

  # === ERROR HANDLING ===

  Scenario: Account service failure does not crash Gmail fetcher initialization
    Given the account service is temporarily unavailable
    When the Gmail fetcher is created for "any-user@gmail.com"
    Then the Gmail fetcher should initialize successfully
    And a warning should be logged about account tracking being disabled
    And email processing should continue without account tracking

  Scenario: Invalid connection service is handled gracefully
    Given an account "user@gmail.com" is configured for OAuth
    When the Gmail fetcher is created with an invalid connection service
    Then the system should handle the error gracefully
    And an appropriate error should be logged
