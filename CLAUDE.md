# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Cat-Emails** project - an AI-powered Gmail email categorizer that automatically classifies, labels, and filters emails using machine learning models (Ollama/OpenAI). The system protects users from unwanted commercial content by analyzing email content and sender domains.

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
# or
python setup.py install

# Run the main email scanner (requires env vars)
python gmail_fetcher.py --hours 2

# Run with custom Ollama host
python gmail_fetcher.py --base-url custom-ollama-host:11434

# Run tests
python -m unittest discover tests/
```

### Docker Development
```bash
# Build Docker image
make build

# Run with Docker (reads from .env file)
make run

# Run tests in Docker
make test

# Run as a service (continuous scanning)
make service-build
make service-run
make service-logs
make service-stop

# Clean Docker images
make clean
```

### Kafka-based Processing
```bash
# Start producer (sends emails to Kafka)
python email_scanner_producer.py

# Start consumer (processes emails from Kafka)
python email_scanner_consumer.py
```

## Architecture

### Core Components

1. **gmail_fetcher.py** - Main entry point that connects to Gmail via IMAP and processes emails directly
2. **domain_service.py** - Manages allowed/blocked domains and categories via external Control API
3. **email_scanner_producer.py** / **email_scanner_consumer.py** - Kafka-based distributed processing
4. **gmail_fetcher_service.py** - Service mode for continuous scanning at intervals
5. **models/** - Pydantic models for email categorization and API responses

### Email Processing Flow

1. Connect to Gmail using IMAP with app-specific password
2. Fetch emails from specified time window (default: 2 hours)
3. Check sender domain against allowed/blocked lists via Control API
4. Extract and clean email content (HTML to text conversion)
5. Categorize email content using AI models (llama3.2, gemma2)
6. Apply Gmail labels based on category
7. Optionally delete emails in blocked categories

### Categories

Emails are classified into:
- `Wants-Money` - Payment requests, invoices, donations
- `Advertising` - Direct product promotions
- `Marketing` - Indirect marketing content
- `Personal` - Personal correspondence
- `Financial-Notification` - Bank statements, alerts
- `Appointment-Reminder` - Meeting notifications
- `Service-Updates` - Service notifications
- `Work-related` - Professional emails
- `Other` - Uncategorized

## Configuration

### Required Environment Variables
```bash
GMAIL_EMAIL=your-email@gmail.com
GMAIL_PASSWORD=your-app-password  # Gmail app-specific password
CONTROL_API_TOKEN=your-api-token  # For domain service API
```

### Optional Environment Variables
```bash
HOURS=2  # Hours to look back for emails (default: 2)
SCAN_INTERVAL=2  # Minutes between scans in service mode (default: 2)
OLLAMA_HOST_PRIMARY=10.1.1.247:11434  # Primary Ollama host (default: 10.1.1.247:11434)
OLLAMA_HOST_SECONDARY=10.1.1.212:11434  # Secondary Ollama host (default: 10.1.1.212:11434)
MORNING_HOUR=5  # Morning summary hour (0-23, default: 5 for 5:30 AM)
MORNING_MINUTE=30  # Morning summary minute (0-59, default: 30)
EVENING_HOUR=16  # Evening summary hour (0-23, default: 16 for 4:30 PM)
EVENING_MINUTE=30  # Evening summary minute (0-59, default: 30)
DISABLE_REMOTE_LOGS=false  # Set to "true", "1", or "yes" to disable remote logging
```

### Setting Up Gmail Access
1. Enable 2-factor authentication in Gmail
2. Generate an app-specific password at https://myaccount.google.com/apppasswords
3. Use this password as GMAIL_PASSWORD

## Testing

### Running Tests
```bash
# Local tests
python -m unittest discover tests/

# Docker tests
make test

# Run specific test
python -m unittest tests.test_domain_service.TestDomainService
```

### Mock Mode
The domain service supports a mock mode for testing without external API calls:
```python
domain_service = DomainService(mock_mode=True)
```

## Key Dependencies

- **imapclient** - Gmail IMAP connection
- **email** - Email parsing
- **ell-ai** - AI model integration framework (note: not in requirements.txt)
- **openai** - For Ollama API compatibility
- **beautifulsoup4** - HTML email parsing
- **kafka-python** - Message queue support
- **pydantic** - Data validation and models
- **requests** - HTTP client for Control API
- **pytz** - Timezone handling for scheduled reports
- **jinja2** - HTML email templating
- **matplotlib** - Chart and graph generation
- **seaborn** - Statistical data visualization

## Control API Integration

The system integrates with an external Control API to manage:
- Allowed domains (whitelist)
- Blocked domains (blacklist)
- Blocked categories

API endpoints:
- `GET /api/v1/allowed-domains`
- `GET /api/v1/blocked-domains`
- `GET /api/v1/blocked-categories`

## AI Model Configuration

The system uses a flexible LLM service architecture that allows swapping between different AI providers:

### LLM Service Interface

The project now uses an abstraction layer (`LLMServiceInterface`) that allows the email categorization system to work with any LLM provider without changing core logic:

**Available Implementations:**
- `OpenAILLMService` - Works with OpenAI, Ollama, RequestYAI, or any OpenAI-compatible API
- Custom implementations - Easily create your own by extending `LLMServiceInterface`

**Default Configuration:**
- Provider: RequestYAI (OpenAI-compatible gateway)
- Model: `vertex/google/gemini-2.5-flash`
- Configurable via environment variables

### Using Custom LLM Implementations

You can swap LLM providers by implementing `LLMServiceInterface`:

```python
from services.llm_service_interface import LLMServiceInterface
from services.categorize_emails_llm import LLMCategorizeEmails

