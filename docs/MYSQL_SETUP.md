# MySQL Database Setup Guide

This guide shows how to configure the Cat-Emails application to use MySQL instead of SQLite.

## Benefits of Using MySQL

- **Cloud-hosted databases**: Use managed MySQL services (AWS RDS, Google Cloud SQL, Azure Database)
- **Better concurrency**: Handle multiple concurrent connections more efficiently
- **Scalability**: Better performance for large datasets
- **Data persistence**: Centralized database accessible from multiple application instances
- **Replication**: Built-in support for master-slave replication and high availability

## Installation

### 1. Install MySQL Dependencies

The MySQL dependencies are already listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

This installs:
- `pymysql>=1.1.0` - Pure Python MySQL driver
- `cryptography>=41.0.0` - Required for secure MySQL connections

### 2. Set Up MySQL Database

#### Option A: Local MySQL Server

Install MySQL on your local machine:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install mysql-server

# macOS (using Homebrew)
brew install mysql
brew services start mysql

# Windows
# Download and install from https://dev.mysql.com/downloads/installer/
```

Create database and user:

```bash
# Connect to MySQL as root
mysql -u root -p

# Create database
CREATE DATABASE cat_emails CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Create user and grant permissions
CREATE USER 'cat_emails_user'@'localhost' IDENTIFIED BY 'your-secure-password';
GRANT ALL PRIVILEGES ON cat_emails.* TO 'cat_emails_user'@'localhost';
FLUSH PRIVILEGES;

EXIT;
```

#### Option B: Cloud-Hosted MySQL (AWS RDS Example)

1. Create an RDS MySQL instance in AWS Console
2. Choose MySQL 8.0 or later
3. Configure security group to allow connections from your application
4. Note the endpoint, port, database name, username, and password

#### Option C: Docker MySQL

```bash
docker run -d \
  --name cat-emails-mysql \
  -e MYSQL_DATABASE=cat_emails \
  -e MYSQL_USER=cat_emails_user \
  -e MYSQL_PASSWORD=your-secure-password \
  -e MYSQL_ROOT_PASSWORD=root-password \
  -p 3306:3306 \
  mysql:8.0
```

## Configuration

### Environment Variables

Set these environment variables in your `.env` file:

#### Method 1: Individual Parameters (Recommended)

```bash
# MySQL connection parameters
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=cat_emails
MYSQL_USER=cat_emails_user
MYSQL_PASSWORD=your-secure-password

# Optional: Connection pool settings
MYSQL_POOL_SIZE=5
MYSQL_MAX_OVERFLOW=10
MYSQL_POOL_RECYCLE=3600
```

#### Method 2: Connection String

```bash
# Full MySQL connection URL
MYSQL_URL=mysql+pymysql://cat_emails_user:your-secure-password@localhost:3306/cat_emails

# OR using DATABASE_URL (alternative name)
DATABASE_URL=mysql+pymysql://cat_emails_user:your-secure-password@localhost:3306/cat_emails
```

**Note**: When using MySQL, do NOT set `DATABASE_PATH` - this is for SQLite only.

### Cloud MySQL Examples

#### AWS RDS

```bash
MYSQL_HOST=cat-emails.abc123.us-east-1.rds.amazonaws.com
MYSQL_PORT=3306
MYSQL_DATABASE=cat_emails
MYSQL_USER=admin
MYSQL_PASSWORD=your-rds-password
```

#### Google Cloud SQL

```bash
MYSQL_HOST=34.123.45.67  # Public IP of Cloud SQL instance
MYSQL_PORT=3306
MYSQL_DATABASE=cat_emails
MYSQL_USER=cat_emails_user
MYSQL_PASSWORD=your-cloud-sql-password

# OR use Cloud SQL Proxy connection string
MYSQL_URL=mysql+pymysql://user:pass@/cat_emails?unix_socket=/cloudsql/project:region:instance
```

#### Azure Database for MySQL

```bash
MYSQL_HOST=cat-emails.mysql.database.azure.com
MYSQL_PORT=3306
MYSQL_DATABASE=cat_emails
MYSQL_USER=cat_emails_user@cat-emails
MYSQL_PASSWORD=your-azure-password
```

## Code Integration

### Using MySQL Repository in Your Code

The application services automatically use the repository pattern. To switch to MySQL:

#### Option 1: Use Environment Variables (Recommended)

Just set the MySQL environment variables as shown above. The services will detect them:

```python
from services.database_service import DatabaseService

# This will automatically use MySQL if MYSQL_HOST/MYSQL_URL is set
db_service = DatabaseService()
```

#### Option 2: Explicit MySQL Repository

```python
from repositories.mysql_repository import MySQLRepository
from services.database_service import DatabaseService

# Create MySQL repository explicitly
mysql_repo = MySQLRepository(
    host='localhost',
    port=3306,
    database='cat_emails',
    username='cat_emails_user',
    password='your-password'
)

# Inject into service
db_service = DatabaseService(repository=mysql_repo)
```

#### Option 3: Using Connection String

```python
from repositories.mysql_repository import MySQLRepository

# Using connection string
mysql_repo = MySQLRepository(
    connection_string='mysql+pymysql://user:pass@host:3306/dbname'
)
```

### Example: Complete Service Setup

```python
from repositories.mysql_repository import MySQLRepository
from services.database_service import DatabaseService
from services.settings_service import SettingsService
from clients.account_category_client import AccountCategoryClient

