# Email Provider Interface

This module provides a clean, extensible interface for sending emails through various email service providers.

## Architecture

The email system is built with the following components:

### 1. Data Models (`models/email_models.py`)
- **EmailAddress**: Represents an email address with optional display name
- **Attachment**: Represents file attachments with base64 encoding
- **EmailMessage**: Complete email message with all fields (to, cc, bcc, subject, content, etc.)
- **EmailSendResponse**: Successful send response
- **EmailErrorResponse**: Error response with details

### 2. Provider Interface (`email_providers/base.py`)
- **EmailProviderInterface**: Abstract base class that all providers must implement
- **EmailProviderConfig**: Base configuration model for providers

### 3. Provider Implementations
- **MailtrapProvider** (`email_providers/mailtrap.py`): Implementation for Mailtrap email service

### 4. Email Service (`services/email_service.py`)
- High-level service that manages multiple providers
- Automatic retry logic with configurable delays
- Fallback support to alternate providers
- Bulk email sending capabilities

## Usage Example

```python
from models.email_models import EmailAddress, EmailMessage
from email_providers.mailtrap import MailtrapProvider, MailtrapConfig
from services.email_service import EmailService, EmailServiceConfig

# Configure Mailtrap provider
mailtrap_config = MailtrapConfig(
    api_token="your-mailtrap-token",
    sandbox=True
)
mailtrap_provider = MailtrapProvider(mailtrap_config)

# Create email service
service_config = EmailServiceConfig(
    default_provider="mailtrap",
    retry_delays=[1, 2, 5]
)
email_service = EmailService(service_config)
email_service.register_provider(mailtrap_provider)

# Create and send email
email = EmailMessage(
    sender=EmailAddress(email="sender@example.com", name="Sender Name"),
    to=[EmailAddress(email="recipient@example.com")],
    subject="Test Email",
    text="This is a test email.",
    html="<p>This is a <strong>test</strong> email.</p>"
)

result = email_service.send_email(email)
if result.status == "success":
    print(f"Email sent! Message ID: {result.message_id}")
else:
    print(f"Failed: {result.error_message}")
```

## Adding New Providers

To add a new email provider:

1. Create a new file in `email_providers/` (e.g., `sendgrid.py`)
2. Create a config class extending `EmailProviderConfig`
3. Create a provider class implementing `EmailProviderInterface`
4. Implement the required methods:
   - `validate_config()`: Validate provider configuration
   - `send_email()`: Send email and return result

Example structure:

```python
from email_providers.base import EmailProviderInterface, EmailProviderConfig
from models.email_models import EmailMessage, EmailOperationResult

class SendGridConfig(EmailProviderConfig):
    api_key: str
    
    def __init__(self, **data):
        data['provider_name'] = 'sendgrid'
        super().__init__(**data)

class SendGridProvider(EmailProviderInterface):
    def validate_config(self) -> bool:
        # Validate API key exists
        return bool(self.config.api_key)
    
    def send_email(self, message: EmailMessage) -> EmailOperationResult:
        # Implement SendGrid API call
        pass
```

## Features

- **Multiple Provider Support**: Easy to add new email providers
- **Retry Logic**: Automatic retries with configurable delays
- **Fallback Support**: Automatically try alternate providers on failure
- **Type Safety**: Full Pydantic model validation
- **Error Handling**: Detailed error responses with provider-specific codes
- **Bulk Sending**: Send multiple emails efficiently
- **Attachment Support**: Base64 encoded file attachments
- **Custom Headers**: Support for custom email headers
- **Template Variables**: Support for provider-specific template variables

## Configuration

### Environment Variables

- `MAILTRAP_API_TOKEN`: API token for Mailtrap provider

### Provider-Specific Configuration

Each provider has its own configuration class with specific requirements:

- **Mailtrap**: Requires `api_token`, supports `sandbox` mode
- Future providers can add their own configuration fields

## Error Handling

The system uses typed responses with specific error codes:

- `AUTH_FAILED`: Authentication/authorization failure
- `INVALID_CONFIG`: Invalid provider configuration
- `SEND_FAILED`: General send failure
- `RATE_LIMITED`: Rate limiting error
- `CONNECTION_ERROR`: Network/connection issues
- `PROVIDER_NOT_FOUND`: Requested provider not registered
- `PROVIDER_ERROR`: Unexpected provider error

## Testing

See `examples/email_example.py` for a complete working example that demonstrates:
- Creating email messages with attachments
- Configuring providers
- Sending emails
- Handling responses
- Bulk email sending