# Create your custom LLM service
class CustomLLMService(LLMServiceInterface):
    def call(self, prompt, system_prompt=None, **kwargs):
        # Your LLM logic here
        return "Marketing"

    def is_available(self):
        return True

    def get_model_name(self):
        return "my-custom-model"

    def get_provider_name(self):
        return "custom-provider"

# Use it with the categorizer
llm_service = CustomLLMService()
categorizer = LLMCategorizeEmails(llm_service=llm_service)
```

See `examples/custom_llm_example.py` for complete examples including:
- Mock LLM for testing
- Rule-based categorization
- Runtime provider swapping

### Legacy Support

The system maintains backward compatibility with the original `ell` framework approach, but new code should use the `LLMServiceInterface` for better flexibility.

### Ollama Host Failover

The system includes automatic failover between multiple Ollama hosts for high availability:

1. **Primary Host**: Specified by `OLLAMA_HOST_PRIMARY` or `--primary-host`
2. **Secondary Host**: Specified by `OLLAMA_HOST_SECONDARY` or `--secondary-host`

Features:
- Automatic health checks every 5 minutes
- Immediate failover on connection errors
- Exponential backoff retry logic
- Automatic recovery when failed hosts come back online
- Detailed logging of failover events

Example usage:
```bash
# Using command line arguments
python gmail_fetcher.py --primary-host 192.168.1.100:11434 --secondary-host 192.168.1.101:11434

# Using environment variables
export OLLAMA_HOST_PRIMARY=192.168.1.100:11434
export OLLAMA_HOST_SECONDARY=192.168.1.101:11434
python gmail_fetcher.py
```

The failover is transparent - if the primary host fails, requests automatically route to the secondary host without interrupting email processing.

## Common Development Tasks

### Adding New Categories
1. Update the category list in `models/email_category.py`
2. Modify the AI prompts in `gmail_fetcher.py` to recognize the new category
3. Add corresponding Gmail label creation logic

### Modifying Domain Rules
Domain rules are managed via the Control API. The local cache refreshes on each run.

### Debugging Email Processing
- Enable verbose logging by checking the logging configuration in `gmail_fetcher.py`
- Use mock mode to test without connecting to Gmail
- Check Docker logs: `docker logs <container-id>`
- Review ell logs in `./logdir` for AI model interactions

## Email Sending Interface

The project includes a flexible email sending interface that supports multiple providers:

### Architecture
- **Interface**: `EmailProviderInterface` in `email_providers/base.py` - Abstract base class for all providers
- **Models**: Pydantic models in `models/email_models.py` for type-safe email handling
- **Providers**: Concrete implementations (currently Mailtrap) in `email_providers/`

### Usage Example
```python
from models.email_models import EmailAddress, EmailMessage
from email_providers.mailtrap import MailtrapProvider, MailtrapConfig

# Configure provider
config = MailtrapConfig(api_token="your-mailtrap-token")
provider = MailtrapProvider(config)

# Create and send email
message = EmailMessage(
    sender=EmailAddress(email="noreply@example.com", name="System"),
    to=[EmailAddress(email="user@example.com")],
    subject="Test Email",
    text="Email content"
)
result = provider.send_email(message)
```

### Running Examples
```bash
# Set Mailtrap API token
export MAILTRAP_API_TOKEN="your-token"

# Run examples
python examples/send_email_example.py
```

### Testing Email Interface
```bash
# Run email interface tests
python -m unittest tests.test_email_interface
```

### Available Email Providers

#### Mailtrap (API-based)
- Uses Mailtrap API for sending emails
- Requires `MAILTRAP_KEY` environment variable
- Good for development and testing

#### mailfrom.dev (SMTP-based)
- Uses SMTP authentication for sending emails
- Requires `SMTP_USERNAME` and `SMTP_PASSWORD` environment variables
- More reliable for production use
- Default configuration: `smtp.mailfrom.dev:587` with STARTTLS

### Running Email Integration Tests
```bash
# Test Mailtrap provider
export MAILTRAP_KEY="your-api-token"
make test-email-integration

