import unittest
from pydantic import ValidationError

from models.email_models import (
    EmailAddress,
    Attachment,
    EmailMessage,
    EmailSendResponse,
    EmailErrorResponse,
    EmailSendStatus
)


class TestEmailModels(unittest.TestCase):
    """Test cases for email data models."""
    
    def test_email_address_with_name(self):
        """Test EmailAddress with name."""
        addr = EmailAddress(email="test@example.com", name="Test User")
        self.assertEqual(addr.email, "test@example.com")
        self.assertEqual(addr.name, "Test User")
        self.assertEqual(addr.to_string(), "Test User <test@example.com>")
    
    def test_email_address_without_name(self):
        """Test EmailAddress without name."""
        addr = EmailAddress(email="test@example.com")
        self.assertEqual(addr.email, "test@example.com")
        self.assertIsNone(addr.name)
        self.assertEqual(addr.to_string(), "test@example.com")
    
    def test_email_address_invalid_email(self):
        """Test EmailAddress with invalid email."""
        with self.assertRaises(ValidationError):
            EmailAddress(email="invalid-email")
    
    def test_attachment_creation(self):
        """Test Attachment creation."""
        attachment = Attachment(
            filename="test.pdf",
            content="base64content",
            content_type="application/pdf"
        )
        self.assertEqual(attachment.filename, "test.pdf")
        self.assertEqual(attachment.content, "base64content")
        self.assertEqual(attachment.content_type, "application/pdf")
        self.assertEqual(attachment.disposition, "attachment")
    
    def test_email_message_minimal(self):
        """Test EmailMessage with minimal required fields."""
        msg = EmailMessage(
            sender=EmailAddress(email="sender@example.com"),
            to=[EmailAddress(email="recipient@example.com")],
            subject="Test Subject",
            text="Test content"
        )
        self.assertEqual(msg.subject, "Test Subject")
        self.assertEqual(msg.text, "Test content")
        self.assertIsNone(msg.html)
        self.assertEqual(len(msg.to), 1)
        self.assertEqual(len(msg.cc), 0)
        self.assertEqual(len(msg.bcc), 0)
    
    def test_email_message_full(self):
        """Test EmailMessage with all fields."""
        msg = EmailMessage(
            sender=EmailAddress(email="sender@example.com", name="Sender"),
            to=[EmailAddress(email="to@example.com")],
            cc=[EmailAddress(email="cc@example.com")],
            bcc=[EmailAddress(email="bcc@example.com")],
            subject="Full Test",
            text="Plain text",
            html="<p>HTML text</p>",
            attachments=[Attachment(filename="test.txt", content="data")],
            headers={"X-Custom": "value"},
            variables={"key": "value"},
            reply_to=EmailAddress(email="reply@example.com")
        )
        self.assertEqual(len(msg.cc), 1)
        self.assertEqual(len(msg.bcc), 1)
        self.assertEqual(len(msg.attachments), 1)
        self.assertIsNotNone(msg.reply_to)
    
    def test_email_message_no_content(self):
        """Test EmailMessage without any content."""
        with self.assertRaises(ValueError) as context:
            EmailMessage(
                sender=EmailAddress(email="sender@example.com"),
                to=[EmailAddress(email="recipient@example.com")],
                subject="Test"
            )
        self.assertIn("must have either text or html", str(context.exception))
    
    def test_email_send_response(self):
        """Test EmailSendResponse."""
        response = EmailSendResponse(
            status=EmailSendStatus.SUCCESS,
            message_id="msg-123",
            provider="mailtrap",
            details={"key": "value"}
        )
        self.assertEqual(response.status, EmailSendStatus.SUCCESS)
        self.assertEqual(response.message_id, "msg-123")
        self.assertEqual(response.provider, "mailtrap")
    
    def test_email_error_response(self):
        """Test EmailErrorResponse."""
        error = EmailErrorResponse(
            error_code="AUTH_FAILED",
            error_message="Invalid API token",
            provider="sendgrid"
        )
        self.assertEqual(error.status, EmailSendStatus.FAILED)
        self.assertEqual(error.error_code, "AUTH_FAILED")
        self.assertEqual(error.error_message, "Invalid API token")


if __name__ == "__main__":
    unittest.main()