# Cat-Emails Audit Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKGROUND PROCESSOR LOOP                         │
│              (BackgroundProcessorService.run())                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ├─ Every N seconds (scan_interval)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GET ACTIVE ACCOUNTS                               │
│     (AccountCategoryClient.get_all_accounts())                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                      For each account:
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│            PROCESS ACCOUNT                                           │
│    (AccountEmailProcessorService.process_account())                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Status Manager  │ │ Summary Service  │ │  Log Collector   │
│  (In-Memory)     │ │ (Lifecycle)      │ │  (Remote Logs)   │
└──────────────────┘ └──────────────────┘ └──────────────────┘
        │                    │                    │
        ├─ start_processing  ├─ start_run        ├─ send_log
        │                    │  ├─ create DB     │
        │                    │  │  record        │
        │                    │  └─ reset metrics │
        │                    │                   │
        ├─ update_status     ├─ track_email     │
        │ (every step)       │ (every email)    │
        │                    │  ├─ increment    │
        │                    │  │   run_metrics │
        │                    │  └─ update stats │
        │                    │                   │
        ├─ complete_         ├─ complete_run   │
        │  processing        │  ├─ save DB     │
        │                    │  │  metrics     │
        │                    │  └─ save summary│
        │                    │                   │
        └────────────────────┴───────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────┐
    │  Returns result dict:             │
    │  - success: bool                  │
    │  - emails_found: int              │
    │  - emails_processed: int          │
    │  - processing_time_seconds: float │
    └──────────────────────────────────┘
```

## Detailed Flow: Single Processing Run

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. START PROCESSING RUN                                              │
└─────────────────────────────────────────────────────────────────────┘

AccountEmailProcessorService.process_account("user@gmail.com")
│
├─ ProcessingStatusManager
│  └─ start_processing("user@gmail.com")
│     Creates AccountStatus in memory:
│     {
│       email_address: "user@gmail.com",
│       state: IDLE,
│       start_time: now(),
│       progress: None,
│       error_message: None
│     }
│
├─ EmailSummaryService
│  └─ start_processing_run(scan_hours=2)
│     ├─ Reset run_metrics:
│     │  {fetched: 0, processed: 0, deleted: 0, archived: 0, error: 0}
│     ├─ Reset performance_metrics:
│     │  {start_time: now(), end_time: None, ...}
│     └─ DatabaseService.start_processing_run("user@gmail.com")
│        └─ MySQLRepository.create_processing_run()
│           └─ INSERT INTO processing_runs
│              (email_address, start_time, state)
│              VALUES ('user@gmail.com', now(), 'started')
│           └─ Return run_id: 'run-42'
│
└─ ProcessingStatusManager.update_status()
   state: CONNECTING, step: "Connecting to Gmail IMAP..."

┌─────────────────────────────────────────────────────────────────────┐
│ 2. FETCH & PROCESS EMAILS                                            │
└─────────────────────────────────────────────────────────────────────┘

GmailFetcherService.get_recent_emails(hours=2)
│
└─ Returns list of 42 emails

DeduplicationClient.filter_new_emails(emails)
│
└─ Returns 35 new emails (7 were already processed)

ProcessingStatusManager.update_status()
state: FETCHING, step: "Fetching emails from last 2 hours"
progress: {current: 0, total: 35}

For each email (1-35):
│
├─ ProcessingStatusManager.update_status()
│  state: PROCESSING, step: "Processing email 5 of 35"
│  progress: {current: 5, total: 35}
│
├─ ProcessingStatusManager.update_status()
│  state: CATEGORIZING, step: "Categorizing email 5 with AI"
│
├─ EmailProcessorService.process_email()
│  ├─ Fetch content from Gmail
│  ├─ Categorize with LLM
│  ├─ Apply label to Gmail
│  ├─ Optional: Delete/Archive
│  └─ Return action taken: 'kept' | 'deleted' | 'archived'
│
├─ EmailSummaryService.track_email()
│  │
│  ├─ Increment run_metrics['processed'] += 1
│  │
│  ├─ Based on action:
│  │  ├─ 'deleted': run_metrics['deleted'] += 1
│  │  ├─ 'archived': run_metrics['archived'] += 1
│  │  └─ 'kept': (already counted in processed)
│  │
│  ├─ Accumulate category_stats[category]
│  ├─ Accumulate sender_stats[sender]
│  └─ Accumulate domain_stats[domain]
│
├─ ProcessingStatusManager.update_status()
│  state: LABELING, step: "Applying Gmail labels for email 5"
│
└─ DeduplicationClient.mark_as_processed(message_id)
   (bulk operation later)

[Final metrics after all 35 emails processed]:
run_metrics = {
    fetched: 42,
    processed: 35,
    deleted: 20,
    archived: 15,
    error: 0
}

category_stats = {
    'Marketing': {count: 15, deleted: 15, archived: 0},
    'Advertising': {count: 10, deleted: 5, archived: 5},
    'Personal': {count: 10, deleted: 0, archived: 10}
}

sender_stats = {...}
domain_stats = {...}

┌─────────────────────────────────────────────────────────────────────┐
│ 3. COMPLETE PROCESSING RUN                                           │
└─────────────────────────────────────────────────────────────────────┘

AccountEmailProcessorService.process_account()
│
├─ EmailSummaryService.complete_processing_run(success=True)
│  │
│  ├─ Finalize performance_metrics
│  │  end_time = now()
│  │  duration = end_time - start_time
│  │
│  ├─ DatabaseService.complete_processing_run(
│  │    run_id='run-42',
│  │    metrics={processed: 35, deleted: 20, archived: 15, error: 0},
│  │    success=True,
│  │    error_message=None
│  │  )
│  │  └─ MySQLRepository.complete_processing_run()
│  │     └─ UPDATE processing_runs SET
│  │        end_time = now(),
│  │        emails_processed = 35,
│  │        state = 'completed',
│  │        error_message = NULL
│  │        WHERE id = 42
│  │
│  └─ DatabaseService.save_email_summary(summary_data)
│     └─ INSERT INTO email_summaries
│        (account_id, date, total_processed, total_deleted, total_archived, ...)
│
├─ ProcessingStatusManager.complete_processing()
│  │
│  ├─ Archive to recent_runs history:
│  │  {
│  │    email_address: "user@gmail.com",
│  │    start_time: "2025-11-19T10:30:00Z",
│  │    end_time: "2025-11-19T10:35:00Z",
│  │    duration_seconds: 300,
│  │    final_state: "COMPLETED",
│  │    final_step: "Successfully processed 35 emails",
│  │    error_message: None,
│  │    final_progress: {current: 35, total: 35}
│  │  }
│  │
│  └─ Reset current_status to None
│
└─ Return result to background processor:
   {
     account: "user@gmail.com",
     emails_found: 42,
     emails_processed: 35,
     emails_categorized: 35,
     emails_labeled: 35,
     processing_time_seconds: 300.0,
     success: True
   }
```

