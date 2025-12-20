-- V9__add_oauth_columns_simple.sql
-- Migration to add OAuth authentication columns to email_accounts table
-- Uses simple ALTER TABLE statements compatible with Flyway

-- Add authentication method column (default to 'imap' for existing accounts)
ALTER TABLE email_accounts ADD COLUMN auth_method VARCHAR(20) DEFAULT 'imap';

-- Add OAuth client credentials columns
ALTER TABLE email_accounts ADD COLUMN oauth_client_id VARCHAR(255);
ALTER TABLE email_accounts ADD COLUMN oauth_client_secret VARCHAR(500);

-- Add OAuth token columns
ALTER TABLE email_accounts ADD COLUMN oauth_refresh_token VARCHAR(500);
ALTER TABLE email_accounts ADD COLUMN oauth_access_token TEXT;
ALTER TABLE email_accounts ADD COLUMN oauth_token_expiry DATETIME;

-- Add OAuth scopes column (stores JSON array as text)
ALTER TABLE email_accounts ADD COLUMN oauth_scopes TEXT;

-- Add index on auth_method for efficient filtering
CREATE INDEX idx_auth_method ON email_accounts(auth_method);
