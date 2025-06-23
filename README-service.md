# Gmail Fetcher Service

This is a containerized service version of the Gmail Fetcher that runs continuously, processing emails at regular intervals.

## Building the Service

```bash
docker build -f Dockerfile.service -t gmail-fetcher-service .
```

## Running the Service

### Using Docker Run

```bash
docker run -d \
  --name gmail-fetcher-service \
  -e GMAIL_EMAIL="your-email@gmail.com" \
  -e GMAIL_PASSWORD="your-app-password" \
  -e CONTROL_API_TOKEN="your-api-token" \
  -e HOURS=2 \
  -e SCAN_INTERVAL=2 \
  gmail-fetcher-service
```

### Using Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  gmail-fetcher:
    build:
      context: .
      dockerfile: Dockerfile.service
    image: gmail-fetcher-service
    container_name: gmail-fetcher-service
    environment:
      - GMAIL_EMAIL=${GMAIL_EMAIL}
      - GMAIL_PASSWORD=${GMAIL_PASSWORD}
      - CONTROL_API_TOKEN=${CONTROL_API_TOKEN}
      - HOURS=${HOURS:-2}
      - SCAN_INTERVAL=${SCAN_INTERVAL:-2}
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Then run:
```bash
docker-compose up -d
```

## Environment Variables

- `GMAIL_EMAIL`: Your Gmail email address (required)
- `GMAIL_PASSWORD`: Your Gmail app-specific password (required)
- `CONTROL_API_TOKEN`: API token for the control service (required)
- `HOURS`: Number of hours to look back for emails (default: 2)
- `SCAN_INTERVAL`: Minutes between email scans (default: 2)

## Monitoring the Service

### View Logs
```bash
docker logs -f gmail-fetcher-service
```

### Check Service Health
```bash
docker ps
docker inspect gmail-fetcher-service --format='{{.State.Health.Status}}'
```

### Stop the Service
```bash
docker stop gmail-fetcher-service
```

## Service Features

- **Continuous Operation**: Runs indefinitely, scanning emails every SCAN_INTERVAL minutes
- **Error Recovery**: Continues running even if individual scan cycles fail
- **Graceful Shutdown**: Responds to SIGTERM and SIGINT signals for clean container stops
- **Health Checks**: Built-in Docker health check to monitor service status
- **Structured Logging**: Clear logs showing scan cycles, errors, and next run times

## Example Log Output

```
2024-01-15 10:00:00,123 - __main__ - INFO - Gmail Fetcher Service starting...
2024-01-15 10:00:00,124 - __main__ - INFO - Configuration:
2024-01-15 10:00:00,124 - __main__ - INFO -   - Email: user@gmail.com
2024-01-15 10:00:00,124 - __main__ - INFO -   - Hours to scan: 2
2024-01-15 10:00:00,124 - __main__ - INFO -   - Scan interval: 2 minutes
2024-01-15 10:00:00,125 - __main__ - INFO - Starting scan cycle #1
2024-01-15 10:00:15,234 - __main__ - INFO - Scan cycle #1 completed successfully in 15.11 seconds
2024-01-15 10:00:15,235 - __main__ - INFO - Next scan will run in 2 minutes at approximately 2024-01-15 10:02:15
```