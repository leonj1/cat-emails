-- Flyway migration V10: Reconcile schema to expected state
-- This migration ensures all columns from V3-V9 exist, handling cases where:
-- 1. Columns were added manually outside of Flyway
-- 2. Previous migrations partially failed
-- 3. Database schema is inconsistent with flyway_schema_history
--
-- All operations are idempotent - safe to run multiple times

DELIMITER //

CREATE PROCEDURE reconcile_schema()
BEGIN
    -- ============================================================
    -- V3 columns: emails_categorized and emails_skipped on processing_runs
    -- ============================================================

    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'processing_runs'
        AND COLUMN_NAME = 'emails_categorized'
    ) THEN
        ALTER TABLE processing_runs ADD COLUMN emails_categorized INT NOT NULL DEFAULT 0;
    END IF;

    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'processing_runs'
        AND COLUMN_NAME = 'emails_skipped'
    ) THEN
        ALTER TABLE processing_runs ADD COLUMN emails_skipped INT NOT NULL DEFAULT 0;
    END IF;

    -- ============================================================
    -- V5/V9 columns: OAuth columns on email_accounts
    -- ============================================================

    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'auth_method'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN auth_method VARCHAR(20) DEFAULT 'imap';
    END IF;

    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'oauth_client_id'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_client_id VARCHAR(255);
    END IF;

    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'oauth_client_secret'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_client_secret VARCHAR(500);
    END IF;

    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'oauth_refresh_token'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_refresh_token VARCHAR(500);
    END IF;

    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'oauth_access_token'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_access_token TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'oauth_token_expiry'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_token_expiry DATETIME;
    END IF;

    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'email_accounts'
        AND COLUMN_NAME = 'oauth_scopes'
    ) THEN
        ALTER TABLE email_accounts ADD COLUMN oauth_scopes TEXT;
    END IF;

    -- Add index on auth_method if it doesn't exist
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

-- Execute the reconciliation procedure
CALL reconcile_schema();

-- Clean up the procedure
DROP PROCEDURE IF EXISTS reconcile_schema;
