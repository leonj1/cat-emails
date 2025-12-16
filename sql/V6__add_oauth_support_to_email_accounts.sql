-- Flyway migration V6: Add OAuth 2.0 support to email_accounts
-- Adds customer relationship and OAuth token storage
-- Removes dependency on app_password in favor of OAuth tokens

-- Step 1: Add new columns for OAuth and customer relationship
ALTER TABLE email_accounts
ADD COLUMN customer_id INT COMMENT 'FK to customers table',
ADD COLUMN auth_method VARCHAR(20) DEFAULT 'app_password' NOT NULL
    COMMENT 'Authentication method: app_password or oauth',
ADD COLUMN oauth_refresh_token TEXT COMMENT 'OAuth refresh token (plaintext for now, encrypt in future)',
ADD COLUMN oauth_access_token TEXT COMMENT 'OAuth access token (short-lived, typically 1 hour)',
ADD COLUMN oauth_token_expires_at DATETIME COMMENT 'When access token expires (UTC)',
ADD COLUMN oauth_scope TEXT COMMENT 'Granted OAuth scopes (e.g., https://mail.google.com/)',
ADD COLUMN oauth_token_type VARCHAR(50) DEFAULT 'Bearer' COMMENT 'Token type from OAuth response',
ADD COLUMN oauth_authorized_at DATETIME COMMENT 'When user authorized this account via OAuth';

-- Step 2: Add foreign key constraint to customers
ALTER TABLE email_accounts
ADD CONSTRAINT fk_email_accounts_customer
    FOREIGN KEY (customer_id) REFERENCES customers(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

-- Step 3: Add indexes for performance
ALTER TABLE email_accounts
ADD INDEX idx_customer_id (customer_id),
ADD INDEX idx_auth_method (auth_method),
ADD INDEX idx_customer_email (customer_id, email_address),
ADD INDEX idx_oauth_expires (oauth_token_expires_at);

-- Step 4: Add check constraint for auth_method values
ALTER TABLE email_accounts
ADD CONSTRAINT chk_auth_method
    CHECK (auth_method IN ('app_password', 'oauth'));

-- Migration notes:
-- 1. Existing rows will have auth_method='app_password' by default
-- 2. app_password column is NOT removed for backward compatibility during migration
-- 3. customer_id is nullable initially (accounts created before customers existed)
-- 4. Future migration (V7) can remove app_password after full OAuth transition
-- 5. Token encryption should be implemented at application layer before production use
