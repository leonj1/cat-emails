#!/usr/bin/env python3
"""
Example demonstrating how to use the email interface with Mailtrap provider.
"""

import os
import base64
from typing import List

from models.email_models import EmailAddress, EmailMessage, Attachment
from email_providers.mailtrap import MailtrapProvider, MailtrapConfig
from services.email_service import EmailService, EmailServiceConfig


def create_sample_attachment() -> Attachment:
    """Create a sample text attachment."""
    content = "This is a sample attachment content."
    encoded_content = base64.b64encode(content.encode()).decode()
    
    return Attachment(
        filename="sample.txt",
        content=encoded_content,
        content_type="text/plain"
    )


def create_sample_email() -> EmailMessage:
    """Create a sample email message."""
    return EmailMessage(
        sender=EmailAddress(
            email="sender@example.com",
            name="John Doe"
        ),
        to=[
            EmailAddress(email="recipient@example.com", name="Jane Smith"),
            EmailAddress(email="another@example.com")
        ],
        cc=[EmailAddress(email="cc@example.com")],
        subject="Test Email from Cat-Emails System",
        text="This is a plain text email body.",
        html="""
        <html>
            <body>
                <h1>Test Email</h1>
                <p>This is an <strong>HTML</strong> email body.</p>
                <p>Best regards,<br>The Cat-Emails Team</p>
            </body>
        </html>
        """,
        attachments=[create_sample_attachment()],
        headers={
            "X-Custom-Header": "CustomValue",
            "X-Priority": "1"
        },
        variables={
            "user_name": "Jane Smith",
            "account_id": "12345"
        }
    )


def main():
    """Main example function."""
    # Get Mailtrap token from environment
    mailtrap_token = os.environ.get("MAILTRAP_API_TOKEN")
    
    if not mailtrap_token:
        print("Error: Please set MAILTRAP_API_TOKEN environment variable")
        print("You can get your token from: https://mailtrap.io/api-tokens")
        return
    
    # Create Mailtrap provider configuration
    mailtrap_config = MailtrapConfig(
        api_token=mailtrap_token,
        sandbox=True  # Use sandbox mode for testing
    )
    
    # Create Mailtrap provider
    mailtrap_provider = MailtrapProvider(mailtrap_config)
    
    # Create email service configuration
    service_config = EmailServiceConfig(
        default_provider="mailtrap",
        retry_delays=[1, 2, 5],  # Retry after 1, 2, and 5 seconds
        enable_fallback=True
    )
    
    # Create email service and register provider
    email_service = EmailService(service_config)
    email_service.register_provider(mailtrap_provider)
    
    # Create sample email
    email = create_sample_email()
    
    print("Sending email via Mailtrap...")
    print(f"From: {email.sender.to_string()}")
    print(f"To: {', '.join(addr.to_string() for addr in email.to)}")
    print(f"Subject: {email.subject}")
    print()
    
    # Send the email
    result = email_service.send_email(email)
    
    # Check the result
    if result.status == "success":
        print(f"✅ Email sent successfully!")
        print(f"Message ID: {result.message_id}")
        print(f"Provider: {result.provider}")
        if result.details:
            print(f"Details: {result.details}")
    else:
        print(f"❌ Failed to send email")
        print(f"Error Code: {result.error_code}")
        print(f"Error Message: {result.error_message}")
        if result.details:
            print(f"Details: {result.details}")
    
    # Example of sending to a specific provider
    print("\n" + "="*50 + "\n")
    print("Sending email with specific provider...")
    
    result2 = email_service.send_email(email, provider_name="mailtrap")
    print(f"Result: {result2.status}")
    
    # Example of bulk sending
    print("\n" + "="*50 + "\n")
    print("Sending bulk emails...")
    
    emails = [
        create_sample_email(),
        create_sample_email(),
        create_sample_email()
    ]
    
    # Modify subjects to make them unique
    for i, email in enumerate(emails):
        email.subject = f"Bulk Email #{i+1}"
    
    results = email_service.send_bulk_emails(emails)
    
    success_count = sum(1 for r in results if r.status == "success")
    print(f"Bulk send complete: {success_count}/{len(results)} successful")


if __name__ == "__main__":
    main()