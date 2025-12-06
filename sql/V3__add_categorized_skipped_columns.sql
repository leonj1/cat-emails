-- Add emails_categorized and emails_skipped columns to processing_runs table
ALTER TABLE processing_runs ADD COLUMN emails_categorized INTEGER NOT NULL DEFAULT 0;
ALTER TABLE processing_runs ADD COLUMN emails_skipped INTEGER NOT NULL DEFAULT 0;
