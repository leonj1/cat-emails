#!/bin/bash
# Example script to verify Gmail app password using the API

# Configuration
API_URL="http://localhost:8001"  # Change to your API URL
API_KEY=""  # Set your API key if required
EMAIL="leonj1@gmail.com"  # Email to verify

echo "Verifying password for: $EMAIL"
echo "================================"

# Build the curl command
if [ -z "$API_KEY" ]; then
    # No API key required
    RESPONSE=$(curl -s -X GET "$API_URL/api/accounts/$EMAIL/verify-password")
else
    # API key required
    RESPONSE=$(curl -s -X GET "$API_URL/api/accounts/$EMAIL/verify-password" \
        -H "X-API-Key: $API_KEY")
fi

# Check if curl succeeded
if [ $? -ne 0 ]; then
    echo "Error: Failed to connect to API"
    exit 1
fi

# Parse and display the response
echo "$RESPONSE" | python3 -c "
import json
import sys

try:
    data = json.load(sys.stdin)

    # Check for error responses
    if 'detail' in data:
        print(f'Error: {data[\"detail\"]}')
        sys.exit(1)

    # Display the result
    status = data.get('status', 'unknown')
    message = data.get('message', 'No message')

    if status == 'success':
        print('✅ Password Status: VALID')
        print(f'   {message}')
    elif status == 'error':
        if 'No app password configured' in message:
            print('❌ Password Status: MISSING')
            print(f'   {message}')
            print()
            print('To fix:')
            print('1. Enable 2-Step Verification in your Gmail account')
            print('2. Generate an app password at:')
            print('   https://myaccount.google.com/apppasswords')
            print('3. Update the account with:')
            print(f'   curl -X POST \"{API_URL}/api/accounts\" \\\\')
            print(f'     -H \"Content-Type: application/json\" \\\\')
            if '$API_KEY':
                print(f'     -H \"X-API-Key: $API_KEY\" \\\\')
            print(f'     -d \'{{\"email_address\": \"{data.get(\"email\", EMAIL)}\", \"app_password\": \"your-16-char-password\"}}\'')
        elif 'incorrect' in message.lower() or 'invalid' in message.lower():
            print('❌ Password Status: INVALID')
            print(f'   {message}')
            print()
            print('The app password is incorrect. To fix:')
            print('1. Generate a new app password at:')
            print('   https://myaccount.google.com/apppasswords')
            print('2. Update the account with the new password')
        else:
            print('⚠️  Password Status: ERROR')
            print(f'   {message}')
    else:
        print(f'Status: {status}')
        print(f'Message: {message}')

except json.JSONDecodeError:
    print('Error: Invalid JSON response')
    print('Response:', sys.stdin.read())
except Exception as e:
    print(f'Error parsing response: {e}')
" || {
    echo "Raw response: $RESPONSE"
}

echo "================================"