# Architect's Digest
> Status: In Progress

## Active Stack
4. Add OAuth State Init Endpoint for Popup Flow (In Progress)
   - **Task**: Create POST /api/auth/gmail/init endpoint for popup-based OAuth flow
   - **Problem**: Current OAuth flow generates state tokens server-side, but popup-based frontend flows need client-controlled state tokens
   - **Solution (Option B)**: Allow frontend to pre-register a client-generated state token before OAuth flow
   - **Key Files**:
     - api_service.py (lines 1555-1649) - existing /api/auth/gmail/authorize endpoint
     - api_service.py (lines 1651-1789) - existing /api/auth/gmail/callback endpoint
     - repositories/oauth_state_repository.py - state token storage
     - sql/V6__add_oauth_state_table.sql - oauth_state table schema
   - **Workflow**:
     1. Frontend generates state token (e.g., crypto.randomUUID())
     2. Frontend calls POST /api/auth/gmail/init with {state_token, redirect_uri}
     3. Backend stores state_token in oauth_state table with TTL
     4. Frontend opens popup with OAuth URL containing registered state
     5. Google redirects to callback with same state
     6. Backend validates state (existing flow)

3. Fix Gmail OAuth Auth Method Corruption Bug (BDD Scenarios Complete)
   - Root Cause: /root/repo/services/gmail_fetcher_service.py line 78 always sets auth_method='imap'
   - Fix Part 1: Conditionally set auth_method based on connection_service presence
   - Fix Part 2: Create migration to restore corrupted OAuth accounts (auth_method='imap' but have oauth_refresh_token)
   - Key Files: gmail_fetcher_service.py:78, account_category_client.py:137-250
   - **BDD Phase Complete**: 24 Gherkin scenarios generated and approved
   - Feature Files:
     - tests/bdd/gmail-oauth-auth-preservation.feature (8 scenarios)
     - tests/bdd/corrupted-oauth-account-restoration.feature (10 scenarios)
     - tests/bdd/auth-method-resolution-logic.feature (6 scenarios)
   - BDD Spec: specs/BDD-SPEC-gmail-oauth-auth-fix.md
   - **Next**: gherkin-to-test agent to create TDD prompts

2. Add OAuth Status Visual Indicator on Accounts Page (In Progress)
   - Display auth_method badge in accounts table
   - Green "OAuth Connected" badge for OAuth accounts
   - Gray "IMAP" badge for IMAP credential accounts
   - Efficient: Include auth_method in /api/accounts response (avoid N+1 queries)

1. Enhance Audit Records for Email Processing (All Sub-tasks Completed)
   1.1 Core Fields - Database Model and Basic Field Existence (Completed)
       - Added emails_categorized and emails_skipped columns to ProcessingRun model
       - Added fields to AccountStatus dataclass
       - Database migration (Flyway SQL V3)
       - Verified field initialization defaults to 0
       - All 37 TDD tests passing
   1.2 Increment Methods - Increment Behavior (Completed)
       - Created increment_categorized() method
       - Created increment_skipped() method
       - Verified default increment of 1
       - Verified batch increment with count parameter
       - All 20 TDD tests passing
   1.3 Edge Cases - Zero and Empty Handling (Completed)
       - DRAFT spec created: specs/DRAFT-edge-cases-zero-empty-handling.md
       - Zero counts in completed runs
       - Empty batch processing (increment with count=0)
       - Field initialization verification
       - Archived run includes new fields
       - All 10 edge case tests passing
       - Test file: tests/test_edge_cases_zero_empty_handling.py
   1.4 Edge Cases - No Active Session (Completed - Already Tested in 1.2)
       - Increment categorized without active session (no-op)
       - Increment skipped without active session (no-op)
       - Verified in tests/test_increment_categorized_skipped.py (lines 166-260)
       - 4 comprehensive tests covering all no-session scenarios
   1.5 Data Integrity and Persistence (Decomposed)
       1.5a Python Migration 006 - Core (Completed)
           - Created migrations/migration_006_add_categorized_skipped_columns.py
           - Migration creates columns when missing
           - Migration is idempotent (safe to run multiple times)
           - Migration downgrade removes columns
           - All 13 tests passing
           - Test file: tests/test_migration_006.py
       1.5b Persistence Verification (Completed)
           - Single value persistence through session close/reopen
           - Cumulative increments persist as total
           - Large values (1000+) persist correctly
           - Zero values persist as 0 (not NULL)
           - All 10 tests passing
           - Test file: tests/test_data_integrity_persistence.py
   1.6 Thread Safety and Large Counts (Completed)
       - Concurrent access safety verified (10-100 threads)
       - Large count handling (1000+, up to 50000) tested
       - Lock mechanism prevents race conditions
       - Mixed operations (read/write) thread-safe
       - All 13 tests passing
       - Test file: tests/test_thread_safety_concurrent_increments.py
   1.7 API Response Enhancement (Completed)
       - Status endpoint includes emails_categorized and emails_skipped via AccountStatus.to_dict()
       - History endpoint includes new fields via database_service.get_processing_runs()
       - Both fields default to 0 for NULL/missing values
       - All 9 API integration tests passing
       - Test file: tests/test_api_response_categorized_skipped.py

