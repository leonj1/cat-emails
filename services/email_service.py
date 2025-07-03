from typing import Dict, Optional, List
from pydantic import BaseModel, Field
import logging
import time

from models.email_models import (
    EmailMessage, 
    EmailOperationResult,
    EmailSendResponse,
    EmailErrorResponse,
    EmailSendStatus
)
from email_providers.base import EmailProviderInterface


class EmailServiceConfig(BaseModel):
    """Configuration for the email service."""
    default_provider: str = Field(description="Name of the default email provider")
    retry_delays: List[int] = Field(
        default=[1, 2, 5], 
        description="Delays in seconds between retry attempts"
    )
    enable_fallback: bool = Field(
        default=True,
        description="Whether to fallback to other providers on failure"
    )


class EmailService:
    """High-level email service that manages multiple providers."""
    
    def __init__(self, config: EmailServiceConfig):
        """
        Initialize email service.
        
        Args:
            config: Service configuration
        """
        self.config = config
        self.providers: Dict[str, EmailProviderInterface] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_provider(self, provider: EmailProviderInterface) -> None:
        """
        Register an email provider.
        
        Args:
            provider: Email provider instance
        """
        provider_name = provider.get_provider_name()
        self.providers[provider_name] = provider
        self.logger.info(f"Registered email provider: {provider_name}")
    
    def unregister_provider(self, provider_name: str) -> None:
        """
        Unregister an email provider.
        
        Args:
            provider_name: Name of the provider to unregister
        """
        if provider_name in self.providers:
            del self.providers[provider_name]
            self.logger.info(f"Unregistered email provider: {provider_name}")
    
    def get_provider(self, provider_name: Optional[str] = None) -> Optional[EmailProviderInterface]:
        """
        Get a specific provider or the default one.
        
        Args:
            provider_name: Name of the provider (optional)
            
        Returns:
            Email provider instance or None if not found
        """
        if provider_name:
            return self.providers.get(provider_name)
        
        # Return default provider
        return self.providers.get(self.config.default_provider)
    
    def list_providers(self) -> List[str]:
        """Get list of registered provider names."""
        return list(self.providers.keys())
    
    def _send_with_retry(
        self, 
        provider: EmailProviderInterface, 
        message: EmailMessage
    ) -> EmailOperationResult:
        """
        Send email with retry logic.
        
        Args:
            provider: Email provider to use
            message: Email message to send
            
        Returns:
            Email operation result
        """
        last_error = None
        
        for attempt, delay in enumerate(self.config.retry_delays + [0], 1):
            try:
                result = provider.send_email(message)
                
                # If successful, return immediately
                if isinstance(result, EmailSendResponse):
                    return result
                
                # If error, save it for potential retry
                last_error = result
                
                # Don't retry on certain errors
                if result and result.error_code in ["AUTH_FAILED", "INVALID_CONFIG"]:
                    return result
                
            except Exception as e:
                self.logger.error(
                    f"Unexpected error in provider {provider.get_provider_name()}: {e}"
                )
                last_error = EmailErrorResponse(
                    error_code="PROVIDER_ERROR",
                    error_message=str(e),
                    provider=provider.get_provider_name()
                )
            
            # Wait before retry (except on last attempt)
            if attempt <= len(self.config.retry_delays):
                self.logger.info(
                    f"Retrying in {delay} seconds (attempt {attempt}/{len(self.config.retry_delays) + 1})"
                )
                time.sleep(delay)
        
        # Return the last error if all retries failed
        return last_error or EmailErrorResponse(
            error_code="UNKNOWN_ERROR",
            error_message="All retry attempts failed",
            provider=provider.get_provider_name()
        )
    
    def send_email(
        self, 
        message: EmailMessage, 
        provider_name: Optional[str] = None
    ) -> EmailOperationResult:
        """
        Send an email using the specified or default provider.
        
        Args:
            message: Email message to send
            provider_name: Specific provider to use (optional)
            
        Returns:
            Email operation result
        """
        # Get the requested provider
        provider = self.get_provider(provider_name)
        
        if not provider:
            return EmailErrorResponse(
                error_code="PROVIDER_NOT_FOUND",
                error_message=f"Email provider not found: {provider_name or self.config.default_provider}",
                provider=provider_name or self.config.default_provider
            )
        
        # Try sending with the primary provider
        result = self._send_with_retry(provider, message)
        
        # If successful or fallback is disabled, return the result
        if isinstance(result, EmailSendResponse) or not self.config.enable_fallback:
            return result
        
        # Try fallback providers if enabled
        primary_error = result
        for fallback_name, fallback_provider in self.providers.items():
            if fallback_name == provider.get_provider_name():
                continue  # Skip the provider we already tried
            
            self.logger.warning(
                f"Primary provider {provider.get_provider_name()} failed, "
                f"trying fallback: {fallback_name}"
            )
            
            fallback_result = self._send_with_retry(fallback_provider, message)
            
            if isinstance(fallback_result, EmailSendResponse):
                # Add note about fallback in details
                if not fallback_result.details:
                    fallback_result.details = {}
                fallback_result.details["fallback_from"] = provider.get_provider_name()
                return fallback_result
        
        # All providers failed, return the primary error
        return primary_error
    
    def send_bulk_emails(
        self, 
        messages: List[EmailMessage],
        provider_name: Optional[str] = None
    ) -> List[EmailOperationResult]:
        """
        Send multiple emails.
        
        Args:
            messages: List of email messages to send
            provider_name: Specific provider to use (optional)
            
        Returns:
            List of operation results for each message
        """
        results = []
        
        for message in messages:
            result = self.send_email(message, provider_name)
            results.append(result)
            
            # Small delay between bulk sends to avoid rate limiting
            if len(messages) > 10:
                time.sleep(0.1)
        
        return results