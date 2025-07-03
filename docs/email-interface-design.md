# Email Interface Design Summary

## Overview

Based on the Mailtrap example provided, I've designed and implemented a clean, extensible email interface that abstracts email sending functionality and supports multiple providers.

## 1. Interface Methods

The email interface (`EmailProviderInterface`) includes the following core methods:

### Required Methods:
- **`send_email(message: EmailMessage) -> EmailOperationResult`**
  - Sends an email message
  - Returns either `EmailSendResponse` (success) or `EmailErrorResponse` (failure)
  - Handles all provider-specific logic internally

- **`validate_config() -> bool`**
  - Validates provider configuration
  - Returns True if config is valid, False otherwise
  - Called before attempting to send emails

### Helper Methods (inherited):
- **`get_provider_name() -> str`** - Returns the provider name
- **`_log_send_attempt(message)`** - Logs email send attempts
- **`_log_send_success(message_id)`** - Logs successful sends
- **`_log_send_error(error)`** - Logs send failures

## 2. Data Models/Classes

### Email Models (`models/email_models.py`):

1. **`EmailAddress`**
   - `email: EmailStr` - The email address (validated)
   - `name: Optional[str]` - Display name
   - `to_string() -> str` - Formats as "Name <email>" or just "email"

2. **`Attachment`**
   - `filename: str` - File name
   - `content: str` - Base64 encoded content
   - `content_type: Optional[str]` - MIME type (default: "application/octet-stream")
   - `disposition: Optional[str]` - Content disposition (default: "attachment")
   - `content_id: Optional[str]` - For inline attachments

3. **`EmailMessage`**
   - `sender: EmailAddress` - Email sender
   - `to: List[EmailAddress]` - Primary recipients
   - `cc: Optional[List[EmailAddress]]` - CC recipients
   - `bcc: Optional[List[EmailAddress]]` - BCC recipients
   - `subject: str` - Email subject
   - `text: Optional[str]` - Plain text content
   - `html: Optional[str]` - HTML content
   - `attachments: Optional[List[Attachment]]` - File attachments
   - `headers: Optional[Dict[str, str]]` - Custom headers
   - `variables: Optional[Dict[str, any]]` - Template variables
   - `reply_to: Optional[EmailAddress]` - Reply-to address

4. **Response Models**:
   - `EmailSendResponse` - Success response with message_id, status, provider
   - `EmailErrorResponse` - Error response with error_code, error_message, provider
   - `EmailSendStatus` - Enum: SUCCESS, FAILED, QUEUED, PENDING

### Provider Configuration:

1. **`EmailProviderConfig`** (base class)
   - `provider_name: str` - Provider identifier
   - `api_endpoint: Optional[str]` - API URL
   - `timeout: int` - Request timeout (default: 30s)
   - `retry_attempts: int` - Number of retries (default: 3)
   - `custom_config: Optional[Dict[str, Any]]` - Provider-specific settings

2. **`MailtrapConfig`** (example implementation)
   - Inherits from `EmailProviderConfig`
   - `api_token: str` - Mailtrap API token
   - `sandbox: bool` - Sandbox mode flag

## 3. Interface Structure for Multiple Providers

The design uses several patterns to support multiple email providers:

### 1. **Abstract Base Class Pattern**
```python
# email_providers/base.py
class EmailProviderInterface(ABC):
    @abstractmethod
    def send_email(self, message: EmailMessage) -> EmailOperationResult:
        pass
```

### 2. **Provider Registry Pattern**
The `EmailService` class manages multiple providers:
```python
# services/email_service.py
class EmailService:
    def register_provider(self, provider: EmailProviderInterface)
    def unregister_provider(self, provider_name: str)
    def get_provider(self, provider_name: Optional[str])
```

### 3. **Configuration Inheritance**
Each provider has its own config class that extends the base:
```python
class MailtrapConfig(EmailProviderConfig):
    api_token: str
    sandbox: bool
```

### 4. **Standardized Data Models**
All providers use the same `EmailMessage` format, which they convert internally:
```python
# In MailtrapProvider
def _build_mail_object(self, message: EmailMessage):
    # Convert EmailMessage to Mailtrap's mt.Mail format
```

### 5. **Service Layer Features**:
- **Automatic Retry**: Configurable retry delays with smart error handling
- **Provider Fallback**: Automatically try alternate providers on failure
- **Bulk Sending**: Send multiple emails efficiently
- **Unified Error Handling**: Consistent error codes across providers

## Example: Adding a New Provider

To add a new provider (e.g., SendGrid):

```python
# email_providers/sendgrid.py
from email_providers.base import EmailProviderInterface, EmailProviderConfig

class SendGridConfig(EmailProviderConfig):
    api_key: str
    
    def __init__(self, **data):
        data['provider_name'] = 'sendgrid'
        super().__init__(**data)

class SendGridProvider(EmailProviderInterface):
    def validate_config(self) -> bool:
        return bool(self.config.api_key)
    
    def send_email(self, message: EmailMessage) -> EmailOperationResult:
        # Convert EmailMessage to SendGrid format
        # Make API call
        # Return standardized response
        pass
```

## Key Design Benefits

1. **Provider Agnostic**: Core application code doesn't need to know which provider is being used
2. **Easy to Extend**: New providers can be added without modifying existing code
3. **Type Safety**: Full Pydantic validation ensures data integrity
4. **Testable**: Mock providers can be easily created for testing
5. **Resilient**: Built-in retry logic and fallback support
6. **Consistent**: Uniform interface regardless of provider

## File Structure

```
cat-emails/
├── models/
│   └── email_models.py          # Data models
├── email_providers/
│   ├── __init__.py
│   ├── base.py                  # Abstract interface
│   ├── mailtrap.py              # Mailtrap implementation
│   └── README.md                # Provider documentation
├── services/
│   ├── __init__.py
│   └── email_service.py         # High-level service
├── tests/
│   ├── test_email_models.py     # Model tests
│   └── test_email_service.py    # Service tests
└── examples/
    └── email_example.py         # Usage example
```