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
OLLAMA_HOST=http://localhost:11434  # Custom Ollama server
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

The system uses Ollama with multiple models for categorization:
- Primary: `llama3.2` (fast, accurate)
- Secondary: `gemma2` (fallback)

Models are accessed via the Ollama API at the configured OLLAMA_HOST. The `ell` framework is used for LLM orchestration with logging stored in `./logdir`.

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

## Security Notes

- Never commit `.env` files with real credentials
- Use app-specific passwords for Gmail
- Keep CONTROL_API_TOKEN secure
- SSL/TLS is enforced for IMAP connections