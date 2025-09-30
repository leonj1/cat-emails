#!/bin/bash
# Production Credentials Setup Script
# This script helps you set up Gmail credentials in SQLite database for production use

set -e  # Exit on error

echo "=================================================="
echo "Gmail Credentials Setup for Cat-Emails"
echo "=================================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    exit 1
fi

# Check if setup_credentials.py exists
if [ ! -f "setup_credentials.py" ]; then
    echo "Error: setup_credentials.py not found"
    echo "Make sure you're running this script from the project root directory"
    exit 1
fi

echo "This script will help you set up Gmail credentials in SQLite database."
echo ""
echo "Prerequisites:"
echo "  1. You have a Gmail account with 2FA enabled"
echo "  2. You have generated an app-specific password"
echo "     (https://myaccount.google.com/apppasswords)"
echo ""

read -p "Do you want to continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

echo ""
echo "Enter your Gmail credentials:"
echo ""

# Prompt for email
read -p "Gmail Email Address: " GMAIL_EMAIL

# Validate email format (basic validation)
if [[ ! $GMAIL_EMAIL =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    echo "Error: Invalid email format"
    exit 1
fi

# Prompt for password (hidden input)
read -s -p "Gmail App-Specific Password: " GMAIL_PASSWORD
echo ""

# Validate password is not empty
if [ -z "$GMAIL_PASSWORD" ]; then
    echo "Error: Password cannot be empty"
    exit 1
fi

echo ""
echo "Storing credentials in SQLite database..."

# Store credentials using the Python script
if python3 setup_credentials.py --email "$GMAIL_EMAIL" --password "$GMAIL_PASSWORD"; then
    echo ""
    echo "=================================================="
    echo "✓ Credentials stored successfully!"
    echo "=================================================="
    echo ""
    echo "Database location: ./credentials.db"
    echo ""
    echo "Next steps:"
    echo "  1. Verify credentials: python3 setup_credentials.py --list"
    echo "  2. Run the application: python3 gmail_fetcher.py"
    echo "  3. For Docker deployment, mount the database:"
    echo "     docker run -v \$(pwd)/credentials.db:/app/credentials.db ..."
    echo ""
    echo "Security recommendations:"
    echo "  - Set secure file permissions: chmod 600 credentials.db"
    echo "  - Never commit credentials.db to version control"
    echo "  - Rotate app-specific passwords regularly"
    echo ""
    echo "=================================================="
else
    echo ""
    echo "Error: Failed to store credentials"
    exit 1
fi