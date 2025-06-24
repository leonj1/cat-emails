from typing import Optional, List, Dict, Any
from pydantic import Field
import base64

from models.email_models import (
    EmailMessage, 
    EmailOperationResult, 
    EmailSendResponse, 
    EmailErrorResponse,
    EmailSendStatus,
    EmailAddress,
    Attachment
)
from email_providers.base import EmailProviderInterface, EmailProviderConfig


class MailtrapConfig(EmailProviderConfig):
    """Configuration specific to Mailtrap email provider."""
    api_token: str = Field(description="Mailtrap API token")
    sandbox: bool = Field(True, description="Whether to use sandbox mode")
    
    def __init__(self, **data):
        data['provider_name'] = 'mailtrap'
        if 'api_endpoint' not in data:
            data['api_endpoint'] = 'https://send.api.mailtrap.io/api/send'
        super().__init__(**data)


class MailtrapProvider(EmailProviderInterface):
    """Mailtrap email provider implementation."""
    
    def __init__(self, config: MailtrapConfig):
        """
        Initialize Mailtrap provider.
        
        Args:
            config: Mailtrap-specific configuration
        """
        super().__init__(config)
        self.config: MailtrapConfig = config
        self._client = None
    
    def _get_client(self):
        """Get or create Mailtrap client."""
        if self._client is None:
            try:
                import mailtrap as mt
                self._client = mt.MailtrapClient(token=self.config.api_token)
            except ImportError:
                raise ImportError(
                    "mailtrap package is not installed. "
                    "Install it with: pip install mailtrap"
                )
        return self._client
    
    def validate_config(self) -> bool:
        """Validate Mailtrap configuration."""
        if not self.config.api_token:
            self.logger.error("Mailtrap API token is required")
            return False
        
        if not self.config.api_token.strip():
            self.logger.error("Mailtrap API token cannot be empty")
            return False
        
        return True
    
    def _convert_email_address(self, address: EmailAddress):
        """Convert EmailAddress to Mailtrap format."""
        import mailtrap as mt
        return mt.Address(email=address.email, name=address.name)
    
    def _convert_attachment(self, attachment: Attachment):
        """Convert Attachment to Mailtrap format."""
        import mailtrap as mt
        
        # Determine disposition type
        if attachment.disposition == "inline":
            disposition = mt.Disposition.INLINE
        else:
            disposition = mt.Disposition.ATTACHMENT
        
        return mt.Attachment(
            filename=attachment.filename,
            content=attachment.content,
            mimetype=attachment.content_type or "application/octet-stream",
            disposition=disposition,
            content_id=attachment.content_id
        )
    
    def _build_mail_object(self, message: EmailMessage):
        """Build Mailtrap Mail object from EmailMessage."""
        import mailtrap as mt
        
        # Create mail object with required fields
        mail = mt.Mail(
            sender=self._convert_email_address(message.sender),
            to=[self._convert_email_address(addr) for addr in message.to],
            subject=message.subject
        )
        
        # Add optional recipients
        if message.cc:
            mail.cc = [self._convert_email_address(addr) for addr in message.cc]
        
        if message.bcc:
            mail.bcc = [self._convert_email_address(addr) for addr in message.bcc]
        
        # Add content
        if message.text:
            mail.text = message.text
        
        if message.html:
            mail.html = message.html
        
        # Add reply-to
        if message.reply_to:
            mail.reply_to = self._convert_email_address(message.reply_to)
        
        # Add attachments
        if message.attachments:
            mail.attachments = [
                self._convert_attachment(att) for att in message.attachments
            ]
        
        # Add custom headers
        if message.headers:
            mail.headers = message.headers
        
        # Add variables (for template support)
        if message.variables:
            mail.custom_variables = message.variables
        
        return mail
    
    def send_email(self, message: EmailMessage) -> EmailOperationResult:
        """
        Send email via Mailtrap.
        
        Args:
            message: Email message to send
            
        Returns:
            EmailOperationResult: Send response or error
        """
        if not self.validate_config():
            return EmailErrorResponse(
                error_code="INVALID_CONFIG",
                error_message="Invalid Mailtrap configuration",
                provider=self.config.provider_name
            )
        
        self._log_send_attempt(message)
        
        try:
            client = self._get_client()
            mail = self._build_mail_object(message)
            
            # Send the email
            response = client.send(mail)
            
            # Extract message ID from response
            # Note: Actual response structure may vary based on Mailtrap SDK version
            message_id = getattr(response, 'message_id', None) or \
                        getattr(response, 'id', None) or \
                        str(response)
            
            self._log_send_success(message_id)
            
            return EmailSendResponse(
                status=EmailSendStatus.SUCCESS,
                message_id=message_id,
                provider=self.config.provider_name,
                details={
                    "sandbox": self.config.sandbox,
                    "response": str(response)
                }
            )
            
        except Exception as e:
            self._log_send_error(e)
            
            # Determine error code based on exception type
            error_code = "SEND_FAILED"
            if "auth" in str(e).lower() or "token" in str(e).lower():
                error_code = "AUTH_FAILED"
            elif "rate" in str(e).lower():
                error_code = "RATE_LIMITED"
            elif "connection" in str(e).lower() or "timeout" in str(e).lower():
                error_code = "CONNECTION_ERROR"
            
            return EmailErrorResponse(
                error_code=error_code,
                error_message=str(e),
                provider=self.config.provider_name,
                details={
                    "exception_type": type(e).__name__,
                    "sandbox": self.config.sandbox
                }
            )