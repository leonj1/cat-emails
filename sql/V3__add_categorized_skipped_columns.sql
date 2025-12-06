-- Flyway migration V3: Add emails_categorized and emails_skipped columns
-- Adds missing audit columns to processing_runs table for email categorization tracking

ALTER TABLE processing_runs ADD COLUMN emails_categorized INT NOT NULL DEFAULT 0;
ALTER TABLE processing_runs ADD COLUMN emails_skipped INT NOT NULL DEFAULT 0;
