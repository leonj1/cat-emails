# Cat-Emails Account Tracking API Documentation

> Version: 1.1.0  
> Last Updated: 2025-01-04  
> Base URL: `http://localhost:8000` (default)

## Overview

The Cat-Emails Account Tracking API provides endpoints for managing email account tracking and retrieving category statistics. This API allows you to:

- Track multiple Gmail accounts for email categorization
- Retrieve top email categories for specific accounts with historical data
- Manage account lifecycle (register, list, deactivate)
- Access detailed statistics including email processing actions

## Authentication

The API supports optional authentication via API key header:

```http
X-API-Key: your-api-key-here
```

**Authentication Requirements:**
- If the `API_KEY` environment variable is set, all requests require the `X-API-Key` header
- If no `API_KEY` is configured, the API operates without authentication
- Invalid or missing API keys return `401 Unauthorized`

## Base Configuration

**Default Server:** `http://localhost:8000`  
**API Version:** v1  
**Content-Type:** `application/json`

## Endpoints

### 1. Get Top Categories by Account

**GET** `/api/accounts/{email_address}/categories/top`

Retrieves the most frequent email categories for a specific Gmail account over a specified time period, ranked by email volume.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email_address` | string | Yes | Gmail email address (URL-encoded) |

#### Query Parameters

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `days` | integer | Yes | - | 1-365 | Number of days to look back from today |
| `limit` | integer | No | 10 | 1-50 | Maximum number of categories to return |
| `include_counts` | boolean | No | false | - | Include detailed action counts (kept/deleted/archived) |

#### Request Example

```bash
curl -X GET "http://localhost:8000/api/accounts/user%40gmail.com/categories/top?days=30&limit=5&include_counts=true" \
  -H "X-API-Key: your-api-key" \
  -H "Accept: application/json"
```

#### Response Format

**Success Response (200 OK):**

```json
{
  "email_address": "user@gmail.com",
  "period": {
    "start_date": "2024-12-05",
    "end_date": "2025-01-04",
    "days": 30
  },
  "total_emails": 245,
  "top_categories": [
    {
      "category": "Marketing",
      "total_count": 89,
      "percentage": 36.33,
      "kept_count": 12,
      "deleted_count": 77,
      "archived_count": 0
    },
    {
      "category": "Personal",
      "total_count": 67,
      "percentage": 27.35,
      "kept_count": 65,
      "deleted_count": 2,
      "archived_count": 0
    },
    {
      "category": "Financial-Notification",
      "total_count": 34,
      "percentage": 13.88,
      "kept_count": 34,
      "deleted_count": 0,
      "archived_count": 0
    }
  ]
}
```

**Response without detailed counts (include_counts=false):**

```json
{
  "email_address": "user@gmail.com",
  "period": {
    "start_date": "2024-12-05",
    "end_date": "2025-01-04",
    "days": 30
  },
  "total_emails": 245,
  "top_categories": [
    {
      "category": "Marketing",
      "total_count": 89,
      "percentage": 36.33
    },
    {
      "category": "Personal", 
      "total_count": 67,
      "percentage": 27.35
    }
  ]
}
```

#### Error Responses

**400 Bad Request - Invalid Parameters:**
```json
{
  "detail": "Invalid email address format"
}
```

**401 Unauthorized - Missing/Invalid API Key:**
```json
{
  "detail": "Invalid or missing API key"
}
```

**404 Not Found - Account Not Found:**
```json
{
  "detail": "Account not found: user@gmail.com"
}
```

**422 Unprocessable Entity - Validation Error:**
```json
{
  "detail": "Invalid request parameters: days must be between 1 and 365"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Database error occurred"
}
```

---

### 2. List All Tracked Accounts

**GET** `/api/accounts`

Retrieves a list of all Gmail accounts being tracked by the system, with optional filtering for active accounts only.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `active_only` | boolean | No | true | Filter to only active accounts |

#### Request Example

```bash
curl -X GET "http://localhost:8000/api/accounts?active_only=false" \
  -H "X-API-Key: your-api-key" \
  -H "Accept: application/json"
```

#### Response Format

**Success Response (200 OK):**

```json
{
  "accounts": [
    {
      "id": 1,
      "email_address": "user1@gmail.com",
      "display_name": "John Doe",
      "is_active": true,
      "last_scan_at": "2025-01-04T14:30:00.123456",
      "created_at": "2024-11-15T08:00:00.000000"
    },
    {
      "id": 2,
      "email_address": "user2@gmail.com",
      "display_name": null,
      "is_active": false,
      "last_scan_at": "2024-12-20T10:15:00.987654",
      "created_at": "2024-10-01T12:30:00.000000"
    }
  ],
  "total_count": 2
}
```

#### Error Responses

**401 Unauthorized:**
```json
{
  "detail": "Invalid or missing API key"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Database error occurred"
}
```

---

### 3. Register New Account

**POST** `/api/accounts`

Creates a new account entry in the system for email category tracking. If the account already exists, it will be reactivated and updated.

#### Request Body

```json
{
  "email_address": "newuser@gmail.com",
  "display_name": "New User"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email_address` | string | Yes | Valid Gmail email address |
| `display_name` | string | No | Optional display name for the account |

#### Request Example

```bash
curl -X POST "http://localhost:8000/api/accounts" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "email_address": "newuser@gmail.com",
    "display_name": "New User"
  }'
