"""Unit tests for email interface and providers."""
import unittest
from unittest.mock import Mock, patch, MagicMock
import base64

from models.email_models import (
    EmailAddress, 
    EmailMessage, 
    Attachment,
    EmailSendResponse,
    EmailErrorResponse,
    EmailSendStatus
)
from email_providers.base import EmailProviderInterface, EmailProviderConfig
from email_providers.mailtrap import MailtrapProvider, MailtrapConfig


class TestEmailModels(unittest.TestCase):
    """Test email data models."""
    
    def test_email_address_creation(self):
        """Test EmailAddress model creation."""
        # Test with name
        addr = EmailAddress(email="test@example.com", name="Test User")
        self.assertEqual(addr.email, "test@example.com")
        self.assertEqual(addr.name, "Test User")
        self.assertEqual(addr.to_string(), "Test User <test@example.com>")
        
        # Test without name
        addr2 = EmailAddress(email="simple@example.com")
        self.assertIsNone(addr2.name)
        self.assertEqual(addr2.to_string(), "simple@example.com")
    
    def test_email_message_validation(self):
        """Test EmailMessage validation."""
        # Valid message with text
        msg = EmailMessage(
            sender=EmailAddress(email="sender@example.com"),
            to=[EmailAddress(email="recipient@example.com")],
            subject="Test",
            text="Test content"
        )
        self.assertEqual(msg.subject, "Test")
        
        # Valid message with HTML
        msg2 = EmailMessage(
            sender=EmailAddress(email="sender@example.com"),
            to=[EmailAddress(email="recipient@example.com")],
            subject="Test",
            html="<p>Test content</p>"
        )
        self.assertEqual(msg2.subject, "Test")
        
        # Invalid message without content
        with self.assertRaises(ValueError):
            EmailMessage(
                sender=EmailAddress(email="sender@example.com"),
                to=[EmailAddress(email="recipient@example.com")],
                subject="Test"
                # No text or html content
            )
    
    def test_attachment_creation(self):
        """Test Attachment model."""
        content = base64.b64encode(b"test file content").decode()
        att = Attachment(
            filename="test.txt",
            content=content,
            content_type="text/plain"
        )
        self.assertEqual(att.filename, "test.txt")
        self.assertEqual(att.content, content)
        self.assertEqual(att.disposition, "attachment")  # default


