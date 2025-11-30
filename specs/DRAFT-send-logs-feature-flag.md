# DRAFT: Send Logs Feature Flag Specification

**Status**: DRAFT
**Date**: 2025-11-30
**Feature**: Add `send_logs` boolean parameter to LogsCollectorService

---

## Overview

This specification defines the design for adding a required `send_logs: bool` constructor parameter to `LogsCollectorService`. The value originates from the `SEND_LOGS` environment variable read at application startup, defaulting to `False` if not set. The value propagates through the service dependency chain via constructor injection.

---

## Interfaces Needed

### ILogsCollector

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class ILogsCollector(ABC):
    """Interface for log collection and transmission."""

    @abstractmethod
    def collect(self, log_entry: Dict[str, Any]) -> None:
        """Collect a log entry for potential transmission."""
        pass

    @abstractmethod
    def flush(self) -> bool:
        """Flush collected logs to remote location if enabled."""
        pass

    @property
    @abstractmethod
    def is_send_enabled(self) -> bool:
        """Returns True if remote log sending is enabled."""
        pass
```

### IFeatureFlagProvider

```python
from abc import ABC, abstractmethod

class IFeatureFlagProvider(ABC):
    """Interface for retrieving feature flag values."""

    @abstractmethod
    def get_send_logs_enabled(self) -> bool:
        """Returns the value of the SEND_LOGS feature flag."""
        pass
```

### ILogsCollectorFactory

```python
from abc import ABC, abstractmethod

class ILogsCollectorFactory(ABC):
    """Factory interface for creating LogsCollector instances."""

    @abstractmethod
    def create(self) -> ILogsCollector:
        """Create a LogsCollector with appropriate configuration."""
        pass
```

---

## Data Models

### LogsCollectorConfig

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class LogsCollectorConfig:
    """Configuration for LogsCollectorService."""

    send_logs: bool
    api_url: Optional[str] = None
    api_token: Optional[str] = None

    @property
    def is_fully_enabled(self) -> bool:
        """Returns True if sending is enabled AND api_url is configured."""
        return self.send_logs and self.api_url is not None
```

### FeatureFlags

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class FeatureFlags:
    """Application-wide feature flags read at startup."""

    send_logs: bool

    @classmethod
    def from_environment(cls, env_vars: dict) -> "FeatureFlags":
        """
        Create FeatureFlags from environment variables.

        Args:
            env_vars: Dictionary of environment variables

        Returns:
            FeatureFlags with values from env or defaults
        """
        send_logs_raw = env_vars.get("SEND_LOGS", "").lower()
        send_logs = send_logs_raw in ("true", "1", "yes")

        return cls(send_logs=send_logs)
```

---

## Constructor Signatures

All constructors follow the rule of fewer than 4 arguments. No environment variables are read within constructors.

### LogsCollectorService

```python
class LogsCollectorService(ILogsCollector):
    def __init__(
        self,
        send_logs: bool,  # Required, no default
        config: Optional[LogsCollectorConfig] = None
    ) -> None:
        """
        Args:
            send_logs: Whether to send logs to remote location. Required.
            config: Optional configuration with api_url and api_token.
        """
```

### EmailProcessorService

```python
class EmailProcessorService:
    def __init__(
        self,
        logs_collector: ILogsCollector,
        email_client: IEmailClient
    ) -> None:
        """
        Args:
            logs_collector: Pre-configured logs collector instance.
            email_client: Email client for fetching emails.
        """
```

### EmailSummaryService

```python
class EmailSummaryService:
    def __init__(
        self,
        logs_collector: ILogsCollector,
        summary_generator: ISummaryGenerator
    ) -> None:
        """
        Args:
            logs_collector: Pre-configured logs collector instance.
            summary_generator: Service to generate email summaries.
        """
```

### AccountEmailProcessorService

```python
class AccountEmailProcessorService:
    def __init__(
        self,
        logs_collector: ILogsCollector,
        email_processor: IEmailProcessor
    ) -> None:
        """
        Args:
            logs_collector: Pre-configured logs collector instance.
            email_processor: Service to process individual emails.
        """
```

### LogsCollectorFactory

```python
class LogsCollectorFactory(ILogsCollectorFactory):
    def __init__(
        self,
        feature_flags: FeatureFlags,
        api_config: Optional[LogsCollectorConfig] = None
    ) -> None:
        """
        Args:
            feature_flags: Application feature flags containing send_logs.
            api_config: Optional API configuration for log endpoint.
        """
```

---

## Logic Flow

### Application Startup (api_service.py)

```pseudocode
FUNCTION initialize_application():
    # Step 1: Read environment variables ONCE at startup
    env_vars = read_all_environment_variables()

    # Step 2: Create feature flags from environment
    feature_flags = FeatureFlags.from_environment(env_vars)

    # Step 3: Create LogsCollectorConfig from environment
    logs_config = LogsCollectorConfig(
        send_logs=feature_flags.send_logs,
        api_url=env_vars.get("LOGS_API_URL"),
        api_token=env_vars.get("LOGS_API_TOKEN")
    )

    # Step 4: Create single LogsCollectorService instance
    logs_collector = LogsCollectorService(
        send_logs=feature_flags.send_logs,
        config=logs_config
    )

    # Step 5: Inject into dependent services
    email_processor = create_email_processor(logs_collector)
    account_processor = create_account_processor(logs_collector)

    RETURN application_context
