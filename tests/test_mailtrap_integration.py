#!/usr/bin/env python3
"""
Integration test for Mailtrap email sending.

This script validates that we can successfully send emails via Mailtrap
using the MAILTRAP_KEY environment variable.

Usage:
    python tests/test_mailtrap_integration.py

Environment Variables:
    MAILTRAP_KEY: Required. The Mailtrap API token for authentication.
"""
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.email_models import EmailAddress, EmailMessage, EmailSendStatus
from email_providers.mailtrap import MailtrapProvider, MailtrapConfig


def test_send_simple_email():
    """Test sending a simple email via Mailtrap."""
    # Get API token from environment
    api_token = os.getenv("MAILTRAP_KEY")
    if not api_token:
        print("ERROR: MAILTRAP_KEY environment variable is required")
        print("Set it with: export MAILTRAP_KEY='your-api-token'")
        return False

    print("=" * 60)
    print("Mailtrap Integration Test")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"API Token: {api_token[:8]}...{api_token[-4:]}")
    print("=" * 60)

    # Configure Mailtrap provider
    print("\n1. Configuring Mailtrap provider...")
    config = MailtrapConfig(
        api_token=api_token,
        sandbox=False  # Use production mode
    )
    provider = MailtrapProvider(config)

    # Validate configuration
    print("2. Validating configuration...")
    if not provider.validate_config():
        print("ERROR: Invalid Mailtrap configuration")
        return False
    print("   Configuration is valid")

    # Create test email message
    print("\n3. Creating test email message...")
    message = EmailMessage(
        sender=EmailAddress(
            email="info@joseserver.com",
            name="Cat Emails System"
        ),
        to=[
            EmailAddress(
                email="leonj1@gmail.com",
                name="Jose Leon"
            )
        ],
        subject=f"Mailtrap Integration Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        text="This is a test email sent from the Cat Emails Mailtrap integration test.",
        html="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Mailtrap Integration Test</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745;">
                <h1 style="color: #28a745; margin-top: 0;">Mailtrap Integration Test</h1>
                <p>This is a test email sent from the Cat Emails system to validate Mailtrap integration.</p>
                <ul>
                    <li><strong>Sender:</strong> info@joseserver.com</li>
                    <li><strong>Recipient:</strong> leonj1@gmail.com</li>
                    <li><strong>Timestamp:</strong> {timestamp}</li>
                </ul>
                <p style="color: #666; font-size: 14px; margin-bottom: 0;">
                    If you received this email, the Mailtrap integration is working correctly.
                </p>
            </div>
        </body>
        </html>
        """.format(timestamp=datetime.now().isoformat())
    )
    print(f"   From: {message.sender.email}")
    print(f"   To: {message.to[0].email}")
    print(f"   Subject: {message.subject}")

    # Send email
    print("\n4. Sending email via Mailtrap...")
    result = provider.send_email(message)

    # Check result
    print("\n5. Checking result...")
    if result.status == EmailSendStatus.SUCCESS:
        print("=" * 60)
        print("SUCCESS: Email sent successfully!")
        print("=" * 60)
        print(f"   Message ID: {result.message_id}")
        print(f"   Provider: {result.provider}")
        if result.details:
            print(f"   Details: {result.details}")
        return True
    else:
        print("=" * 60)
        print("FAILED: Email sending failed!")
        print("=" * 60)
        print(f"   Error Code: {result.error_code}")
        print(f"   Error Message: {result.error_message}")
        if hasattr(result, 'details') and result.details:
            print(f"   Details: {result.details}")
        return False


def main():
    """Run the Mailtrap integration test."""
    success = test_send_simple_email()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
