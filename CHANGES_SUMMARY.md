# Changes Summary: SQLite Credentials Storage

## Overview

Updated the Cat-Emails project to retrieve Gmail credentials from a SQLite database instead of requiring environment variables. The system maintains backward compatibility by falling back to environment variables if the database is empty.

## Problem Solved

**Original Error:**
```
ValueError: Please set GMAIL_EMAIL and GMAIL_PASSWORD environment variables
```

**Root Cause:** The application required `GMAIL_EMAIL` and `GMAIL_PASSWORD` environment variables to be set, but they were not available in the container environment.

**Solution:** Implemented a SQLite-based credentials storage system that:
1. Stores credentials persistently in a database
2. Retrieves credentials automatically at runtime
3. Falls back to environment variables if database is empty
4. Maintains backward compatibility with existing deployments

## Files Created

### 1. `credentials_service.py` (NEW)
- Core module for managing Gmail credentials in SQLite
- Provides methods to store, retrieve, update, and delete credentials
- Automatically creates database and schema on first use

**Key Methods:**
- `store_credentials(email, password)` - Store or update credentials
- `get_credentials(email=None)` - Retrieve credentials
- `delete_credentials(email)` - Delete credentials
- `list_all_emails()` - List all stored email addresses

### 2. `setup_credentials.py` (NEW)
- Command-line utility for managing credentials
- Supports storing, listing, and deleting credentials
- Can use command-line arguments or environment variables

**Usage:**
```bash
python3 setup_credentials.py --email EMAIL --password PASSWORD
python3 setup_credentials.py --list
python3 setup_credentials.py --delete EMAIL
```

### 3. `tests/test_credentials_service.py` (NEW)
- Comprehensive test suite for credentials service
- Tests database operations, credential management, and integration
- All 13 tests passing

**Test Coverage:**
- Database creation and initialization
- Credential storage and retrieval
- Multiple account management
- Update and delete operations
- Integration with gmail_fetcher.py
- Fallback to environment variables

### 4. `test_integration.py` (NEW)
- End-to-end integration test
- Demonstrates complete workflow
- Verifies both database and fallback mechanisms

### 5. `CREDENTIALS_SETUP.md` (NEW)
- Comprehensive documentation for credential management
- Includes setup instructions, usage examples, and troubleshooting
- Docker deployment guide
- Security best practices

### 6. `CHANGES_SUMMARY.md` (NEW - this file)
- Summary of all changes made
- Migration guide for existing deployments

## Files Modified

### 1. `gmail_fetcher.py`
**Changes:**
- Added import: `from credentials_service import CredentialsService`
- Modified `__main__` block to check SQLite database first
- Falls back to environment variables if database is empty
- Better error messages indicating both credential sources

**Before:**
```python
email_address = os.getenv("GMAIL_EMAIL")
app_password = os.getenv("GMAIL_PASSWORD")

if not email_address or not app_password:
    raise ValueError("Please set GMAIL_EMAIL and GMAIL_PASSWORD environment variables")
```

**After:**
```python
credentials_service = CredentialsService()
credentials = credentials_service.get_credentials()

if credentials:
    email_address, app_password = credentials
    logger.info("Using Gmail credentials from SQLite database")
else:
    email_address = os.getenv("GMAIL_EMAIL")
    app_password = os.getenv("GMAIL_PASSWORD")

    if email_address and app_password:
        logger.info("Using Gmail credentials from environment variables")
    else:
        raise ValueError("Please provide GMAIL_EMAIL and GMAIL_PASSWORD either in SQLite database or as environment variables")
```

### 2. `gmail_fetcher_service.py`
**Changes:**
- Added import: `from credentials_service import CredentialsService`
- Modified credential retrieval to check database first
- Maintains service mode functionality with new credential system

### 3. `Dockerfile`
**Changes:**
- Added `credentials_service.py` to COPY instruction
- Added `CREDENTIALS_DB_PATH` environment variable
- Maintains existing environment variable structure for backward compatibility

**Modified Line:**
```dockerfile
COPY gmail_fetcher.py domain_service.py remote_sqlite_helper.py credentials_service.py ./
ENV CREDENTIALS_DB_PATH="/app/credentials.db"
```

### 4. `CLAUDE.md`
**Changes:**
- Updated Core Components section to include `credentials_service.py`
- Added comprehensive Gmail Credentials section
- Documented both SQLite and environment variable options
- Updated configuration examples

### 5. `.gitignore`
**Changes:**
- Added `credentials.db` to prevent committing sensitive data
- Added `*.db` pattern for all database files
- Added `*.log` pattern for log files

## Database Schema

```sql
CREATE TABLE gmail_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Migration Guide

### For Existing Deployments Using Environment Variables

**Option 1: Continue Using Environment Variables (No Change Required)**
- The system automatically falls back to environment variables
- No action needed if you want to keep using env vars

**Option 2: Migrate to SQLite Database (Recommended)**

1. Store your existing credentials in the database:
   ```bash
   python3 setup_credentials.py \
     --email $GMAIL_EMAIL \
     --password $GMAIL_PASSWORD
   ```

2. (Optional) Remove environment variables from your deployment:
   ```bash
   unset GMAIL_EMAIL
   unset GMAIL_PASSWORD
   ```

3. For Docker, mount the database as a volume:
   ```bash
   docker run -v $(pwd)/credentials.db:/app/credentials.db \
     -e CONTROL_API_TOKEN=your-token \
     your-image-name
   ```

### For New Deployments

1. Set up credentials:
   ```bash
   python3 setup_credentials.py --email EMAIL --password PASSWORD
   ```

2. Run the application:
   ```bash
   python3 gmail_fetcher.py
   ```

## Testing

All tests passing:

```bash
$ python3 -m unittest tests.test_credentials_service -v
Ran 13 tests in 0.071s
OK

$ python3 test_integration.py
✓ All integration tests passed!
```

## Benefits

1. **Persistence**: Credentials survive container restarts
2. **Security**: Database file can be secured with file permissions
3. **Flexibility**: Easy to update credentials without redeploying
4. **Multi-account**: Support for multiple Gmail accounts
5. **Backward Compatibility**: Existing deployments continue to work
6. **Better UX**: Clear error messages and setup utilities

## Security Considerations

1. **File Permissions**: Set `chmod 600 credentials.db` for security
2. **Version Control**: Database files are excluded via `.gitignore`
3. **App-Specific Passwords**: Always use Gmail app-specific passwords
4. **Volume Mounts**: Use Docker volumes for persistent credential storage

## Environment Variables

### New Variables
- `CREDENTIALS_DB_PATH` - Path to credentials database (default: `./credentials.db`)

### Existing Variables (Still Supported)
- `GMAIL_EMAIL` - Gmail email (fallback if database is empty)
- `GMAIL_PASSWORD` - Gmail app password (fallback if database is empty)
- `CONTROL_API_TOKEN` - Still required
- `HOURS` - Still supported
- `SCAN_INTERVAL` - Still supported
- `OLLAMA_HOST` - Still supported

## Future Enhancements

Potential improvements for future versions:
1. Password encryption at rest
2. Multiple account selection via command-line argument
3. Credential rotation notifications
4. Integration with secret management systems (HashiCorp Vault, AWS Secrets Manager)
5. Web UI for credential management

## Support

For issues or questions:
1. Check `CREDENTIALS_SETUP.md` for detailed usage instructions
2. Run integration tests: `python3 test_integration.py`
3. Review test suite: `python3 -m unittest tests.test_credentials_service -v`
4. Check logs for credential source being used