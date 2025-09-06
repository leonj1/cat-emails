# Cat-Emails Scripts

This directory contains utility scripts for managing and migrating Cat-Emails data.

## backfill_account_data.py

**Purpose**: Migrates existing email_summaries data to work with the new account tracking system.

### What it does:

1. **Account Discovery**: Finds email accounts from environment variables and existing database records
2. **Account Creation**: Creates EmailAccount records for discovered email addresses  
3. **Summary Linking**: Updates existing email_summaries to populate the account_id field
4. **Category Stats Generation**: Creates AccountCategoryStats records from historical CategorySummary data

### Usage Examples:

```bash
# Dry run to see what would be changed (recommended first step)
python3 scripts/backfill_account_data.py --dry-run

# Run migration with verbose output
python3 scripts/backfill_account_data.py --verbose

# Run migration with specific email account
python3 scripts/backfill_account_data.py --email user@gmail.com

# Run with custom database location
python3 scripts/backfill_account_data.py --database ./custom/path/summaries.db

# Combine options
python3 scripts/backfill_account_data.py --email user@gmail.com --verbose --dry-run
```

### Safety Features:

- **Dry Run Mode**: Shows what changes would be made without actually making them
- **Transaction Safety**: Uses database transactions with rollback on errors
- **Idempotent**: Can be run multiple times safely (skips already processed data)
- **Validation**: Verifies data integrity before and after migration
- **Comprehensive Logging**: Detailed progress reporting and error handling

### Account Discovery:

The script discovers accounts in this order:
1. Command line `--email` parameter (highest priority)
2. `GMAIL_EMAIL` environment variable
3. `SUMMARY_RECIPIENT_EMAIL` environment variable  
4. Existing EmailAccount records in the database

### Migration Process:

1. **Discovery**: Find unique email accounts
2. **Account Creation**: Create EmailAccount records for new accounts
3. **Summary Linking**: Update email_summaries.account_id for existing summaries
4. **Category Stats**: Generate AccountCategoryStats from existing CategorySummary data
5. **Validation**: Verify all data was migrated correctly

### Requirements:

- Existing SQLite database with email_summaries data
- Python 3.8+ with required dependencies
- Proper file permissions to read/write database

### Error Handling:

- Database connection failures are caught and reported
- Integrity constraint violations trigger rollback
- Validation failures prevent commit
- All errors include detailed logging for debugging

### Post-Migration:

After successful migration:
- All email_summaries will have account_id populated
- New AccountCategoryStats records will be available for API queries
- EmailAccount records will be available for multi-account support
- Data integrity is validated automatically