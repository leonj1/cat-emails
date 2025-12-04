# Architect's Digest
> Status: In Progress

## Active Stack
1. Add Email Processing Audit Counts (In Progress)
   - Add emails_reviewed, emails_tagged, emails_deleted counts to ProcessingRun audit entries

## Completed
- [x] Remove Remote Logs Collector Integration (Phase 1: Core files deleted)
- [x] Phase 1.1: Delete Core Service Files (5 files deleted)
- [x] Phase 1.2: Update API Service and Gmail Fetcher Imports

## Context

### Task Description
Add email processing audit entry that includes the number of emails reviewed, how many were tagged, and how many were deleted. Current audit entry only shows: email address, state, start/end time, duration, progress, and step. Need to add: emails_reviewed count, emails_tagged count, emails_deleted count

### Current System Analysis

#### ProcessingRun Model (database.py:204-225)
Current fields:
- id, email_address, start_time, end_time
- state, current_step
- emails_found, emails_processed
- error_message, created_at, updated_at

Missing fields (to be added):
- emails_reviewed (Integer) - count of emails reviewed during processing
- emails_tagged (Integer) - count of emails that received labels
- emails_deleted (Integer) - count of emails deleted

#### Key Files to Modify
1. `/root/repo/models/database.py` - Add new columns to ProcessingRun
2. `/root/repo/services/processing_status_manager.py` - Track new counts in AccountStatus
3. `/root/repo/migrations/` - New migration for schema changes
4. `/root/repo/gmail_fetcher.py` or `/root/repo/email_scanner_consumer.py` - Report counts during processing
5. API endpoints - Return new fields in responses

#### Related Existing Fields
- EmailSummary has: total_emails_processed, total_emails_deleted, total_emails_archived
- CategorySummary has: email_count, deleted_count, archived_count
- These are aggregated summaries, not per-run audit entries
