# Quick Reference: Audit/Tracking Functionality

## What's Currently Tracked (EXIST)

| Item | Location | Database | Details |
|------|----------|----------|---------|
| **Processing Run Start Time** | ProcessingRun.start_time | ✅ Yes | DateTime when processing began |
| **Processing Run End Time** | ProcessingRun.end_time | ✅ Yes | DateTime when processing completed |
| **Email Account** | ProcessingRun.email_address | ✅ Yes | Which Gmail account was processed |
| **Emails Found** | ProcessingRun.emails_found | ✅ Yes | Total emails fetched from Gmail |
| **Emails Processed** | ProcessingRun.emails_processed | ✅ Yes | Count of emails with actions taken |
| **Processing State** | ProcessingRun.state | ✅ Yes | 'started', 'completed', or 'error' |
| **Current Step** | ProcessingRun.current_step | ✅ Yes | Description of what was happening |
| **Error Message** | ProcessingRun.error_message | ✅ Yes | Error details if failed |
| **Created/Updated Timestamps** | ProcessingRun.created_at/updated_at | ✅ Yes | Audit metadata |
| **Aggregated Delete Count** | EmailSummary.total_emails_deleted | ✅ Yes | Count of deleted emails per run |
| **Aggregated Archive Count** | EmailSummary.total_emails_archived | ✅ Yes | Count of archived emails per run |
| **Category Statistics** | CategorySummary | ✅ Yes | Per-category actions (delete/archive) |
| **Sender Statistics** | SenderSummary | ✅ Yes | Per-sender actions (delete/archive) |
| **Domain Statistics** | DomainSummary | ✅ Yes | Per-domain actions (delete/archive) |
| **In-Memory Status** | ProcessingStatusManager | ✅ Yes (RAM) | Real-time status during processing |
| **Run History** | ProcessingStatusManager | ✅ Yes (RAM) | Recent 50 runs in memory |

## What's NOT Tracked (MISSING)

| Item | Why Missing | Impact | Database |
|------|------------|--------|----------|
| **Per-Email Action Log** | Not designed in schema | Can't audit individual email actions | ❌ No |
| **Email Message IDs per Run** | No audit table for it | Can't link emails to processing runs | ❌ No |
| **Per-Email Category** | Not persisted per email | Can't audit which category was assigned | ❌ No |
| **Per-Email Processing Time** | Not persisted | Can't identify slow emails | ❌ No |
| **Categorization Confidence** | Not calculated/stored | Can't know AI confidence level | ❌ No |
| **Pre-categorized vs AI-categorized** | Not tracked | Can't distinguish categorization method | ❌ No |
| **Deleted Emails List** | No per-run email log | Can't query which emails were deleted | ❌ No |
| **Archived Emails List** | No per-run email log | Can't query which emails were archived | ❌ No |
| **Emails Per Minute** | Not calculated | Can't measure throughput | ❌ No |
| **LLM Model Used** | Not tracked | Can't audit which AI model was used | ❌ No |
| **Retry/Fallback Counts** | Not tracked | Can't see error recovery | ❌ No |

## Key Data Structures

### ProcessingRun Table (Database)

```sql
CREATE TABLE processing_runs (
    id INTEGER PRIMARY KEY,
    email_address TEXT NOT NULL,        -- Which account
    start_time DATETIME NOT NULL,        -- When it started
    end_time DATETIME,                   -- When it ended
    state TEXT NOT NULL,                 -- 'started', 'completed', 'error'
    current_step TEXT,                   -- What was being done
    emails_found INTEGER DEFAULT 0,      -- Total fetched
    emails_processed INTEGER DEFAULT 0,  -- Total processed
    error_message TEXT,                  -- If failed
    created_at DATETIME,                 -- Audit timestamp
    updated_at DATETIME                  -- Audit timestamp
);
-- Indexes: email_address, start_time, email_address+start_time, state
```

### EmailSummary Table (Related)

