# Gap Analysis: Gmail OAuth Auth Method Fix

## Analysis Date
2026-01-07

## Source Requirements
- Feature files: `./tests/bdd/*.feature` (3 features, 24 scenarios total)
- BDD Spec: `specs/BDD-SPEC-gmail-oauth-auth-fix.md`

## Codebase Analysis

### 1. Existing Code Reuse Opportunities

#### Core Fix Location (HIGH REUSE)
**File**: `/root/repo/services/gmail_fetcher_service.py` (lines 73-83)

The bug exists at line 78 where `auth_method='imap'` is unconditionally set:
```python
self.account_service.get_or_create_account(self.email_address, None, app_password, 'imap', None)
```

**Reuse**: The `GmailFetcher.__init__()` method already has:
- `connection_service` parameter to distinguish OAuth vs IMAP
- `account_service` initialization pattern
- Error handling for `AccountCategoryClient` failures

The fix requires minimal code change: conditional logic based on `connection_service is not None`.

#### Account Service (FULL REUSE)
**File**: `/root/repo/clients/account_category_client.py`

Existing methods that can be reused as-is:
- `get_or_create_account()` (lines 137-177) - Already supports `auth_method` and `oauth_refresh_token` parameters
- `get_account_by_email()` (lines 252-279) - For querying account state
- `update_oauth_tokens()` (lines 652-712) - Sets `auth_method='oauth'` correctly
- `_validate_email_address()` (lines 114-135) - Email validation
- `_detach_account()` (lines 86-112) - Session management

**Key Insight**: `get_or_create_account()` accepts `auth_method=None` which means "don't update", solving the OAuth preservation problem.

#### Database Models (FULL REUSE)
**File**: `/root/repo/models/database.py`

The `EmailAccount` model (lines 31-60) already has all required fields:
- `auth_method` - Column exists with default 'imap'
- `oauth_refresh_token` - Column exists
- `oauth_access_token` - Column exists
- Indexes on `auth_method` already exist

**No schema changes needed** - all fields for the fix already exist.

### 2. Similar Patterns Already Implemented

#### OAuth Token Updates Pattern
**File**: `/root/repo/clients/account_category_client.py` (lines 652-712)

The `update_oauth_tokens()` method shows correct pattern:
```python
account.auth_method = 'oauth'
account.oauth_refresh_token = refresh_token
```

This pattern should be followed for consistency.

#### Conditional Update Pattern
**File**: `/root/repo/clients/account_category_client.py` (lines 189-207)

The `_get_or_create_account_impl()` shows conditional update pattern:
```python
if auth_method and auth_method != account.auth_method:
    account.auth_method = auth_method
    updated = True
```

**Key**: When `auth_method=None`, no update occurs. This is the desired behavior for OAuth.

### 3. Components That Need Refactoring

#### NONE REQUIRED
The existing codebase is well-structured. No refactoring is needed before implementing the fix.

### 4. New Components That Need to Be Built

#### A. Auth Method Resolution Logic (NEW)
A utility to determine auth context based on connection service presence.

**Location**: Could be added to `gmail_fetcher_service.py` or extracted to a utility.

**Scope**:
```python
def resolve_auth_context(connection_service, app_password):
    """Determine auth method based on connection type."""
    if connection_service is not None:
        return {'auth_method': None, 'app_password': None}  # OAuth - don't update
    else:
        return {'auth_method': 'imap', 'app_password': app_password}  # IMAP - set values
```

#### B. Corrupted Account Restoration Service (NEW)
A service/migration to restore previously corrupted OAuth accounts.

**Location**: New file recommended: `/root/repo/services/oauth_account_restoration_service.py`

**Scope**:
- Query accounts with `auth_method='imap' AND oauth_refresh_token IS NOT NULL`
- Update `auth_method` to 'oauth'
- Log all changes for audit
- Support idempotent execution

**SQL Query Pattern**:
```sql
SELECT * FROM email_accounts
WHERE auth_method = 'imap'
AND oauth_refresh_token IS NOT NULL
AND oauth_refresh_token != '';
```

#### C. Database Migration (NEW)
Flyway migration to restore corrupted accounts.

**Location**: New file: `/root/repo/sql/V11__restore_corrupted_oauth_accounts.sql`

**Content**:
```sql
-- Restore OAuth accounts that were incorrectly set to 'imap'
UPDATE email_accounts
SET auth_method = 'oauth', updated_at = NOW()
WHERE auth_method = 'imap'
AND oauth_refresh_token IS NOT NULL
AND oauth_refresh_token != '';
```

### 5. Test Coverage Analysis

#### Existing Test Patterns
**Directory**: `/root/repo/tests/`

Relevant existing tests:
- `test_account_category_client_oauth.py` - OAuth token management tests
- `test_account_email_processor_oauth.py` - OAuth processing tests
- `tests/unit/test_gmail_oauth_connection_service.py` - OAuth connection tests

These can serve as templates for new tests.

#### New Tests Needed

Based on Gherkin scenarios, these test files need to be created:

1. **`tests/bdd/test_gmail_oauth_auth_preservation.py`**
   - 8 tests from `gmail-oauth-auth-preservation.feature`

2. **`tests/bdd/test_corrupted_oauth_account_restoration.py`**
   - 10 tests from `corrupted-oauth-account-restoration.feature`

3. **`tests/bdd/test_auth_method_resolution_logic.py`**
   - 6 tests from `auth-method-resolution-logic.feature`

### 6. Implementation Order Recommendation

**Order by dependency**:

1. **Feature 1: Auth Method Resolution Logic** (Foundation)
   - No dependencies
   - Provides utility function used by other features

2. **Feature 2: Gmail OAuth Auth Preservation** (Core Fix)
   - Depends on: Auth Method Resolution Logic
   - Modifies: `gmail_fetcher_service.py`

3. **Feature 3: Corrupted OAuth Account Restoration** (Cleanup)
   - Depends on: Core fix must be in place to prevent re-corruption
   - Creates: Restoration service and migration

## Summary

| Category | Count | Details |
|----------|-------|---------|
| Existing Code Reuse | HIGH | AccountCategoryClient, EmailAccount model |
| New Files | 3 | Resolution util, restoration service, SQL migration |
| Refactoring Required | 0 | No refactoring needed |
| Core Fix Scope | ~10 lines | Conditional logic in GmailFetcher.\_\_init\_\_ |
| Total Scenarios | 24 | 8 + 10 + 6 across 3 features |

## GO Signal Assessment

**REFACTORING NEEDED**: No
**BLOCKERS**: None identified
**RECOMMENDATION**: Proceed with implementation

---
*Generated by codebase-analyst agent*
