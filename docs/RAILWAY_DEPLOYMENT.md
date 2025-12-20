# Railway Deployment Guide

## Overview

This guide helps you deploy the Cat-Emails API to Railway and troubleshoot common deployment issues.

## Prerequisites

Before deploying to Railway, ensure you have:

1. A Railway account
2. Railway CLI installed (optional but recommended)
3. Required API keys ready

## Required Environment Variables

Set these environment variables in Railway dashboard:

### Essential Variables

- **`REQUESTYAI_API_KEY`** or **`OPENAI_API_KEY`** (Required)
  - API key for the LLM service used to categorize emails
  - **CRITICAL**: Service will immediately exit with error if not set
  - At least one of these keys must be provided
  - Get from: https://requestyai.com or https://platform.openai.com

- **`PORT`** (Automatically set by Railway)
  - Railway sets this automatically
  - Default: 8001 if not set

### Optional Variables

- **`API_KEY`** (Recommended for production)
  - Protects your API endpoints
  - If not set, endpoints are publicly accessible

- **`DATABASE_PATH`** (Optional)
  - Path for SQLite database
  - Default: `./email_summaries/summaries.db`
  - Recommend: `/app/data/summaries.db` for Railway

- **`BACKGROUND_PROCESSING`** (Optional)
  - Enable/disable background Gmail processing
  - Default: `true`
  - Set to `false` to disable

- **`BACKGROUND_SCAN_INTERVAL`** (Optional)
  - Interval in seconds between scans
  - Default: `300` (5 minutes)

- **`LLM_MODEL`** (Optional)
  - Model to use for email categorization
  - Default: `vertex/google/gemini-2.5-flash`
  - Examples: `gpt-4`, `gpt-3.5-turbo`, `vertex/google/gemini-2.5-flash`

- **`CONTROL_TOKEN`** (Optional)
  - Token for external Control API integration
  - Only needed if using domain blocking features

## Deployment Steps

### Option 1: Deploy from GitHub

1. Go to Railway dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will auto-detect the Dockerfile
6. Set environment variables in Railway dashboard
7. Deploy

### Option 2: Deploy using Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Link to existing project or create new one
railway link

# Set environment variables
railway variables set REQUESTYAI_API_KEY=your-key-here
railway variables set API_KEY=your-api-key-here

# Deploy
railway up
```

## Healthcheck Configuration

The service includes a health check endpoint at `/api/health`. Railway automatically checks this endpoint.

**Healthcheck settings in `railway.json`:**
```json
{
  "deploy": {
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 100
  }
}
```

## Troubleshooting

### 1. Healthcheck Failing (Service Unavailable)

**Symptoms:** Railway shows "Healthcheck failed!" during deployment

**Causes:**
- Missing `REQUESTYAI_API_KEY` or `OPENAI_API_KEY` - **Most Common**
- Database initialization failure
- Import errors in dependencies

**Solutions:**

1. **Check Railway logs** for startup errors:
   ```bash
   railway logs
   ```

2. **Look for the critical configuration error message:**
   ```
   ╔════════════════════════════════════════════════════════════════╗
   ║                  CRITICAL CONFIGURATION ERROR                   ║
   ╚════════════════════════════════════════════════════════════════╝

   Missing required environment variables:
     ✗ REQUESTYAI_API_KEY or OPENAI_API_KEY
   ```

   If you see this, the service is **intentionally exiting** because it cannot function without an LLM API key.

3. **Set the missing API key:**
   ```bash
   railway variables set REQUESTYAI_API_KEY your-key-here
   # OR
   railway variables set OPENAI_API_KEY your-key-here
   ```

4. **Verify environment variables** are set:
   ```bash
   railway variables
   ```

5. **After setting variables, look for these success messages:**
   ```
   ✓ All required environment variables are set
   === API Service Startup ===
   Environment configuration: {...}
   Testing database connection...
   Database connection successful
   === API Service Startup Complete ===
   ```

### 2. Database Errors

**Symptoms:** `Database error` or `Failed to create database directory`

**Solution:**
Set a Railway-friendly database path:
```bash
railway variables set DATABASE_PATH=/app/data/summaries.db
```

### 3. Service Starts But Healthcheck Times Out

**Symptoms:** Service logs show startup but healthcheck still fails

**Possible causes:**
- Service taking too long to initialize
- PORT environment variable mismatch

**Solutions:**

1. **Check if PORT is correct:**
   ```bash
   railway variables
   ```
   Railway automatically sets PORT - don't override it unless needed

2. **Increase healthcheck timeout** in `railway.json`:
   ```json
   {
     "deploy": {
       "healthcheckTimeout": 200
     }
   }
   ```

3. **Test health endpoint manually:**
   ```bash
   curl https://your-app.railway.app/api/health
   ```

### 4. Module Import Errors

**Symptoms:** `ModuleNotFoundError` or `ImportError` in logs

**Solution:**
The Dockerfile installs all requirements. If you see import errors:

1. Verify `requirements.txt` is up to date
2. Check if `ell-ai[all]` is being installed (included in Dockerfile)
3. Rebuild deployment:
   ```bash
   railway up --detach
   ```

### 5. Background Processing Not Working

**Symptoms:** API works but no emails are being processed

**Causes:**
- Missing Gmail credentials
- Background processing disabled

**Solutions:**

1. **Check if enabled:**
   ```bash
   railway variables get BACKGROUND_PROCESSING
   ```

2. **Ensure Gmail credentials are set** (if using background processing):
   ```bash
   railway variables set GMAIL_EMAIL=your-email@gmail.com
   railway variables set GMAIL_PASSWORD=your-app-password
   ```

## Viewing Logs

### Via Railway CLI
```bash
# View real-time logs
railway logs