## Data Storage Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 1: IN-MEMORY (ProcessingStatusManager)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─ Current Processing Session ─────────────┐                      │
│  │ email_address: "user@gmail.com"          │                      │
│  │ state: PROCESSING                        │                      │
│  │ current_step: "Processing email 5 of 35" │                      │
│  │ progress: {current: 5, total: 35}        │                      │
│  │ start_time: datetime                     │                      │
│  │ last_updated: datetime                   │                      │
│  │ error_message: None                      │                      │
│  └──────────────────────────────────────────┘                      │
│                                                                      │
│  ┌─ Recent Runs History (Deque, maxlen=50) ─┐                      │
│  │ [Run 50, Run 49, ..., Run 1]              │                      │
│  │ Each with start_time, end_time, duration │                      │
│  └──────────────────────────────────────────┘                      │
│                                                                      │
│  ✅ PROS: Fast, real-time, zero DB overhead                        │
│  ❌ CONS: Lost on restart, limited to 50 runs                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 2: DATABASE (ProcessingRun Table)                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  processing_runs                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ id  │ email_address    │ start_time │ end_time │ state │... │  │
│  ├─────┼──────────────────┼────────────┼──────────┼────────┼────┤  │
│  │ 42  │ user@gmail.com   │ 10:30:00   │ 10:35:00 │ DONE  │... │  │
│  │ 41  │ user@gmail.com   │ 10:25:00   │ 10:28:00 │ DONE  │... │  │
│  │ 40  │ other@gmail.com  │ 10:20:00   │ 10:32:00 │ ERROR │... │  │
│  └─────┴──────────────────┴────────────┴──────────┴────────┴────┘  │
│                                                                      │
│  ✅ PROS: Persistent, queryable, indefinite history                │
│  ❌ CONS: Less detailed (aggregate only)                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 3: SUMMARY TABLES (EmailSummary, CategorySummary, etc.)      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  email_summaries                                                    │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ account_id │ date │ total_processed │ total_deleted │ ...   │   │
│  ├────────────┼──────┼─────────────────┼───────────────┼─────┤   │
│  │ 1          │ 11-19│ 35              │ 20            │ ...   │   │
│  └────────────┴──────┴─────────────────┴───────────────┴─────┘   │
│                                                                      │
│  category_summaries                                                 │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ summary_id │ category      │ count │ deleted │ archived   │   │
│  ├────────────┼───────────────┼───────┼─────────┼────────────┤   │
│  │ 1          │ Marketing     │ 15    │ 15      │ 0          │   │
│  │ 1          │ Advertising   │ 10    │ 5       │ 5          │   │
│  │ 1          │ Personal      │ 10    │ 0       │ 10         │   │
│  └────────────┴───────────────┴───────┴─────────┴────────────┘   │
│                                                                      │
│  ✅ PROS: Detailed breakdown, analytics-ready                     │
│  ❌ CONS: Per-day aggregation, no per-email detail                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Access Patterns

