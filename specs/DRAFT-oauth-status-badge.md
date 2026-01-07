# DRAFT Spec: OAuth Status Badge on Accounts Page

## Summary
Add a visual indicator on the Accounts page showing Gmail OAuth connection status. The accounts table displays whether each account is connected via OAuth (green "OAuth Connected" badge) or using IMAP credentials (gray "IMAP" badge).

## Root Request
> "Add a visual indicator on the Accounts page showing Gmail OAuth connection status. The accounts table should display whether each account is connected via OAuth (showing a green 'OAuth Connected' badge) or using IMAP credentials (showing a gray 'IMAP' badge). The frontend should call the existing /api/accounts/{email}/oauth-status endpoint to get connection status, or ideally include auth_method in the /api/accounts response to avoid extra API calls per account."

---

## Interfaces Needed

### 1. IAuthMethodBadgeRenderer (Frontend Interface)
**Purpose**: Renders the appropriate badge based on auth_method value.

```typescript
interface IAuthMethodBadgeRenderer {
    /**
     * Renders HTML for auth method badge
     * @param authMethod - "oauth" | "imap" | null
     * @returns HTML string for badge element
     */
    renderBadge(authMethod: string | null): string;
}
```

### 2. IEmailAccountInfoExtended (API Response Model)
**Purpose**: Extended account info response that includes auth_method field.

```python
class IEmailAccountInfoExtended(Protocol):
    """Protocol for email account info with auth method"""
    email: str
    is_active: bool
    auth_method: Optional[str]  # "oauth" or "imap"
    # ... other existing fields
```

---

## Data Models

### 1. EmailAccountInfo (Modified Response Model)
**Location**: models/account_models.py

```python
class EmailAccountInfo(BaseModel):
    """Email account information for API responses"""
    email: str
    is_active: bool
    fetch_interval_minutes: int
    max_emails_per_fetch: int
    last_successful_fetch: Optional[datetime] = None
    auth_method: Optional[str] = None  # NEW FIELD: "oauth" or "imap"

    class Config:
        from_attributes = True
```

### 2. Badge Display Constants (Frontend)
**Location**: frontend/templates/accounts.html (inline JavaScript)

```javascript
const AUTH_METHOD_BADGES = {
    oauth: {
        text: "OAuth Connected",
        cssClass: "badge bg-success"
    },
    imap: {
        text: "IMAP",
        cssClass: "badge bg-secondary"
    },
    unknown: {
        text: "Unknown",
        cssClass: "badge bg-light text-dark"
    }
};
```

---

## Logic Flow

### Backend: GET /api/accounts Enhancement

```pseudocode
FUNCTION get_accounts(request):
    accounts = database.get_all_email_accounts()

    response_list = []
    FOR account IN accounts:
        account_info = EmailAccountInfo(
            email = account.email,
            is_active = account.is_active,
            fetch_interval_minutes = account.fetch_interval_minutes,
            max_emails_per_fetch = account.max_emails_per_fetch,
            last_successful_fetch = account.last_successful_fetch,
            auth_method = account.auth_method  # NEW: include from database
        )
        response_list.append(account_info)

    RETURN response_list
```

### Frontend: Badge Rendering

```pseudocode
FUNCTION renderAuthMethodBadge(authMethod):
    IF authMethod == "oauth":
        RETURN '<span class="badge bg-success">OAuth Connected</span>'
    ELSE IF authMethod == "imap":
        RETURN '<span class="badge bg-secondary">IMAP</span>'
    ELSE:
        RETURN '<span class="badge bg-light text-dark">Unknown</span>'
```

### Frontend: Table Column Addition

```pseudocode
FUNCTION renderAccountsTable(accounts):
    FOR account IN accounts:
        row = CREATE table_row
        row.append(cell(account.email))
        row.append(cell(account.is_active))
        row.append(cell(renderAuthMethodBadge(account.auth_method)))  # NEW COLUMN
        row.append(cell(account.fetch_interval_minutes))
        row.append(cell(account.last_successful_fetch))
        row.append(cell(action_buttons))
        table.append(row)
```

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| models/account_models.py | Modify | Add `auth_method: Optional[str]` field to EmailAccountInfo |
| api_service.py | Modify | Include `auth_method=account.auth_method` in GET /api/accounts response construction |
| frontend/templates/accounts.html | Modify | Add "Auth Method" column header to table |
| frontend/templates/accounts.html | Modify | Update renderAccountsTable() to display badge for auth_method |

---

## Context Budget

| Category | Estimate |
|----------|----------|
| Files to read | 4 files (~400 lines) |
| New code to write | ~30 lines |
| Test code to write | ~80 lines |
| Estimated context usage | **15%** |

**Assessment**: Well within the 60% limit. This is a small, focused feature.

---

## Test Scenarios

### Backend Tests
1. **API returns auth_method in response**: Verify GET /api/accounts includes auth_method for each account
2. **OAuth account shows "oauth"**: Account with auth_method="oauth" returns "oauth" in response
3. **IMAP account shows "imap"**: Account with auth_method="imap" returns "imap" in response
4. **Null auth_method handled**: Account with NULL auth_method returns null/None in response

### Frontend Tests (Manual/E2E)
1. **OAuth badge displayed**: Account with auth_method="oauth" shows green "OAuth Connected" badge
2. **IMAP badge displayed**: Account with auth_method="imap" shows gray "IMAP" badge
3. **Unknown badge displayed**: Account with null auth_method shows neutral "Unknown" badge
4. **Column alignment**: Auth Method column aligns properly with other table columns

---

## Edge Cases

1. **Legacy accounts with NULL auth_method**: Display "Unknown" badge
2. **Mixed account types**: Table correctly shows different badges for different accounts
3. **Empty accounts list**: Table renders correctly with no rows
4. **Case sensitivity**: Handle both "OAuth" and "oauth" consistently (normalize to lowercase)

---

## Dependencies

- Existing EmailAccount database model already has `auth_method` column
- Existing GET /api/accounts endpoint structure
- Bootstrap CSS classes for badge styling (bg-success, bg-secondary, bg-light)

---

## Out of Scope

- OAuth token refresh status (valid/expired) - use existing oauth-status endpoint for detailed info
- OAuth connection/disconnection actions - handled by existing OAuth flow
- IMAP credential management - existing functionality