```

#### Response Format

**Success Response (200 OK):**

```json
{
  "status": "success",
  "message": "Account registered successfully: newuser@gmail.com",
  "timestamp": "2025-01-04T15:30:00.123456"
}
```

#### Error Responses

**400 Bad Request - Invalid Email:**
```json
{
  "detail": "Invalid email address format"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Invalid or missing API key"
}
```

**422 Unprocessable Entity - Validation Error:**
```json
{
  "detail": "Invalid request format: field required"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Database error occurred"
}
```

---

### 4. Deactivate Account

**PUT** `/api/accounts/{email_address}/deactivate`

Marks an account as inactive, excluding it from active scanning while preserving historical data. The account can be reactivated later by creating it again.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email_address` | string | Yes | Gmail email address to deactivate (URL-encoded) |

#### Request Example

```bash
curl -X PUT "http://localhost:8000/api/accounts/user%40gmail.com/deactivate" \
  -H "X-API-Key: your-api-key" \
  -H "Accept: application/json"
```

#### Response Format

**Success Response (200 OK):**

```json
{
  "status": "success",
  "message": "Account deactivated successfully: user@gmail.com",
  "timestamp": "2025-01-04T15:45:00.123456"
}
```

#### Error Responses

**400 Bad Request:**
```json
{
  "detail": "Invalid email address format"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Invalid or missing API key"
}
```

**404 Not Found:**
```json
{
  "detail": "Account not found: user@gmail.com"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Database error occurred"
}
```

## Data Models

### CategoryStats

Represents statistics for a single email category.

```json
{
  "category": "Marketing",
  "total_count": 89,
  "percentage": 36.33,
  "kept_count": 12,          // Optional: only if include_counts=true
  "deleted_count": 77,       // Optional: only if include_counts=true
  "archived_count": 0        // Optional: only if include_counts=true
}
```

### DatePeriod

Represents a date range period for category statistics.

```json
{
  "start_date": "2024-12-05",
  "end_date": "2025-01-04", 
  "days": 30
}
```

### EmailAccountInfo

Information about a tracked email account.

```json
{
  "id": 1,
  "email_address": "user@gmail.com",
  "display_name": "John Doe",           // Optional
  "is_active": true,
  "last_scan_at": "2025-01-04T14:30:00.123456",  // Optional
  "created_at": "2024-11-15T08:00:00.000000"
}
```

## Email Categories

The system recognizes these email categories:

- **Marketing** - Indirect marketing content and newsletters
- **Advertising** - Direct product promotions and sales
- **Personal** - Personal correspondence from friends/family
- **Wants-Money** - Payment requests, invoices, donations
- **Financial-Notification** - Bank statements and financial alerts
- **Work-related** - Professional and business emails
- **Service-Updates** - Service notifications and updates
- **Appointment-Reminder** - Meeting and appointment notifications
- **Other** - Uncategorized emails

## Common Use Cases

### 1. Dashboard Analytics

Get recent activity for multiple accounts:

```bash
# Get top 5 categories for last 7 days
curl -X GET "http://localhost:8000/api/accounts/user%40gmail.com/categories/top?days=7&limit=5" \
  -H "X-API-Key: your-api-key"

# Get all tracked accounts
curl -X GET "http://localhost:8000/api/accounts" \
  -H "X-API-Key: your-api-key"
```

### 2. Account Management Workflow

```bash
# 1. Register new account
curl -X POST "http://localhost:8000/api/accounts" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"email_address": "new@gmail.com", "display_name": "New Account"}'

# 2. Check account was created
curl -X GET "http://localhost:8000/api/accounts" \
  -H "X-API-Key: your-api-key"

# 3. Get statistics after some time
curl -X GET "http://localhost:8000/api/accounts/new%40gmail.com/categories/top?days=30&include_counts=true" \
  -H "X-API-Key: your-api-key"

# 4. Deactivate when no longer needed  
curl -X PUT "http://localhost:8000/api/accounts/new%40gmail.com/deactivate" \
  -H "X-API-Key: your-api-key"
```

### 3. Performance Analysis

Get detailed statistics with action breakdown:

