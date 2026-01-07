---
executor: bdd
source_feature: ./tests/bdd/corrupted-oauth-account-restoration.feature
---

<objective>
Implement the Corrupted OAuth Account Restoration feature as defined by the BDD scenarios below.
The implementation must make all Gherkin scenarios pass.

This feature provides a migration/service to restore OAuth accounts that were corrupted by the
auth method bug (auth_method incorrectly set to 'imap' when oauth_refresh_token exists).
</objective>

<gherkin>
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
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. OAuth Account Restoration Service:
   - Scan for corrupted accounts (auth_method='imap' AND oauth_refresh_token IS NOT NULL AND NOT EMPTY)
   - Restore corrupted accounts by setting auth_method='oauth'
   - Return count of restored accounts
   - Support idempotent execution

2. Corrupted Account Detection Logic:
   - Account is corrupted if: auth_method='imap' AND oauth_refresh_token exists AND is not empty
   - Account is NOT corrupted if: oauth_refresh_token is NULL or empty string
   - Account is NOT corrupted if: auth_method is already 'oauth'

3. Database Migration (Flyway):
   - SQL migration to fix all corrupted accounts in one operation
   - Must be idempotent (safe to run multiple times)

4. Audit Logging:
   - Log each account restoration with email, old_method, new_method, timestamp
   - Log total restoration count
   - Log errors with rollback information

Edge Cases to Handle:
- True IMAP accounts (no oauth_refresh_token) must NOT be modified
- Empty string oauth_refresh_token should be treated as "no token"
- Null auth_method accounts should not be affected
- Multiple restoration runs should be safe (idempotent)
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-gmail-oauth-auth-fix.md
Gap Analysis: specs/GAP-ANALYSIS.md

Reuse Opportunities (from gap analysis):
- `AccountCategoryClient` for database operations
- `EmailAccount` model already has all required fields
- Transaction/rollback pattern from existing database code

Dependencies:
- Feature 002 (Gmail OAuth Auth Preservation) should be in place to prevent re-corruption

New Components Needed:
- `/root/repo/services/oauth_account_restoration_service.py` - Restoration service
- `/root/repo/sql/V11__restore_corrupted_oauth_accounts.sql` - Flyway migration

SQL Migration Pattern:
```sql
-- V11__restore_corrupted_oauth_accounts.sql
-- Restore OAuth accounts that were incorrectly set to 'imap' by the bug

UPDATE email_accounts
SET auth_method = 'oauth',
    updated_at = NOW()
WHERE auth_method = 'imap'
  AND oauth_refresh_token IS NOT NULL
  AND oauth_refresh_token != '';
```
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
- Use transactions for database operations

Service Implementation Pattern:
```python
class OAuthAccountRestorationService:
    """Service to restore corrupted OAuth accounts."""

    def __init__(self, repository: DatabaseRepositoryInterface = None):
        self.repository = repository or MySQLRepository()
        self.logger = get_logger(__name__)

    def scan_corrupted_accounts(self) -> List[dict]:
        """Find accounts with auth_method='imap' but have oauth_refresh_token."""
        # Query: auth_method='imap' AND oauth_refresh_token IS NOT NULL AND != ''
        pass

    def restore_corrupted_accounts(self) -> int:
        """Restore all corrupted accounts to auth_method='oauth'."""
        # Returns count of restored accounts
        pass

    def is_account_corrupted(self, account: EmailAccount) -> bool:
        """Check if an account has corrupted auth_method."""
        return (
            account.auth_method == 'imap' and
            account.oauth_refresh_token is not None and
            account.oauth_refresh_token != ''
        )
```
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Corrupted OAuth account is identified
- [ ] Scenario: Corrupted OAuth account is restored to correct auth method
- [ ] Scenario: Multiple corrupted accounts are restored in one migration
- [ ] Scenario: Already correct OAuth account is not modified
- [ ] Scenario: True IMAP account without OAuth token is not modified
- [ ] Scenario: Account with empty oauth_refresh_token is not modified
- [ ] Scenario: Restoration is idempotent - running twice has no additional effect
- [ ] Scenario: Legacy account with null auth_method and no OAuth token is not modified
- [ ] Scenario: Database error during restoration is handled gracefully
- [ ] Scenario: Restoration logs detailed information for audit
</verification>

<success_criteria>
- All 10 Gherkin scenarios pass
- Corrupted OAuth accounts are correctly identified and restored
- True IMAP accounts are not affected
- Restoration is idempotent (safe to run multiple times)
- Proper audit logging is in place
- Database errors are handled with rollback
- Code follows project coding standards
- Tests provide complete coverage of scenarios
</success_criteria>
