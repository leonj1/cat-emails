-- Flyway migration V5: Add customers table for multi-tenant support
-- Each customer can have multiple email accounts
-- Each customer authorizes via their own Google login (not their own client_id/secret)

CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Customer identification
    google_user_id VARCHAR(255) NOT NULL COMMENT 'Google sub claim from OAuth id_token',
    email_address VARCHAR(255) NOT NULL COMMENT 'Customer primary email from Google profile',
    display_name VARCHAR(255) COMMENT 'Customer full name from Google profile',

    -- Status tracking
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    last_login_at DATETIME COMMENT 'Last time customer authorized via OAuth',

    -- Indexes for performance
    UNIQUE KEY uq_google_user_id (google_user_id),
    UNIQUE KEY uq_customer_email (email_address),
    INDEX idx_is_active (is_active),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Customers who use the application - each can manage multiple Gmail accounts';
