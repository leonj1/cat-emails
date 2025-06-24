"""
Mailfrom.dev email provider using SMTP authentication.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr, make_msgid
from typing import Optional
import base64
from datetime import datetime

from pydantic import Field

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


class MailfromDevConfig(EmailProviderConfig):
    """Configuration for mailfrom.dev SMTP provider."""
    smtp_host: str = Field(default="smtp.mailfrom.dev", description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_username: str = Field(description="SMTP username for authentication")
    smtp_password: str = Field(description="SMTP password for authentication")
    use_tls: bool = Field(default=True, description="Use TLS encryption")
    
    def __init__(self, **data):
        data['provider_name'] = 'mailfrom.dev'
        super().__init__(**data)


class MailfromDevProvider(EmailProviderInterface):
    """Mailfrom.dev SMTP email provider implementation."""
    
    def __init__(self, config: MailfromDevConfig):
        """
        Initialize mailfrom.dev provider.
        
        Args:
            config: Mailfrom.dev-specific configuration
        """
        super().__init__(config)
        self.config: MailfromDevConfig = config
    
    def validate_config(self) -> bool:
        """Validate mailfrom.dev configuration."""
        if not self.config.smtp_username:
            self.logger.error("SMTP username is required")
            return False
        
        if not self.config.smtp_password:
            self.logger.error("SMTP password is required")
            return False
        
        if not self.config.smtp_host:
            self.logger.error("SMTP host is required")
            return False
        
        if self.config.smtp_port <= 0 or self.config.smtp_port > 65535:
            self.logger.error("Invalid SMTP port")
            return False
        
        return True
    
    def _format_address(self, address: EmailAddress) -> str:
        """Format email address for SMTP."""
        if address.name:
            return formataddr((address.name, address.email))
        return address.email
    
    def _create_mime_message(self, message: EmailMessage) -> MIMEMultipart:
        """Create MIME message from EmailMessage."""
        # Create multipart message
        if message.attachments or (message.text and message.html):
            msg = MIMEMultipart('mixed')
            
            # Create alternative part for text/html
            if message.text and message.html:
                alt_part = MIMEMultipart('alternative')
                alt_part.attach(MIMEText(message.text, 'plain'))
                alt_part.attach(MIMEText(message.html, 'html'))
                msg.attach(alt_part)
            elif message.text:
                msg.attach(MIMEText(message.text, 'plain'))
            elif message.html:
                msg.attach(MIMEText(message.html, 'html'))
        else:
            # Simple message
            if message.html:
                msg = MIMEMultipart()
                msg.attach(MIMEText(message.html, 'html'))
            else:
                msg = MIMEMultipart()
                msg.attach(MIMEText(message.text or '', 'plain'))
        
        # Set headers
        msg['From'] = self._format_address(message.sender)
        msg['To'] = ', '.join([self._format_address(addr) for addr in message.to])
        
        if message.cc:
            msg['Cc'] = ', '.join([self._format_address(addr) for addr in message.cc])
        
        msg['Subject'] = message.subject
        msg['Message-ID'] = make_msgid()
        msg['Date'] = formataddr(('', datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')))
        
        if message.reply_to:
            msg['Reply-To'] = self._format_address(message.reply_to)
        
        # Add custom headers
        if message.headers:
            for key, value in message.headers.items():
                msg[key] = value
        
        # Add attachments
        if message.attachments:
            for attachment in message.attachments:
                self._add_attachment(msg, attachment)
        
        return msg
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Attachment) -> None:
        """Add attachment to MIME message."""
        # Create MIME attachment
        part = MIMEBase('application', 'octet-stream')
        
        # Decode base64 content
        content = base64.b64decode(attachment.content)
        part.set_payload(content)
        
        # Encode for email
        encoders.encode_base64(part)
        
        # Set headers
        if attachment.disposition == 'inline':
            part.add_header(
                'Content-Disposition',
                'inline',
                filename=attachment.filename
            )
            if attachment.content_id:
                part.add_header('Content-ID', f'<{attachment.content_id}>')
        else:
            part.add_header(
                'Content-Disposition',
                'attachment',
                filename=attachment.filename
            )
        
        if attachment.content_type:
            main_type, sub_type = attachment.content_type.split('/', 1)
            part.set_type(attachment.content_type)
        
        msg.attach(part)
    
    def send_email(self, message: EmailMessage) -> EmailOperationResult:
        """
        Send email via mailfrom.dev SMTP.
        
        Args:
            message: Email message to send
            
        Returns:
            EmailOperationResult: Send response or error
        """
        if not self.validate_config():
            return EmailErrorResponse(
                error_code="INVALID_CONFIG",
                error_message="Invalid mailfrom.dev configuration",
                provider=self.config.provider_name
            )
        
        self._log_send_attempt(message)
        
        try:
            # Create MIME message
            mime_msg = self._create_mime_message(message)
            message_id = mime_msg['Message-ID']
            
            # Get all recipients
            all_recipients = [addr.email for addr in message.to]
            if message.cc:
                all_recipients.extend([addr.email for addr in message.cc])
            if message.bcc:
                all_recipients.extend([addr.email for addr in message.bcc])
            
            # Create SMTP connection
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                # Enable debug output for troubleshooting
                # server.set_debuglevel(1)
                
                # Start TLS if configured
                if self.config.use_tls:
                    server.starttls(context=context)
                
                # Authenticate
                server.login(self.config.smtp_username, self.config.smtp_password)
                
                # Send email
                server.sendmail(
                    message.sender.email,
                    all_recipients,
                    mime_msg.as_string()
                )
            
            self._log_send_success(message_id)
            
            return EmailSendResponse(
                status=EmailSendStatus.SUCCESS,
                message_id=message_id,
                provider=self.config.provider_name,
                details={
                    "smtp_host": self.config.smtp_host,
                    "smtp_port": self.config.smtp_port,
                    "recipients": all_recipients
                }
            )
            
        except smtplib.SMTPAuthenticationError as e:
            self._log_send_error(e)
            return EmailErrorResponse(
                error_code="AUTH_FAILED",
                error_message=f"SMTP authentication failed: {str(e)}",
                provider=self.config.provider_name,
                details={"smtp_code": e.smtp_code if hasattr(e, 'smtp_code') else None}
            )
            
        except smtplib.SMTPException as e:
            self._log_send_error(e)
            error_code = "SMTP_ERROR"
            if "connection" in str(e).lower():
                error_code = "CONNECTION_ERROR"
            elif "recipient" in str(e).lower():
                error_code = "INVALID_RECIPIENT"
                
            return EmailErrorResponse(
                error_code=error_code,
                error_message=f"SMTP error: {str(e)}",
                provider=self.config.provider_name,
                details={"exception_type": type(e).__name__}
            )
            
        except Exception as e:
            self._log_send_error(e)
            return EmailErrorResponse(
                error_code="SEND_FAILED",
                error_message=str(e),
                provider=self.config.provider_name,
                details={"exception_type": type(e).__name__}
            )