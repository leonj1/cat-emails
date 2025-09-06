# Cat-Emails Account API Quick Start Guide

> Get started with the Cat-Emails Account Tracking API in minutes

## Table of Contents

1. [Quick Setup](#quick-setup)
2. [Authentication](#authentication)
3. [First API Call](#first-api-call)
4. [Common Use Cases](#common-use-cases)
5. [Integration Examples](#integration-examples)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Quick Setup

### 1. Start the API Server

```bash
# Navigate to your Cat-Emails project directory
cd /path/to/cat-emails

# Install dependencies if not already done
pip install -r requirements.txt

# Start the API server (default: http://localhost:8000)
python api_service.py
```

### 2. Verify Server is Running

```bash
# Test the health endpoint
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-04T15:30:00.123456",
  "service": "Cat Emails Summary API"
}
```

### 3. Check Available Endpoints

```bash
# View all available endpoints
curl http://localhost:8000/
```

## Authentication

The API supports optional authentication via API key:

### Option 1: No Authentication (Development)

If no `API_KEY` environment variable is set, the API runs without authentication.

### Option 2: API Key Authentication (Recommended)

```bash
# Set API key environment variable
export API_KEY="your-secret-api-key-here"

# Restart the API server
python api_service.py

# All requests now require X-API-Key header
curl -H "X-API-Key: your-secret-api-key-here" http://localhost:8000/api/health
```

## First API Call

Let's make your first API call to list tracked accounts:

### Without Authentication

```bash
curl -X GET "http://localhost:8000/api/accounts" \
  -H "Accept: application/json"
```

### With Authentication

```bash
curl -X GET "http://localhost:8000/api/accounts" \
  -H "X-API-Key: your-secret-api-key-here" \
  -H "Accept: application/json"
```

### Expected Response

```json
{
  "accounts": [],
  "total_count": 0
}
```

Since this is a fresh setup, you'll see an empty list. Let's add your first account!

## Common Use Cases

### Use Case 1: Register Your First Account

```bash
# Register a new Gmail account for tracking
curl -X POST "http://localhost:8000/api/accounts" \
  -H "X-API-Key: your-secret-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "email_address": "your-email@gmail.com",
    "display_name": "My Main Account"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Account registered successfully: your-email@gmail.com",
  "timestamp": "2025-01-04T15:30:00.123456"
}
```

### Use Case 2: View Account Statistics

After your account has processed some emails, get category statistics:

```bash
# Get top 5 categories from the last 30 days
curl -X GET "http://localhost:8000/api/accounts/your-email%40gmail.com/categories/top?days=30&limit=5" \
  -H "X-API-Key: your-secret-api-key-here"
```

**Response:**
```json
{
  "email_address": "your-email@gmail.com",
  "period": {
    "start_date": "2024-12-05",
    "end_date": "2025-01-04",
    "days": 30
  },
  "total_emails": 156,
  "top_categories": [
    {
      "category": "Marketing",
      "total_count": 47,
      "percentage": 30.13
    },
    {
      "category": "Personal", 
      "total_count": 32,
      "percentage": 20.51
    }
  ]
}
```

### Use Case 3: Get Detailed Action Statistics

See how many emails were kept vs deleted for each category:

```bash
# Get detailed statistics with action counts
curl -X GET "http://localhost:8000/api/accounts/your-email%40gmail.com/categories/top?days=7&limit=3&include_counts=true" \
  -H "X-API-Key: your-secret-api-key-here"
```

**Response:**
```json
{
  "email_address": "your-email@gmail.com",
  "period": {
    "start_date": "2024-12-28",
    "end_date": "2025-01-04",
    "days": 7
  },
  "total_emails": 42,
  "top_categories": [
    {
      "category": "Marketing",
      "total_count": 15,
      "percentage": 35.71,
      "kept_count": 2,
      "deleted_count": 13,
      "archived_count": 0
    }
  ]
}
```

### Use Case 4: Managing Multiple Accounts

```bash
# Register additional accounts
curl -X POST "http://localhost:8000/api/accounts" \
  -H "X-API-Key: your-secret-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"email_address": "work@company.com", "display_name": "Work Email"}'

# List all accounts
curl -X GET "http://localhost:8000/api/accounts" \
  -H "X-API-Key: your-secret-api-key-here"

# Deactivate an account when no longer needed
curl -X PUT "http://localhost:8000/api/accounts/old%40gmail.com/deactivate" \
  -H "X-API-Key: your-secret-api-key-here"
```

## Integration Examples

### Python Script

Create a simple Python script to interact with the API:

```python
#!/usr/bin/env python3
"""
Simple Cat-Emails API client example
"""
import requests
import json
from urllib.parse import quote

# Configuration
API_BASE = "http://localhost:8000"
API_KEY = "your-secret-api-key-here"  # Set to None if no auth

def make_request(method, endpoint, data=None, params=None):
    """Make API request with error handling"""
    headers = {"Accept": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    
    if data:
        headers["Content-Type"] = "application/json"
    
    url = f"{API_BASE}{endpoint}"
    
    try:
        response = requests.request(method, url, headers=headers, json=data, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None

def main():
    # Register an account
    print("1. Registering account...")
    result = make_request("POST", "/api/accounts", {
        "email_address": "test@gmail.com",
        "display_name": "Test Account"
    })
    print(f"Result: {result}")
    
    # List accounts
    print("\n2. Listing accounts...")
    accounts = make_request("GET", "/api/accounts")
    print(f"Found {accounts['total_count']} accounts")
    
    # Get categories (this will only work if the account has processed emails)
    print("\n3. Getting top categories...")
    email = quote("test@gmail.com")
    categories = make_request("GET", f"/api/accounts/{email}/categories/top", 
                            params={"days": 30, "limit": 5})
    if categories:
        print(f"Top categories for last 30 days: {len(categories['top_categories'])} found")

if __name__ == "__main__":
    main()
```

Save as `api_example.py` and run:

```bash
python api_example.py
```

### Shell Script

Create a shell script for common operations:

```bash
#!/bin/bash
# Cat-Emails API Helper Script

API_BASE="http://localhost:8000"
API_KEY="your-secret-api-key-here"

# Function to make authenticated requests
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    local headers=("-H" "Accept: application/json")
    
    if [ ! -z "$API_KEY" ]; then
        headers+=("-H" "X-API-Key: $API_KEY")
    fi
    
    if [ ! -z "$data" ]; then
        headers+=("-H" "Content-Type: application/json")
        curl -X "$method" "${headers[@]}" -d "$data" "$API_BASE$endpoint"
    else
        curl -X "$method" "${headers[@]}" "$API_BASE$endpoint"
    fi
}

# Commands
case "$1" in
    "add-account")
        if [ -z "$2" ]; then
            echo "Usage: $0 add-account <email@gmail.com> [display_name]"
            exit 1
        fi
        data="{\"email_address\":\"$2\""
        if [ ! -z "$3" ]; then
            data="$data,\"display_name\":\"$3\""
        fi
        data="$data}"
        api_call "POST" "/api/accounts" "$data"
        ;;
    "list-accounts")
        api_call "GET" "/api/accounts"
        ;;
    "get-categories")
        if [ -z "$2" ]; then
            echo "Usage: $0 get-categories <email@gmail.com> [days]"
            exit 1
        fi
        encoded_email=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$2'))")
        days=${3:-30}
        api_call "GET" "/api/accounts/$encoded_email/categories/top?days=$days&limit=10"
        ;;
    "deactivate")
        if [ -z "$2" ]; then
            echo "Usage: $0 deactivate <email@gmail.com>"
            exit 1
        fi
        encoded_email=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$2'))")
        api_call "PUT" "/api/accounts/$encoded_email/deactivate"
        ;;
    *)
        echo "Usage: $0 {add-account|list-accounts|get-categories|deactivate}"
        echo "Examples:"
        echo "  $0 add-account user@gmail.com 'My Account'"
        echo "  $0 list-accounts"
        echo "  $0 get-categories user@gmail.com 30"
        echo "  $0 deactivate user@gmail.com"
        exit 1
        ;;
esac
```

Save as `api_helper.sh`, make executable, and use:

```bash
chmod +x api_helper.sh

# Add an account
./api_helper.sh add-account "your-email@gmail.com" "Your Name"

# List accounts
./api_helper.sh list-accounts

# Get categories
./api_helper.sh get-categories "your-email@gmail.com" 30
```

## Best Practices

### 1. Error Handling

Always check HTTP status codes and handle errors gracefully:

```bash
# Good: Check status and capture response
response=$(curl -s -w "%{http_code}" -o response.json \
  -X GET "http://localhost:8000/api/accounts" \
  -H "X-API-Key: $API_KEY")

if [ "$response" -eq 200 ]; then
    echo "Success!"
    cat response.json
else
    echo "Error: HTTP $response"
    cat response.json
fi
```

### 2. URL Encoding

Always URL-encode email addresses in path parameters:

```bash
# Wrong - will fail with special characters
curl "http://localhost:8000/api/accounts/user+tag@gmail.com/categories/top"

# Correct - properly encoded
curl "http://localhost:8000/api/accounts/user%2Btag%40gmail.com/categories/top"
```

### 3. Parameter Validation

Validate parameters before making requests:

```python
def get_categories(email, days=30, limit=10):
    # Validate parameters
    if not email or "@" not in email:
        raise ValueError("Invalid email address")
    
    if not (1 <= days <= 365):
        raise ValueError("Days must be between 1 and 365")
    
    if not (1 <= limit <= 50):
        raise ValueError("Limit must be between 1 and 50")
    
    # Make request...
```

### 4. Secure API Key Storage

Never hardcode API keys in your scripts:

```bash
# Good: Use environment variables
export CAT_EMAILS_API_KEY="your-key-here"

# In your script
API_KEY=${CAT_EMAILS_API_KEY}

# Or read from file
API_KEY=$(cat ~/.cat-emails-api-key)
```

### 5. Rate Limiting

Be respectful with your requests:

```python
import time

# Add delays between requests
for account in accounts:
    get_categories(account)
    time.sleep(1)  # Wait 1 second between requests
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: "Connection refused"

**Problem:** The API server isn't running.

**Solution:**
```bash
# Check if server is running
ps aux | grep api_service.py

# Start the server if not running
python api_service.py
```

#### Issue: "Invalid or missing API key"

**Problem:** API key authentication is enabled but not provided correctly.

**Solutions:**
```bash
# Check if API_KEY is set on server
echo $API_KEY

# Ensure header is correct (X-API-Key, not Api-Key)
curl -H "X-API-Key: your-key" ...

# Verify key matches server configuration
```

#### Issue: "Account not found"

**Problem:** Trying to get statistics for an account that isn't registered.

**Solution:**
```bash
# First register the account
curl -X POST "http://localhost:8000/api/accounts" \
  -H "Content-Type: application/json" \
  -d '{"email_address": "your@gmail.com"}'

# Then get statistics
curl "http://localhost:8000/api/accounts/your%40gmail.com/categories/top?days=30"
```

#### Issue: "No data to summarize"

**Problem:** The account exists but has no processed emails.

**Solution:** This is normal for new accounts. Run the email scanner first:
```bash
# Process emails for the account
python gmail_fetcher.py --hours 24

# Then try the API call again
```

#### Issue: "Invalid email address format"

**Problem:** Email address isn't properly formatted or encoded.

**Solutions:**
```bash
# Ensure valid email format
echo "user@gmail.com" | grep -E '^[^@]+@[^@]+\.[^@]+$'

# URL encode for path parameters
python3 -c "import urllib.parse; print(urllib.parse.quote('user+tag@gmail.com'))"
# Output: user%2Btag%40gmail.com
```

### Testing Your Setup

Run this comprehensive test to verify everything is working:

```bash
#!/bin/bash
echo "=== Cat-Emails API Test ==="

# Test 1: Health check
echo "1. Testing health endpoint..."
curl -s "http://localhost:8000/api/health" | grep -q "healthy" && echo "✓ Health check passed" || echo "✗ Health check failed"

# Test 2: List accounts (should work even if empty)
echo "2. Testing account listing..."
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/accounts" | grep -q "200" && echo "✓ Account listing works" || echo "✗ Account listing failed"

# Test 3: Try creating account
echo "3. Testing account creation..."
response=$(curl -s -w "%{http_code}" -o response.json -X POST "http://localhost:8000/api/accounts" \
  -H "Content-Type: application/json" \
  -d '{"email_address": "test@example.com", "display_name": "Test Account"}')

if [ "$response" -eq 200 ]; then
    echo "✓ Account creation works"
else
    echo "✗ Account creation failed (HTTP $response)"
    cat response.json
fi

# Clean up
rm -f response.json

echo "=== Test Complete ==="
```

### Getting Help

If you encounter issues not covered here:

1. **Check the logs**: Look at the API server output for detailed error messages
2. **Verify the database**: Ensure `projects.db` is accessible and not corrupted
3. **Test with curl**: Use simple curl commands to isolate issues
4. **Check permissions**: Ensure the API can read/write to necessary directories
5. **Review the full documentation**: See `API_ACCOUNT_ENDPOINTS.md` for complete details

### Next Steps

Once you're comfortable with the basics:

1. **Explore advanced features**: Try the `include_counts` parameter for detailed statistics
2. **Build integrations**: Create scripts or applications that use multiple endpoints
3. **Monitor performance**: Track your email processing efficiency over time
4. **Automate workflows**: Set up scheduled scripts to generate reports

For complete API documentation, see [`API_ACCOUNT_ENDPOINTS.md`](./API_ACCOUNT_ENDPOINTS.md).