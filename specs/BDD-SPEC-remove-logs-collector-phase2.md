# BDD Specification: Remove Logs Collector Phase 2 - Update Integration Points

**Date**: 2025-12-01
**Phase**: 2 of 4
**Depends On**: Phase 1 (Core Service File Deletion)

---

## Overview

Phase 2 removes all imports and usage of `LogsCollectorService` from the two integration points: `api_service.py` and `gmail_fetcher.py`. This ensures the application can start without import errors after Phase 1 deleted the core service files.

---

## Feature Summary

| Attribute | Value |
|-----------|-------|
| Feature Name | Remove Logs Collector Phase 2 |
| Files to Modify | 2 |
| Lines to Remove | ~40 |
| New Code | 0 |
| Complexity | Low |

---

## Scenarios

### Scenario 1: api_service.py has no LogsCollectorService references

**Purpose**: Verify all logs collector code is removed from the API service.

**Acceptance Criteria**:
- No `LogsCollectorService` class reference
- No `logs_collector_service` variable reference
- No `SEND_LOGS_ENABLED` feature flag reference

### Scenario 2: gmail_fetcher.py has no LogsCollectorService references

**Purpose**: Verify all logs collector code is removed from the Gmail fetcher.

**Acceptance Criteria**:
- No `LogsCollectorService` class reference
- No `logs_collector` variable reference
- No `send_log` method calls

### Scenario 3: api_service.py can be imported without errors

**Purpose**: Verify the API service module can be imported in Python without ModuleNotFoundError.

**Acceptance Criteria**:
- `python -c "import api_service"` succeeds

### Scenario 4: gmail_fetcher.py can be imported without errors

**Purpose**: Verify the Gmail fetcher module can be imported in Python without ModuleNotFoundError.

**Acceptance Criteria**:
- `python -c "import gmail_fetcher"` succeeds

---

## Implementation Details

### File 1: api_service.py

**Lines to Remove:**

1. **Line 32** - Import statement:
   ```python
   from services.logs_collector_service import LogsCollectorService
   ```

2. **Lines ~185-186** - Feature flag:
   ```python
   SEND_LOGS_ENABLED = os.getenv("SEND_LOGS", "false").lower() in ("true", "1", "yes")
   ```

3. **Lines ~291-292** - Global instance:
   ```python
   logs_collector_service = LogsCollectorService(send_logs=SEND_LOGS_ENABLED)
   ```

4. **Line ~367** - Constructor parameter:
   ```python
   logs_collector=logs_collector_service
   ```

### File 2: gmail_fetcher.py

**Lines to Remove:**

1. **Line 27** - Import statement:
   ```python
   from services.logs_collector_service import LogsCollectorService
   ```

2. **Lines ~612-623** - Initialization and startup log:
   ```python
   send_logs_raw = os.environ.get("SEND_LOGS", "false").lower().strip()
   send_logs_enabled = send_logs_raw in ("true", "1", "yes")
   logs_collector = LogsCollectorService(send_logs=send_logs_enabled)
   logs_collector.send_log(...)
   ```

3. **Lines ~632-638** - API failure log:
   ```python
   logs_collector.send_log("ERROR", "Failed to connect...", ...)
   ```

4. **Lines ~746-755** - Success log:
   ```python
   logs_collector.send_log("INFO", "Email processing completed...", ...)
   ```

5. **Lines ~761-766** - Error log:
   ```python
   logs_collector.send_log("ERROR", "Email processing failed...", ...)
   ```

---

## Preservation Requirements

**MUST KEEP** (do not remove):

- All `logger.info()`, `logger.error()`, `logger.warning()`, `logger.debug()` calls
- `initialize_central_logging()` call in api_service.py
- `shutdown_logging()` call in api_service.py
- `logger = get_logger(__name__)` in gmail_fetcher.py

---

## Verification Commands

```bash
# Verify no LogsCollectorService references
grep -n "LogsCollectorService" api_service.py gmail_fetcher.py

# Verify no logs_collector references
grep -n "logs_collector" api_service.py gmail_fetcher.py

# Verify no send_log references
grep -n "send_log" api_service.py gmail_fetcher.py

# Verify no SEND_LOGS_ENABLED references
grep -n "SEND_LOGS_ENABLED" api_service.py

# Verify imports succeed
python -c "import api_service"
python -c "import gmail_fetcher"
```

---

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Accidental removal of local logging | Low | Explicit preservation list |
| Incomplete removal | Low | grep verification |
| Import errors | Low | Python import verification |

---

## Dependencies

- **Requires**: Phase 1 complete (core files deleted)
- **Blocks**: Phase 3 (test file cleanup)
