# DRAFT Specification: Remove Remote Logs Collector Integration

## Overview

**Feature**: Remove all remote logs collector references from the codebase
**Status**: DRAFT
**Reason**: The remote logs collector at `https://logs-collector-production.up.railway.app/logs` is returning 404 errors and the service is no longer available.

## Scope

### Goal
Completely remove the remote logging infrastructure while preserving local Python `logging` module functionality for stdout/stderr output.

### What This Changes
- Removes all code that sends logs to the remote collector
- Removes the `SEND_LOGS` feature flag (no longer needed)
- Removes related environment variables from configuration
- Updates tests to remove remote logging assertions

### What This Preserves
- Python's standard `logging` module for console output
- Existing log format and log levels
- The `utils/logger.py` module (local logging utility)

---

## Files to DELETE (Complete Removal)

These files serve no purpose without the remote logging service:

| File | Lines | Purpose |
|------|-------|---------|
| `/root/repo/services/logs_collector_service.py` | 365 | Main LogsCollectorService class |
| `/root/repo/services/logs_collector_interface.py` | 39 | ILogsCollector abstract interface |
| `/root/repo/clients/logs_collector_client.py` | 167 | RemoteLogsCollectorClient, FakeLogsCollectorClient, LogEntry |
| `/root/repo/services/logging_service.py` | 278 | CentralLoggingService (depends on LogsCollectorClient) |
| `/root/repo/services/logging_factory.py` | 106 | Factory creating RemoteLogsCollectorClient |

**Total lines to delete**: ~955 lines

---

## Files to MODIFY (Remove Imports and Usage)

### 1. `/root/repo/api_service.py`
**Changes Required**:
- Remove import: `from services.logs_collector_service import LogsCollectorService`
- Remove instantiation of `LogsCollectorService`
- Remove any `send_log()` calls
- Remove any `logs_collector_service` variable/parameter passing

### 2. `/root/repo/gmail_fetcher.py`
**Changes Required**:
- Remove import: `from services.logs_collector_service import LogsCollectorService`
- Remove all `send_log()` calls (lines 617-761 contain multiple calls)
- Remove any `logs_collector_service` constructor parameters
- Keep all local `logger.info()`, `logger.error()` calls intact

### 3. `/root/repo/models/feature_flags.py`
**Changes Required**:
- Remove `send_logs: bool` attribute from `FeatureFlags` dataclass
- Remove `send_logs` parsing logic from `from_environment()` method
- If this is the only flag, consider whether `FeatureFlags` class is still needed

---

## Feature Flag to REMOVE

| Environment Variable | Purpose | Action |
|---------------------|---------|--------|
| `SEND_LOGS` | Toggles remote log sending | Remove from FeatureFlags |
| `LOGS_COLLECTOR_API` | Remote collector URL | Remove from .env.example |
| `LOGS_COLLECTOR_TOKEN` | Auth token | Remove from .env.example |
| `LOGS_COLLECTOR_API_TOKEN` | Alt auth token | Remove from .env.example |
| `DISABLE_REMOTE_LOGS` | Disables remote logging | Remove from .env.example |

---

## Test Files to UPDATE or DELETE

### Files to DELETE (test removed functionality)
- `/root/repo/test_logs_collector_service.py`
- `/root/repo/test_centralized_logging.py`
- `/root/repo/test_logging_compliance*.py`
- `/root/repo/tests/test_logs_collector_*.py` (all 4 files)

### Files to MODIFY (remove mock/reference)
- Any integration test that mocks `LogsCollectorService`
- Any test that asserts on `send_log()` calls
- Tests for `FeatureFlags` that reference `send_logs`

---

## Documentation Files to UPDATE or DELETE

| File | Action |
|------|--------|
| `/root/repo/services/LOGGING_SERVICE_README.md` | DELETE |
| `/root/repo/docs/LOGGING_SERVICE_*.md` | DELETE |
| `/root/repo/examples/logging_service_example.py` | DELETE |
| `/root/repo/.env.example` | MODIFY - remove LOGS_COLLECTOR_* vars |

