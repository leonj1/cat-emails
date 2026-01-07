---
executor: bdd
source_feature: ./tests/bdd/gmail-oauth-auth-preservation.feature
---

<objective>
Implement the Gmail OAuth Auth Method Preservation feature as defined by the BDD scenarios below.
The implementation must make all Gherkin scenarios pass.

This is the core fix for the Gmail OAuth authentication corruption bug. The bug at
`/root/repo/services/gmail_fetcher_service.py` line 78 unconditionally sets `auth_method='imap'`
for ALL accounts during processing, including OAuth-authenticated accounts.
</objective>

<gherkin>
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
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. Core Fix in `gmail_fetcher_service.py` (around line 78):
   - Use auth method resolution logic from Feature 001
   - When connection_service is provided (OAuth): call get_or_create_account with auth_method=None
   - When connection_service is NOT provided (IMAP): call get_or_create_account with auth_method='imap'

2. Modify GmailFetcher.__init__() to:
   - Check if connection_service is provided
   - Conditionally set auth_method and app_password based on connection type
   - Preserve existing OAuth accounts' auth_method

3. Error Handling:
   - Account service failure should not crash GmailFetcher initialization
   - Continue with account_service=None if initialization fails
   - Log appropriate warnings

Edge Cases to Handle:
- New IMAP accounts should be created with auth_method='imap'
- Existing OAuth accounts should NOT have auth_method changed
- Accounts with both OAuth tokens and app passwords should be treated as OAuth
- Multiple processing runs should not corrupt OAuth accounts
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-gmail-oauth-auth-fix.md
Gap Analysis: specs/GAP-ANALYSIS.md

Reuse Opportunities (from gap analysis):
- `AccountCategoryClient.get_or_create_account()` already supports auth_method=None (don't update)
- Existing error handling pattern in GmailFetcher.__init__() lines 73-83
- Auth method resolution logic from Feature 001

Dependencies:
- Feature 001 (Auth Method Resolution Logic) must be implemented first

Related Files:
- `/root/repo/services/gmail_fetcher_service.py` - Core fix location (line 78)
- `/root/repo/clients/account_category_client.py` - Account service
- `/root/repo/services/gmail_connection_service.py` - Connection service
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Maintain consistency with project structure

Core Fix (replace line 78 in gmail_fetcher_service.py):
```python
# Lines 76-82 (FIXED)
if connection_service is not None:
    # OAuth: Don't overwrite auth_method - pass None to preserve existing value
    self.account_service.get_or_create_account(self.email_address, None, None, None, None)
else:
    # IMAP: Set auth_method and app_password
    self.account_service.get_or_create_account(self.email_address, None, app_password, 'imap', None)
```

Or using auth method resolver:
```python
auth_context = resolve_auth_method(connection_service, app_password)
self.account_service.get_or_create_account(
    self.email_address,
    None,  # display_name
    auth_context['app_password'],
    auth_context['auth_method'],
    None   # oauth_refresh_token
)
```
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: OAuth account authentication method is not overwritten during processing
- [ ] Scenario: IMAP account authentication method is set correctly during processing
- [ ] Scenario: OAuth account remains functional after multiple processing runs
- [ ] Scenario: New IMAP account is created with correct auth method
- [ ] Scenario: Existing OAuth account is not modified when processing with OAuth
- [ ] Scenario: Account with both OAuth token and app password is treated as OAuth
- [ ] Scenario: Account service failure does not crash Gmail fetcher initialization
- [ ] Scenario: Invalid connection service is handled gracefully
</verification>

<success_criteria>
- All 8 Gherkin scenarios pass
- OAuth accounts retain auth_method='oauth' after processing
- IMAP accounts correctly have auth_method='imap'
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent from CRASH-RCA investigation
</success_criteria>
