from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging
from utils.logger import get_logger

from models.email_models import EmailMessage, EmailOperationResult


class EmailProviderConfig(BaseModel):
    """Base configuration for email providers."""
    provider_name: str = Field(description="Name of the email provider")
    api_endpoint: Optional[str] = Field(None, description="API endpoint URL")
    timeout: int = Field(30, description="Request timeout in seconds")
    retry_attempts: int = Field(3, description="Number of retry attempts on failure")
    custom_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Provider-specific configuration")


class EmailProviderInterface(ABC):
    """Abstract base class for email providers."""
    
    def __init__(self, config: EmailProviderConfig):
        """
        Initialize the email provider with configuration.
        
        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.logger = get_logger(f"{__name__}.{config.provider_name}")
    
    @abstractmethod
    def send_email(self, message: EmailMessage) -> EmailOperationResult:
        """
        Send an email message.
        
        Args:
            message: The email message to send
            
        Returns:
            EmailOperationResult: Either EmailSendResponse on success or EmailErrorResponse on failure
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate the provider configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return self.config.provider_name
    
    def _log_send_attempt(self, message: EmailMessage) -> None:
        """Log email send attempt."""
        self.logger.info(
            f"Attempting to send email via {self.config.provider_name}: "
            f"to={[addr.email for addr in message.to]}, "
            f"subject='{message.subject}'"
        )
    
    def _log_send_success(self, message_id: str) -> None:
        """Log successful email send."""
        self.logger.info(
            f"Email sent successfully via {self.config.provider_name}: "
            f"message_id={message_id}"
        )
    
    def _log_send_error(self, error: Exception) -> None:
        """Log email send error."""
        self.logger.error(
            f"Failed to send email via {self.config.provider_name}: "
            f"{type(error).__name__}: {str(error)}"
        )