# Create shared MySQL repository
mysql_repo = MySQLRepository()  # Uses env vars

# Inject into all services
db_service = DatabaseService(repository=mysql_repo)
settings_service = SettingsService(repository=mysql_repo)
account_client = AccountCategoryClient(repository=mysql_repo)
```

## Database Migration

### Migrating from SQLite to MySQL

If you have existing data in SQLite and want to migrate to MySQL:

#### 1. Export SQLite Data

```bash
# Export to SQL dump
sqlite3 ./email_summaries/summaries.db .dump > sqlite_dump.sql
```

#### 2. Convert and Import to MySQL

```bash
# Clean up SQLite-specific syntax
sed -i 's/AUTOINCREMENT/AUTO_INCREMENT/g' sqlite_dump.sql
sed -i '/^PRAGMA/d' sqlite_dump.sql
sed -i '/^BEGIN TRANSACTION/d' sqlite_dump.sql
sed -i '/^COMMIT/d' sqlite_dump.sql

# Import to MySQL
mysql -u cat_emails_user -p cat_emails < sqlite_dump.sql
```

#### 3. Alternative: Use a Migration Tool

```bash
pip install sqlalchemy-utils

# Python script to copy data
python migrate_sqlite_to_mysql.py
```

Example migration script:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Source: SQLite
sqlite_engine = create_engine('sqlite:///./email_summaries/summaries.db')
SQLiteSession = sessionmaker(bind=sqlite_engine)

# Destination: MySQL
mysql_engine = create_engine('mysql+pymysql://user:pass@localhost/cat_emails')
MySQLSession = sessionmaker(bind=mysql_engine)

# Create tables in MySQL
from models.database import Base
Base.metadata.create_all(mysql_engine)

# Copy data (implement based on your needs)
# ...
```

## Testing the Connection

### Test MySQL Connectivity

```python
from repositories.mysql_repository import MySQLRepository

try:
    repo = MySQLRepository(
        host='localhost',
        database='cat_emails',
        username='cat_emails_user',
        password='your-password'
    )
    
    if repo.is_connected():
        print("✅ Successfully connected to MySQL!")
        
        # Test a simple operation
        settings = repo.get_all_settings()
        print(f"Found {len(settings)} settings in database")
    else:
        print("❌ Not connected to MySQL")
        
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

### Verify Database Tables

```bash
mysql -u cat_emails_user -p cat_emails

# List all tables
SHOW TABLES;

# Check a specific table structure
DESCRIBE email_accounts;
DESCRIBE processing_runs;
```

## Connection Pool Configuration

MySQL repository uses connection pooling for better performance:

```bash
# Pool size: Number of connections to maintain
MYSQL_POOL_SIZE=5

# Max overflow: Additional connections allowed beyond pool_size
MYSQL_MAX_OVERFLOW=10

# Pool recycle: Recycle connections after this many seconds (prevents timeout)
MYSQL_POOL_RECYCLE=3600
```

**Recommendations:**
- Small apps: `POOL_SIZE=5, MAX_OVERFLOW=10`
- Medium apps: `POOL_SIZE=10, MAX_OVERFLOW=20`
- Large apps: `POOL_SIZE=20, MAX_OVERFLOW=30`

## Troubleshooting

### Connection Refused

```bash
# Check if MySQL is running
sudo systemctl status mysql  # Linux
brew services list  # macOS

# Verify MySQL is listening
netstat -an | grep 3306
```

### Authentication Failed

```bash
# Reset MySQL user password
mysql -u root -p
ALTER USER 'cat_emails_user'@'localhost' IDENTIFIED BY 'new-password';
FLUSH PRIVILEGES;
```

### Character Encoding Issues

Ensure your database uses UTF-8:

```sql
ALTER DATABASE cat_emails CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Firewall/Security Groups

For cloud-hosted MySQL, ensure:
- Security group allows inbound TCP on port 3306
- Your IP is whitelisted
- SSL/TLS is configured if required

### Connection Timeout

Increase pool recycle time:

```bash
MYSQL_POOL_RECYCLE=7200  # 2 hours
```

## Performance Optimization

### Indexes

The repository automatically creates tables with indexes, but you can add more:

```sql
-- Index for faster email lookups
CREATE INDEX idx_processed_emails_date ON processed_email_log(processed_at);

-- Index for account queries
CREATE INDEX idx_email_summaries_account_date ON email_summaries(account_id, date);
```

### Query Optimization

Enable slow query log to identify performance issues:

```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;  -- Log queries taking > 2 seconds
```

## Security Best Practices

1. **Use strong passwords**: Generate random passwords for database users
2. **Limit privileges**: Grant only necessary permissions
3. **Use SSL/TLS**: Enable encrypted connections for production
4. **Network isolation**: Use private networks/VPCs for cloud databases
5. **Regular backups**: Set up automated backups
6. **Monitor access**: Enable audit logging

## Switching Back to SQLite

To switch back to SQLite:

1. Comment out MySQL environment variables
2. Set `DATABASE_PATH` in `.env`
3. Restart the application

```bash
# .env
DATABASE_PATH=./email_summaries/summaries.db
# MYSQL_HOST=localhost  # Commented out
# MYSQL_DATABASE=cat_emails  # Commented out
```

The application will automatically use SQLite when `DATABASE_PATH` is set.
