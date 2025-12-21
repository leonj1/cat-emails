-- Flyway migration V3: Add emails_categorized and emails_skipped columns
-- Adds audit columns to processing_runs table for email categorization tracking
-- Uses idempotent pattern to safely handle cases where columns already exist

DELIMITER //

CREATE PROCEDURE add_categorized_skipped_columns_v3()
BEGIN
    -- Add emails_categorized if missing
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'processing_runs'
        AND COLUMN_NAME = 'emails_categorized'
    ) THEN
        ALTER TABLE processing_runs ADD COLUMN emails_categorized INT NOT NULL DEFAULT 0;
    END IF;

    -- Add emails_skipped if missing
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'processing_runs'
        AND COLUMN_NAME = 'emails_skipped'
    ) THEN
        ALTER TABLE processing_runs ADD COLUMN emails_skipped INT NOT NULL DEFAULT 0;
    END IF;
END //

DELIMITER ;

-- Execute the procedure
CALL add_categorized_skipped_columns_v3();

-- Clean up the procedure
DROP PROCEDURE IF EXISTS add_categorized_skipped_columns_v3;