## Recently Completed
1. Generate Mermaid Gantt Chart Text for Email Categorization Runs (COMPLETED)
   1.1 State Transition Tracking (Completed)
       - Record state transitions with timestamps during processing
       - Calculate duration between transitions
       - Store transitions in archived run data structure
   1.2 Gantt Chart Generator Core (Completed)
       - Generate Mermaid Gantt syntax from transition data
       - Section groupings by processing phase
       - Date/time formatting for Mermaid
       - Task status modifiers (done, crit, active)
   1.3 API Enhancement and Integration (Completed)
       - Include gantt_chart_text in API response
       - Backward compatibility
       - Edge cases (zero duration, missing data)

## Completed
- [x] Remove Remote Logs Collector Integration (Phase 1: Core files deleted)
- [x] Phase 1.1: Delete Core Service Files (5 files deleted)
- [x] Phase 1.2: Update API Service and Gmail Fetcher Imports
- [x] 1.1 Add Database Columns and Migration
- [x] 1.2 Add AccountStatus Tracking and Increment Methods
- [x] 1.3 Update API Responses to Expose New Fields
- [x] 1.4 Add Concurrency Safety and Edge Cases
- [x] Add Email Processing Audit Counts (All 4 phases completed)
- [x] 1.1 State Transition Tracking (Sub-task of Gantt Chart feature)
- [x] 1.2 Gantt Chart Generator Core (Sub-task of Gantt Chart feature)
- [x] 1.3 API Enhancement and Integration (Sub-task of Gantt Chart feature)
- [x] Generate Mermaid Gantt Chart Text for Email Categorization Runs (ALL SUB-TASKS COMPLETE)
- [x] 1.1 Core Fields - Database Model and Basic Field Existence (emails_categorized and emails_skipped)
- [x] 1.2 Increment Methods - Increment Behavior (increment_categorized and increment_skipped)
- [x] 1.3 Edge Cases - Zero and Empty Handling (10 tests passing)
- [x] 1.4 Edge Cases - No Active Session (4 tests in 1.2)
- [x] 1.5a Python Migration 006 - Core (13 tests passing)
- [x] 1.5b Persistence Verification (10 tests passing)
- [x] 1.6 Thread Safety and Large Counts (13 tests passing)
- [x] 1.7 API Response Enhancement (9 tests passing)
- [x] Enhance Audit Records for Email Processing (ALL SUB-TASKS 1.1-1.7 COMPLETE)

## Context

### Current Task Description (Task 4 - OAuth State Init Endpoint)
Create POST /api/auth/gmail/init endpoint to support frontend popup-based OAuth flows.

**Problem:**
The current OAuth flow generates state tokens server-side in /api/auth/gmail/authorize, but this doesn't
work well with popup-based OAuth flows where the frontend needs to control the state token to correlate
the OAuth response with the original popup window.

**Solution (Option B):**
Create a new endpoint /api/auth/gmail/init that allows the frontend to:
1. Generate a state token client-side
2. Pre-register that state token with the backend via POST /api/auth/gmail/init
3. Use the pre-registered state token when constructing the OAuth authorization URL
4. Complete the OAuth flow via popup
5. Backend validates the state token during callback (existing flow)

**Implementation Requirements:**
1. **New Endpoint**: POST /api/auth/gmail/init
   - Request body: { state_token: string, redirect_uri: string }
   - Validate state_token format (non-empty, reasonable length 16-64 chars)
   - Store state_token in oauth_state table with 10-minute TTL
   - Return: { success: true, expires_at: timestamp }

2. **Security Considerations:**
   - Rate limiting to prevent state token flooding
   - State token format validation
   - Reuse existing OAuthStateRepository.store_state() method
   - Same TTL as server-generated tokens (10 minutes)

3. **Integration:**
   - No changes needed to /api/auth/gmail/callback (validates any registered state)
   - Frontend can choose between:
     - Old flow: GET /api/auth/gmail/authorize (server-generated state)
     - New flow: POST /api/auth/gmail/init + client-constructed OAuth URL

**Key Files:**
- api_service.py - Add new endpoint
- repositories/oauth_state_repository.py - Reuse store_state() method
- models/oauth_models.py - May need new request/response models

### Previous Task Context (Task 3 - OAuth Auth Method Bug)
Fix the Gmail OAuth authentication corruption bug identified in the CRASH-RCA investigation.

**Root Cause:**
At `/root/repo/services/gmail_fetcher_service.py` line 78:
```python
self.account_service.get_or_create_account(self.email_address, None, app_password, 'imap', None)
```

This line ALWAYS sets `auth_method='imap'` regardless of whether the account uses OAuth authentication.

**Fix Requirements:**
1. **Part 1 - Code Fix:** Modify `/root/repo/services/gmail_fetcher_service.py` line 78
2. **Part 2 - Database Migration:** Restore corrupted OAuth accounts

### Existing OAuth Infrastructure
- EmailAccount model has auth_method column (models/database.py:45)
- OAuthStateRepository for state token storage
- GET /api/auth/gmail/authorize - server-generated state flow
- POST /api/auth/gmail/callback - validates state and completes OAuth
- OAuth state table with 10-minute TTL
