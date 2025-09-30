# Gmail Credentials Setup Guide

This project now supports storing Gmail credentials in a SQLite database instead of relying solely on environment variables. This provides better security and flexibility for credential management.

## Quick Start

### 1. Store Credentials in Database

```bash
# Using command line arguments
python3 setup_credentials.py --email your-email@gmail.com --password your-app-password

# Using environment variables
GMAIL_EMAIL=your-email@gmail.com GMAIL_PASSWORD=your-app-password python3 setup_credentials.py
```

### 2. Verify Credentials Are Stored

```bash
python3 setup_credentials.py --list
```

### 3. Run the Application

The application will automatically use credentials from the database:

```bash
python3 gmail_fetcher.py --hours 2
```

## Credential Storage Options

The system supports two methods for storing credentials, with the following priority:

1. **SQLite Database** (Recommended) - Checked first
2. **Environment Variables** (Fallback) - Used if database is empty

### Method 1: SQLite Database (Recommended)

**Advantages:**
- Credentials persist across container restarts
- Easier to manage multiple accounts
- Can be updated without restarting the service
- More secure than environment variables

**Usage:**

```bash
# Store credentials
python3 setup_credentials.py \
  --email your-email@gmail.com \
  --password your-app-specific-password

# Custom database location
python3 setup_credentials.py \
  --email your-email@gmail.com \
  --password your-app-password \
  --db-path /custom/path/credentials.db

# List stored accounts
python3 setup_credentials.py --list

# Delete credentials
python3 setup_credentials.py --delete your-email@gmail.com
```

### Method 2: Environment Variables (Fallback)

If no credentials are found in the database, the system falls back to environment variables:

```bash
export GMAIL_EMAIL=your-email@gmail.com
export GMAIL_PASSWORD=your-app-password
export CONTROL_API_TOKEN=your-api-token

python3 gmail_fetcher.py
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CREDENTIALS_DB_PATH` | No | `./credentials.db` | Path to the credentials SQLite database |
| `GMAIL_EMAIL` | No* | - | Gmail email address (fallback if database is empty) |
| `GMAIL_PASSWORD` | No* | - | Gmail app-specific password (fallback) |
| `CONTROL_API_TOKEN` | Yes | - | API token for domain control service |
| `HOURS` | No | `2` | Hours to look back for emails |
| `SCAN_INTERVAL` | No | `2` | Minutes between scans (service mode) |

*Required only if credentials are not stored in the database.

## Docker Usage

### Option 1: Using Database (Recommended)

1. Set up credentials locally:
   ```bash
   python3 setup_credentials.py --email EMAIL --password PASSWORD
   ```

2. Mount the credentials database as a volume:
   ```bash
   docker run -v $(pwd)/credentials.db:/app/credentials.db \
     -e CONTROL_API_TOKEN=your-token \
     your-image-name
   ```

### Option 2: Using Environment Variables

```bash
docker run \
  -e GMAIL_EMAIL=your-email@gmail.com \
  -e GMAIL_PASSWORD=your-app-password \
  -e CONTROL_API_TOKEN=your-token \
  your-image-name
```

## Security Best Practices

1. **Use App-Specific Passwords**: Always use Gmail app-specific passwords, never your main account password
2. **Secure Database File**: Set appropriate file permissions on `credentials.db`:
   ```bash
   chmod 600 credentials.db
   ```
3. **Don't Commit Credentials**: Ensure `credentials.db` is in `.gitignore`
4. **Rotate Passwords Regularly**: Update credentials periodically
5. **Use Volume Mounts in Docker**: Mount the database as a volume for persistence

## Generating Gmail App-Specific Password

1. Enable 2-factor authentication on your Google account
2. Go to https://myaccount.google.com/apppasswords
3. Select "Mail" and the device you're using
4. Google will generate a 16-character password
5. Use this password (without spaces) when setting up credentials

## Troubleshooting

### Error: "Please provide GMAIL_EMAIL and GMAIL_PASSWORD"

This means credentials are not found in either the database or environment variables.

**Solution:**
```bash
# Store credentials in database
python3 setup_credentials.py --email EMAIL --password PASSWORD

# Or set environment variables
export GMAIL_EMAIL=your-email@gmail.com
export GMAIL_PASSWORD=your-app-password
```

### Error: "No credentials found"

The database exists but is empty.

**Solution:**
```bash
python3 setup_credentials.py --email EMAIL --password PASSWORD
```

### Database Permission Issues

**Solution:**
```bash
chmod 600 credentials.db
chown $USER:$USER credentials.db
```

### Multiple Accounts

The system currently uses the most recently updated credential. To specify a particular account:

1. Delete other credentials:
   ```bash
   python3 setup_credentials.py --delete old-email@gmail.com
   ```

2. Or modify `gmail_fetcher.py` to specify an email:
   ```python
   credentials = credentials_service.get_credentials("specific-email@gmail.com")
   ```

## API Reference

### CredentialsService

```python
from credentials_service import CredentialsService

# Initialize
service = CredentialsService(db_path="./credentials.db")

# Store credentials
service.store_credentials("email@gmail.com", "app-password")

# Retrieve credentials
email, password = service.get_credentials()

# Retrieve specific credentials
email, password = service.get_credentials("email@gmail.com")

# List all stored emails
emails = service.list_all_emails()

# Delete credentials
service.delete_credentials("email@gmail.com")
```

## Migration from Environment Variables

If you're currently using environment variables:

1. Store credentials in database:
   ```bash
   python3 setup_credentials.py \
     --email $GMAIL_EMAIL \
     --password $GMAIL_PASSWORD
   ```

2. Remove environment variables from your deployment (optional but recommended):
   ```bash
   unset GMAIL_EMAIL
   unset GMAIL_PASSWORD
   ```

3. The system will now use database credentials

## Database Schema

The credentials are stored in a SQLite database with the following schema:

```sql
CREATE TABLE gmail_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Testing

Run the test suite to verify the credentials system:

```bash
python3 -m unittest tests.test_credentials_service -v
```

All tests should pass, confirming that:
- Database creation works
- Credentials can be stored and retrieved
- Multiple accounts are supported
- Update and delete operations work
- Fallback to environment variables functions correctly