```

### Background Worker (gmail_fetcher.py)

```pseudocode
FUNCTION main():
    # Step 1: Read SEND_LOGS env var with False default
    send_logs_raw = os.environ.get("SEND_LOGS", "false").lower()
    send_logs = send_logs_raw in ("true", "1", "yes")

    # Step 2: Create LogsCollectorService with explicit flag
    logs_collector = LogsCollectorService(
        send_logs=send_logs,
        config=LogsCollectorConfig(
            send_logs=send_logs,
            api_url=os.environ.get("LOGS_API_URL"),
            api_token=os.environ.get("LOGS_API_TOKEN")
        )
    )

    # Step 3: Create services with injected logs_collector
    processor = EmailProcessorService(
        logs_collector=logs_collector,
        email_client=create_email_client()
    )

    # Step 4: Run processing
    processor.process_emails()
```

### LogsCollectorService.flush()

```pseudocode
FUNCTION flush(self) -> bool:
    # Guard: Check if sending is enabled
    IF NOT self._send_logs:
        log_debug("Log sending disabled by feature flag")
        RETURN False

    # Guard: Check if API is configured
    IF self._api_url IS None:
        log_debug("Log sending disabled: no API URL configured")
        RETURN False

    # Send collected logs
    TRY:
        response = http_post(
            url=self._api_url,
            headers={"Authorization": f"Bearer {self._api_token}"},
            body=self._collected_logs
        )
        self._collected_logs.clear()
        RETURN response.is_success
    CATCH HttpError as e:
        log_error(f"Failed to send logs: {e}")
        RETURN False
```

---

## Environment Variable Handling

### Centralized Reading Pattern

Environment variables are read ONLY at application entry points:

| Entry Point | Responsibility |
|-------------|----------------|
| `api_service.py` | Read `SEND_LOGS` during FastAPI startup |
| `gmail_fetcher.py` | Read `SEND_LOGS` at script initialization |

### SEND_LOGS Parsing Rules

```python
def parse_send_logs_env(value: Optional[str]) -> bool:
    """
    Parse SEND_LOGS environment variable.

    Returns True for: "true", "1", "yes" (case-insensitive)
    Returns False for: missing, empty, or any other value
    """
    if value is None:
        return False
    return value.lower() in ("true", "1", "yes")
```

---

## Dependency Injection Chain

```
Application Startup
        |
        v
+-------------------+
|   FeatureFlags    |  <-- Reads SEND_LOGS env var
+-------------------+
        |
        v
+-------------------+
| LogsCollectorSvc  |  <-- Receives send_logs: bool (required)
+-------------------+
        |
        +---> EmailProcessorService (receives ILogsCollector)
        |
        +---> EmailSummaryService (receives ILogsCollector)
        |
        +---> AccountEmailProcessorService (receives ILogsCollector)
```

---

## Breaking Changes

### Required Migration

1. **LogsCollectorService instantiation**: All call sites MUST provide `send_logs` parameter
2. **No internal LogsCollector creation**: Services can no longer create their own LogsCollectorService instances
3. **Factory pattern recommended**: Use LogsCollectorFactory at entry points

### Before (Current Pattern)

```python
# BAD: Service creates its own LogsCollector
class EmailProcessorService:
    def __init__(self, logs_collector=None):
        self.logs = logs_collector or LogsCollectorService()
```

### After (Required Pattern)

```python
# GOOD: LogsCollector is injected, never created internally
class EmailProcessorService:
    def __init__(self, logs_collector: ILogsCollector):
        self.logs = logs_collector
```

---

## Test Strategy

### Unit Tests for LogsCollectorService

```python
def test_send_logs_true_enables_transmission():
    collector = LogsCollectorService(send_logs=True, config=mock_config)
    collector.collect({"message": "test"})
    result = collector.flush()
    assert result is True
    assert mock_api.was_called

def test_send_logs_false_prevents_transmission():
    collector = LogsCollectorService(send_logs=False, config=mock_config)
    collector.collect({"message": "test"})
    result = collector.flush()
    assert result is False
    assert mock_api.was_not_called

def test_constructor_requires_send_logs_parameter():
    with pytest.raises(TypeError):
        LogsCollectorService()  # Missing required argument
```

### Integration Tests for Env Var Handling

```python
def test_missing_send_logs_env_defaults_to_false(monkeypatch):
    monkeypatch.delenv("SEND_LOGS", raising=False)
    flags = FeatureFlags.from_environment(os.environ)
    assert flags.send_logs is False

def test_send_logs_env_true_enables_flag(monkeypatch):
    monkeypatch.setenv("SEND_LOGS", "true")
    flags = FeatureFlags.from_environment(os.environ)
    assert flags.send_logs is True
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `services/logs_collector_service.py` | Add required `send_logs: bool` parameter |
| `api_service.py` | Read `SEND_LOGS` env var, create and inject LogsCollectorService |
| `services/account_email_processor_service.py` | Require `ILogsCollector` in constructor |
| `services/email_processor_service.py` | Require `ILogsCollector` in constructor |
| `services/email_summary_service.py` | Require `ILogsCollector` in constructor |
| `services/email_processor_factory.py` | Accept `ILogsCollector` or `send_logs` flag |
| `gmail_fetcher.py` | Read `SEND_LOGS` env var, create LogsCollectorService |
| `tests/test_logs_collector_service.py` | Update all instantiations with `send_logs` param |
| `tests/test_email_processor_service.py` | Inject mock ILogsCollector |
| `tests/test_account_email_processor_service.py` | Inject mock ILogsCollector |

---

## Acceptance Criteria

1. `LogsCollectorService.__init__()` requires `send_logs: bool` with no default value
2. Calling `LogsCollectorService()` without `send_logs` raises `TypeError`
3. `SEND_LOGS` env var is read at application startup only
4. Missing `SEND_LOGS` env var defaults to `False`
5. `SEND_LOGS=true` (case-insensitive) enables log transmission
6. All services receive `ILogsCollector` via constructor injection
7. No service creates its own `LogsCollectorService` internally
8. All existing tests pass after migration
9. Constructor argument count remains under 4 for all services
