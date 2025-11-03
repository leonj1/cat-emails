#!/bin/bash
#
# Script to query accounts from the Railway-deployed API service
#
# Usage: ./query_accounts_api.sh [API_URL] [API_KEY]
#
# Example:
#   ./query_accounts_api.sh https://your-app.railway.app your-api-key
#

API_URL="${1:-https://cat-emails-production.up.railway.app}"
API_KEY="${2:-${API_KEY}}"

echo "====================================="
echo "Querying Gmail Accounts from API"
echo "====================================="
echo ""
echo "API URL: $API_URL"
echo ""

# Check health endpoint first
echo "1. Checking API health..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/api/health" 2>/dev/null)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n 1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ API is healthy"
    echo "Response: $HEALTH_BODY"
else
    echo "❌ API health check failed (HTTP $HTTP_CODE)"
    echo "Response: $HEALTH_BODY"
    echo ""
    echo "Please provide the correct API URL as the first argument"
    exit 1
fi

echo ""
echo "2. Querying accounts..."

if [ -z "$API_KEY" ]; then
    echo "⚠️  No API_KEY provided - attempting without authentication"
    echo ""
    ACCOUNTS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/api/accounts" 2>/dev/null)
else
    echo "Using API Key: ${API_KEY:0:4}****${API_KEY: -4}"
    echo ""
    ACCOUNTS_RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" "${API_URL}/api/accounts" 2>/dev/null)
fi

HTTP_CODE=$(echo "$ACCOUNTS_RESPONSE" | tail -n 1)
ACCOUNTS_BODY=$(echo "$ACCOUNTS_RESPONSE" | sed '$d')

echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Successfully retrieved accounts"
    echo ""
    echo "$ACCOUNTS_BODY" | python3 -m json.tool 2>/dev/null || echo "$ACCOUNTS_BODY"

    # Count accounts
    ACCOUNT_COUNT=$(echo "$ACCOUNTS_BODY" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('total_count', 0))" 2>/dev/null || echo "?")
    echo ""
    echo "====================================="
    echo "Total Accounts: $ACCOUNT_COUNT"
    echo "====================================="
elif [ "$HTTP_CODE" = "401" ]; then
    echo "❌ Authentication failed - API key required or invalid"
    echo ""
    echo "Response: $ACCOUNTS_BODY"
    echo ""
    echo "Please provide API_KEY as the second argument or set API_KEY environment variable"
else
    echo "❌ Failed to retrieve accounts (HTTP $HTTP_CODE)"
    echo ""
    echo "Response: $ACCOUNTS_BODY"
fi

echo ""
