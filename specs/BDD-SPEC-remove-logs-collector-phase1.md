# BDD Specification: Remove Logs Collector Phase 1

## Feature Overview

**Feature**: Remove Logs Collector Phase 1 - Delete Core Service Files

**Purpose**: Remove the centralized logs collector infrastructure to simplify the codebase and eliminate unnecessary dependencies.

## User Story

As a maintainer, I want to remove the centralized logs collector infrastructure so that the codebase is simplified and unnecessary dependencies are eliminated.

## Scenarios

### Scenario 1: Logs collector service file is deleted

**Given**: The codebase is under version control
**When**: The logs collector removal phase 1 is complete
**Then**: The file "services/logs_collector_service.py" should not exist

### Scenario 2: Logs collector interface file is deleted

**Given**: The codebase is under version control
**When**: The logs collector removal phase 1 is complete
**Then**: The file "services/logs_collector_interface.py" should not exist

### Scenario 3: Logs collector client file is deleted

**Given**: The codebase is under version control
**When**: The logs collector removal phase 1 is complete
**Then**: The file "clients/logs_collector_client.py" should not exist

### Scenario 4: Central logging service files are deleted

**Given**: The codebase is under version control
**When**: The logs collector removal phase 1 is complete
**Then**: The file "services/logging_service.py" should not exist
**And**: The file "services/logging_factory.py" should not exist

## Files to Delete

| File Path | Description |
|-----------|-------------|
| `services/logs_collector_service.py` | Main LogsCollectorService class that orchestrates log collection |
| `services/logs_collector_interface.py` | ILogsCollector interface defining the contract for log collectors |
| `clients/logs_collector_client.py` | Contains RemoteLogsCollectorClient, FakeLogsCollectorClient, and LogEntry models |
| `services/logging_service.py` | CentralLoggingService that uses LogsCollectorClient |
| `services/logging_factory.py` | Factory that creates RemoteLogsCollectorClient instances |

## Acceptance Criteria

1. All 5 specified files are deleted from the repository
2. Files are properly removed (not just emptied)
3. Deletion is verified by checking file system

## Expected Side Effects

After Phase 1 completion:
- Import errors will occur in dependent files (api_service.py, gmail_fetcher.py) - Phase 2 will fix these
- Test failures will occur for logs collector tests - Phase 4 will fix these
- These side effects are expected and acceptable

## Verification Method

```bash
# Verify each file no longer exists
test ! -f services/logs_collector_service.py
test ! -f services/logs_collector_interface.py
test ! -f clients/logs_collector_client.py
test ! -f services/logging_service.py
test ! -f services/logging_factory.py
```

## Related Phases

- **Phase 1** (this): Delete core service files
- **Phase 2**: Update API Service and Gmail Fetcher imports
- **Phase 3**: Update Dockerfile and startup scripts
- **Phase 4**: Remove tests and config references
