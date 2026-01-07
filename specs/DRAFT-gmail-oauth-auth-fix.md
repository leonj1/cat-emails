# DRAFT Specification: Gmail OAuth Auth Method Corruption Fix

**Status**: DRAFT
**Task**: Fix Gmail OAuth Auth Method Corruption Bug
**Origin**: CRASH-RCA Investigation
**Author**: Architect Agent
**Date**: 2026-01-07

---

## Problem Statement

The Gmail OAuth authentication is corrupted when processing OAuth-authenticated accounts. The root cause is at `/root/repo/services/gmail_fetcher_service.py` line 78, which unconditionally sets `auth_method='imap'` for ALL accounts, including those using OAuth.

### Bug Behavior

1. User connects Gmail account via OAuth (auth_method='oauth')
2. Processing run starts, creates GmailFetcher with `connection_service` (OAuth)
3. Line 78 calls `get_or_create_account(email, None, app_password, 'imap', None)`
4. Database updates: `auth_method` changes from 'oauth' to 'imap'
5. Next processing attempt tries IMAP authentication (fails - no valid app_password)

### Impact

- OAuth accounts become non-functional after first processing run
- Users must re-authenticate via OAuth after every run
- Introduced in commit `fb1599b` on 2026-01-07

---

## Interfaces Needed

### IAuthMethodResolver (New)

Determines the correct auth_method based on connection type.

```python
from abc import ABC, abstractmethod
from typing import Optional

class IAuthMethodResolver(ABC):
    """Resolves authentication method based on connection context."""

    @abstractmethod
    def resolve(
        self,
        connection_service: Optional[object],
        app_password: Optional[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Resolve auth method and password based on connection type.

        Args:
            connection_service: Optional OAuth connection service
            app_password: Optional IMAP app password

        Returns:
            Tuple of (auth_method, password):
            - For OAuth: (None, None) - don't overwrite existing
            - For IMAP: ('imap', app_password)
        """
        pass
```

### IOAuthAccountRestorer (New)

Identifies and restores corrupted OAuth accounts.

```python
from abc import ABC, abstractmethod
from typing import List

class IOAuthAccountRestorer(ABC):
    """Restores corrupted OAuth accounts in the database."""

    @abstractmethod
    def find_corrupted_accounts(self) -> List[str]:
        """
        Find accounts with oauth_refresh_token but auth_method='imap'.

        Returns:
            List of email addresses of corrupted accounts
        """
        pass

    @abstractmethod
    def restore_oauth_auth_method(self, email_address: str) -> bool:
        """
        Restore auth_method to 'oauth' for a corrupted account.

        Args:
            email_address: Email of account to restore

        Returns:
            True if restored, False if not found or already correct
        """
        pass

    @abstractmethod
    def restore_all_corrupted(self) -> int:
        """
        Restore all corrupted OAuth accounts.

        Returns:
            Count of accounts restored
        """
        pass
```

---

## Data Models

### AuthMethodContext (New Value Object)

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class AuthMethodContext:
    """Context for determining authentication method."""

    has_connection_service: bool
    has_app_password: bool

    @property
    def is_oauth(self) -> bool:
        """True if connection service indicates OAuth."""
        return self.has_connection_service

    @property
    def should_update_auth_method(self) -> bool:
        """True if auth_method should be set (IMAP only)."""
        return not self.has_connection_service
```

### CorruptedAccountResult (New Data Class)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class CorruptedAccountResult:
    """Result of finding a corrupted OAuth account."""

    email_address: str
    current_auth_method: str
    has_refresh_token: bool
    corrupted_at: Optional[datetime] = None
```

---

## Logic Flow

### Part 1: Fix gmail_fetcher_service.py Line 78

**Current (Buggy) Code:**
```python
# Line 78
self.account_service.get_or_create_account(self.email_address, None, app_password, 'imap', None)
```

**Fixed Code:**
```python
# Lines 76-82 (expanded)
# Determine auth method based on connection type
if connection_service is not None:
    # OAuth: Don't overwrite auth_method - account already has correct settings
    # Pass None for auth_method and app_password to avoid corrupting OAuth accounts
    self.account_service.get_or_create_account(
        self.email_address, None, None, None, None
    )
else:
    # IMAP: Set auth_method and pass app_password
    self.account_service.get_or_create_account(
        self.email_address, None, app_password, 'imap', None
    )
```

**Pseudocode:**
```
function register_account(email_address, app_password, connection_service):
    if connection_service is provided:
        # OAuth path - don't modify auth credentials
        call get_or_create_account(email_address, None, None, None, None)
    else:
        # IMAP path - set credentials
        call get_or_create_account(email_address, None, app_password, 'imap', None)
```

### Part 2: Database Migration to Restore Corrupted Accounts

**Migration Script: migration_007_restore_corrupted_oauth_accounts.py**

