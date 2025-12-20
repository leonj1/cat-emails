-- V6__add_oauth_state_table.sql
-- Migration to add OAuth state token storage table for CSRF protection

-- Create oauth_state table to store temporary state tokens
CREATE TABLE IF NOT EXISTS oauth_state (
    state_token VARCHAR(255) PRIMARY KEY,
    redirect_uri TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    metadata JSON,
    INDEX idx_expires_at (expires_at)
);

-- Add comment explaining the table purpose
ALTER TABLE oauth_state COMMENT = 'Stores OAuth state tokens for CSRF protection during authorization flow';
