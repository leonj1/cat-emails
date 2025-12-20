-- Flyway migration V2: Clear failed migration records
-- This migration removes any previously failed Flyway migration records
-- from the schema history table to allow re-running migrations

-- Delete any failed migration records (success = 0)
DELETE FROM flyway_schema_history WHERE success = 0;
