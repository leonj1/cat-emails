#!/usr/bin/env python3
"""
Example script demonstrating how to use the mailfrom.dev SMTP email provider.
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.email_models import EmailAddress, EmailMessage, Attachment
from email_providers.mailfrom_dev import MailfromDevProvider, MailfromDevConfig


def send_simple_smtp_email():
    """Send a simple text email via SMTP."""
    # Configure mailfrom.dev provider
    config = MailfromDevConfig(
        smtp_username=os.getenv("SMTP_USERNAME", "your-username"),
        smtp_password=os.getenv("SMTP_PASSWORD", "your-password"),
        smtp_host="smtp.mailfrom.dev",
        smtp_port=587,
        use_tls=True
    )
    
    # Create provider instance
    provider = MailfromDevProvider(config)
    
    # Create email message
    message = EmailMessage(
        sender=EmailAddress(
            email="noreply@example.com",
            name="Cat Emails SMTP System"
        ),
        to=[
            EmailAddress(
                email="user@example.com",
                name="Test User"
            )
        ],
        subject="Test SMTP Email from Cat Emails",
        text="This is a test email sent using the Cat Emails system with mailfrom.dev SMTP provider."
    )
    
    # Send email
    result = provider.send_email(message)
    
    if hasattr(result, 'status') and result.status == 'success':
        print(f"✅ Email sent successfully via SMTP!")
        print(f"Message ID: {result.message_id}")
        print(f"Provider: {result.provider}")
    else:
        print(f"❌ Failed to send email")
        print(f"Error Code: {result.error_code}")
        print(f"Error: {result.error_message}")


def send_html_email_with_cc_bcc():
    """Send HTML email with CC and BCC recipients."""
    # Configure provider
    config = MailfromDevConfig(
        smtp_username=os.getenv("SMTP_USERNAME", "your-username"),
        smtp_password=os.getenv("SMTP_PASSWORD", "your-password")
    )
    provider = MailfromDevProvider(config)
    
    # Create rich email
    message = EmailMessage(
        sender=EmailAddress(
            email="notifications@cat-emails.com",
            name="Cat Emails Notifications"
        ),
        to=[
            EmailAddress(email="primary@example.com", name="Primary Recipient")
        ],
        cc=[
            EmailAddress(email="cc1@example.com", name="CC Recipient 1"),
            EmailAddress(email="cc2@example.com", name="CC Recipient 2")
        ],
        bcc=[
            EmailAddress(email="bcc@example.com", name="Hidden Recipient")
        ],
        reply_to=EmailAddress(
            email="support@cat-emails.com",
            name="Cat Emails Support"
        ),
        subject="SMTP Provider Test - HTML Email",
        text="Plain text version for email clients that don't support HTML.",
        html="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>SMTP Email Test</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #333;">SMTP Email Provider Test</h2>
                
                <p>This email demonstrates the SMTP provider capabilities:</p>
                
                <ul style="color: #666;">
                    <li>HTML formatting with inline styles</li>
                    <li>Multiple recipients (TO, CC, BCC)</li>
                    <li>Reply-To address configuration</li>
                    <li>Custom headers</li>
                    <li>Plain text fallback</li>
                </ul>
                
                <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0; color: #555;">
                        <strong>SMTP Benefits:</strong><br>
                        ✓ Universal protocol support<br>
                        ✓ Works with any SMTP server<br>
                        ✓ No API dependencies<br>
                        ✓ Standard authentication
                    </p>
                </div>
                
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    Sent using Cat Emails SMTP Provider<br>
                    Powered by mailfrom.dev
                </p>
            </div>
        </body>
        </html>
        """,
        headers={
            "X-Priority": "3",
            "X-Mailer": "Cat-Emails-SMTP/1.0",
            "X-Custom-Header": "SMTP-Test"
        }
    )
    
    # Send email
    result = provider.send_email(message)
    
    if hasattr(result, 'status') and result.status == 'success':
        print(f"\n✅ Rich HTML email sent successfully!")
        print(f"Message ID: {result.message_id}")
        print(f"Recipients: {result.details.get('recipients', [])}")
    else:
        print(f"\n❌ Failed to send email")
        print(f"Error: {result.error_message}")


def main():
    """Run SMTP email examples."""
    print("=== SMTP Email Provider Examples ===\n")
    
    # Check for SMTP credentials
    if not os.getenv("SMTP_USERNAME") or not os.getenv("SMTP_PASSWORD"):
        print("⚠️  Warning: SMTP credentials not set in environment")
        print("Set them with:")
        print("  export SMTP_USERNAME='your-username'")
        print("  export SMTP_PASSWORD='your-password'\n")
    
    print("1. Sending simple text email via SMTP...")
    send_simple_smtp_email()
    
    print("\n2. Sending HTML email with CC/BCC...")
    send_html_email_with_cc_bcc()
    
    print("\n✨ SMTP examples completed!")
    print("\nNote: The mailfrom.dev provider supports all standard SMTP features:")
    print("- Plain text and HTML emails")
    print("- File attachments")
    print("- Multiple recipients (TO, CC, BCC)")
    print("- Custom headers")
    print("- Reply-To addresses")


if __name__ == "__main__":
    main()