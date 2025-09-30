# Quick Start Guide - Gmail Credentials Setup

## TL;DR

```bash
# Setup credentials
python3 setup_credentials.py --email your@gmail.com --password your-app-password

# Verify
python3 setup_credentials.py --list

# Run
python3 gmail_fetcher.py
```

## Step-by-Step Setup

### 1. Get Gmail App-Specific Password

1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and your device
3. Copy the 16-character password

### 2. Store Credentials

**Option A: Interactive Setup**
```bash
./setup_production_credentials.sh
```

**Option B: Command Line**
```bash
python3 setup_credentials.py \
  --email your-email@gmail.com \
  --password your-app-password
```

**Option C: Environment Variables**
```bash
export GMAIL_EMAIL=your-email@gmail.com
export GMAIL_PASSWORD=your-app-password
python3 setup_credentials.py
```

### 3. Verify Setup

```bash
# List stored credentials
python3 setup_credentials.py --list

# Run integration test
python3 test_integration.py

# Run unit tests
python3 -m unittest tests.test_credentials_service -v
```

### 4. Run Application

```bash
# Set required API token
export CONTROL_API_TOKEN=your-api-token

# Run email fetcher
python3 gmail_fetcher.py --hours 2

# Or run as a service
python3 gmail_fetcher_service.py
```

## Docker Usage

### Build Image

```bash
docker build -t cat-emails .
```

### Run with Database Volume

```bash
# First, set up credentials locally
python3 setup_credentials.py --email EMAIL --password PASSWORD

# Run container with database mounted
docker run -v $(pwd)/credentials.db:/app/credentials.db \
  -e CONTROL_API_TOKEN=your-token \
  cat-emails
```

### Run with Environment Variables (Fallback)

```bash
docker run \
  -e GMAIL_EMAIL=your@gmail.com \
  -e GMAIL_PASSWORD=your-app-password \
  -e CONTROL_API_TOKEN=your-token \
  cat-emails
```

## Common Commands

```bash
# Store credentials
python3 setup_credentials.py --email EMAIL --password PASSWORD

# List stored accounts
python3 setup_credentials.py --list

# Delete credentials
python3 setup_credentials.py --delete EMAIL

# Custom database location
python3 setup_credentials.py --email EMAIL --password PASSWORD --db-path /path/to/db

# Run tests
python3 -m unittest tests.test_credentials_service -v

# Run integration test
python3 test_integration.py
```

## Troubleshooting

### "No credentials found"

```bash
# Solution: Store credentials
python3 setup_credentials.py --email EMAIL --password PASSWORD
```

### "Please set CONTROL_API_TOKEN"

```bash
# Solution: Set API token
export CONTROL_API_TOKEN=your-api-token
```

### Docker container fails with credential error

```bash
# Solution 1: Mount database
docker run -v $(pwd)/credentials.db:/app/credentials.db ...

# Solution 2: Use environment variables
docker run -e GMAIL_EMAIL=... -e GMAIL_PASSWORD=... ...
```

### Permission denied on credentials.db

```bash
# Solution: Fix permissions
chmod 600 credentials.db
chown $USER:$USER credentials.db
```

## Security

```bash
# Secure the database file
chmod 600 credentials.db

# Verify it's not committed
git status  # Should not show credentials.db

# Check .gitignore includes it
grep credentials.db .gitignore
```

## Migration from Environment Variables

```bash
# Store existing env vars in database
python3 setup_credentials.py \
  --email $GMAIL_EMAIL \
  --password $GMAIL_PASSWORD

# Remove env vars (optional)
unset GMAIL_EMAIL
unset GMAIL_PASSWORD

# Application will now use database
python3 gmail_fetcher.py
```

## Documentation

- **Full Setup Guide**: `CREDENTIALS_SETUP.md`
- **Changes Summary**: `CHANGES_SUMMARY.md`
- **Project Documentation**: `CLAUDE.md`

## Support

Run the integration test to verify everything works:

```bash
python3 test_integration.py
```

Expected output:
```
✓ All integration tests passed!
```