Feature: Corrupted OAuth Account Restoration
  As a database administrator
  I want to restore OAuth accounts that were corrupted by the auth method bug
  So that previously affected accounts become functional again

  Background:
    Given the database contains email accounts
    And the restoration service is available

  # === HAPPY PATHS ===

  Scenario: Corrupted OAuth account is identified
    Given an account "corrupted@gmail.com" has:
      | auth_method          | imap                     |
      | oauth_refresh_token  | valid-refresh-token      |
    When the system scans for corrupted accounts
    Then the account "corrupted@gmail.com" should be identified as corrupted
    And the reason should be "has oauth_refresh_token but auth_method is imap"

  Scenario: Corrupted OAuth account is restored to correct auth method
    Given an account "corrupted@gmail.com" has:
      | auth_method          | imap                     |
      | oauth_refresh_token  | valid-refresh-token      |
    When the restoration process runs
    Then the account "corrupted@gmail.com" should have auth_method "oauth"
    And a log entry should record the restoration

  Scenario: Multiple corrupted accounts are restored in one migration
    Given the following corrupted accounts exist:
      | email                | auth_method | oauth_refresh_token |
      | user1@gmail.com      | imap        | token-1             |
      | user2@gmail.com      | imap        | token-2             |
      | user3@gmail.com      | imap        | token-3             |
    When the restoration process runs
    Then all three accounts should have auth_method "oauth"
    And the restoration count should be 3

  Scenario: Already correct OAuth account is not modified
    Given an account "healthy@gmail.com" has:
      | auth_method          | oauth                    |
      | oauth_refresh_token  | valid-refresh-token      |
    When the restoration process runs
    Then the account "healthy@gmail.com" should not be modified
    And the restoration count for this account should be 0

  # === EDGE CASES ===

  Scenario: True IMAP account without OAuth token is not modified
    Given an account "true-imap@gmail.com" has:
      | auth_method          | imap                     |
      | oauth_refresh_token  | null                     |
      | app_password         | valid-app-password       |
    When the restoration process runs
    Then the account "true-imap@gmail.com" should still have auth_method "imap"
    And the account should not be flagged as corrupted

  Scenario: Account with empty oauth_refresh_token is not modified
    Given an account "empty-token@gmail.com" has:
      | auth_method          | imap                     |
      | oauth_refresh_token  | empty string             |
    When the restoration process runs
    Then the account "empty-token@gmail.com" should still have auth_method "imap"

  Scenario: Restoration is idempotent - running twice has no additional effect
    Given an account "corrupted@gmail.com" has:
      | auth_method          | imap                     |
      | oauth_refresh_token  | valid-refresh-token      |
    When the restoration process runs
    And the restoration process runs again
    Then the account "corrupted@gmail.com" should have auth_method "oauth"
    And the second run should report 0 accounts restored

  Scenario: Legacy account with null auth_method and no OAuth token is not modified
    Given an account "legacy@gmail.com" has:
      | auth_method          | null                     |
      | oauth_refresh_token  | null                     |
    When the restoration process runs
    Then the account "legacy@gmail.com" should not be modified

  # === ERROR HANDLING ===

  Scenario: Database error during restoration is handled gracefully
    Given corrupted accounts exist in the database
    And the database becomes unavailable during restoration
    When the restoration process runs
    Then an error should be logged
    And the restoration should be rolled back
    And no accounts should be partially modified

  Scenario: Restoration logs detailed information for audit
    Given an account "corrupted@gmail.com" has:
      | auth_method          | imap                     |
      | oauth_refresh_token  | valid-refresh-token      |
    When the restoration process runs
    Then the log should include:
      | field        | value                    |
      | email        | corrupted@gmail.com      |
      | old_method   | imap                     |
      | new_method   | oauth                    |
      | timestamp    | restoration time         |
