-- Flyway migration V4: Fix missing emails_categorized and emails_skipped columns
-- This migration adds the columns if they don't already exist (handles case where V3 partially failed)
-- Uses MySQL procedure to check column existence before adding

DELIMITER //

CREATE PROCEDURE add_missing_audit_columns()
BEGIN
    -- Check and add emails_categorized if missing
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()  -- Use current Flyway schema context
        AND TABLE_NAME = 'processing_runs'
        AND COLUMN_NAME = 'emails_categorized'
    ) THEN
        ALTER TABLE processing_runs ADD COLUMN emails_categorized INT NOT NULL DEFAULT 0;
    END IF;

    -- Check and add emails_skipped if missing
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()  -- Use current Flyway schema context
        AND TABLE_NAME = 'processing_runs'
        AND COLUMN_NAME = 'emails_skipped'
    ) THEN
        ALTER TABLE processing_runs ADD COLUMN emails_skipped INT NOT NULL DEFAULT 0;
    END IF;
END //

DELIMITER ;

-- Execute the procedure
CALL add_missing_audit_columns();

-- Drop the procedure after use
DROP PROCEDURE IF EXISTS add_missing_audit_columns;
