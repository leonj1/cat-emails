# DRAFT: Remove Logs Collector - Phase 1: Delete Core Service Files

## Overview
This phase focuses exclusively on deleting the core logs collector service files. No modifications to other files are performed in this phase - dependent files will be updated in subsequent phases.

## Scope
**Operation**: File Deletion Only
**Files to Delete**: 5

## Files to Delete

### 1. `/root/repo/services/logs_collector_service.py`
- **Description**: Main LogsCollectorService class that orchestrates log collection
- **Action**: DELETE entire file

### 2. `/root/repo/services/logs_collector_interface.py`
- **Description**: ILogsCollector interface defining the contract for log collectors
- **Action**: DELETE entire file

### 3. `/root/repo/clients/logs_collector_client.py`
- **Description**: Contains RemoteLogsCollectorClient, FakeLogsCollectorClient, and LogEntry models
- **Action**: DELETE entire file

### 4. `/root/repo/services/logging_service.py`
- **Description**: CentralLoggingService that uses LogsCollectorClient
- **Action**: DELETE entire file

### 5. `/root/repo/services/logging_factory.py`
- **Description**: Factory that creates RemoteLogsCollectorClient instances
- **Action**: DELETE entire file

## Interfaces Needed
None - this is a deletion-only phase.

## Data Models
None - this is a deletion-only phase.

## Logic Flow

```
1. Verify each file exists at the specified path
2. Delete each file:
   - services/logs_collector_service.py
   - services/logs_collector_interface.py
   - clients/logs_collector_client.py
   - services/logging_service.py
   - services/logging_factory.py
3. Verify files are deleted
```

## Expected Outcomes

After this phase:
- The 5 core logs collector files will no longer exist
- Import errors will occur in dependent files (api_service.py, gmail_fetcher.py) - these are expected and will be fixed in Phase 2
- Test failures will occur for logs collector tests - these are expected and will be fixed in Phase 4

## Verification Steps

1. Confirm files do not exist:
   ```bash
   ls -la services/logs_collector_service.py 2>&1 | grep -q "No such file"
   ls -la services/logs_collector_interface.py 2>&1 | grep -q "No such file"
   ls -la clients/logs_collector_client.py 2>&1 | grep -q "No such file"
   ls -la services/logging_service.py 2>&1 | grep -q "No such file"
   ls -la services/logging_factory.py 2>&1 | grep -q "No such file"
   ```

## Context Budget

| Metric | Value |
|--------|-------|
| Files to read | 0 (deletion only) |
| New code to write | 0 lines |
| Test code to write | 0 lines |
| Estimated context usage | ~5% (verification commands only) |

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Import errors in dependent files | Expected - Phase 2 will address these |
| Test failures | Expected - Phase 4 will address these |
| Build failures | Expected temporarily until Phase 2 completes |

## Dependencies

- **Depends on**: Nothing (first phase)
- **Blocks**: Phase 2 (Update API Service and Gmail Fetcher Imports)

## Phase Completion Criteria

- [ ] All 5 files have been deleted
- [ ] Git shows 5 deleted files in staging
- [ ] Phase 2 can proceed
