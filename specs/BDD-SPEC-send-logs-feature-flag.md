# BDD Specification: SEND_LOGS Feature Flag

## Overview

This specification defines the behavior for the SEND_LOGS feature flag, which controls whether logs are transmitted to a remote logging API. The flag enables administrators to disable log transmission in development/testing environments while enabling it in production.

## User Stories

- As a system administrator, I want to control whether logs are sent to a remote location so that I can enable or disable log transmission based on environment requirements.

## Feature Files

| Feature File | Scenarios | Coverage |
|--------------|-----------|----------|
| send_logs_feature_flag.feature | 27 | Constructor requirements, env parsing, log sending behavior, DI, API integration, script integration, error handling |

## Scenarios Summary

### send_logs_feature_flag.feature

#### Constructor Requirements (3 scenarios)
1. LogsCollectorService requires send_logs parameter - Validates send_logs is a required argument
2. LogsCollectorService accepts send_logs=True - Service creation with enabled flag
3. LogsCollectorService accepts send_logs=False - Service creation with disabled flag

#### Environment Variable Parsing (4 scenarios)
4. SEND_LOGS environment variable missing defaults to False
5. SEND_LOGS environment variable is empty string defaults to False
6. SEND_LOGS truthy values are parsed correctly (7 examples: true, True, TRUE, 1, yes, Yes, YES)
7. SEND_LOGS falsy values are parsed correctly (9 examples: false, False, FALSE, 0, no, No, NO, random, invalid)

#### Log Sending Behavior (5 scenarios)
8. Logs are transmitted when send_logs is True and API is configured
9. Logs are suppressed when send_logs is False
10. Logs are suppressed when API URL is not configured
11. Flush returns False when sending is disabled
12. Flush returns True when sending succeeds

#### Service Dependency Injection (3 scenarios)
13. EmailProcessorService receives ILogsCollector via constructor
14. EmailSummaryService receives ILogsCollector via constructor
15. AccountEmailProcessorService receives ILogsCollector via constructor

#### API Service Integration (3 scenarios)
16. API service reads SEND_LOGS at startup
17. API service propagates send_logs through service chain
18. API service defaults send_logs to False when env var missing

#### Standalone Script Integration (3 scenarios)
19. gmail_fetcher reads SEND_LOGS at startup
20. gmail_fetcher defaults send_logs to False when env var missing
21. gmail_fetcher creates LogsCollectorService with explicit flag

#### Constructor Argument Limit Compliance (2 scenarios)
22. LogsCollectorService has fewer than 4 constructor arguments
23. Services maintain constructor argument limit

#### Error Handling (3 scenarios)
24. LogsCollectorService handles API transmission errors gracefully
25. LogsCollectorService clears collected logs after successful transmission
26. LogsCollectorService retains logs after failed transmission

## Acceptance Criteria

### Must Have
- [ ] `send_logs` is a **required** constructor parameter for LogsCollectorService (no default value)
- [ ] LogsCollectorService exposes `is_send_enabled` property
- [ ] FeatureFlags class parses SEND_LOGS environment variable with truthy/falsy detection
- [ ] Missing or empty SEND_LOGS defaults to False
- [ ] Logs are only transmitted when `send_logs=True` AND API URL is configured
- [ ] Services receive ILogsCollector via constructor injection (not created internally)
- [ ] api_service.py creates LogsCollectorService at startup using FeatureFlags
- [ ] gmail_fetcher.py creates LogsCollectorService at startup using FeatureFlags
- [ ] Constructor argument limit (max 3, excluding self) is maintained

### Should Have
- [ ] Debug logging when log sending is disabled
- [ ] Debug logging when API URL is not configured
- [ ] Graceful error handling for API transmission failures
- [ ] Log buffer retention on transmission failure
- [ ] Log buffer clearing on transmission success

## Technical Notes

### FeatureFlags Class
The FeatureFlags class should parse SEND_LOGS with the following truthy values:
- `true`, `True`, `TRUE`
- `1`
- `yes`, `Yes`, `YES`

All other values (including empty string, missing, `false`, `0`, `no`, `random`) should evaluate to False.

### Dependency Injection Pattern
Services should receive `ILogsCollector` as a constructor parameter:
```python
class EmailProcessorService:
    def __init__(self, logs_collector: ILogsCollector, ...):
        self._logs_collector = logs_collector
```

### Entry Points
Two entry points create the LogsCollectorService:
1. `api_service.py` - FastAPI application startup
2. `gmail_fetcher.py` - Standalone script main()

Both must read FeatureFlags and pass `send_logs` to LogsCollectorService constructor.
