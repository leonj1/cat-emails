# BDD Specification: Gmail OAuth Auth Method Fix

## Overview

This specification addresses the Gmail OAuth authentication corruption bug discovered through CRASH-RCA investigation. The bug at `/root/repo/services/gmail_fetcher_service.py` line 78 unconditionally sets `auth_method='imap'` for ALL accounts during processing, including OAuth-authenticated accounts. This corrupts OAuth accounts, making them non-functional after the first processing run.

The fix involves:
1. Conditionally setting auth_method based on connection type (OAuth vs IMAP)
2. Database migration to restore previously corrupted OAuth accounts

## User Stories

- As an OAuth-connected Gmail user, I want my authentication settings preserved during processing so that my account remains functional
- As an IMAP user, I want my auth_method correctly set to 'imap' so that my credentials are properly stored
- As a database administrator, I want corrupted OAuth accounts restored so that affected users can access their email again

## Feature Files

| Feature File | Scenarios | Coverage |
|--------------|-----------|----------|
| gmail-oauth-auth-preservation.feature | 8 | Happy paths (3), Edge cases (3), Error handling (2) |
| corrupted-oauth-account-restoration.feature | 10 | Happy paths (4), Edge cases (4), Error handling (2) |
| auth-method-resolution-logic.feature | 6 | Happy paths (4), Edge cases (2) |

**Total: 24 scenarios**

## Scenarios Summary

### gmail-oauth-auth-preservation.feature

**Happy Paths:**
1. OAuth account authentication method is not overwritten during processing
2. IMAP account authentication method is set correctly during processing
3. OAuth account remains functional after multiple processing runs

**Edge Cases:**
4. New IMAP account is created with correct auth method
5. Existing OAuth account is not modified when processing with OAuth
6. Account with both OAuth token and app password is treated as OAuth

**Error Handling:**
7. Account service failure does not crash Gmail fetcher initialization
8. Invalid connection service is handled gracefully

### corrupted-oauth-account-restoration.feature

**Happy Paths:**
1. Corrupted OAuth account is identified
2. Corrupted OAuth account is restored to correct auth method
3. Multiple corrupted accounts are restored in one migration
4. Already correct OAuth account is not modified

**Edge Cases:**
5. True IMAP account without OAuth token is not modified
6. Account with empty oauth_refresh_token is not modified
7. Restoration is idempotent - running twice has no additional effect
8. Legacy account with null auth_method and no OAuth token is not modified

**Error Handling:**
9. Database error during restoration is handled gracefully
10. Restoration logs detailed information for audit

### auth-method-resolution-logic.feature

**Happy Paths:**
1. Connection service present indicates OAuth authentication
2. No connection service indicates IMAP authentication
3. Auth context correctly identifies OAuth connection
4. Auth context correctly identifies IMAP connection

**Edge Cases:**
5. Null app password with IMAP still sets auth method
6. Empty app password with IMAP still sets auth method

## Acceptance Criteria

### Core Fix (gmail_fetcher_service.py line 78)
- [ ] When `connection_service` is provided (OAuth), `get_or_create_account` is called with `auth_method=None` and `app_password=None`
- [ ] When `connection_service` is NOT provided (IMAP), `get_or_create_account` is called with `auth_method='imap'` and the actual `app_password`
- [ ] OAuth accounts retain `auth_method='oauth'` after processing runs
- [ ] IMAP accounts have `auth_method='imap'` set correctly

### Database Restoration
- [ ] Accounts with `auth_method='imap'` AND `oauth_refresh_token IS NOT NULL` are identified as corrupted
- [ ] Corrupted accounts are restored to `auth_method='oauth'`
- [ ] True IMAP accounts (no `oauth_refresh_token`) are NOT modified
- [ ] Restoration is idempotent (safe to run multiple times)
- [ ] Restoration logs all changes for audit purposes

### Error Handling
- [ ] Account service failures do not crash the Gmail fetcher
- [ ] Database errors during restoration are rolled back
- [ ] All errors are logged appropriately

## Technical Context

### Root Cause
Commit `fb1599b` introduced code that unconditionally sets `auth_method='imap'` at line 78 of `gmail_fetcher_service.py`, regardless of whether the account uses OAuth or IMAP authentication.

### Affected Code
```python
# Line 78 (BUGGY)
self.account_service.get_or_create_account(self.email_address, None, app_password, 'imap', None)
```

### Proposed Fix
```python
# Lines 76-82 (FIXED)
if connection_service is not None:
    # OAuth: Don't overwrite auth_method
    self.account_service.get_or_create_account(self.email_address, None, None, None, None)
else:
    # IMAP: Set auth_method and app_password
    self.account_service.get_or_create_account(self.email_address, None, app_password, 'imap', None)
```

### Corruption Detection Query
```sql
SELECT * FROM email_accounts
WHERE auth_method = 'imap'
AND oauth_refresh_token IS NOT NULL;
```

## Dependencies

- Existing `AccountCategoryClient.get_or_create_account()` method
- Existing `EmailAccount` SQLAlchemy model
- No new external dependencies required

## Related Files

- `/root/repo/services/gmail_fetcher_service.py` - Core fix location
- `/root/repo/clients/account_category_client.py` - Account service
- `/root/repo/database.py` - Database models
- `/root/repo/tests/bdd/gmail-oauth-auth-preservation.feature` - BDD scenarios
- `/root/repo/tests/bdd/corrupted-oauth-account-restoration.feature` - BDD scenarios
- `/root/repo/tests/bdd/auth-method-resolution-logic.feature` - BDD scenarios

## Origin

- **CRASH-RCA Investigation**: Gmail OAuth auth failure debugging session
- **Bug Introduced**: Commit `fb1599b` on 2026-01-07
- **DRAFT Spec**: `specs/DRAFT-gmail-oauth-auth-fix.md`
