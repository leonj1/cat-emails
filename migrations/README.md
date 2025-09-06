# Database Migrations

This directory contains database migration scripts for the Cat-Emails project. Migrations help manage schema changes and maintain database versioning across different environments.

## Structure

- `migrate.py` - Main migration runner utility
- `001_add_account_tracking.py` - Migration 001: Adds account tracking functionality
- `__init__.py` - Package initialization

## Usage

### Check Migration Status

```bash
# Show current migration status
python migrations/migrate.py --action status

# Verbose output
python migrations/migrate.py --action status --verbose
```

### Apply Migrations (Upgrade)

```bash
# Apply all pending migrations
python migrations/migrate.py --action upgrade

# Apply migrations up to a specific version
python migrations/migrate.py --action upgrade --target 001

# Use custom database path
python migrations/migrate.py --action upgrade --db-path /path/to/database.db
```

### Rollback Migrations (Downgrade)

```bash
# Rollback the latest migration
python migrations/migrate.py --action downgrade --target 000

# Rollback to a specific version
python migrations/migrate.py --action downgrade --target 001
```

### Running Individual Migrations

You can also run individual migration scripts directly:

```bash
# Apply migration 001
python migrations/001_add_account_tracking.py --action upgrade

# Rollback migration 001
python migrations/001_add_account_tracking.py --action downgrade

# Verbose output
python migrations/001_add_account_tracking.py --action upgrade --verbose
```

## Migration 001: Account Tracking

This migration adds multi-account support to the Cat-Emails project:

### New Tables Created

#### `email_accounts`
Tracks different email accounts being monitored:
- `id` - Primary key
- `email_address` - Unique email address (with index)
- `display_name` - Optional display name
- `created_at` - Account creation timestamp
- `updated_at` - Last update timestamp (auto-updated)
- `is_active` - Boolean flag for active accounts (with index)
- `last_scan_at` - Last scan timestamp

#### `account_category_stats`
Stores per-account category statistics:
- `id` - Primary key
- `account_id` - Foreign key to email_accounts
- `date` - Statistics date
- `category_name` - Email category name
- `email_count` - Total emails in category
- `deleted_count` - Number of deleted emails
- `archived_count` - Number of archived emails
- `kept_count` - Number of kept emails
- `created_at` - Record creation timestamp
- `updated_at` - Last update timestamp (auto-updated)

### Modified Tables

#### `email_summaries`
- Added `account_id` column as foreign key to email_accounts
- Added index on `account_id` for performance

### Indexes Created

- `email_accounts(email_address)` - Unique lookup
- `email_accounts(is_active)` - Active account filtering
- `account_category_stats(account_id, date)` - Account-date queries
- `account_category_stats(date, account_id)` - Date-account queries
- `account_category_stats(category_name)` - Category filtering
- `email_summaries(account_id)` - Summary lookup by account
- Unique constraint on `(account_id, date, category_name)` for account_category_stats

### Usage After Migration

After running this migration, the system will support multiple email accounts. The existing data in `email_summaries` will have `account_id` set to NULL initially, which can be updated to associate with specific accounts.

## Creating New Migrations

To create a new migration:

1. Create a new file with the naming pattern: `XXX_description.py` (where XXX is the next sequential number)
2. Include the following structure:

```python
#!/usr/bin/env python3
"""
Migration XXX: Description

Brief description of what this migration does.

Version: XXX
Created: YYYY-MM-DD
"""

def upgrade(db_path=None):
    """Apply the migration"""
    # Implementation here
    pass

def downgrade(db_path=None):
    """Rollback the migration"""  
    # Implementation here
    pass

def main():
    """Command line interface"""
    # Standard CLI implementation
    pass

if __name__ == '__main__':
    main()
```

3. Test the migration thoroughly:
   - Run upgrade and verify schema changes
   - Run downgrade and verify rollback
   - Test with different database states

## Best Practices

- Always test migrations on a copy of production data
- Make migrations reversible when possible
- Use transactions to ensure atomicity
- Add appropriate indexes for performance
- Document any manual steps required
- Backup database before running migrations in production

## Troubleshooting

### SQLite Limitations

SQLite has some limitations for schema changes:
- Cannot drop columns easily (requires table recreation)
- Cannot add foreign key constraints to existing tables
- Some ALTER TABLE operations are not supported

The migration scripts work around these limitations where possible, but some operations may require manual intervention.

### Migration Conflicts

If you encounter migration conflicts:
1. Check migration history: `python migrations/migrate.py --action status`
2. Manually resolve database state if needed
3. Update migration history table if required

### Rollback Issues

If a rollback fails:
1. Check the error logs
2. Manually inspect database state
3. Consider creating a new migration to fix issues rather than forcing rollback