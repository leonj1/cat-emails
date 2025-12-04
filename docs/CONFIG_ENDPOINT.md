# Configuration Endpoint Documentation

## Overview

The `/api/config` endpoint provides complete visibility into how the Cat-Emails backend is configured and launched. This endpoint returns all configuration settings in a structured format using Pydantic models.

## Endpoint Details

- **URL**: `GET /api/config`
- **Response Model**: `ConfigurationResponse`
- **Authentication**: Requires API key if configured (`X-API-Key` header)
- **Tags**: `health`

## Response Structure

The endpoint returns a JSON response with the following structure:

```json
{
  "database": {
    "type": "mysql|sqlite_local|sqlite_cloud|unknown",
    "host": "database-host",
    "port": 3306,
    "database_name": "cat_emails",
    "path": "/path/to/sqlite.db",
    "connection_pool_size": 5,
    "connected": true,
    "connection_status": "Connected",
    "connection_error": null,
    "env_vars": {
      "host_var": "DATABASE_HOST",
      "host_value": "database-host",
      "name_var": "DATABASE_NAME",
      "name_value": "cat_emails",
      "user_var": "DATABASE_USER",
      "user_value": "app_user"
    }
  },
  "llm": {
    "provider": "RequestYAI|OpenAI",
    "model": "vertex/google/gemini-2.5-flash",
    "base_url": "https://router.requesty.ai/v1",
    "api_key_configured": true
  },
  "background_processing": {
    "enabled": true,
    "scan_interval_seconds": 300,
    "lookback_hours": 2
  },
  "api_service": {
    "host": "0.0.0.0",
    "port": 8001,
    "api_key_required": true
  },
  "environment": "production|development|testing",
  "version": "1.1.0"
}
```

## Configuration Fields

### Database Configuration

The `database` object shows which database backend is being used:

- **type**: Database type
  - `mysql` - MySQL database (local or cloud)
  - `sqlite_local` - Local SQLite file
  - `sqlite_cloud` - Cloud-hosted SQLite
  - `unknown` - Could not determine type
  
- **host**: Database hostname (MySQL only)
- **port**: Database port (MySQL only, default: 3306)
- **database_name**: Database name (MySQL only)
- **path**: File path (SQLite only)
- **connection_pool_size**: Connection pool size (MySQL only)
- **connected**: Whether the database connection is active
- **connection_status**: Human-readable connection status message
- **connection_error**: Error message if connection failed (null if connected)
- **env_vars**: Environment variable names and values (MySQL only, excludes password and port for security)
  - **host_var**: Name of the host environment variable (`DATABASE_HOST`)
  - **host_value**: Current value of `DATABASE_HOST`
  - **name_var**: Name of the database name environment variable (`DATABASE_NAME`)
  - **name_value**: Current value of `DATABASE_NAME`
  - **user_var**: Name of the user environment variable (`DATABASE_USER`)
  - **user_value**: Current value of `DATABASE_USER`

#### Database Type Detection Logic

The system determines database type based on environment variables:

1. **MySQL** - If any of these are set:
   - `DATABASE_HOST`
   - `DATABASE_USER`
   - `DATABASE_URL`

2. **SQLite** - If `DATABASE_PATH` is set:
   - `:memory:` → `sqlite_local`
   - Starts with `sqlitecloud://`, `http://`, or `https://` → `sqlite_cloud`
   - Other paths → `sqlite_local`

3. **Default** - Falls back to MySQL if no explicit config

### LLM Configuration

The `llm` object shows which AI service is being used for email categorization:

- **provider**: LLM service provider
  - `RequestYAI` - Using RequestYAI service
  - `OpenAI` - Using OpenAI service
  - `Unknown` - No API key configured
  
- **model**: Model name (e.g., `vertex/google/gemini-2.5-flash`)
- **base_url**: API endpoint URL
- **api_key_configured**: Whether an API key is set (boolean, never shows the actual key)

#### LLM Provider Detection Logic

1. If `REQUESTYAI_API_KEY` is set → `RequestYAI`
2. Else if `OPENAI_API_KEY` is set → `OpenAI`
3. Else → `Unknown`

### Background Processing Configuration

