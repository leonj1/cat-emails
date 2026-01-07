---
executor: bdd
source_feature: ./tests/bdd/auth-method-resolution-logic.feature
---

<objective>
Implement the Auth Method Resolution Logic feature as defined by the BDD scenarios below.
The implementation must make all Gherkin scenarios pass.

This is the foundation feature that provides utility functions for determining authentication
context based on whether a connection service (OAuth) or app password (IMAP) is being used.
</objective>

<gherkin>
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
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. Auth Method Resolver utility function/class that determines auth context
   - Input: connection_service (Optional), app_password (Optional[str])
   - Output: dict with auth_method and app_password values

2. Auth Context dataclass or dict structure with fields:
   - has_connection_service: bool
   - is_oauth: bool
   - should_update_auth_method: bool
   - auth_method: Optional[str]
   - app_password: Optional[str]

3. Resolution Logic:
   - If connection_service is not None -> OAuth mode (don't update auth_method)
   - If connection_service is None -> IMAP mode (set auth_method='imap')

Edge Cases to Handle:
- Null app_password with IMAP should still set auth_method='imap'
- Empty string app_password with IMAP should still set auth_method='imap'
- Connection service presence is the sole determinant of OAuth vs IMAP

</requirements>

<context>
BDD Specification: specs/BDD-SPEC-gmail-oauth-auth-fix.md
Gap Analysis: specs/GAP-ANALYSIS.md

Reuse Opportunities (from gap analysis):
- Pattern from `AccountCategoryClient.get_or_create_account()` where `auth_method=None` means "don't update"
- Conditional update pattern from `_get_or_create_account_impl()` lines 189-207

New Components Needed:
- Auth method resolver utility (could be function or class)
- May be implemented in `gmail_fetcher_service.py` or as standalone utility
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
- Keep the resolver simple and focused

Suggested Implementation:
```python
def resolve_auth_method(connection_service, app_password):
    """
    Resolve authentication method based on connection type.

    Args:
        connection_service: OAuth connection service if using OAuth, None for IMAP
        app_password: App password for IMAP authentication

    Returns:
        dict with 'auth_method' and 'app_password' keys
    """
    if connection_service is not None:
        # OAuth: Don't update auth_method (let existing value remain)
        return {
            'auth_method': None,
            'app_password': None,
            'is_oauth': True,
            'should_update_auth_method': False
        }
    else:
        # IMAP: Set auth_method to 'imap'
        return {
            'auth_method': 'imap',
            'app_password': app_password,
            'is_oauth': False,
            'should_update_auth_method': True
        }
```
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Connection service present indicates OAuth authentication
- [ ] Scenario: No connection service indicates IMAP authentication
- [ ] Scenario: Auth context correctly identifies OAuth connection
- [ ] Scenario: Auth context correctly identifies IMAP connection
- [ ] Scenario: Null app password with IMAP still sets auth method
- [ ] Scenario: Empty app password with IMAP still sets auth method
</verification>

<success_criteria>
- All 6 Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation is simple and focused
- Can be reused by other features (Gmail OAuth Auth Preservation)
</success_criteria>
