# BDD Specification: OAuth Status Badge on Accounts Page

## Overview

This feature adds a visual indicator on the Accounts page showing the authentication method for each email account. Users can quickly identify which accounts are connected via OAuth (green "OAuth Connected" badge) and which use IMAP credentials (gray "IMAP" badge). Legacy accounts with no configured authentication method display a neutral "Not Configured" badge.

## Root Request

> "Add a visual indicator on the Accounts page showing Gmail OAuth connection status. The accounts table should display whether each account is connected via OAuth (showing a green 'OAuth Connected' badge) or using IMAP credentials (showing a gray 'IMAP' badge). The frontend should call the existing /api/accounts/{email}/oauth-status endpoint to get connection status, or ideally include auth_method in the /api/accounts response to avoid extra API calls per account."

## User Stories

- As a user of the email management system, I want to see the authentication method for each account on the Accounts page, so that I can quickly identify which accounts use OAuth and which use IMAP.

## Feature Files

| Feature File | Scenarios | Coverage |
|--------------|-----------|----------|
| oauth-status-badge.feature | 17 | Happy paths, edge cases, API response, error handling, accessibility |

## Scenarios Summary

### oauth-status-badge.feature

#### Happy Paths (4 scenarios)
1. **OAuth Connected account displays green badge** - Account with auth_method "oauth" shows green "OAuth Connected" badge
2. **IMAP account displays gray badge** - Account with auth_method "imap" shows gray "IMAP" badge
3. **Accounts list shows mixed authentication methods** - Table correctly displays different badges for different account types
4. **Auth Method column is visible in accounts table** - Column header present, positioned after Email column

#### Edge Cases (3 scenarios)
5. **Legacy account with null auth_method displays Not Configured badge** - Null/legacy accounts show neutral badge
6. **Empty accounts list renders correctly** - Table renders headers with no data rows
7. **Case insensitive auth_method handling** - "OAuth" and "oauth" both render green badge

#### API Response Behavior (4 scenarios)
8. **API response includes auth_method for each account** - Every account has auth_method field
9. **OAuth account returns oauth auth_method in API response** - OAuth accounts return "oauth"
10. **IMAP account returns imap auth_method in API response** - IMAP accounts return "imap"
11. **Legacy account returns null auth_method in API response** - Legacy accounts return null

#### Error Handling (2 scenarios)
12. **Badge renders gracefully for unexpected auth_method value** - Unknown values show "Not Configured"
13. **Badge renders when auth_method field is missing from response** - Missing field shows "Not Configured"

#### Accessibility (4 scenarios)
14. **OAuth badge has accessible aria-label** - "Authentication method: OAuth Connected"
15. **IMAP badge has accessible aria-label** - "Authentication method: IMAP"
16. **Not Configured badge has accessible aria-label** - "Authentication method: Not Configured"
17. **Auth Method column header is accessible** - Proper table header scope

## Badge Specifications

| auth_method Value | Badge Text | Badge Color | CSS Class | aria-label |
|-------------------|------------|-------------|-----------|------------|
| "oauth" | OAuth Connected | Green | bg-success | Authentication method: OAuth Connected |
| "imap" | IMAP | Gray | bg-secondary | Authentication method: IMAP |
| null / undefined / unexpected | Not Configured | Neutral | bg-light text-dark | Authentication method: Not Configured |

## Column Position

The "Auth Method" column should appear **after the Email column** as the second data column. Rationale:
- Authentication method is a fundamental property of account identity
- Users scanning the table want to quickly see: "Which account? How is it connected?"
- Follows pattern of "identity first, then status, then operational details"

## Acceptance Criteria

### Backend
- [ ] GET /api/accounts response includes `auth_method` field for each account
- [ ] OAuth accounts return `auth_method: "oauth"`
- [ ] IMAP accounts return `auth_method: "imap"`
- [ ] Legacy accounts return `auth_method: null`

### Frontend
- [ ] Accounts table displays "Auth Method" column header
- [ ] Column positioned after Email column
- [ ] OAuth accounts show green "OAuth Connected" badge
- [ ] IMAP accounts show gray "IMAP" badge
- [ ] Null/undefined/unexpected values show neutral "Not Configured" badge
- [ ] Case insensitive handling (normalize to lowercase)
- [ ] Empty table renders correctly with headers

### Accessibility
- [ ] All badges have appropriate aria-labels
- [ ] Column header has proper table header scope
- [ ] Screen readers can identify badge meaning

## Dependencies

- Existing `EmailAccount` database model with `auth_method` column
- Existing GET /api/accounts endpoint structure
- Bootstrap CSS classes for badge styling (bg-success, bg-secondary, bg-light)

## Out of Scope

- OAuth token refresh status (valid/expired)
- OAuth connection/disconnection actions
- IMAP credential management

## Related Files

- `models/account_models.py` - EmailAccountInfo model
- `api_service.py` - GET /api/accounts endpoint
- `frontend/templates/accounts.html` - Accounts page template

---

**Ready for**: gherkin-to-test agent
