-- Flyway migration V5: Add OAuth columns to email_accounts table
-- Enables multi-user OAuth support for Gmail API access
-- Uses idempotent pattern to safely add columns if they don't exist

DELIMITER //

CREATE PROCEDURE add_oauth_columns_to_email_accounts()
BEGIN
    -- Add auth_method column (imap or oauth)
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'auth_method'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN auth_method VARCHAR(20) DEFAULT 'imap';
    END IF;

    -- Add oauth_client_id column
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'oauth_client_id'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_client_id VARCHAR(255);
    END IF;

    -- Add oauth_client_secret column
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'oauth_client_secret'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_client_secret VARCHAR(500);
    END IF;

    -- Add oauth_refresh_token column
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'oauth_refresh_token'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_refresh_token VARCHAR(500);
    END IF;

    -- Add oauth_access_token column (can be longer due to JWT format)
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'oauth_access_token'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_access_token TEXT;
    END IF;

    -- Add oauth_token_expiry column
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'oauth_token_expiry'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_token_expiry DATETIME;
    END IF;

    -- Add oauth_scopes column (JSON array stored as text)
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'oauth_scopes'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_scopes TEXT;
    END IF;

    -- Add index on auth_method for filtering
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND INDEX_NAME = 'idx_auth_method'
    ) THEN
        CREATE INDEX idx_auth_method ON email_accounts(auth_method);
    END IF;
END //

DELIMITER ;

-- Execute the procedure
CALL add_oauth_columns_to_email_accounts();

-- Drop the procedure after use
DROP PROCEDURE IF EXISTS add_oauth_columns_to_email_accounts;