```python
"""
Migration 007: Restore corrupted OAuth accounts

Finds accounts where:
- auth_method = 'imap'
- oauth_refresh_token IS NOT NULL

These accounts were corrupted by the bug at gmail_fetcher_service.py:78
and should have auth_method = 'oauth'.
"""

def upgrade(session):
    """
    Restore corrupted OAuth accounts.

    Pseudocode:
    1. Query accounts WHERE auth_method='imap' AND oauth_refresh_token IS NOT NULL
    2. For each account:
       a. Set auth_method = 'oauth'
       b. Log the restoration
    3. Commit changes
    """
    corrupted = session.query(EmailAccount).filter(
        EmailAccount.auth_method == 'imap',
        EmailAccount.oauth_refresh_token.isnot(None)
    ).all()

    count = 0
    for account in corrupted:
        account.auth_method = 'oauth'
        count += 1
        logger.info(f"Restored OAuth auth_method for: {account.email_address}")

    session.commit()
    logger.info(f"Migration 007: Restored {count} corrupted OAuth accounts")
    return count

def downgrade(session):
    """
    No downgrade - cannot determine which accounts were originally corrupted.
    """
    logger.warning("Migration 007 downgrade: No action (irreversible)")
    pass
```

---

## Implementation Steps

### Step 1: Create AuthMethodResolver Service

```
File: services/auth_method_resolver.py

class AuthMethodResolver(IAuthMethodResolver):
    def resolve(self, connection_service, app_password):
        if connection_service is not None:
            return (None, None)  # Don't overwrite OAuth
        else:
            return ('imap', app_password)  # Set IMAP credentials
```

### Step 2: Update GmailFetcher.__init__

```
File: services/gmail_fetcher_service.py
Location: Lines 74-82

Changes:
1. Add conditional logic before get_or_create_account call
2. Check if connection_service is provided
3. If OAuth (connection_service provided): pass None for auth_method and app_password
4. If IMAP (no connection_service): pass 'imap' and app_password
```

### Step 3: Create Migration Script

```
File: migrations/migration_007_restore_corrupted_oauth_accounts.py

Purpose: One-time fix for accounts corrupted before the code fix
Query: auth_method='imap' AND oauth_refresh_token IS NOT NULL
Action: Set auth_method='oauth'
```

### Step 4: Add Unit Tests

```
File: tests/test_gmail_oauth_auth_fix.py

Tests:
1. test_oauth_account_auth_method_not_overwritten
   - Create GmailFetcher with connection_service
   - Verify get_or_create_account called with auth_method=None

2. test_imap_account_auth_method_set_correctly
   - Create GmailFetcher without connection_service
   - Verify get_or_create_account called with auth_method='imap'

3. test_migration_restores_corrupted_oauth_accounts
   - Create account with oauth_refresh_token but auth_method='imap'
   - Run migration
   - Verify auth_method changed to 'oauth'

4. test_migration_ignores_true_imap_accounts
   - Create account with auth_method='imap' and no oauth_refresh_token
   - Run migration
   - Verify auth_method still 'imap'

5. test_migration_ignores_healthy_oauth_accounts
   - Create account with auth_method='oauth' and oauth_refresh_token
   - Run migration
   - Verify no change
```

---

## Context Budget

| Category | Count | Lines (Estimated) |
|----------|-------|-------------------|
| Files to read | 3 | ~900 lines |
| - gmail_fetcher_service.py | 1 | ~450 lines |
| - account_category_client.py | 1 | ~850 lines |
| - database.py | 1 | ~330 lines |
| New code to write | | ~80 lines |
| - Auth method conditional in GmailFetcher | | ~15 lines |
| - Migration script | | ~50 lines |
| - AuthMethodResolver (optional) | | ~15 lines |
| Test code to write | | ~120 lines |
| - test_gmail_oauth_auth_fix.py | | ~120 lines |
| **Total new code** | | ~200 lines |
| **Estimated context usage** | | **35%** |

**Verdict**: WITHIN BUDGET (35% < 60%)

---

## Edge Cases

1. **New IMAP Account**: Should set auth_method='imap' (current behavior preserved)
2. **Existing OAuth Account Processing**: Should NOT overwrite auth_method
3. **Account with Both Credentials**: If oauth_refresh_token exists, treat as OAuth
4. **Migration Idempotency**: Running migration twice should be safe (no-op second time)
5. **Null oauth_refresh_token with auth_method='imap'**: True IMAP account, no change needed

---

## Rollback Plan

1. **Code Fix**: Revert changes to gmail_fetcher_service.py (restores bug)
2. **Migration**: No automatic rollback - manually set accounts back to 'imap' if needed
3. **Feature Flag** (optional): Add env var to disable conditional logic for testing

---

## Success Criteria

1. OAuth accounts retain `auth_method='oauth'` after processing runs
2. IMAP accounts continue to have `auth_method='imap'` set correctly
3. Previously corrupted OAuth accounts are restored by migration
4. All existing tests continue to pass
5. New tests cover both OAuth and IMAP paths

---

## Dependencies

- No new dependencies required
- Uses existing SQLAlchemy models and session management
- Uses existing AccountCategoryClient interface

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration affects true IMAP accounts | Low | Migration only touches accounts with oauth_refresh_token |
| get_or_create_account changes behavior | Medium | Only changes when auth_method/password are None |
| Existing tests fail | Low | No existing tests for this specific path |

---

## Approval Checklist

- [ ] Interfaces follow strict-architecture guidelines
- [ ] Data models are immutable where appropriate
- [ ] Logic flow is clear and testable
- [ ] Context budget is within 60% limit
- [ ] Edge cases are documented
- [ ] Rollback plan exists