class TestMailtrapProvider(unittest.TestCase):
    """Test Mailtrap email provider."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = MailtrapConfig(api_token="test-token")
        self.provider = MailtrapProvider(self.config)
        
        # Sample email message
        self.message = EmailMessage(
            sender=EmailAddress(email="sender@example.com", name="Sender"),
            to=[EmailAddress(email="recipient@example.com", name="Recipient")],
            subject="Test Email",
            text="Test content",
            html="<p>Test content</p>"
        )
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        self.assertTrue(self.provider.validate_config())
        
        # Invalid config - no token
        invalid_config = MailtrapConfig(api_token="")
        invalid_provider = MailtrapProvider(invalid_config)
        self.assertFalse(invalid_provider.validate_config())
        
        # Invalid config - whitespace token
        invalid_config2 = MailtrapConfig(api_token="   ")
        invalid_provider2 = MailtrapProvider(invalid_config2)
        self.assertFalse(invalid_provider2.validate_config())
    
    @patch('email_providers.mailtrap.mt')
    def test_send_email_success(self, mock_mt):
        """Test successful email send."""
        # Mock Mailtrap client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.message_id = "test-message-id"
        mock_client.send.return_value = mock_response
        
        mock_mt.MailtrapClient.return_value = mock_client
        mock_mt.Mail = MagicMock()
        
        # Send email
        result = self.provider.send_email(self.message)
        
        # Verify result
        self.assertIsInstance(result, EmailSendResponse)
        self.assertEqual(result.status, EmailSendStatus.SUCCESS)
        self.assertEqual(result.message_id, "test-message-id")
        self.assertEqual(result.provider, "mailtrap")
        
        # Verify client was called
        mock_mt.MailtrapClient.assert_called_once_with(token="test-token")
        mock_client.send.assert_called_once()
    
    @patch('email_providers.mailtrap.mt')
    def test_send_email_with_attachments(self, mock_mt):
        """Test sending email with attachments."""
        # Add attachment to message
        self.message.attachments = [
            Attachment(
                filename="test.pdf",
                content=base64.b64encode(b"PDF content").decode(),
                content_type="application/pdf"
            )
        ]
        
        # Mock client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.id = "test-id-123"
        mock_client.send.return_value = mock_response
        
        mock_mt.MailtrapClient.return_value = mock_client
        mock_mt.Mail = MagicMock()
        
        # Send email
        result = self.provider.send_email(self.message)
        
        # Verify success
        self.assertIsInstance(result, EmailSendResponse)
        self.assertEqual(result.status, EmailSendStatus.SUCCESS)
    
    @patch('email_providers.mailtrap.mt')
    def test_send_email_failure(self, mock_mt):
        """Test email send failure."""
        # Mock client to raise exception
        mock_client = MagicMock()
        mock_client.send.side_effect = Exception("Authentication failed")
        
        mock_mt.MailtrapClient.return_value = mock_client
        mock_mt.Mail = MagicMock()
        
        # Send email
        result = self.provider.send_email(self.message)
        
        # Verify error response
        self.assertIsInstance(result, EmailErrorResponse)
        self.assertEqual(result.status, EmailSendStatus.FAILED)
        self.assertEqual(result.error_code, "AUTH_FAILED")
        self.assertIn("Authentication failed", result.error_message)
        self.assertEqual(result.provider, "mailtrap")
    
    def test_send_email_invalid_config(self):
        """Test sending email with invalid configuration."""
        # Create provider with invalid config
        invalid_config = MailtrapConfig(api_token="")
        invalid_provider = MailtrapProvider(invalid_config)
        
        # Try to send email
        result = invalid_provider.send_email(self.message)
        
        # Verify error response
        self.assertIsInstance(result, EmailErrorResponse)
        self.assertEqual(result.error_code, "INVALID_CONFIG")
        self.assertEqual(result.provider, "mailtrap")
    
    def test_email_address_conversion(self):
        """Test email address conversion to Mailtrap format."""
        # With name
        addr = EmailAddress(email="test@example.com", name="Test User")
        converted = self.provider._convert_email_address(addr)
        self.assertEqual(converted, {"email": "test@example.com", "name": "Test User"})
        
        # Without name
        addr2 = EmailAddress(email="simple@example.com")
        converted2 = self.provider._convert_email_address(addr2)
        self.assertEqual(converted2, {"email": "simple@example.com"})
    
    def test_attachment_conversion(self):
        """Test attachment conversion to Mailtrap format."""
        att = Attachment(
            filename="doc.pdf",
            content="base64content",
            content_type="application/pdf",
            disposition="inline",
            content_id="doc123"
        )
        converted = self.provider._convert_attachment(att)
        
        self.assertEqual(converted["filename"], "doc.pdf")
        self.assertEqual(converted["content"], "base64content")
        self.assertEqual(converted["type"], "application/pdf")
        self.assertEqual(converted["disposition"], "inline")
        self.assertEqual(converted["content_id"], "doc123")


class TestEmailProviderInterface(unittest.TestCase):
    """Test the abstract email provider interface."""
    
    def test_interface_requires_implementation(self):
        """Test that interface methods must be implemented."""
        # Create a mock implementation
        class IncompleteProvider(EmailProviderInterface):
            pass
        
        # Should not be able to instantiate without implementing abstract methods
        with self.assertRaises(TypeError):
            config = EmailProviderConfig(provider_name="test")
            IncompleteProvider(config)
    
    def test_complete_implementation(self):
        """Test complete interface implementation."""
        class CompleteProvider(EmailProviderInterface):
            def send_email(self, message):
                return EmailSendResponse(
                    status=EmailSendStatus.SUCCESS,
                    message_id="test-123",
                    provider=self.config.provider_name
                )
            
            def validate_config(self):
                return True
        
        # Should be able to instantiate
        config = EmailProviderConfig(provider_name="test")
        provider = CompleteProvider(config)
        
        # Test methods
        self.assertEqual(provider.get_provider_name(), "test")
        self.assertTrue(provider.validate_config())
        
        # Test send
        msg = EmailMessage(
            sender=EmailAddress(email="sender@test.com"),
            to=[EmailAddress(email="recipient@test.com")],
            subject="Test",
            text="Content"
        )
        result = provider.send_email(msg)
        self.assertEqual(result.status, EmailSendStatus.SUCCESS)


if __name__ == "__main__":
    unittest.main()