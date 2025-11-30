# Gap Analysis: SEND_LOGS Feature Flag

**Date**: 2025-11-30
**Feature**: Add `send_logs` boolean parameter to LogsCollectorService
**Source**: specs/BDD-SPEC-send-logs-feature-flag.md, tests/bdd/send_logs_feature_flag.feature

---

## Executive Summary

This analysis identifies the changes required to implement the SEND_LOGS feature flag across the codebase. The feature requires modifying the `LogsCollectorService` constructor to accept a required `send_logs` parameter and propagating this through the dependency injection chain.

---

## Existing Code Analysis

### 1. LogsCollectorService (`services/logs_collector_service.py`)

**Current State**:
- Constructor accepts `api_url: Optional[str]` and `api_token: Optional[str]`
- Reads `LOGS_COLLECTOR_API` and `LOGS_COLLECTOR_TOKEN` environment variables inside constructor
- Has `self.enabled` flag that is set based on whether `api_url` is configured
- Does NOT have a `send_logs` parameter
- Does NOT have `is_send_enabled` property

**Required Changes**:
- Add `send_logs: bool` as first required parameter (no default value)
- Add `is_send_enabled` property returning `self._send_logs`
- Modify `flush()` method (currently `send_log()`) to check `send_logs` flag first
- Add debug logging when sending is disabled

**Current Constructor (lines 23-50)**:
```python
def __init__(self, api_url: Optional[str] = None, api_token: Optional[str] = None):
    self.api_url = api_url or os.getenv("LOGS_COLLECTOR_API")
    self.api_token = api_token or os.getenv("LOGS_COLLECTOR_TOKEN") or os.getenv("LOGS_COLLECTOR_API_TOKEN")
    # ... rest of initialization
```

**Target Constructor**:
```python
def __init__(self, send_logs: bool, api_url: Optional[str] = None, api_token: Optional[str] = None):
    self._send_logs = send_logs
    self.api_url = api_url or os.getenv("LOGS_COLLECTOR_API")
    # ... rest of initialization
```

### 2. Entry Points

#### api_service.py (`api_service.py`)

**Current State** (line 32):
```python
from services.logs_collector_service import LogsCollectorService
```

**Current Instantiation** (line 64 in AccountEmailProcessorService, line 614 in gmail_fetcher.py):
- `LogsCollectorService()` - called without arguments
- Services create their own `LogsCollectorService` instances internally

**Required Changes**:
- Read `SEND_LOGS` environment variable at startup
- Create `FeatureFlags` dataclass from environment
- Create single `LogsCollectorService` instance with `send_logs` parameter
- Inject into all dependent services

#### gmail_fetcher.py (`gmail_fetcher.py`)

**Current State** (lines 613-618):
```python
logs_collector = LogsCollectorService()
logs_collector.send_log(
    "INFO",
    f"Email processing started for {email_address}",
    {"hours": hours},
    "gmail-fetcher"
)
```

**Required Changes**:
- Read `SEND_LOGS` environment variable in `main()`
- Pass `send_logs` parameter to `LogsCollectorService` constructor

### 3. Services Using LogsCollectorService

| Service | File | Current Pattern | Required Change |
|---------|------|-----------------|-----------------|
| `EmailProcessorService` | `services/email_processor_service.py` | Optional injection, creates default if None | Keep injection, make required |
| `AccountEmailProcessorService` | `services/account_email_processor_service.py` | Optional injection, creates default if None | Keep injection, make required |
| `EmailSummaryService` | `services/email_summary_service.py` | Optional injection, creates default if None | Keep injection, make required |

#### EmailProcessorService (lines 24-32):
```python
def __init__(
    self,
    fetcher: ServiceGmailFetcher,
    email_address: str,
    model: str,
    email_categorizer: EmailCategorizerInterface,
    email_extractor: EmailExtractorInterface,
    logs_collector: Optional[LogsCollectorService] = None,  # Line 31
) -> None:
    # ...
    self.logs_collector = logs_collector if logs_collector is not None else LogsCollectorService()
```

#### AccountEmailProcessorService (lines 36-64):
```python
def __init__(
    self,
    # ...
    logs_collector: Optional[LogsCollectorService] = None,
    # ...
):
    # ...
    self.logs_collector = logs_collector if logs_collector is not None else LogsCollectorService()
```

#### EmailSummaryService (lines 32-55):
```python
def __init__(self, data_dir: str = "./email_summaries", use_database: bool = True,
             gmail_email: Optional[str] = None, logs_collector: Optional[LogsCollectorService] = None,
             repository=None):
    # ...
    self.logs_collector = logs_collector if logs_collector is not None else LogsCollectorService()
```

### 4. FeatureFlags (NEW)

**Does Not Exist** - Must be created