```
┌────────────────────────────────────────────────────────────────┐
│ API CLIENTS                                                     │
│ (Browser, Monitoring, Dashboard)                               │
└───────────────────┬──────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
     ┌─────────┐ ┌─────────┐ ┌─────────┐
     │ REST    │ │REST (no │ │WebSocket│
     │API      │ │history) │ │(live)   │
     │(history)│ │         │ │         │
     └────┬────┘ └────┬────┘ └────┬────┘
          │           │           │
          ├─ GET /api/processing/history
          │   └─ ProcessingStatusManager.get_recent_runs()
          │       └─ Returns in-memory history
          │
          ├─ GET /api/processing/current-status
          │   ├─ ProcessingStatusManager.get_current_status()
          │   └─ Optional: get_recent_runs() + statistics()
          │
          ├─ GET /api/processing/status (current only)
          │   └─ ProcessingStatusManager.get_current_status()
          │       └─ Returns active session or None
          │
          ├─ GET /api/processing/statistics
          │   └─ ProcessingStatusManager.get_statistics()
          │       └─ Aggregate stats from recent_runs
          │
          └─ WS /ws/status (live updates)
              └─ StatusWebSocketManager
                  └─ Broadcasts ProcessingStatusManager updates

    FUTURE CAPABILITY (Not yet implemented):
    └─ GET /api/processing/runs?email=user@gmail.com&limit=100&since=2025-11-01
        └─ Query processing_runs table in database
            └─ Would enable long-term historical queries
```

## ProcessingRun Database Table Lifecycle

```
TIME: 10:30:00 AM
┌─────────────────────────────────────────────────────────────────┐
│ CREATE processing run (INSERT)                                   │
│ INSERT INTO processing_runs                                      │
│   (email_address, start_time, state)                             │
│ VALUES                                                           │
│   ('user@gmail.com', '2025-11-19 10:30:00', 'started')          │
└─────────────────────────────────────────────────────────────────┘
         │
         │ [Record created with ID=42]
         │
         ▼
    DB State at 10:30:00
    ┌──────────────────────────────────┐
    │ id: 42                            │
    │ email_address: user@gmail.com    │
    │ start_time: 10:30:00              │
    │ end_time: NULL                    │
    │ state: started                    │
    │ emails_processed: 0               │
    │ current_step: NULL                │
    │ error_message: NULL               │
    │ created_at: 10:30:00              │
    │ updated_at: 10:30:00              │
    └──────────────────────────────────┘

[Processing happens for ~5 minutes...]

TIME: 10:35:00 AM
┌─────────────────────────────────────────────────────────────────┐
│ COMPLETE processing run (UPDATE)                                 │
│ UPDATE processing_runs SET                                       │
│   end_time = '2025-11-19 10:35:00',                              │
│   state = 'completed',                                           │
│   emails_processed = 35,                                         │
│   current_step = 'Successfully processed 35 emails'              │
│ WHERE id = 42                                                    │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
    DB State at 10:35:00
    ┌──────────────────────────────────┐
    │ id: 42                            │
    │ email_address: user@gmail.com    │
    │ start_time: 10:30:00              │
    │ end_time: 10:35:00                │
    │ state: completed                  │
    │ emails_processed: 35              │
    │ current_step: Successfully...     │
    │ error_message: NULL               │
    │ created_at: 10:30:00              │
    │ updated_at: 10:35:00              │
    └──────────────────────────────────┘

[Record persists indefinitely]

Available for queries:
- Get duration: SELECT (julianday(end_time) - julianday(start_time)) * 24 * 3600
- Count processed: SELECT SUM(emails_processed) FROM processing_runs WHERE email_address = 'user@gmail.com'
- Get failures: SELECT * FROM processing_runs WHERE state = 'error'
- Get recent: SELECT * FROM processing_runs ORDER BY start_time DESC LIMIT 10
```

## Summary Matrix

```
┌──────────────────────┬──────────────┬──────────────┬────────────────┐
│ Aspect               │ In-Memory    │ ProcessingRun│ Summary Tables │
│                      │ (Live)       │ (DB)         │ (DB)           │
├──────────────────────┼──────────────┼──────────────┼────────────────┤
│ Persistence          │ ✅ No        │ ✅ Yes       │ ✅ Yes         │
│ Real-time            │ ✅ Yes       │ ❌ No        │ ❌ No          │
│ Query-able           │ ⚠️ Limited   │ ✅ Yes       │ ✅ Yes         │
│ History retention    │ 50 runs      │ Unlimited    │ Daily          │
│ Start time           │ ✅           │ ✅           │ ✅ (daily)     │
│ End time             │ ✅           │ ✅           │ ❌             │
│ Duration/timing      │ ✅           │ ✅           │ ❌             │
│ Email counts         │ ✅           │ ✅           │ ✅ (daily)     │
│ Per-email breakdown  │ ❌           │ ❌           │ ✅ (by day)    │
│ Current progress     │ ✅           │ ❌           │ ❌             │
│ Error details        │ ✅           │ ✅           │ ❌             │
│ Error message        │ ✅           │ ✅           │ ❌             │
└──────────────────────┴──────────────┴──────────────┴────────────────┘
```

