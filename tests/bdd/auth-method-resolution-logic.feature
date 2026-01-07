Feature: Auth Method Resolution Logic
  As the email processing system
  I want to correctly determine the auth method based on connection type
  So that accounts are registered with the appropriate authentication settings

  Background:
    Given the auth method resolver is initialized

  # === HAPPY PATHS ===

  Scenario: Connection service present indicates OAuth authentication
    Given a connection service is provided
    When the auth method is resolved
    Then the result should indicate OAuth authentication
    And auth_method should be null (not overwritten)
    And app_password should be null (not overwritten)

  Scenario: No connection service indicates IMAP authentication
    Given no connection service is provided
    And an app password "my-app-password" is available
    When the auth method is resolved
    Then the result should indicate IMAP authentication
    And auth_method should be "imap"
    And app_password should be "my-app-password"

  Scenario: Auth context correctly identifies OAuth connection
    Given a connection service object exists
    When the auth method context is created
    Then the context should report has_connection_service as true
    And the context should report is_oauth as true
    And the context should report should_update_auth_method as false

  Scenario: Auth context correctly identifies IMAP connection
    Given no connection service object exists
    And an app password is available
    When the auth method context is created
    Then the context should report has_connection_service as false
    And the context should report is_oauth as false
    And the context should report should_update_auth_method as true

  # === EDGE CASES ===

  Scenario: Null app password with IMAP still sets auth method
    Given no connection service is provided
    And app password is null
    When the auth method is resolved
    Then auth_method should be "imap"
    And app_password should be null

  Scenario: Empty app password with IMAP still sets auth method
    Given no connection service is provided
    And app password is empty string
    When the auth method is resolved
    Then auth_method should be "imap"
    And app_password should be empty string