**Required Implementation**:
```python
@dataclass(frozen=True)
class FeatureFlags:
    send_logs: bool

    @classmethod
    def from_environment(cls, env_vars: dict) -> "FeatureFlags":
        send_logs_raw = env_vars.get("SEND_LOGS", "").lower()
        send_logs = send_logs_raw in ("true", "1", "yes")
        return cls(send_logs=send_logs)
```

**Location**: Could be `models/feature_flags.py` or `services/feature_flags.py`

### 5. ILogsCollector Interface (NEW)

**Does Not Exist** - Must be created for proper DI

**Required Implementation**:
```python
from abc import ABC, abstractmethod

class ILogsCollector(ABC):
    @abstractmethod
    def collect(self, log_entry: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def flush(self) -> bool:
        pass

    @property
    @abstractmethod
    def is_send_enabled(self) -> bool:
        pass
```

---

## Reuse Opportunities

### 1. Existing Pattern: Optional Injection with Default Creation

All three services (EmailProcessorService, AccountEmailProcessorService, EmailSummaryService) use the same pattern:
```python
self.logs_collector = logs_collector if logs_collector is not None else LogsCollectorService()
```

**Recommendation**: Keep the injection pattern but require the parameter at entry points (api_service.py, gmail_fetcher.py).

### 2. Existing Pattern: Environment Variable Reading

The codebase already has patterns for reading environment variables at startup:
- `api_service.py` lines 181-236: `BACKGROUND_PROCESSING_ENABLED`, `BACKGROUND_SCAN_INTERVAL`, etc.
- Uses `os.getenv()` with defaults

**Recommendation**: Follow same pattern for `SEND_LOGS`.

### 3. Existing Pattern: Service Dependency Injection

`AccountEmailProcessorService` already receives many dependencies via constructor:
- `processing_status_manager`
- `settings_service`
- `email_categorizer`
- `account_category_client`
- `deduplication_factory`
- `logs_collector` (optional)

**Recommendation**: Convert `logs_collector` from optional to required at entry point level.

---

## Files to Modify

| File | Priority | Changes |
|------|----------|---------|
| `services/logs_collector_service.py` | HIGH | Add `send_logs` parameter, `is_send_enabled` property |
| `api_service.py` | HIGH | Read SEND_LOGS env var, inject LogsCollectorService |
| `gmail_fetcher.py` | HIGH | Read SEND_LOGS env var, pass to LogsCollectorService |
| `services/email_processor_service.py` | MEDIUM | Update any internal LogsCollectorService creation |
| `services/account_email_processor_service.py` | MEDIUM | Update any internal LogsCollectorService creation |
| `services/email_summary_service.py` | MEDIUM | Update any internal LogsCollectorService creation |

## New Files to Create

| File | Purpose |
|------|---------|
| `models/feature_flags.py` | FeatureFlags dataclass with from_environment() |
| `services/logs_collector_interface.py` | ILogsCollector interface (optional but recommended) |

---

## Constructor Argument Compliance

All services currently comply with the 3-argument limit (excluding self):

| Service | Current Args | Status |
|---------|--------------|--------|
| `LogsCollectorService` | 2 (api_url, api_token) | COMPLIANT - will become 3 |
| `EmailProcessorService` | 6 | EXCEEDS LIMIT - needs review |
| `AccountEmailProcessorService` | 10 | EXCEEDS LIMIT - needs review |
| `EmailSummaryService` | 5 | EXCEEDS LIMIT - needs review |

**Note**: The BDD spec mentions 3-argument limit but existing services already exceed this. The implementation should focus on LogsCollectorService staying at 3 arguments.

---

## Refactoring Decision

### Recommendation: GO (No Blocking Refactoring Needed)

The existing codebase patterns support the required changes without major refactoring:

1. **Dependency Injection Pattern**: Already in place for `logs_collector`
2. **Environment Variable Reading**: Pattern exists in `api_service.py`
3. **Service Instantiation**: Clear entry points identified

### Minor Refactoring During Implementation:
- Remove internal `LogsCollectorService()` creation from services
- Ensure all call sites pass `send_logs` parameter

---

## Test Impact

Existing tests will need updates:
- `tests/test_logs_collector_client.py` - Update instantiations
- `tests/test_central_logging_integration.py` - Update instantiations
- `tests/test_logs_collector_dns_fix.py` - Update instantiations

New tests needed:
- Constructor requirement tests
- Environment variable parsing tests
- Flag propagation tests
- Flush behavior tests

---

## Summary

| Category | Count |
|----------|-------|
| Files to Modify | 6 |
| New Files | 2 |
| Services Affected | 4 |
| Entry Points | 2 |
| Test Files to Update | 3+ |

**GO Signal**: Approved - No blocking refactoring required before implementation.
