---
executor: bdd
source_feature: ./tests/bdd/oauth-status-badge.feature
---

<objective>
Implement the OAuth Status Badge feature on the Accounts page as defined by the BDD scenarios below.
The implementation must make all 17 Gherkin scenarios pass, displaying authentication method badges
(green "OAuth Connected", gray "IMAP", or neutral "Not Configured") for each email account in the
accounts table.
</objective>

<gherkin>
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
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement the following:

## Backend Requirements

1. **Update EmailAccountInfo model** (`models/account_models.py`)
   - Add `auth_method: Optional[str]` field to the Pydantic model
   - Field should accept "oauth", "imap", or null values
   - Include appropriate Field description

2. **Update GET /api/accounts endpoint** (`api_service.py`)
   - Include `auth_method` in the EmailAccountInfo mapping
   - Map directly from `account.auth_method` database value
   - Handle null values gracefully (legacy accounts)

## Frontend Requirements

3. **Add Auth Method column to table header**
   - Position after "Email Address" column
   - Include proper scope attribute for accessibility

4. **Create auth method badge styles** (CSS)
   - Green badge for OAuth: `auth-badge oauth` with `bg-success` styling
   - Gray badge for IMAP: `auth-badge imap` with `bg-secondary` styling
   - Neutral badge for Not Configured: `auth-badge not-configured` with `bg-light text-dark` styling

5. **Update renderAccountsTable() JavaScript function**
   - Create auth method cell after email cell
   - Normalize auth_method to lowercase for comparison
   - Render appropriate badge based on value:
     - "oauth" (case-insensitive) -> green "OAuth Connected"
     - "imap" (case-insensitive) -> gray "IMAP"
     - null/undefined/other -> neutral "Not Configured"
   - Add aria-label attribute to each badge

## Edge Cases to Handle

- **Null auth_method**: Display "Not Configured" badge
- **Missing auth_method field**: Display "Not Configured" badge
- **Unexpected values**: Display "Not Configured" badge (fallback)
- **Case sensitivity**: Normalize to lowercase before comparison
- **Empty accounts list**: Table headers still visible including Auth Method
- **Responsive design**: Include data-label for mobile layout

## Badge Specification Table

| auth_method Value | Badge Text | Color | CSS Classes | aria-label |
|-------------------|------------|-------|-------------|------------|
| "oauth" | OAuth Connected | Green | auth-badge oauth | Authentication method: OAuth Connected |
| "imap" | IMAP | Gray | auth-badge imap | Authentication method: IMAP |
| null/undefined/other | Not Configured | Neutral | auth-badge not-configured | Authentication method: Not Configured |
</requirements>

<context>
**BDD Specification**: specs/BDD-SPEC-oauth-status-badge.md
**Gap Analysis**: specs/GAP-ANALYSIS-oauth-status-badge.md

## Reuse Opportunities (from gap analysis)

1. **Database schema is complete** - `EmailAccount.auth_method` column already exists in `models/database.py`
2. **Badge CSS pattern** - Existing `.status-badge` class in accounts.html can be adapted
3. **Table cell creation pattern** - Follow existing DOM manipulation in `renderAccountsTable()`
4. **Pydantic optional field pattern** - Follow existing `display_name` field pattern

## Files to Modify

| File | Changes |
|------|---------|
| `models/account_models.py` | Add auth_method field to EmailAccountInfo |
| `api_service.py` | Include auth_method in account mapping (~line 1856) |
| `frontend/templates/accounts.html` | Add column, CSS, JavaScript badge logic |

## New Components Needed

None - all changes are additions to existing files.
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all 17 scenarios are green

## Implementation Order

### Phase 1: Backend (API Response)
1. Add `auth_method` field to `EmailAccountInfo` model
2. Update endpoint mapping in `api_service.py` to include auth_method
3. Verify API returns auth_method for all accounts

### Phase 2: Frontend (Column and Badge Display)
1. Add "Auth Method" column header to table (after Email Address)
2. Add CSS styles for auth badges
3. Update `renderAccountsTable()` to create auth method cell with badge
4. Implement badge selection logic (oauth/imap/not-configured)
5. Add aria-labels for accessibility

## Architecture Guidelines

- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Maintain consistency with project structure
- Keep frontend JavaScript in template (matching existing pattern)
</implementation>

<verification>
All Gherkin scenarios must pass:

### Happy Paths
- [ ] Scenario: OAuth Connected account displays green badge
- [ ] Scenario: IMAP account displays gray badge
- [ ] Scenario: Accounts list shows mixed authentication methods
- [ ] Scenario: Auth Method column is visible in accounts table

### Edge Cases
- [ ] Scenario: Legacy account with null auth_method displays Not Configured badge
- [ ] Scenario: Empty accounts list renders correctly
- [ ] Scenario: Case insensitive auth_method handling

### API Response Behavior
- [ ] Scenario: API response includes auth_method for each account
- [ ] Scenario: OAuth account returns oauth auth_method in API response
- [ ] Scenario: IMAP account returns imap auth_method in API response
- [ ] Scenario: Legacy account returns null auth_method in API response

### Error Handling
- [ ] Scenario: Badge renders gracefully for unexpected auth_method value
- [ ] Scenario: Badge renders when auth_method field is missing from response

### Accessibility
- [ ] Scenario: OAuth badge has accessible aria-label
- [ ] Scenario: IMAP badge has accessible aria-label
- [ ] Scenario: Not Configured badge has accessible aria-label
- [ ] Scenario: Auth Method column header is accessible
</verification>

<success_criteria>
- All 17 Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent:
  - Green "OAuth Connected" badge for OAuth accounts
  - Gray "IMAP" badge for IMAP accounts
  - Neutral "Not Configured" badge for legacy/null accounts
  - Auth Method column positioned after Email column
  - All badges have appropriate aria-labels for accessibility
</success_criteria>
