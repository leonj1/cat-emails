# Swagger/OpenAPI Documentation

The Cat Emails API includes comprehensive Swagger/OpenAPI documentation for easy API exploration and testing.

## Accessing Swagger Documentation

Once the API service is running, you can access the interactive documentation at:

### Swagger UI (Interactive)
```
http://localhost:8001/docs
```

**Features:**
- Interactive API explorer
- Try out endpoints directly from the browser
- View request/response schemas
- Test authentication
- See example values

### ReDoc (Documentation)
```
http://localhost:8001/redoc
```

**Features:**
- Clean, readable documentation format
- Better for printing or sharing
- Hierarchical navigation
- Code samples in multiple languages
- Search functionality

### OpenAPI JSON Schema
```
http://localhost:8001/openapi.json
```

**Features:**
- Raw OpenAPI 3.0 specification in JSON format
- Can be imported into API tools (Postman, Insomnia, etc.)
- Used by code generators and other tooling

## API Organization

The API endpoints are organized into the following categories:

### 🏥 Health
- `GET /` - Root endpoint with API information
- `GET /api/health` - Health check and service status

### 🔄 Background Processing
- `POST /api/background/start` - Start background Gmail processor
- `POST /api/background/stop` - Stop background Gmail processor
- `GET /api/background/status` - Get background processor status
- `GET /api/background/next-execution` - Get next scheduled execution time

### 📊 Processing Status
- `GET /api/processing/status` - Get current processing status
- `GET /api/processing/history` - Get recent processing history
- `GET /api/processing/statistics` - Get processing statistics
- `GET /api/processing/current-status` - Get comprehensive current status

### 📧 Summaries
- `POST /api/summaries/morning` - Trigger morning summary report
- `POST /api/summaries/evening` - Trigger evening summary report
- `POST /api/summaries/weekly` - Trigger weekly summary report
- `POST /api/summaries/monthly` - Trigger monthly summary report

### 👥 Accounts
- `GET /api/accounts` - List all tracked email accounts
- `POST /api/accounts` - Register a new email account
- `GET /api/accounts/{email_address}/categories/top` - Get top categories for an account
- `PUT /api/accounts/{email_address}/deactivate` - Deactivate an account
- `DELETE /api/accounts/{email_address}` - Delete an account

### 🧪 Testing
- `POST /api/test/create-sample-data` - Create sample data for testing

### 🔌 WebSocket
- `WS /ws/status` - Real-time processing status updates
- `WS /ws` - Alias for /ws/status

## Authentication

Most endpoints require authentication via the `X-API-Key` header when `API_KEY` environment variable is configured.

**Example:**
```bash
curl -H "X-API-Key: your-api-key-here" http://localhost:8001/api/health
```

**In Swagger UI:**
1. Click the "Authorize" button at the top
2. Enter your API key
3. Click "Authorize"
4. All subsequent requests will include the key

## Starting the API Server

```bash
# Start the API server
python api_service.py

# With custom port
export PORT=8080
python api_service.py

# With API key authentication
export API_KEY=your-secret-key
python api_service.py
```

## Testing Swagger Endpoints

Run the test script to verify all Swagger endpoints are accessible:

```bash
python test_swagger.py
```

## Using the OpenAPI Schema

### Import into Postman
1. Open Postman
2. Click "Import" → "Link"
3. Enter: `http://localhost:8001/openapi.json`
4. Click "Continue" → "Import"

### Import into Insomnia
1. Open Insomnia
2. Click "Create" → "Import From" → "URL"
3. Enter: `http://localhost:8001/openapi.json`
4. Click "Fetch and Import"

### Generate Client Code
```bash
# Install OpenAPI Generator
npm install -g @openapitools/openapi-generator-cli

# Generate Python client
openapi-generator-cli generate \
  -i http://localhost:8001/openapi.json \
  -g python \
  -o ./client-python

# Generate TypeScript/JavaScript client
openapi-generator-cli generate \
  -i http://localhost:8001/openapi.json \
  -g typescript-fetch \
  -o ./client-typescript
```

## API Metadata

The API includes the following metadata in the OpenAPI specification:

- **Title**: Cat Emails API
- **Version**: 1.1.0
- **Description**: AI-powered Gmail email categorizer API
- **Contact**: Terragon Labs
- **License**: MIT
- **Tags**: Organized by functional area (health, accounts, summaries, etc.)

## Example Usage

### Using curl with Swagger-generated examples

```bash
# Get API health
curl http://localhost:8001/api/health

# List all accounts (with auth)
curl -H "X-API-Key: your-key" http://localhost:8001/api/accounts

# Get top categories for an account
curl -H "X-API-Key: your-key" \
  "http://localhost:8001/api/accounts/user@example.com/categories/top?days=30&limit=10"

# Trigger morning summary
curl -X POST -H "X-API-Key: your-key" \
  http://localhost:8001/api/summaries/morning
```

### Using Python requests

```python
import requests

base_url = "http://localhost:8001"
headers = {"X-API-Key": "your-api-key"}

# Get health status
response = requests.get(f"{base_url}/api/health")
print(response.json())

# List accounts
response = requests.get(f"{base_url}/api/accounts", headers=headers)
accounts = response.json()
print(f"Total accounts: {accounts['total_count']}")

# Get top categories
response = requests.get(
    f"{base_url}/api/accounts/user@example.com/categories/top",
    params={"days": 30, "limit": 10},
    headers=headers
)
categories = response.json()
for cat in categories['top_categories']:
    print(f"{cat['category']}: {cat['email_count']} emails")
```

## WebSocket Example

```javascript
// Connect to WebSocket for real-time updates
const ws = new WebSocket('ws://localhost:8001/ws/status?api_key=your-key');

ws.onopen = () => {
    console.log('Connected to status updates');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Status update:', data);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};
```

## Response Models

All endpoints use Pydantic models for request/response validation. The Swagger UI shows:

- **Request schemas**: What data to send in POST/PUT requests
- **Response schemas**: What data you'll receive back
- **Query parameters**: Available filters and options
- **Path parameters**: Required URL variables
- **Headers**: Authentication and other headers

## Troubleshooting

### Swagger UI not loading
- Ensure the API server is running: `python api_service.py`
- Check the server is accessible: `curl http://localhost:8001/api/health`
- Verify the port matches your configuration (default: 8001)

### Authentication errors
- Set the `X-API-Key` header or use the "Authorize" button in Swagger UI
- Verify your API key matches the server's `API_KEY` environment variable
- If no authentication is needed, ensure `API_KEY` is not set

### CORS errors
- The API includes CORS middleware configured for common origins
- Add your frontend origin to the `origins` list in `api_service.py`

## Additional Resources

- [OpenAPI Specification](https://swagger.io/specification/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Swagger UI Documentation](https://swagger.io/tools/swagger-ui/)
- [ReDoc Documentation](https://redocly.com/redoc/)
