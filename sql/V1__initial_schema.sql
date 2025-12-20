-- Flyway migration V1: Initial schema
-- Creates all tables for the email processing application

-- User settings table
CREATE TABLE IF NOT EXISTS user_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL,
    setting_value VARCHAR(255) NOT NULL,
    setting_type VARCHAR(50) DEFAULT 'string',
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_setting_key (setting_key),
    INDEX idx_setting_key (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Email accounts table
CREATE TABLE IF NOT EXISTS email_accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email_address VARCHAR(255) NOT NULL,
    app_password VARCHAR(255),
    display_name VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_scan_at DATETIME,
    UNIQUE KEY uq_email_address (email_address),
    INDEX idx_email_address (email_address),
    INDEX idx_is_active (is_active),
    INDEX idx_email_active (email_address, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Email summaries table
CREATE TABLE IF NOT EXISTS email_summaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT,
    date DATETIME NOT NULL,
    total_emails_processed INT DEFAULT 0,
    total_emails_deleted INT DEFAULT 0,
    total_emails_archived INT DEFAULT 0,
    total_emails_skipped INT DEFAULT 0,
    processing_duration_seconds FLOAT,
    scan_interval_hours INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date (date),
    INDEX idx_date_created (date, created_at),
    FOREIGN KEY (account_id) REFERENCES email_accounts(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Category summaries table
CREATE TABLE IF NOT EXISTS category_summaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email_summary_id INT NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    email_count INT DEFAULT 0,
    deleted_count INT DEFAULT 0,
    archived_count INT DEFAULT 0,
    INDEX idx_summary_category (email_summary_id, category_name),
    FOREIGN KEY (email_summary_id) REFERENCES email_summaries(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sender summaries table
CREATE TABLE IF NOT EXISTS sender_summaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email_summary_id INT NOT NULL,
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255),
    email_count INT DEFAULT 0,
    deleted_count INT DEFAULT 0,
    archived_count INT DEFAULT 0,
    INDEX idx_summary_sender (email_summary_id, sender_email),
    FOREIGN KEY (email_summary_id) REFERENCES email_summaries(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Domain summaries table
CREATE TABLE IF NOT EXISTS domain_summaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email_summary_id INT NOT NULL,
    domain VARCHAR(255) NOT NULL,
    email_count INT DEFAULT 0,
    deleted_count INT DEFAULT 0,
    archived_count INT DEFAULT 0,
    is_blocked BOOLEAN DEFAULT FALSE,
    INDEX idx_summary_domain (email_summary_id, domain),
    FOREIGN KEY (email_summary_id) REFERENCES email_summaries(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Repeat offender patterns table
CREATE TABLE IF NOT EXISTS repeat_offender_patterns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_name VARCHAR(255) NOT NULL,
    sender_email VARCHAR(255),
    sender_domain VARCHAR(255),
    subject_pattern VARCHAR(500),
    category VARCHAR(100) NOT NULL,
    total_occurrences INT DEFAULT 0,
    deletion_count INT DEFAULT 0,
    confidence_score FLOAT DEFAULT 0.0,
    first_seen DATETIME NOT NULL,
    last_seen DATETIME NOT NULL,
    marked_as_repeat_offender DATETIME,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_account_sender (account_name, sender_email),
    INDEX idx_account_domain (account_name, sender_domain),
    INDEX idx_account_subject (account_name, subject_pattern(255)),
    INDEX idx_active_patterns (account_name, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Account category stats table
CREATE TABLE IF NOT EXISTS account_category_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    date DATE NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    email_count INT DEFAULT 0,
    deleted_count INT DEFAULT 0,
    archived_count INT DEFAULT 0,
    kept_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_account_date_category (account_id, date, category_name),
    INDEX idx_account_date (account_id, date),
    INDEX idx_account_category (account_id, category_name),
    INDEX idx_date_category (date, category_name),
    FOREIGN KEY (account_id) REFERENCES email_accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Processing runs table
CREATE TABLE IF NOT EXISTS processing_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email_address TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    state TEXT NOT NULL,
    current_step TEXT,
    emails_found INT DEFAULT 0,
    emails_processed INT DEFAULT 0,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    emails_reviewed INT DEFAULT 0 NOT NULL,
    emails_tagged INT DEFAULT 0 NOT NULL,
    emails_deleted INT DEFAULT 0 NOT NULL,
    INDEX idx_processing_runs_email_address (email_address(255)),
    INDEX idx_processing_runs_start_time (start_time),
    INDEX idx_processing_runs_email_start (email_address(255), start_time),
    INDEX idx_processing_runs_state (state(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Processed email log table
CREATE TABLE IF NOT EXISTS processed_email_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_email VARCHAR(255) NOT NULL,
    message_id VARCHAR(255) NOT NULL,
    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_account_email_message_id (account_email, message_id),
    INDEX idx_account_email (account_email),
    INDEX idx_message_id (message_id),
    INDEX idx_processed_at (processed_at),
    INDEX idx_processed_account_message (account_email, message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Category daily tallies table
CREATE TABLE IF NOT EXISTS category_daily_tallies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email_address VARCHAR(255) NOT NULL,
    tally_date DATE NOT NULL,
    category VARCHAR(100) NOT NULL,
    count INT DEFAULT 0 NOT NULL,
    total_emails INT DEFAULT 0 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    UNIQUE KEY uq_email_date_category (email_address, tally_date, category),
    INDEX idx_email_address (email_address),
    INDEX idx_tally_date (tally_date),
    INDEX idx_email_date (email_address, tally_date),
    INDEX idx_email_category (email_address, category),
    INDEX idx_date_range (email_address, tally_date, category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