# Follow logs
railway logs --follow
```

### Via Railway Dashboard
1. Go to your project
2. Click on "Deployments"
3. Click on the active deployment
4. View "Logs" tab

## Testing the Deployment

Once deployed, test these endpoints:

### 1. Health Check
```bash
curl https://your-app.railway.app/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-05T12:00:00",
  "service": "Cat Emails Summary API",
  "version": "1.1.0",
  "background_processor": {
    "enabled": true,
    "status": "running"
  },
  "database": "connected"
}
```

### 2. Root Endpoint
```bash
curl https://your-app.railway.app/
```

### 3. API Documentation
Open in browser:
```
https://your-app.railway.app/docs
```

## Performance Optimization

### 1. Database Persistence

Railway deployments are ephemeral. For production:

1. **Use Railway Volume** for database:
   ```bash
   railway volume create data
   railway variables set DATABASE_PATH=/app/data/summaries.db
   ```

2. **Or use external database:**
   - PostgreSQL: Add Railway PostgreSQL plugin
   - Update code to use PostgreSQL instead of SQLite

### 2. Resource Limits

Monitor usage in Railway dashboard. Upgrade plan if needed for:
- More CPU
- More memory
- Faster response times

## Environment Variables Summary

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REQUESTYAI_API_KEY` or `OPENAI_API_KEY` | ✅ Yes | None | LLM API key |
| `PORT` | Auto-set | 8001 | Server port |
| `API_KEY` | ⚠️ Recommended | None | API auth key |
| `DATABASE_PATH` | No | `./email_summaries/summaries.db` | Database file path |
| `BACKGROUND_PROCESSING` | No | `true` | Enable background processing |
| `BACKGROUND_SCAN_INTERVAL` | No | `300` | Scan interval (seconds) |
| `LLM_MODEL` | No | `vertex/google/gemini-2.5-flash` | LLM model name |
| `CONTROL_TOKEN` | No | Empty | External API token |
| `GMAIL_EMAIL` | No* | None | Gmail account (*required for processing) |
| `GMAIL_PASSWORD` | No* | None | Gmail app password (*required for processing) |

## Getting Help

If you encounter issues not covered here:

1. Check Railway logs for detailed error messages
2. Review this guide's troubleshooting section
3. Open an issue on GitHub with:
   - Railway deployment logs
   - Environment variables (redact sensitive values)
   - Error messages

## Useful Links

- [Railway Documentation](https://docs.railway.app)
- [Railway CLI Reference](https://docs.railway.app/develop/cli)
- [Cat-Emails API Documentation](./API_DOCUMENTATION.md)
- [Swagger UI](https://your-app.railway.app/docs)