```sql
CREATE TABLE email_summaries (
    id INTEGER PRIMARY KEY,
    account_id INTEGER,
    date DATETIME,
    total_emails_processed INTEGER,     -- From this run
    total_emails_deleted INTEGER,       -- Deleted in this run
    total_emails_archived INTEGER,      -- Archived in this run
    total_emails_skipped INTEGER,       -- Skipped in this run
    processing_duration_seconds FLOAT,
    scan_interval_hours INTEGER
);
```

### In-Memory Status (ProcessingStatusManager)

```python
{
    'email_address': 'user@gmail.com',
    'state': 'PROCESSING',              # From ProcessingState enum
    'current_step': 'Processing email 5 of 20',
    'progress': {'current': 5, 'total': 20},
    'start_time': datetime,
    'last_updated': datetime,
    'error_message': None
}
```

## Run Metrics Tracked (Before Persisting)

```python
run_metrics = {
    'fetched': 42,      # Total emails from Gmail
    'processed': 35,    # Emails with actions
    'deleted': 20,      # Emails deleted
    'archived': 15,     # Emails archived
    'error': 0          # Errors during processing
}
```

## Data Flow

```text
1. START RUN
   └─ ProcessingStatusManager.start_processing(email)
   └─ EmailSummaryService.start_processing_run()
      └─ Repository.create_processing_run()
         └─ INSERT INTO processing_runs (email_address, start_time, state='started')

2. DURING PROCESSING
   ├─ For each email:
   │  ├─ ProcessingStatusManager.update_status() [in-memory only]
   │  └─ EmailSummaryService.track_email()
   │     └─ Increment run_metrics[action]
   │
   └─ Accumulate statistics:
      ├─ category_stats (per-category counts)
      ├─ sender_stats (per-sender counts)
      └─ domain_stats (per-domain counts)

3. END RUN
   └─ EmailSummaryService.complete_processing_run()
   └─ Repository.complete_processing_run()
      └─ UPDATE processing_runs SET end_time=?, emails_processed=?, state='completed'
   └─ Repository.save_email_summary()
      └─ INSERT INTO email_summaries (account_id, total_processed, total_deleted, ...)
```

## API Endpoints to Access Audit Data

| Endpoint | Purpose | Returns | Live/Historical |
|----------|---------|---------|-----------------|
| `GET /api/processing/status` | Current status | Active run details | Live |
| `GET /api/processing/history?limit=50` | Past runs | Recent processing runs | Historical (DB) |
| `GET /api/processing/statistics` | Aggregate stats | Success rate, avg duration | Historical (RAM) |
| `GET /api/processing/current-status` | Comprehensive | Current + recent + stats | Both |
| `WS /ws/status` | Real-time updates | Streaming status | Live |

## Database Performance

### Indexes on ProcessingRun

```text
idx_processing_runs_email_address      -- Query by account
idx_processing_runs_start_time          -- Query by date range
idx_processing_runs_email_start         -- Combined: account + time
idx_processing_runs_state               -- Filter by state
```

### Query Examples

```sql
-- Get latest 10 runs
SELECT * FROM processing_runs ORDER BY start_time DESC LIMIT 10;

-- Get runs for specific account
SELECT * FROM processing_runs WHERE email_address = 'user@gmail.com' LIMIT 10;

-- Get all failures
SELECT * FROM processing_runs WHERE state = 'error' ORDER BY start_time DESC;

-- Get runs from last 24 hours
SELECT * FROM processing_runs WHERE start_time > NOW() - INTERVAL 24 HOUR;
```

## Summary

✅ **Complete**: Aggregate metrics per run, timing info, account tracking, state tracking
❌ **Incomplete**: Individual email audit trail, detailed categorization audit, performance metrics per email
⚠️ **In-Memory Only**: Current status history (lost on restart, limited to last 50 runs)
💾 **Persisted**: ProcessingRun records stay in database indefinitely
