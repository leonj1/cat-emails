# Railway Deployment Guide

## Configuration Files

This project includes Railway.app deployment configurations:
- `railway.json` (JSON format)
- `railway.toml` (TOML format)

Both files provide the same configuration. Choose one based on your preference.

## Required Environment Variables

Set these in your Railway project settings before deploying:

### Required
- `GMAIL_EMAIL` - Your Gmail email address
- `GMAIL_PASSWORD` - Gmail app-specific password (NOT your regular password)
- `CONTROL_API_TOKEN` - API token for the Control API

### Optional
- `HOURS` - Number of hours to look back for emails (default: 2)
- `SQLITE_URL` - Remote SQLite database URL for ell-ai storage
- `CREDENTIALS_DB_PATH` - Path to credentials database (default: /app/credentials.db)
- `SCAN_INTERVAL` - Minutes between scans in service mode (default: 2)
- `OLLAMA_HOST` - Custom Ollama server URL (default: http://localhost:11434)

## Deployment Configuration

### Build Settings
- **Builder**: DOCKERFILE
- **Dockerfile**: `Dockerfile` (root level)

### Deploy Settings
- **Start Command**: `python gmail_fetcher.py --hours ${HOURS:-2}`
- **Restart Policy**: ON_FAILURE (restarts only on failure)
- **Healthcheck Timeout**: 300 seconds

## Setup Instructions

1. **Create a new Railway project**
   ```bash
   railway login
   railway init
   ```

2. **Add environment variables**
   - Go to your Railway project dashboard
   - Navigate to Variables section
   - Add all required environment variables listed above

3. **Deploy**
   ```bash
   railway up
   ```

   Or connect your GitHub repository to Railway for automatic deployments.

4. **Alternative: Service Mode**

   If you want continuous scanning instead of one-time runs, you can:
   - Use `Dockerfile.service` instead
   - Update `railway.json` to use `dockerfilePath = "Dockerfile.service"`
   - Set `SCAN_INTERVAL` environment variable for scan frequency

## Gmail Setup

1. Enable 2-factor authentication in Gmail
2. Generate an app-specific password at https://myaccount.google.com/apppasswords
3. Use this app password for `GMAIL_PASSWORD` environment variable

## Monitoring

Railway provides:
- Real-time logs in the dashboard
- Deployment status
- Resource usage metrics
- Automatic restarts on failure

## Troubleshooting

### Build Failures
- Check that all dependencies in `requirements.txt` are available
- Verify Python 3.11 compatibility

### Runtime Errors
- Verify all required environment variables are set
- Check Gmail credentials are valid
- Ensure CONTROL_API_TOKEN has proper permissions
- Review Railway logs for detailed error messages

### Connection Issues
- Verify IMAP access is enabled for your Gmail account
- Check that app-specific password is correct (not regular password)
- Ensure Control API endpoint is accessible from Railway