The `background_processing` object shows settings for automatic email scanning:

- **enabled**: Whether background processing is enabled
- **scan_interval_seconds**: Seconds between automatic scans (default: 300 = 5 minutes)
- **lookback_hours**: How far back to check for emails (default: 2 hours)

### API Service Configuration

The `api_service` object shows API server settings:

- **host**: Host the API is bound to (default: `0.0.0.0`)
- **port**: Port the API is listening on (default: `8001`)
- **api_key_required**: Whether API authentication is enabled

### Environment & Version

- **environment**: Deployment environment (from `ENVIRONMENT` or `RAILWAY_ENVIRONMENT` env vars)
- **version**: API version number

## Environment Variables

The endpoint derives its information from these environment variables:

### Database
- `DATABASE_HOST` - MySQL host
- `DATABASE_PORT` - MySQL port (default: 3306)
- `DATABASE_NAME` - MySQL database name (default: cat_emails)
- `DATABASE_USER` - MySQL username
- `DATABASE_URL` - MySQL connection string
- `DATABASE_PATH` - SQLite file path
- `DATABASE_POOL_SIZE` - Connection pool size (default: 5)

### LLM
- `REQUESTYAI_API_KEY` - RequestYAI API key
- `REQUESTYAI_BASE_URL` - RequestYAI endpoint (default: https://router.requesty.ai/v1)
- `OPENAI_API_KEY` - OpenAI API key
- `OPENAI_BASE_URL` - OpenAI endpoint (default: https://api.openai.com/v1)
- `LLM_MODEL` - Model name (default: vertex/google/gemini-2.5-flash)

### Background Processing
- `BACKGROUND_PROCESSING` - Enable/disable (default: true)
- `BACKGROUND_SCAN_INTERVAL` - Scan interval in seconds (default: 300)
- `BACKGROUND_PROCESS_HOURS` - Lookback hours (default: 2)

### API Service
- `API_HOST` - API host (default: 0.0.0.0)
- `API_PORT` - API port (default: 8001)
- `API_KEY` - API authentication key (optional)
- `ENVIRONMENT` - Environment name (optional)
- `RAILWAY_ENVIRONMENT` - Railway environment name (optional)

## Usage Examples

### cURL

```bash
# Without API key
curl http://localhost:8001/api/config

# With API key
curl -H "X-API-Key: your-api-key" http://localhost:8001/api/config
```

### Python

```python
import requests

response = requests.get(
    "http://localhost:8001/api/config",
    headers={"X-API-Key": "your-api-key"}
)

config = response.json()
print(f"Database: {config['database']['type']}")
print(f"LLM: {config['llm']['provider']} - {config['llm']['model']}")
print(f"Environment: {config['environment']}")
```

### JavaScript

```javascript
const response = await fetch('http://localhost:8001/api/config', {
  headers: {
    'X-API-Key': 'your-api-key'
  }
});

const config = await response.json();
console.log(`Database: ${config.database.type}`);
console.log(`LLM: ${config.llm.provider} - ${config.llm.model}`);
```

## Pydantic Models

All input and output use Pydantic models for type safety and validation:

- `ConfigurationResponse` - Main response model
- `DatabaseConfig` - Database configuration
- `LLMConfig` - LLM service configuration
- `BackgroundProcessingConfig` - Background processing settings
- `APIServiceConfig` - API service settings

These models are defined in `/root/repo/models/config_response.py`.

## OpenAPI/Swagger Documentation

The endpoint is fully documented in the OpenAPI schema:

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## Security Considerations

- **API Key Protection**: The actual API key values are never returned (only boolean flags)
- **Database Passwords**: Database passwords are never exposed
- **Authentication**: Respects the same authentication as other endpoints
- **Read-Only**: This endpoint is read-only and cannot modify configuration

## Use Cases

1. **Debugging**: Verify configuration is correct after deployment
2. **Monitoring**: Check which services and databases are in use
3. **Documentation**: Auto-generate configuration documentation
4. **Health Checks**: Verify all required services are configured
5. **Support**: Help users troubleshoot configuration issues

## Related Endpoints

- `GET /api/health` - Service health status
- `GET /` - Root endpoint with API information
