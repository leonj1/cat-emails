-- Flyway migration V7: Fix missing OAuth columns in email_accounts table
-- V5 migration used DELIMITER-based stored procedures which don't work reliably with Flyway
-- This migration uses simple ALTER TABLE with IF NOT EXISTS checks via column count

-- Add auth_method column if missing
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'email_accounts'
    AND COLUMN_NAME = 'auth_method');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE email_accounts ADD COLUMN auth_method VARCHAR(20) DEFAULT ''imap''',
    'SELECT ''auth_method column already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add oauth_client_id column if missing
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'email_accounts'
    AND COLUMN_NAME = 'oauth_client_id');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE email_accounts ADD COLUMN oauth_client_id VARCHAR(255)',
    'SELECT ''oauth_client_id column already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add oauth_client_secret column if missing
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'email_accounts'
    AND COLUMN_NAME = 'oauth_client_secret');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE email_accounts ADD COLUMN oauth_client_secret VARCHAR(500)',
    'SELECT ''oauth_client_secret column already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add oauth_refresh_token column if missing
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'email_accounts'
    AND COLUMN_NAME = 'oauth_refresh_token');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE email_accounts ADD COLUMN oauth_refresh_token VARCHAR(500)',
    'SELECT ''oauth_refresh_token column already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add oauth_access_token column if missing
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'email_accounts'
    AND COLUMN_NAME = 'oauth_access_token');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE email_accounts ADD COLUMN oauth_access_token TEXT',
    'SELECT ''oauth_access_token column already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add oauth_token_expiry column if missing
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'email_accounts'
    AND COLUMN_NAME = 'oauth_token_expiry');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE email_accounts ADD COLUMN oauth_token_expiry DATETIME',
    'SELECT ''oauth_token_expiry column already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add oauth_scopes column if missing
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'email_accounts'
    AND COLUMN_NAME = 'oauth_scopes');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE email_accounts ADD COLUMN oauth_scopes TEXT',
    'SELECT ''oauth_scopes column already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add index on auth_method if missing
SET @idx_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'email_accounts'
    AND INDEX_NAME = 'idx_auth_method');
SET @sql = IF(@idx_exists = 0,
    'CREATE INDEX idx_auth_method ON email_accounts(auth_method)',
    'SELECT ''idx_auth_method index already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
