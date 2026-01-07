Feature: OAuth Status Badge on Accounts Page
  As a user of the email management system
  I want to see the authentication method for each account on the Accounts page
  So that I can quickly identify which accounts use OAuth and which use IMAP

  Background:
    Given the Accounts page is loaded
    And the accounts list is retrieved from the system

  # === HAPPY PATHS ===

  Scenario: OAuth Connected account displays green badge
    Given an account "user@gmail.com" has auth_method "oauth"
    When the accounts table is displayed
    Then the account "user@gmail.com" should show a green "OAuth Connected" badge

  Scenario: IMAP account displays gray badge
    Given an account "user@company.com" has auth_method "imap"
    When the accounts table is displayed
    Then the account "user@company.com" should show a gray "IMAP" badge

  Scenario: Accounts list shows mixed authentication methods
    Given the following accounts exist:
      | email               | auth_method |
      | oauth1@gmail.com    | oauth       |
      | imap1@company.com   | imap        |
      | oauth2@gmail.com    | oauth       |
    When the accounts table is displayed
    Then "oauth1@gmail.com" should show a green "OAuth Connected" badge
    And "imap1@company.com" should show a gray "IMAP" badge
    And "oauth2@gmail.com" should show a green "OAuth Connected" badge

  Scenario: Auth Method column is visible in accounts table
    Given accounts exist in the system
    When the accounts table is displayed
    Then the table should have an "Auth Method" column header
    And the "Auth Method" column should appear after the "Email" column

  # === EDGE CASES ===

  Scenario: Legacy account with null auth_method displays Not Configured badge
    Given an account "legacy@gmail.com" has auth_method null
    When the accounts table is displayed
    Then the account "legacy@gmail.com" should show a neutral "Not Configured" badge

  Scenario: Empty accounts list renders correctly
    Given no accounts exist in the system
    When the accounts table is displayed
    Then the table should render with headers but no data rows
    And the "Auth Method" column header should still be visible

  Scenario: Case insensitive auth_method handling
    Given an account "user@gmail.com" has auth_method "OAuth"
    When the accounts table is displayed
    Then the account "user@gmail.com" should show a green "OAuth Connected" badge

  # === API RESPONSE BEHAVIOR ===

  Scenario: API response includes auth_method for each account
    Given accounts exist with various authentication methods
    When the system retrieves the accounts list
    Then each account in the response should include an auth_method field

  Scenario: OAuth account returns oauth auth_method in API response
    Given an account "user@gmail.com" is configured with OAuth
    When the system retrieves the accounts list
    Then the response for "user@gmail.com" should have auth_method "oauth"

  Scenario: IMAP account returns imap auth_method in API response
    Given an account "user@company.com" is configured with IMAP credentials
    When the system retrieves the accounts list
    Then the response for "user@company.com" should have auth_method "imap"

  Scenario: Legacy account returns null auth_method in API response
    Given an account "legacy@gmail.com" was created before auth_method tracking
    When the system retrieves the accounts list
    Then the response for "legacy@gmail.com" should have auth_method null

  # === ERROR HANDLING ===

  Scenario: Badge renders gracefully for unexpected auth_method value
    Given an account "user@gmail.com" has auth_method "unexpected_value"
    When the accounts table is displayed
    Then the account "user@gmail.com" should show a neutral "Not Configured" badge

  Scenario: Badge renders when auth_method field is missing from response
    Given an account response is missing the auth_method field
    When the accounts table is displayed
    Then the account should show a neutral "Not Configured" badge

  # === ACCESSIBILITY ===

  Scenario: OAuth badge has accessible aria-label
    Given an account "user@gmail.com" has auth_method "oauth"
    When the accounts table is displayed
    Then the badge for "user@gmail.com" should have aria-label "Authentication method: OAuth Connected"

  Scenario: IMAP badge has accessible aria-label
    Given an account "user@company.com" has auth_method "imap"
    When the accounts table is displayed
    Then the badge for "user@company.com" should have aria-label "Authentication method: IMAP"

  Scenario: Not Configured badge has accessible aria-label
    Given an account "legacy@gmail.com" has auth_method null
    When the accounts table is displayed
    Then the badge for "legacy@gmail.com" should have aria-label "Authentication method: Not Configured"

  Scenario: Auth Method column header is accessible
    Given accounts exist in the system
    When the accounts table is displayed
    Then the "Auth Method" column header should have appropriate table header scope