# Test mailfrom.dev SMTP provider
export SMTP_USERNAME="your-smtp-username"
export SMTP_PASSWORD="your-smtp-password"
make test-mailfrom-integration
```

### Adding New Email Providers
1. Create a new class extending `EmailProviderInterface`
2. Implement `send_email()` and `validate_config()` methods
3. Create a config class extending `EmailProviderConfig`
4. Add provider-specific dependencies to requirements.txt

## Email Summary Reports

The service automatically sends summary reports at the following times (Eastern Time):
- **Morning Report**: Configurable (default: 5:30 AM ET daily)
- **Evening Report**: Configurable (default: 4:30 PM ET daily)  
- **Weekly Report**: Same as evening time on Fridays

Each report contains:
- Total emails processed vs archived/deleted
- Processing performance metrics (emails/minute, average processing time)
- Top 10 email categories with distribution chart
- Top 5 email senders with bar chart
- Beautiful responsive HTML email format with charts and graphs
- Weekly reports include week-over-week trends and comparisons

### Configuration
```bash
# Enable/disable summaries
ENABLE_SUMMARIES=true

# Who receives the summary reports (defaults to GMAIL_EMAIL)
SUMMARY_RECIPIENT_EMAIL=your-email@gmail.com
GMAIL_EMAIL=your-email@gmail.com

# Mailtrap SMTP credentials for sending summaries
MAILTRAP_API_TOKEN=your-mailtrap-api-token

# Email schedule configuration (24-hour format, Eastern Time)
MORNING_HOUR=5     # Morning summary hour (0-23, default: 5 for 5:30 AM)
MORNING_MINUTE=30   # Morning summary minute (0-59, default: 30)
EVENING_HOUR=16    # Evening summary hour (0-23, default: 16 for 4:30 PM)
EVENING_MINUTE=30   # Evening summary minute (0-59, default: 30)
```

Example: To send morning summaries at 6:30 AM and evening summaries at 7:00 PM:
```bash
MORNING_HOUR=6 MORNING_MINUTE=30 EVENING_HOUR=19 EVENING_MINUTE=0 make service-run
```

### Summary Features
- **Timezone-aware scheduling**: Reports are sent at consistent times in Eastern Time regardless of server timezone
- **Performance tracking**: Monitors processing speed and efficiency
- **Visual charts**: Category pie charts, sender bar charts, and trend line graphs
- **Retry logic**: Automatic retry with exponential backoff (max 3 attempts)
- **Template-based**: Customizable HTML email template in `templates/summary_email.html`
- **Graceful failure handling**: Service continues if summary fails to send
- **Data persistence**: Archives historical data for future analysis

### Manual Summary Generation
```bash
# Generate and send a summary report manually
python send_emails.py

# Test with specific recipient
python send_emails.py recipient@example.com
```

### Email Template Customization
The HTML email template is located at `templates/summary_email.html` and uses Jinja2 templating. You can customize:
- Colors and styling
- Chart types and appearance
- Data presentation format
- Company branding

### Chart Generation
The system generates the following charts:
- **Category Distribution**: Pie chart showing email category percentages
- **Top Senders**: Horizontal bar chart of most frequent senders
- **Daily Volume**: Line chart showing email trends over the past week (weekly reports)
- **Performance Metrics**: Time series chart of processing efficiency

## API Service

The Cat-Emails project includes a comprehensive REST API service (`api_service.py`) for managing email accounts, triggering processing, and monitoring status.

### Starting the API Service
```bash
# Start the API service locally
python api_service.py

# Or using environment variables for configuration
API_HOST=0.0.0.0 API_PORT=8001 python api_service.py

# The service will be available at http://localhost:8001
# OpenAPI docs: http://localhost:8001/docs
# ReDoc: http://localhost:8001/redoc
```

### Key API Endpoints

#### Account Management
- `GET /api/accounts` - List all tracked email accounts
- `POST /api/accounts` - Register a new email account for tracking
- `GET /api/accounts/{email_address}/verify-password` - Verify Gmail app password
- `PUT /api/accounts/{email_address}/deactivate` - Deactivate an account
- `DELETE /api/accounts/{email_address}` - Delete account and all data
- `GET /api/accounts/{email_address}/categories/top` - Get top categories for account

#### Force Processing (On-Demand)
- `POST /api/accounts/{email_address}/process` - **Force immediate email processing**

**Force Processing Features:**
- Triggers immediate email processing outside regular background scan cycle
- Returns 202 Accepted immediately (async processing)
- **Concurrency protection**: Blocks if account is already being processed
- **Rate limiting**: Max 1 request per account every 5 minutes (returns 429 if exceeded)
- **Custom lookback hours**: Optional `hours` query parameter (1-168 hours)
- Real-time status via WebSocket or polling endpoint

**Example Usage:**
```bash
# Force process an account with default settings
curl -X POST "http://localhost:8001/api/accounts/user@gmail.com/process" \
  -H "X-API-Key: your-api-key"

