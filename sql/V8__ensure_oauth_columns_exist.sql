-- Flyway migration V8: Ensure OAuth columns exist in email_accounts table
-- This migration fixes the error: "Unknown column 'email_accounts.auth_method' in 'field list'"
-- Uses simple ALTER TABLE statements that are safe to run (will fail silently if column exists)

-- Note: We use a procedure to check and add columns safely
-- This avoids the "Duplicate column name" error if columns already exist

DELIMITER //

CREATE PROCEDURE ensure_oauth_columns()
BEGIN
    DECLARE col_count INT;

    -- Check and add auth_method column
    SELECT COUNT(*) INTO col_count
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'email_accounts'
      AND COLUMN_NAME = 'auth_method';
    IF col_count = 0 THEN
        ALTER TABLE email_accounts ADD COLUMN auth_method VARCHAR(20) DEFAULT 'imap';
    END IF;

    -- Check and add oauth_client_id column
    SELECT COUNT(*) INTO col_count
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'email_accounts'
      AND COLUMN_NAME = 'oauth_client_id';
    IF col_count = 0 THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_client_id VARCHAR(255);
    END IF;

    -- Check and add oauth_client_secret column
    SELECT COUNT(*) INTO col_count
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'email_accounts'
      AND COLUMN_NAME = 'oauth_client_secret';
    IF col_count = 0 THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_client_secret VARCHAR(500);
    END IF;

    -- Check and add oauth_refresh_token column
    SELECT COUNT(*) INTO col_count
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'email_accounts'
      AND COLUMN_NAME = 'oauth_refresh_token';
    IF col_count = 0 THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_refresh_token VARCHAR(500);
    END IF;

    -- Check and add oauth_access_token column
    SELECT COUNT(*) INTO col_count
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'email_accounts'
      AND COLUMN_NAME = 'oauth_access_token';
    IF col_count = 0 THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_access_token TEXT;
    END IF;

    -- Check and add oauth_token_expiry column
    SELECT COUNT(*) INTO col_count
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'email_accounts'
      AND COLUMN_NAME = 'oauth_token_expiry';
    IF col_count = 0 THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_token_expiry DATETIME;
    END IF;

    -- Check and add oauth_scopes column
    SELECT COUNT(*) INTO col_count
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'email_accounts'
      AND COLUMN_NAME = 'oauth_scopes';
    IF col_count = 0 THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_scopes TEXT;
    END IF;

    -- Check and add idx_auth_method index
    SELECT COUNT(*) INTO col_count
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'email_accounts'
      AND INDEX_NAME = 'idx_auth_method';
    IF col_count = 0 THEN
        CREATE INDEX idx_auth_method ON email_accounts(auth_method);
    END IF;

END //

DELIMITER ;

-- Execute the procedure
CALL ensure_oauth_columns();

-- Clean up
DROP PROCEDURE IF EXISTS ensure_oauth_columns;