```bash
curl -X GET "http://localhost:8000/api/accounts/user%40gmail.com/categories/top?days=30&limit=10&include_counts=true" \
  -H "X-API-Key: your-api-key"
```

This shows which categories are being deleted vs kept, helping optimize filtering rules.

## Error Handling

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid email format, invalid parameters |
| 401 | Unauthorized | Missing or invalid API key |
| 404 | Not Found | Account doesn't exist |
| 422 | Unprocessable Entity | Request validation failed |
| 500 | Internal Server Error | Database issues, unexpected errors |

### Error Response Format

All errors follow this standard format:

```json
{
  "detail": "Human-readable error description"
}
```

### Best Practices for Error Handling

1. **Check HTTP status codes** before parsing response body
2. **Implement retry logic** for 5xx errors with exponential backoff
3. **Validate email addresses** client-side before sending requests  
4. **Handle 404 errors gracefully** when account doesn't exist
5. **Store API keys securely** and rotate them regularly

## Rate Limiting

Currently, there are no explicit rate limits imposed by the API. However, consider these recommendations:

- **Be respectful**: Don't overwhelm the server with rapid requests
- **Batch operations**: Use appropriate date ranges rather than multiple small requests
- **Cache responses**: Store category statistics locally when possible
- **Monitor performance**: Watch for slow responses indicating server load

## Security Considerations

1. **API Key Security**:
   - Store API keys in environment variables, never in code
   - Use HTTPS in production environments  
   - Rotate API keys regularly

2. **Email Address Handling**:
   - URL-encode email addresses in path parameters
   - Validate email formats client-side
   - Be aware that email addresses are case-sensitive

3. **Data Privacy**:
   - This API provides metadata about email processing
   - Actual email content is never exposed via the API
   - Account deactivation preserves historical data

## Integration Examples

### Python Integration

```python
import requests
from urllib.parse import quote

class CatEmailsAPI:
    def __init__(self, base_url="http://localhost:8000", api_key=None):
        self.base_url = base_url
        self.headers = {"Accept": "application/json"}
        if api_key:
            self.headers["X-API-Key"] = api_key
    
    def get_top_categories(self, email_address, days=30, limit=10, include_counts=False):
        """Get top categories for an account."""
        url = f"{self.base_url}/api/accounts/{quote(email_address)}/categories/top"
        params = {"days": days, "limit": limit, "include_counts": include_counts}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def list_accounts(self, active_only=True):
        """List all tracked accounts."""
        url = f"{self.base_url}/api/accounts"
        params = {"active_only": active_only}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def create_account(self, email_address, display_name=None):
        """Register a new account."""
        url = f"{self.base_url}/api/accounts"
        data = {"email_address": email_address}
        if display_name:
            data["display_name"] = display_name
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def deactivate_account(self, email_address):
        """Deactivate an account."""
        url = f"{self.base_url}/api/accounts/{quote(email_address)}/deactivate"
        response = requests.put(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

# Usage example
api = CatEmailsAPI(api_key="your-api-key")
categories = api.get_top_categories("user@gmail.com", days=30, include_counts=True)
print(f"Top category: {categories['top_categories'][0]['category']}")
```

### JavaScript Integration

```javascript
class CatEmailsAPI {
    constructor(baseUrl = 'http://localhost:8000', apiKey = null) {
        this.baseUrl = baseUrl;
        this.headers = { 'Accept': 'application/json' };
        if (apiKey) {
            this.headers['X-API-Key'] = apiKey;
        }
    }

    async getTopCategories(emailAddress, days = 30, limit = 10, includeCounts = false) {
        const params = new URLSearchParams({
            days: days.toString(),
            limit: limit.toString(),
            include_counts: includeCounts.toString()
        });
        
        const response = await fetch(
            `${this.baseUrl}/api/accounts/${encodeURIComponent(emailAddress)}/categories/top?${params}`,
            { headers: this.headers }
        );
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }
        
        return await response.json();
    }

    async listAccounts(activeOnly = true) {
        const params = new URLSearchParams({ active_only: activeOnly.toString() });
        const response = await fetch(
            `${this.baseUrl}/api/accounts?${params}`,
            { headers: this.headers }
        );
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }
        
        return await response.json();
    }
}

// Usage example
const api = new CatEmailsAPI('http://localhost:8000', 'your-api-key');
api.getTopCategories('user@gmail.com', 30, 5, true)
    .then(data => console.log('Top categories:', data.top_categories))
    .catch(error => console.error('API Error:', error));
```

---

## Support and Further Information

- **Service Health**: Check `/api/health` for service status
- **API Root**: Visit `/` for endpoint overview and version info
- **Logs**: Check application logs for detailed error information
- **Database**: All data is stored locally in SQLite database

For implementation details, see the source code in `api_service.py` and `models/account_models.py`.