---

## Step-by-Step Implementation Approach

### Phase 1: Remove Core Services (Files to Delete)
1. Delete `/root/repo/services/logs_collector_service.py`
2. Delete `/root/repo/services/logs_collector_interface.py`
3. Delete `/root/repo/clients/logs_collector_client.py`
4. Delete `/root/repo/services/logging_service.py`
5. Delete `/root/repo/services/logging_factory.py`

### Phase 2: Update Integration Points
1. Modify `/root/repo/api_service.py`:
   - Remove LogsCollectorService import and usage
2. Modify `/root/repo/gmail_fetcher.py`:
   - Remove LogsCollectorService import
   - Remove all send_log() calls
   - Retain local logging calls

### Phase 3: Clean Up Feature Flags
1. Modify `/root/repo/models/feature_flags.py`:
   - Remove send_logs attribute and parsing

### Phase 4: Update Tests
1. Delete dedicated logs collector test files
2. Modify integration tests to remove mocking of deleted services

### Phase 5: Clean Up Configuration
1. Update `/root/repo/.env.example` to remove LOGS_COLLECTOR_* variables

---

## Risk Mitigation

### Risk 1: Breaking Local Logging
**Mitigation**:
- Verify `utils/logger.py` is NOT modified or deleted
- Confirm all `logger.info()`, `logger.error()`, etc. calls remain intact
- These use Python's standard `logging` module, not the remote service

### Risk 2: Orphaned Imports
**Mitigation**:
- After deletion, run `grep -r "logs_collector" --include="*.py"` to find remaining references
- Run `grep -r "LogsCollectorService" --include="*.py"` to find remaining usages
- Run `grep -r "CentralLoggingService" --include="*.py"` to find remaining usages

### Risk 3: Test Failures
**Mitigation**:
- Run test suite after each phase
- Many tests may fail initially due to import errors (expected)
- Delete/update test files before running full suite

### Risk 4: Environment Variable Confusion
**Mitigation**:
- Update `.env.example` to remove obsolete variables
- Document in commit message which env vars are no longer used

---

## Context Budget Estimate

| Category | Count | Estimated Lines |
|----------|-------|-----------------|
| Files to read (for modification) | 5 | ~500 lines |
| Files to delete (just verify path) | 10+ | ~1200 lines (verify only) |
| New code to write | 0 | 0 lines (deletion only) |
| Test code to update | 10-15 files | ~200 lines of edits |
| Total context to understand | - | ~1700 lines |

**Estimated context usage**: 25-35% (Well within 60% threshold)

This is a **subtraction-only** task with no new features, making it lower risk than typical changes.

---

## Verification Checklist

After implementation, verify:

- [ ] `grep -r "LogsCollectorService" --include="*.py"` returns no results
- [ ] `grep -r "logs_collector" --include="*.py"` returns no results (except in git history references)
- [ ] `grep -r "CentralLoggingService" --include="*.py"` returns no results
- [ ] `grep -r "LOGS_COLLECTOR" --include="*.py" --include=".env*"` returns no results
- [ ] `grep -r "send_log" --include="*.py"` returns no results (from this service)
- [ ] All local `logger.*()` calls still work
- [ ] Test suite passes
- [ ] Application starts without import errors

---

## Acceptance Criteria

1. **No remote logging code remains**: All files in "Files to DELETE" section are removed
2. **No orphaned references**: No import statements or variable references to deleted modules
3. **Local logging preserved**: `utils/logger.py` and standard `logging` calls work unchanged
4. **Tests pass**: All remaining tests pass; obsolete tests are removed
5. **Clean configuration**: Environment variable examples updated

---

## Notes

This specification follows the principle of **complete removal** rather than feature flagging. Since the remote service is returning 404 errors and is presumably decommissioned, there is no value in keeping dead code paths controlled by feature flags.

If remote logging is ever needed again, it should be reimplemented fresh rather than resurrecting this code.
