#!/usr/bin/env python3
"""
Integration test for email sending with Mailtrap.
This test sends a real email to verify the integration works end-to-end.
"""
import os
import sys
import unittest
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.email_models import EmailAddress, EmailMessage
from email_providers.mailtrap import MailtrapProvider, MailtrapConfig


class TestEmailIntegration(unittest.TestCase):
    """Integration tests for email sending."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        # Get API token from environment
        cls.api_token = os.getenv('MAILTRAP_KEY')
        print(f"Mailtrap Token: {cls.api_token}")
        if not cls.api_token:
            raise unittest.SkipTest("MAILTRAP_KEY environment variable not set")
    
    def setUp(self):
        """Set up each test."""
        # Configure Mailtrap provider
        self.config = MailtrapConfig(
            api_token=self.api_token,
            sandbox=False  # Use real sending, not sandbox
        )
        self.provider = MailtrapProvider(self.config)
    
    def test_send_html_email_to_leonj1(self):
        """Send a test HTML email to leonj1@gmail.com."""
        # Create HTML email
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        import base64
        from pathlib import Path
        
        import mailtrap as mt
        
        api_token = os.getenv('MAILTRAP_KEY')
        
        mail = mt.Mail(
            sender=mt.Address(email="test@joseserver.com", name="Mailtrap Test"),
            to=[mt.Address(email="leonj1@gmail.com", name="Jose Leon")],
            subject="You are awesome!",
            text="Congrats for sending test email with Mailtrap!",
            html="""
            <!doctype html>
            <html>
              <head>
                <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
              </head>
              <body style="font-family: sans-serif;">
                <div style="display: block; margin: auto; max-width: 600px;" class="main">
                  <h1 style="font-size: 18px; font-weight: bold; margin-top: 20px">
                    Congrats for sending test email with Mailtrap!
                  </h1>
                  <p>Inspect it using the tabs you see above and learn how this email can be improved.</p>
                  <img alt="Inspect with Tabs" src="cid:welcome.png" style="width: 100%;">
                  <p>Now send your email using our fake SMTP server and integration of your choice!</p>
                  <p>Good luck! Hope it works.</p>
                </div>
                <!-- Example of invalid for email html/css, will be detected by Mailtrap: -->
                <style>
                  .main { background-color: white; }
                  a:hover { border-left-width: 1em; min-height: 2em; }
                </style>
              </body>
            </html>
            """,
            category="Test",
            headers={"X-MT-Header": "Custom header"},
            custom_variables={"year": 2023},
        )

        client = mt.MailtrapClient(token=api_token)
        client.send(mail)



if __name__ == "__main__":
    # Check for API token before running
    if not os.getenv('MAILTRAP_KEY'):
        print("❌ Error: MAILTRAP_KEY environment variable is not set")
        print("   Set it with: export MAILTRAP_KEY='your-api-token'")
        exit(1)
    
    # Run the test
    unittest.main(verbosity=2)
