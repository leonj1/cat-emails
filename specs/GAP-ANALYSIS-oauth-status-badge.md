# Gap Analysis: OAuth Status Badge on Accounts Page

## Overview

This document analyzes the existing codebase to identify reuse opportunities and new components needed to implement the OAuth Status Badge feature.

## Root Request

> "Add a visual indicator on the Accounts page showing Gmail OAuth connection status. The accounts table should display whether each account is connected via OAuth (showing a green 'OAuth Connected' badge) or using IMAP credentials (showing a gray 'IMAP' badge)."

## Existing Code Analysis

### Database Layer - COMPLETE

**File**: `/root/repo/models/database.py` (lines 31-60)

The `EmailAccount` model already has the required `auth_method` column:

```python
class EmailAccount(Base):
    __tablename__ = 'email_accounts'
    # ...
    auth_method = Column(String(20), default='imap')  # 'imap' or 'oauth'
    # ...
    __table_args__ = (
        Index('idx_auth_method', 'auth_method'),
    )
```

**Status**: No changes needed. The column exists with proper indexing.

### API Response Model - NEEDS UPDATE

**File**: `/root/repo/models/account_models.py` (lines 97-123)

The `EmailAccountInfo` Pydantic model currently does NOT include `auth_method`:

```python
class EmailAccountInfo(BaseModel):
    id: int
    email_address: str
    display_name: Optional[str]
    masked_password: Optional[str]
    password_length: int
    is_active: bool
    last_scan_at: Optional[datetime]
    created_at: datetime
    # MISSING: auth_method field
```

**Action Required**: Add `auth_method: Optional[str]` field to the model.

### API Endpoint - NEEDS UPDATE

**File**: `/root/repo/api_service.py` (lines 1846-1857)

The `get_all_accounts` endpoint maps database fields to `EmailAccountInfo`:

```python
account_infos = [
    EmailAccountInfo(
        id=account.id,
        email_address=account.email_address,
        display_name=account.display_name,
        masked_password=mask_password(account.app_password),
        password_length=len(account.app_password) if account.app_password else 0,
        is_active=account.is_active,
        last_scan_at=account.last_scan_at,
        created_at=account.created_at
        # MISSING: auth_method=account.auth_method
    )
    for account in accounts
]
```

**Action Required**: Add `auth_method=account.auth_method` to the mapping.

### Frontend Template - NEEDS UPDATE

**File**: `/root/repo/frontend/templates/accounts.html`

**Reusable Components**:

1. **Badge styling** (lines 66-87): Existing `status-badge` CSS class can be adapted:
   ```css
   .status-badge {
       padding: 0.375rem 0.75rem;
       border-radius: 1rem;
       font-size: 0.8125rem;
       font-weight: 600;
       display: inline-block;
       min-width: 5rem;
       text-align: center;
   }
   ```

2. **Table structure** (lines 331-346): Existing table with headers - need to add "Auth Method" column

3. **JavaScript rendering** (lines 476-598): `renderAccountsTable()` function - need to add auth method badge logic

**Action Required**:
- Add "Auth Method" column header after "Email Address"
- Add CSS styles for auth method badges (`.auth-badge.oauth`, `.auth-badge.imap`, `.auth-badge.not-configured`)
- Update `renderAccountsTable()` to create auth method badge cell
- Add aria-labels for accessibility

## Components Summary

| Component | File | Status | Action |
|-----------|------|--------|--------|
| Database schema | models/database.py | Complete | None |
| API response model | models/account_models.py | Needs update | Add auth_method field |
| API endpoint mapping | api_service.py | Needs update | Include auth_method in mapping |
| Table column header | frontend/templates/accounts.html | Needs update | Add "Auth Method" column |
| Badge CSS styles | frontend/templates/accounts.html | Needs update | Add auth badge styles |
| Badge rendering JS | frontend/templates/accounts.html | Needs update | Create badge in table rows |
| Accessibility | frontend/templates/accounts.html | Needs update | Add aria-labels |

## Reuse Patterns

### Pattern 1: Badge Styling
Copy existing `status-badge` pattern for `auth-badge`:
- `.auth-badge.oauth` - Green badge (similar to `.status-badge.active`)
- `.auth-badge.imap` - Gray badge (similar to `.status-badge.inactive`)
- `.auth-badge.not-configured` - Neutral badge (new)

### Pattern 2: Table Cell Creation
Follow existing DOM creation pattern in `renderAccountsTable()`:
```javascript
// Existing pattern for cells
const statusCell = document.createElement('td');
statusCell.setAttribute('data-label', 'Status');
const statusBadge = document.createElement('span');
statusBadge.className = account.is_active ? 'status-badge active' : 'status-badge inactive';
statusBadge.textContent = account.is_active ? 'Active' : 'Inactive';
statusCell.appendChild(statusBadge);
```

### Pattern 3: Pydantic Optional Field
Follow existing pattern for optional fields in `EmailAccountInfo`:
```python
display_name: Optional[str] = Field(
    None,
    description="Optional display name for the account"
)
```

## Refactoring Decision

**GO SIGNAL: APPROVED**

No refactoring is required before implementation:
1. Database schema is already in place
2. Existing code patterns are clean and reusable
3. Changes are additive, not modifications to existing behavior
4. All changes follow established project patterns

## Implementation Order

1. **Backend First**: Update `EmailAccountInfo` model and API endpoint
2. **Frontend Second**: Update template with column, styling, and JavaScript

This order ensures the frontend has data to display when implemented.

## Test Coverage Needed

Based on BDD scenarios:
- Unit tests for API response including auth_method
- Integration tests for various auth_method values (oauth, imap, null)
- Frontend tests for badge rendering
- Accessibility tests for aria-labels
