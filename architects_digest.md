# Architect's Digest
> Status: In Progress

## Active Stack
1. Remove Remote Logs Collector Integration (Decomposed)
   1.1 Phase 1: Delete Core Service Files (Completed)
   1.2 Phase 2: Update API Service and Gmail Fetcher Imports (In Progress)
   1.3 Phase 3: Clean Up Feature Flags (Pending)
   1.4 Phase 4: Update and Delete Test Files (Pending)
   1.5 Phase 5: Clean Up Configuration and Documentation (Pending)

## Completed
- [x] Phase 1: Delete Core Service Files (5 files deleted)

## Context

### Task Description
Remove all references in the code that would invoke the remote logs collector. The logs collector at https://logs-collector-production.up.railway.app/logs is returning 404 errors and needs to be removed from the codebase.

### Phase Breakdown

#### Phase 1: Delete Core Service Files (~4 scenarios, 5 files) - COMPLETED
Files DELETED:
- `/root/repo/services/logs_collector_service.py` - Main LogsCollectorService class
- `/root/repo/services/logs_collector_interface.py` - ILogsCollector interface
- `/root/repo/clients/logs_collector_client.py` - RemoteLogsCollectorClient, FakeLogsCollectorClient, LogEntry models
- `/root/repo/services/logging_service.py` - CentralLoggingService
- `/root/repo/services/logging_factory.py` - Factory creating RemoteLogsCollectorClient

#### Phase 2: Update API Service and Gmail Fetcher Imports (~4 scenarios, 2 files) - IN PROGRESS
Files to MODIFY:
- `/root/repo/api_service.py` - Remove imports and instantiation of LogsCollectorService
- `/root/repo/gmail_fetcher.py` - Remove imports and send_log() calls

#### Phase 3: Clean Up Feature Flags (~2 scenarios, 1 file)
Files to MODIFY:
- `/root/repo/models/feature_flags.py` - Remove FeatureFlags.send_logs

#### Phase 4: Update and Delete Test Files (~4 scenarios, ~10 files)
Files to DELETE:
- `/root/repo/tests/test_logs_collector_*.py` (4 files)
- `/root/repo/test_logs_collector_service.py`
- `/root/repo/test_centralized_logging.py`
- `/root/repo/test_logging_compliance*.py`

Files to MODIFY:
- Integration tests with logs_collector references (remove mocks/references)

#### Phase 5: Clean Up Configuration and Documentation (~3 scenarios, ~6 files)
Files to DELETE/MODIFY:
- `/root/repo/services/LOGGING_SERVICE_README.md`
- `/root/repo/docs/LOGGING_SERVICE_*.md`
- `/root/repo/examples/logging_service_example.py`
- `/root/repo/specs/DRAFT-*.md` (related specs)
- `/root/repo/.env.example` - Remove LOGS_COLLECTOR_API, LOGS_COLLECTOR_TOKEN vars
