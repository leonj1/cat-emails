#!/usr/bin/env python3
"""
Example script demonstrating how to use the email interface with Mailtrap provider.
"""
import os
import base64
from pathlib import Path

from models.email_models import EmailAddress, EmailMessage, Attachment
from email_providers.mailtrap import MailtrapProvider, MailtrapConfig


def send_simple_email():
    """Send a simple text email."""
    # Configure Mailtrap provider
    config = MailtrapConfig(
        api_token=os.getenv("MAILTRAP_API_TOKEN", "your-api-token"),
        sandbox=True  # Use sandbox mode for testing
    )
    
    # Create provider instance
    provider = MailtrapProvider(config)
    
    # Create email message
    message = EmailMessage(
        sender=EmailAddress(
            email="noreply@example.com",
            name="Cat Emails System"
        ),
        to=[
            EmailAddress(
                email="user@example.com",
                name="Test User"
            )
        ],
        subject="Test Email from Cat Emails",
        text="This is a test email sent using the Cat Emails system with Mailtrap."
    )
    
    # Send email
    result = provider.send_email(message)
    
    if hasattr(result, 'status') and result.status == 'success':
        print(f"✅ Email sent successfully!")
        print(f"Message ID: {result.message_id}")
    else:
        print(f"❌ Failed to send email")
        print(f"Error: {result.error_message}")


def send_rich_email_with_attachment():
    """Send a rich HTML email with attachment and inline image."""
    # Configure provider
    config = MailtrapConfig(
        api_token=os.getenv("MAILTRAP_API_TOKEN", "your-api-token")
    )
    provider = MailtrapProvider(config)
    
    # Prepare inline image (create a simple placeholder if no image exists)
    logo_path = Path(__file__).parent / "logo.png"
    if logo_path.exists():
        logo_content = base64.b64encode(logo_path.read_bytes()).decode()
    else:
        # Create a simple 1x1 transparent PNG as placeholder
        logo_content = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    # Create PDF attachment content (placeholder)
    pdf_content = base64.b64encode(b"Mock PDF content for example").decode()
    
    # Create rich email
    message = EmailMessage(
        sender=EmailAddress(
            email="noreply@cat-emails.com",
            name="Cat Emails Notification"
        ),
        to=[
            EmailAddress(email="recipient@example.com", name="Main Recipient")
        ],
        cc=[
            EmailAddress(email="cc@example.com", name="CC Recipient")
        ],
        subject="Your Email Categorization Report",
        text="Your email categorization report is ready. Please view the HTML version for the full report.",
        html="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Email Categorization Report</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <img src="cid:logo.png" alt="Cat Emails Logo" style="height: 60px;">
                    <h1 style="color: #2c3e50;">Email Categorization Report</h1>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="color: #2c3e50; margin-top: 0;">Summary</h2>
                    <ul style="list-style-type: none; padding: 0;">
                        <li>📧 <strong>Total Emails Processed:</strong> 150</li>
                        <li>🏷️ <strong>Categories Identified:</strong> 12</li>
                        <li>🚫 <strong>Spam Blocked:</strong> 45</li>
                        <li>✅ <strong>Important Emails:</strong> 23</li>
                    </ul>
                </div>
                
                <div style="background-color: #e8f4f8; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="color: #2c3e50; margin-top: 0;">Top Categories</h2>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <th style="text-align: left; padding: 8px; border-bottom: 2px solid #ddd;">Category</th>
                            <th style="text-align: right; padding: 8px; border-bottom: 2px solid #ddd;">Count</th>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">Marketing</td>
                            <td style="text-align: right; padding: 8px; border-bottom: 1px solid #eee;">45</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">Personal</td>
                            <td style="text-align: right; padding: 8px; border-bottom: 1px solid #eee;">38</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">Work-related</td>
                            <td style="text-align: right; padding: 8px; border-bottom: 1px solid #eee;">32</td>
                        </tr>
                    </table>
                </div>
                
                <p style="text-align: center; color: #666; font-size: 14px;">
                    See the attached PDF for the detailed report.
                </p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="text-align: center; color: #999; font-size: 12px;">
                    © 2024 Cat Emails System. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """,
        attachments=[
            # Inline logo image
            Attachment(
                filename="logo.png",
                content=logo_content,
                content_type="image/png",
                disposition="inline",
                content_id="logo.png"
            ),
            # PDF report attachment
            Attachment(
                filename="email_categorization_report.pdf",
                content=pdf_content,
                content_type="application/pdf",
                disposition="attachment"
            )
        ],
        headers={
            "X-Priority": "1",
            "X-Report-Type": "Weekly"
        },
        variables={
            "report_date": "2024-01-15",
            "user_id": "12345"
        }
    )
    
    # Send email
    result = provider.send_email(message)
    
    if hasattr(result, 'status') and result.status == 'success':
        print(f"✅ Rich email with attachments sent successfully!")
        print(f"Message ID: {result.message_id}")
        print(f"Provider: {result.provider}")
    else:
        print(f"❌ Failed to send email")
        print(f"Error Code: {result.error_code}")
        print(f"Error Message: {result.error_message}")


def main():
    """Run email examples."""
    print("=== Email Interface Examples ===\n")
    
    # Check for API token
    if not os.getenv("MAILTRAP_API_TOKEN"):
        print("⚠️  Warning: MAILTRAP_API_TOKEN not set in environment")
        print("Set it with: export MAILTRAP_API_TOKEN='your-token'\n")
    
    print("1. Sending simple text email...")
    send_simple_email()
    
    print("\n2. Sending rich HTML email with attachments...")
    send_rich_email_with_attachment()
    
    print("\n✨ Examples completed!")


if __name__ == "__main__":
    main()