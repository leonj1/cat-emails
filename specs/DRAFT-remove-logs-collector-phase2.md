# DRAFT: Remove Logs Collector Phase 2 - Update Integration Points

## Overview

Phase 2 removes all imports and usage of `LogsCollectorService` from the two integration points: `api_service.py` and `gmail_fetcher.py`. This ensures the application can start without import errors after Phase 1 deleted the core service files.

## Scope

**Files to Modify:** 2
- `/root/repo/api_service.py`
- `/root/repo/gmail_fetcher.py`

**Estimated Changes:**
- Remove ~15 lines of code total
- Preserve all existing local logging (logger.info, logger.error, etc.)

## Interfaces Needed

No new interfaces required. This phase is purely removal of dead code references.

## Data Models

No new data models required. This phase removes references to the deleted `LogsCollectorService`.

## Logic Flow

### File 1: api_service.py

**Lines to Remove:**

1. **Line 32** - Remove import:
   ```python
   from services.logs_collector_service import LogsCollectorService
   ```

2. **Lines 185-186** - Remove feature flag reading:
   ```python
   # Feature flags - Read SEND_LOGS at startup
   SEND_LOGS_ENABLED = os.getenv("SEND_LOGS", "false").lower() in ("true", "1", "yes")
   ```

3. **Lines 291-292** - Remove global instance creation:
   ```python
   # Global logs collector service instance
   logs_collector_service = LogsCollectorService(send_logs=SEND_LOGS_ENABLED)
   ```

4. **Line 367** - Remove from AccountEmailProcessorService constructor:
   ```python
   logs_collector=logs_collector_service
   ```

**Preservation Requirements:**
- Keep all `logger.info()`, `logger.error()`, `logger.warning()`, `logger.debug()` calls
- Keep `initialize_central_logging()` call (lines 79-82) - this uses `utils/logger.py` not the deleted service
- Keep `shutdown_logging()` call (line 2484)

### File 2: gmail_fetcher.py

**Lines to Remove:**

1. **Line 27** - Remove import:
   ```python
   from services.logs_collector_service import LogsCollectorService
   ```

2. **Lines 612-623** - Remove logs collector initialization and first send_log call:
   ```python
   # Read SEND_LOGS feature flag from environment
   send_logs_raw = os.environ.get("SEND_LOGS", "false").lower().strip()
   send_logs_enabled = send_logs_raw in ("true", "1", "yes")

   # Initialize logs collector service with explicit flag
   logs_collector = LogsCollectorService(send_logs=send_logs_enabled)
   logs_collector.send_log(
       "INFO",
       f"Email processing started for {email_address}",
       {"hours": hours},
       "gmail-fetcher"
   )
   ```

3. **Lines 632-638** - Remove send_log call in API connection failure handler:
   ```python
   logs_collector.send_log(
       "ERROR",
       "Failed to connect to control API - terminating",
       {"email": email_address},
       "gmail-fetcher"
   )
   ```

4. **Lines 746-755** - Remove send_log call in success handler:
   ```python
   # Send completion log
   logs_collector.send_log(
       "INFO",
       f"Email processing completed successfully for {email_address}",
       {
           "processed": fetcher.stats['deleted'] + fetcher.stats['kept'],
           "deleted": fetcher.stats['deleted'],
           "kept": fetcher.stats['kept']
       },
       "gmail-fetcher"
   )
   ```

5. **Lines 761-766** - Remove send_log call in error handler:
   ```python
   # Send error log
   logs_collector.send_log(
       "ERROR",
       f"Email processing failed for {email_address}: {str(e)}",
       {"error": str(e), "email": email_address},
       "gmail-fetcher"
   )
   ```

**Preservation Requirements:**
- Keep all `logger.info()`, `logger.error()`, `logger.warning()`, `logger.debug()` calls
- Keep the logger instantiation at line 47: `logger = get_logger(__name__)`

## Context Budget

| Metric | Estimate |
|--------|----------|
| Files to read | 2 (~2,500 lines total) |
| New code to write | 0 lines (removal only) |
| Lines to remove | ~40 lines |
| Test code to write | ~30 lines (verify imports work) |
| Estimated context usage | ~15% |

## Acceptance Criteria

1. **No Import Errors**: Application starts without `ModuleNotFoundError` for logs_collector_service
2. **Local Logging Preserved**: All `logger.*` calls remain functional
3. **No Dead References**: No remaining references to `LogsCollectorService`, `logs_collector`, or `send_log()` in modified files
4. **Existing Functionality**: All other API endpoints and email processing continue to work

## Verification Steps

1. Run `python -c "import api_service"` - should succeed without import errors
2. Run `python -c "import gmail_fetcher"` - should succeed without import errors
3. Run `grep -n "logs_collector" api_service.py gmail_fetcher.py` - should return no matches
4. Run `grep -n "LogsCollectorService" api_service.py gmail_fetcher.py` - should return no matches
5. Run `grep -n "send_log" api_service.py gmail_fetcher.py` - should return no matches
6. Run existing tests to verify no regressions

## Dependencies

- Phase 1 must be complete (core service files deleted)
- No dependencies on other phases

## Risks

- **Low Risk**: Simple removal of dead code
- **Mitigation**: Comprehensive grep verification ensures no dangling references