# Force process with custom 24-hour lookback
curl -X POST "http://localhost:8001/api/accounts/user@gmail.com/process?hours=24" \
  -H "X-API-Key: your-api-key"

# Response (202 Accepted):
{
  "status": "success",
  "message": "Email processing started for user@gmail.com",
  "email_address": "user@gmail.com",
  "timestamp": "2025-10-07T10:30:00Z",
  "processing_info": {
    "hours": 2,
    "status_url": "/api/processing/current-status",
    "websocket_url": "/ws/status"
  }
}

# If already processing (409 Conflict):
{
  "status": "already_processing",
  "message": "Account user@gmail.com is currently being processed",
  "email_address": "user@gmail.com",
  "timestamp": "2025-10-07T10:30:00Z",
  "processing_info": {
    "state": "PROCESSING",
    "current_step": "Processing email 5 of 20"
  }
}

# If rate limited (429 Too Many Requests):
{
  "error": "Rate limit exceeded",
  "message": "Please wait 3.5 minutes before processing user@gmail.com again",
  "seconds_remaining": 210.0,
  "retry_after": 210
}
```

#### Processing Status & Monitoring
- `GET /api/processing/status` - Get current processing status
- `GET /api/processing/history` - Get recent processing runs
- `GET /api/processing/statistics` - Get aggregate statistics
- `GET /api/processing/current-status` - Comprehensive status (polling-friendly)
- `WS /ws/status` - WebSocket for real-time status updates

#### Background Processing Control
- `POST /api/background/start` - Start background processor
- `POST /api/background/stop` - Stop background processor
- `GET /api/background/status` - Get background processor status
- `GET /api/background/next-execution` - Get next scheduled scan time

#### Summary Reports
- `POST /api/summaries/morning` - Trigger morning summary
- `POST /api/summaries/evening` - Trigger evening summary
- `POST /api/summaries/weekly` - Trigger weekly summary
- `POST /api/summaries/monthly` - Trigger monthly summary

### API Authentication
Configure optional API key authentication:
```bash
export API_KEY="your-secret-api-key"
python api_service.py
```

Include in requests via header:
```bash
curl -H "X-API-Key: your-secret-api-key" http://localhost:8001/api/accounts
```

### WebSocket Real-time Updates
Connect to `/ws/status` for real-time processing status:
```javascript
const ws = new WebSocket('ws://localhost:8001/ws/status?api_key=your-key');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Processing status:', data);
};
```

### Environment Variables for API Service
```bash
# API server configuration
API_HOST=0.0.0.0                    # Host to bind (default: 0.0.0.0)
API_PORT=8001                       # Port to listen (default: 8001)
API_KEY=your-secret-key             # Optional API key for authentication

# Background processing
BACKGROUND_PROCESSING=true          # Enable background processing (default: true)
BACKGROUND_SCAN_INTERVAL=300        # Interval between scans in seconds (default: 300 = 5 min)
BACKGROUND_PROCESS_HOURS=2          # Lookback hours for background scans (default: 2)

# LLM configuration
REQUESTYAI_API_KEY=your-key         # RequestYAI API key
OPENAI_API_KEY=your-key             # OpenAI API key (alternative)
LLM_MODEL=vertex/google/gemini-2.5-flash  # Model to use

# Database
DATABASE_PATH=./email_summaries/summaries.db  # SQLite database path

# Control API
CONTROL_API_TOKEN=your-token        # Control API authentication token
```

### Force Processing vs Background Processing

**Background Processing:**
- Automatic, scheduled scanning of all active accounts
- Runs at regular intervals (configurable, default: 5 minutes)
- Processes all accounts sequentially
- Always-on, daemon-style operation

**Force Processing (On-Demand):**
- Manual, immediate processing of a specific account
- Triggered via API endpoint when needed
- Single account at a time
- Useful for:
  - Immediate processing after adding new account
  - Catching up on missed emails with custom lookback hours
  - Testing/debugging specific account issues
  - User-initiated "refresh" from UI

**Rate Limiting:** Force processing is rate-limited (5 minutes per account) to prevent abuse and excessive Gmail API calls.

## Security Notes

- Never commit `.env` files with real credentials
- Use app-specific passwords for Gmail
- Keep CONTROL_API_TOKEN secure
- Keep email provider API tokens secure (e.g., MAILTRAP_API_TOKEN)
- Keep API_KEY secure if using API authentication
- SSL/TLS is enforced for IMAP connections
- Rate limiting protects against abuse of force processing endpoint