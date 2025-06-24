#!/bin/bash
# Script to run email integration test

if [ -z "$MAILTRAP_KEY" ]; then
    echo "❌ Error: MAILTRAP_KEY environment variable is not set"
    echo ""
    echo "To run the email integration test, you need to:"
    echo "1. Sign up for a free Mailtrap account at https://mailtrap.io"
    echo "2. Get your API token from the Mailtrap dashboard"
    echo "3. Set the environment variable:"
    echo ""
    echo "   export MAILTRAP_KEY='your-api-token'"
    echo ""
    echo "4. Then run: make test-email-integration"
    echo ""
    echo "The test will send a real HTML email to leonj1@gmail.com"
    exit 1
fi

# Run the test
make test-email-integration