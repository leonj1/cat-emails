#!/usr/bin/env python3
"""
Integration test for email sending with mailfrom.dev SMTP provider.
This test sends a real email to verify the integration works end-to-end.
"""
import os
import sys
import unittest
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.email_models import EmailAddress, EmailMessage
from email_providers.mailfrom_dev import MailfromDevProvider, MailfromDevConfig


class TestMailfromIntegration(unittest.TestCase):
    """Integration tests for mailfrom.dev SMTP email sending."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        # Get SMTP credentials from environment
        cls.smtp_username = os.getenv('SMTP_USERNAME')
        cls.smtp_password = os.getenv('SMTP_PASSWORD')
        
        if not cls.smtp_username or not cls.smtp_password:
            raise unittest.SkipTest("SMTP_USERNAME and SMTP_PASSWORD environment variables not set")
    
    def setUp(self):
        """Set up each test."""
        # Configure mailfrom.dev provider
        self.config = MailfromDevConfig(
            smtp_username=self.smtp_username,
            smtp_password=self.smtp_password,
            smtp_host="smtp.mailfrom.dev",
            smtp_port=587,
            use_tls=True
        )
        self.provider = MailfromDevProvider(self.config)
    
    def test_send_html_email_to_leonj1(self):
        """Send a test HTML email to leonj1@gmail.com using SMTP."""
        # Create HTML email
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        message = EmailMessage(
            sender=EmailAddress(
                email="test@cat-emails.com",
                name="Cat Emails SMTP Test"
            ),
            to=[
                EmailAddress(
                    email="leonj1@gmail.com",
                    name="Leon J"
                )
            ],
            subject=f"Cat Emails SMTP Integration Test - {current_time}",
            text="This is a test email from the Cat Emails system using mailfrom.dev SMTP. Please view in HTML for the full experience.",
            html=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Cat Emails SMTP Integration Test</title>
            </head>
            <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden;">
                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                        <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 600;">
                            🐱 Cat Emails SMTP Integration Test
                        </h1>
                        <p style="margin: 10px 0 0 0; color: #e0e0ff; font-size: 16px;">
                            Powered by mailfrom.dev
                        </p>
                    </div>
                    
                    <!-- Content -->
                    <div style="padding: 40px 30px;">
                        <h2 style="margin: 0 0 20px 0; color: #333333; font-size: 22px; font-weight: 600;">
                            SMTP Email Successfully Sent! ✅
                        </h2>
                        
                        <p style="margin: 0 0 20px 0; color: #666666; font-size: 16px; line-height: 1.6;">
                            This email confirms that the Cat Emails system's SMTP interface is working correctly. 
                            The integration with mailfrom.dev has been successfully established using SMTP authentication.
                        </p>
                        
                        <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 30px 0;">
                            <h3 style="margin: 0 0 10px 0; color: #333333; font-size: 18px;">
                                Test Details:
                            </h3>
                            <ul style="margin: 0; padding-left: 20px; color: #666666;">
                                <li style="margin-bottom: 8px;">
                                    <strong>Timestamp:</strong> {current_time}
                                </li>
                                <li style="margin-bottom: 8px;">
                                    <strong>Provider:</strong> mailfrom.dev (SMTP)
                                </li>
                                <li style="margin-bottom: 8px;">
                                    <strong>Protocol:</strong> SMTP with STARTTLS
                                </li>
                                <li style="margin-bottom: 8px;">
                                    <strong>Port:</strong> 587
                                </li>
                                <li style="margin-bottom: 8px;">
                                    <strong>Authentication:</strong> Username/Password
                                </li>
                            </ul>
                        </div>
                        
                        <div style="background-color: #e8f4f8; border-radius: 6px; padding: 20px; margin: 30px 0;">
                            <h3 style="margin: 0 0 10px 0; color: #0066cc; font-size: 18px;">
                                📊 SMTP vs API Comparison:
                            </h3>
                            <table style="width: 100%; margin-top: 15px; border-collapse: collapse;">
                                <tr>
                                    <th style="text-align: left; padding: 8px; border-bottom: 2px solid #ddd; color: #333;">Feature</th>
                                    <th style="text-align: center; padding: 8px; border-bottom: 2px solid #ddd; color: #333;">SMTP</th>
                                    <th style="text-align: center; padding: 8px; border-bottom: 2px solid #ddd; color: #333;">API</th>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border-bottom: 1px solid #eee;">Authentication</td>
                                    <td style="text-align: center; padding: 8px; border-bottom: 1px solid #eee;">Username/Password</td>
                                    <td style="text-align: center; padding: 8px; border-bottom: 1px solid #eee;">API Token</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border-bottom: 1px solid #eee;">Protocol</td>
                                    <td style="text-align: center; padding: 8px; border-bottom: 1px solid #eee;">SMTP/TLS</td>
                                    <td style="text-align: center; padding: 8px; border-bottom: 1px solid #eee;">HTTPS</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border-bottom: 1px solid #eee;">Compatibility</td>
                                    <td style="text-align: center; padding: 8px; border-bottom: 1px solid #eee;">Universal</td>
                                    <td style="text-align: center; padding: 8px; border-bottom: 1px solid #eee;">Provider-specific</td>
                                </tr>
                            </table>
                        </div>
                        
                        <div style="text-align: center; margin: 40px 0 20px 0;">
                            <p style="margin: 0; color: #999999; font-size: 14px;">
                                This is an automated test email. No action is required.
                            </p>
                        </div>
                    </div>
                    
                    <!-- Footer -->
                    <div style="background-color: #f8f9fa; padding: 30px; text-align: center; border-top: 1px solid #e0e0e0;">
                        <p style="margin: 0 0 10px 0; color: #666666; font-size: 14px;">
                            Sent via mailfrom.dev SMTP Service
                        </p>
                        <p style="margin: 0; color: #999999; font-size: 12px;">
                            © 2024 Cat Emails. All rights reserved.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """,
            headers={
                "X-Test-Type": "SMTP Integration",
                "X-Cat-Emails-Version": "1.0",
                "X-Provider": "mailfrom.dev"
            }
        )
        
        # Send the email
        result = self.provider.send_email(message)
        
        # Verify success
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, 'status'))
        
        # If failed, provide detailed error information
        if result.status != 'success':
            print(f"\n❌ Email send failed!")
            print(f"   Error Code: {result.error_code}")
            print(f"   Error Message: {result.error_message}")
            print(f"   Provider: {result.provider}")
            if hasattr(result, 'details'):
                print(f"   Details: {result.details}")
        
        self.assertEqual(result.status, 'success')
        self.assertIsNotNone(result.message_id)
        self.assertEqual(result.provider, 'mailfrom.dev')
        
        # Print success message
        print(f"\n✅ SMTP Integration test successful!")
        print(f"   Email sent to: leonj1@gmail.com")
        print(f"   Message ID: {result.message_id}")
        print(f"   Provider: {result.provider}")
        print(f"   SMTP Host: {self.config.smtp_host}")
        print(f"   Timestamp: {current_time}")


if __name__ == "__main__":
    # Check for SMTP credentials before running
    if not os.getenv('SMTP_USERNAME') or not os.getenv('SMTP_PASSWORD'):
        print("❌ Error: SMTP_USERNAME and SMTP_PASSWORD environment variables are not set")
        print("   Set them with:")
        print("   export SMTP_USERNAME='your-smtp-username'")
        print("   export SMTP_PASSWORD='your-smtp-password'")
        exit(1)
    
    # Run the test
    unittest.main(verbosity=2)