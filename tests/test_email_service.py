import unittest
from unittest.mock import Mock, MagicMock, patch
import time

from models.email_models import (
    EmailAddress,
    EmailMessage,
    EmailSendResponse,
    EmailErrorResponse,
    EmailSendStatus
)
from email_providers.base import EmailProviderInterface, EmailProviderConfig
from services.email_service import EmailService, EmailServiceConfig


class MockProvider(EmailProviderInterface):
    """Mock email provider for testing."""
    
    def __init__(self, config: EmailProviderConfig, should_fail: bool = False):
        super().__init__(config)
        self.should_fail = should_fail
        self.send_count = 0
    
    def validate_config(self) -> bool:
        return True
    
    def send_email(self, message: EmailMessage) -> EmailSendResponse:
        self.send_count += 1
        
        if self.should_fail:
            return EmailErrorResponse(
                error_code="TEST_ERROR",
                error_message="Test error",
                provider=self.config.provider_name
            )
        
        return EmailSendResponse(
            status=EmailSendStatus.SUCCESS,
            message_id=f"test-{self.send_count}",
            provider=self.config.provider_name
        )


class TestEmailService(unittest.TestCase):
    """Test cases for EmailService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service_config = EmailServiceConfig(
            default_provider="mock",
            retry_delays=[0.1, 0.1],  # Short delays for testing
            enable_fallback=True
        )
        self.service = EmailService(self.service_config)
        
        self.test_email = EmailMessage(
            sender=EmailAddress(email="sender@example.com"),
            to=[EmailAddress(email="recipient@example.com")],
            subject="Test",
            text="Test content"
        )
    
    def test_register_provider(self):
        """Test provider registration."""
        mock_config = EmailProviderConfig(provider_name="mock")
        mock_provider = MockProvider(mock_config)
        
        self.service.register_provider(mock_provider)
        self.assertIn("mock", self.service.providers)
        self.assertEqual(self.service.get_provider("mock"), mock_provider)
    
    def test_unregister_provider(self):
        """Test provider unregistration."""
        mock_config = EmailProviderConfig(provider_name="mock")
        mock_provider = MockProvider(mock_config)
        
        self.service.register_provider(mock_provider)
        self.service.unregister_provider("mock")
        self.assertNotIn("mock", self.service.providers)
    
    def test_send_email_success(self):
        """Test successful email send."""
        mock_config = EmailProviderConfig(provider_name="mock")
        mock_provider = MockProvider(mock_config, should_fail=False)
        self.service.register_provider(mock_provider)
        
        result = self.service.send_email(self.test_email)
        
        self.assertIsInstance(result, EmailSendResponse)
        self.assertEqual(result.status, EmailSendStatus.SUCCESS)
        self.assertEqual(result.provider, "mock")
        self.assertEqual(mock_provider.send_count, 1)
    
    def test_send_email_provider_not_found(self):
        """Test send with non-existent provider."""
        result = self.service.send_email(self.test_email)
        
        self.assertIsInstance(result, EmailErrorResponse)
        self.assertEqual(result.error_code, "PROVIDER_NOT_FOUND")
    
    def test_send_email_with_retry(self):
        """Test email send with retry logic."""
        # Create a provider that fails first then succeeds
        mock_config = EmailProviderConfig(provider_name="mock")
        mock_provider = MockProvider(mock_config)
        
        # Mock send_email to fail twice then succeed
        call_count = 0
        def mock_send(message):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return EmailErrorResponse(
                    error_code="TEMP_ERROR",
                    error_message="Temporary error",
                    provider="mock"
                )
            return EmailSendResponse(
                status=EmailSendStatus.SUCCESS,
                message_id="success",
                provider="mock"
            )
        
        mock_provider.send_email = mock_send
        self.service.register_provider(mock_provider)
        
        result = self.service.send_email(self.test_email)
        
        self.assertIsInstance(result, EmailSendResponse)
        self.assertEqual(call_count, 3)  # Failed twice, succeeded on third
    
    def test_send_email_no_retry_on_auth_error(self):
        """Test that AUTH_FAILED errors don't trigger retry."""
        mock_config = EmailProviderConfig(provider_name="mock")
        mock_provider = MockProvider(mock_config)
        
        # Mock to return AUTH_FAILED
        mock_provider.send_email = lambda msg: EmailErrorResponse(
            error_code="AUTH_FAILED",
            error_message="Invalid credentials",
            provider="mock"
        )
        
        self.service.register_provider(mock_provider)
        
        # Track calls
        call_count = 0
        original_send = mock_provider.send_email
        def counting_send(msg):
            nonlocal call_count
            call_count += 1
            return original_send(msg)
        mock_provider.send_email = counting_send
        
        result = self.service.send_email(self.test_email)
        
        self.assertIsInstance(result, EmailErrorResponse)
        self.assertEqual(result.error_code, "AUTH_FAILED")
        self.assertEqual(call_count, 1)  # No retries
    
    def test_send_email_with_fallback(self):
        """Test fallback to alternate provider."""
        # Primary provider that fails
        primary_config = EmailProviderConfig(provider_name="primary")
        primary_provider = MockProvider(primary_config, should_fail=True)
        
        # Fallback provider that succeeds
        fallback_config = EmailProviderConfig(provider_name="fallback")
        fallback_provider = MockProvider(fallback_config, should_fail=False)
        
        self.service.register_provider(primary_provider)
        self.service.register_provider(fallback_provider)
        self.service.config.default_provider = "primary"
        
        result = self.service.send_email(self.test_email)
        
        self.assertIsInstance(result, EmailSendResponse)
        self.assertEqual(result.provider, "fallback")
        self.assertIn("fallback_from", result.details)
        self.assertEqual(result.details["fallback_from"], "primary")
    
    def test_send_bulk_emails(self):
        """Test bulk email sending."""
        mock_config = EmailProviderConfig(provider_name="mock")
        mock_provider = MockProvider(mock_config, should_fail=False)
        self.service.register_provider(mock_provider)
        
        emails = [self.test_email for _ in range(3)]
        results = self.service.send_bulk_emails(emails)
        
        self.assertEqual(len(results), 3)
        self.assertTrue(all(isinstance(r, EmailSendResponse) for r in results))
        self.assertEqual(mock_provider.send_count, 3)
    
    def test_list_providers(self):
        """Test listing registered providers."""
        mock1 = MockProvider(EmailProviderConfig(provider_name="mock1"))
        mock2 = MockProvider(EmailProviderConfig(provider_name="mock2"))
        
        self.service.register_provider(mock1)
        self.service.register_provider(mock2)
        
        providers = self.service.list_providers()
        self.assertEqual(set(providers), {"mock1", "mock2"})


if __name__ == "__main__":
    unittest.main()