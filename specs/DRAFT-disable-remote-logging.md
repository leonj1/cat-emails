# DRAFT: Disable Remote Logging Feature

**Status**: DRAFT
**Created**: 2025-11-29
**Feature**: Update logger to disable remote logging by default with environment variable control

---

## Overview

This specification defines the technical design for disabling remote logging by default while providing an environment variable (`DISABLE_REMOTE_LOGS`) to control this behavior. The solution maintains full stdout/local logging functionality.

---

## Interfaces Needed

### ILoggerConfiguration

Defines the contract for logger configuration management.

```python
from abc import ABC, abstractmethod
from typing import Optional


class ILoggerConfiguration(ABC):
    """Interface for logger configuration management."""

    @abstractmethod
    def is_remote_logging_enabled(self) -> bool:
        """
        Determine if remote logging is enabled.

        Returns:
            bool: True if remote logging should be active, False otherwise.
        """
        pass

    @abstractmethod
    def get_remote_endpoint(self) -> Optional[str]:
        """
        Get the remote logging endpoint URL.

        Returns:
            Optional[str]: The endpoint URL or None if not configured.
        """
        pass

    @abstractmethod
    def get_log_level(self) -> str:
        """
        Get the configured log level.

        Returns:
            str: Log level (e.g., "INFO", "DEBUG", "WARNING").
        """
        pass
```

### ILogHandler

Defines the contract for log handlers (both local and remote).

```python
from abc import ABC, abstractmethod
from typing import Dict, Any


class ILogHandler(ABC):
    """Interface for log handlers."""

    @abstractmethod
    def emit(self, log_record: Dict[str, Any]) -> bool:
        """
        Emit a log record to the handler's destination.

        Args:
            log_record: Dictionary containing log data.

        Returns:
            bool: True if emission was successful, False otherwise.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this handler is available and should be used.

        Returns:
            bool: True if handler is available, False otherwise.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up handler resources."""
        pass
```

### IEnvironmentReader

Defines the contract for reading environment variables (enables testing).

```python
from abc import ABC, abstractmethod
from typing import Optional


class IEnvironmentReader(ABC):
    """Interface for reading environment variables."""

    @abstractmethod
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get an environment variable value.

        Args:
            key: The environment variable name.
            default: Default value if not set.

        Returns:
            Optional[str]: The environment variable value or default.
        """
        pass

    @abstractmethod
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get an environment variable as a boolean.

        Truthy values: "true", "1", "yes" (case-insensitive)
        Falsy values: "false", "0", "no" (case-insensitive)

        Args:
            key: The environment variable name.
            default: Default boolean value if not set.

        Returns:
            bool: The parsed boolean value.
        """
        pass
```

---

## Data Models

### LogRecord

Represents a single log entry.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class LogRecord:
    """Immutable log record data model."""

    timestamp: datetime
    level: str
    message: str
    logger_name: str
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert log record to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "logger_name": self.logger_name,
            "module": self.module,
            "function": self.function,
            "line_number": self.line_number,
            "extra": self.extra or {}
        }
```

### RemoteLoggingConfig

Configuration for remote logging behavior.

```python
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RemoteLoggingConfig:
    """Configuration for remote logging."""

    enabled: bool
    endpoint: Optional[str]
    timeout_seconds: float = 5.0
    retry_count: int = 0

    @classmethod
    def disabled(cls) -> "RemoteLoggingConfig":
        """Factory method for disabled remote logging."""
        return cls(enabled=False, endpoint=None)

    @classmethod
    def from_environment(
        cls,
        env_reader: "IEnvironmentReader",
        default_endpoint: str = "https://logs-collector-production.up.railway.app/logs"
    ) -> "RemoteLoggingConfig":
        """
        Create configuration from environment variables.

        Environment Variables:
            DISABLE_REMOTE_LOGS: Set to "true", "1", or "yes" to disable (DEFAULT: disabled)
            REMOTE_LOG_ENDPOINT: Custom endpoint URL (optional)
            REMOTE_LOG_TIMEOUT: Timeout in seconds (optional, default: 5.0)
        """
        # IMPORTANT: Remote logging is DISABLED by default
        # DISABLE_REMOTE_LOGS=false explicitly enables it
        disable_remote = env_reader.get_bool("DISABLE_REMOTE_LOGS", default=True)

        if disable_remote:
            return cls.disabled()

        endpoint = env_reader.get("REMOTE_LOG_ENDPOINT", default_endpoint)
        timeout_str = env_reader.get("REMOTE_LOG_TIMEOUT", "5.0")

        try:
            timeout = float(timeout_str)
        except ValueError:
            timeout = 5.0

        return cls(
            enabled=True,
            endpoint=endpoint,
            timeout_seconds=timeout
        )
```

---

## Logic Flow

### Initialization Flow

```
1. Application Startup
   |
   v
2. Create EnvironmentReader (or use OsEnvironmentReader)
   |
   v
3. Create RemoteLoggingConfig.from_environment(env_reader)
   |
   +---> Check DISABLE_REMOTE_LOGS env var
   |     |
   |     +---> If not set: default=True (disabled)
   |     +---> If "true"/"1"/"yes": disabled
   |     +---> If "false"/"0"/"no": enabled
   |
   v
4. Create LoggerConfiguration with RemoteLoggingConfig
   |
   v
5. Create appropriate handlers:
   |
   +---> Always: StdoutLogHandler
   +---> Conditionally: RemoteLogHandler (only if config.enabled)
   |
   v
6. Register handlers with Logger
   |
   v
7. Logger ready for use
```

### Logging Flow

```
1. log.info("message") called
   |
   v
2. Create LogRecord with timestamp, level, message, etc.
   |
   v
3. For each registered handler:
   |
   +---> Check handler.is_available()
   |     |
   |     +---> If False: skip handler
   |     +---> If True: continue
   |
   +---> Call handler.emit(log_record)
   |     |
   |     +---> StdoutLogHandler: print to console
   |     +---> RemoteLogHandler: POST to endpoint (if enabled)
   |
   v
4. Log record processed
```

### Environment Variable Parsing Flow

```
1. Read DISABLE_REMOTE_LOGS from environment
   |
   v
2. If not set:
   |  Return True (remote logging DISABLED by default)
   |
   v
3. If set:
   |
   +---> Normalize: strip whitespace, lowercase
   |
   +---> Check against truthy values ["true", "1", "yes"]
   |     |
   |     +---> If match: Return True (disabled)
   |
   +---> Check against falsy values ["false", "0", "no"]
   |     |
   |     +---> If match: Return False (enabled)
   |
   +---> Otherwise: Return True (disabled, safe default)
   |
   v
4. Return parsed boolean
```

---

## Constructor Signatures

### OsEnvironmentReader

```python
class OsEnvironmentReader(IEnvironmentReader):
    """Reads environment variables from os.environ."""

    def __init__(self) -> None:
        """
        Initialize the OS environment reader.

        No arguments required - reads directly from os.environ.
        """
        pass
```

### LoggerConfiguration

```python
class LoggerConfiguration(ILoggerConfiguration):
    """Configuration for the logging system."""

    def __init__(
        self,
        remote_config: RemoteLoggingConfig,
        log_level: str = "INFO"
    ) -> None:
        """
        Initialize logger configuration.

        Args:
            remote_config: Configuration for remote logging behavior.
            log_level: Default log level for the logger.

        Raises:
            ValueError: If log_level is not a valid level.
        """
        pass
```

### StdoutLogHandler

```python
class StdoutLogHandler(ILogHandler):
    """Handles logging to standard output."""

    def __init__(
        self,
        formatter: Optional[logging.Formatter] = None
    ) -> None:
        """
        Initialize stdout log handler.

        Args:
            formatter: Optional custom formatter for log messages.
                      If None, uses default format.
        """
        pass
```

### RemoteLogHandler

```python
class RemoteLogHandler(ILogHandler):
    """Handles logging to a remote endpoint."""

    def __init__(
        self,
        config: RemoteLoggingConfig,
        http_client: Optional[IHttpClient] = None
    ) -> None:
        """
        Initialize remote log handler.

        Args:
            config: Remote logging configuration.
            http_client: Optional HTTP client for making requests.
                        If None, uses default requests-based client.

        Note:
            Handler will be non-functional if config.enabled is False.
        """
        pass
```

### ConfigurableLogger

```python
class ConfigurableLogger:
    """Main logger class with configurable handlers."""

    def __init__(
        self,
        name: str,
        configuration: ILoggerConfiguration,
        handlers: Optional[List[ILogHandler]] = None
    ) -> None:
        """
        Initialize the configurable logger.

        Args:
            name: Logger name (typically module name).
            configuration: Logger configuration instance.
            handlers: Optional list of pre-configured handlers.
                     If None, handlers are created based on configuration.
        """
        pass
```

---

## Pseudocode Implementation

### Main Logger Setup

```python
def create_logger(name: str) -> ConfigurableLogger:
    """Factory function to create a properly configured logger."""

    # Step 1: Read environment
    env_reader = OsEnvironmentReader()

    # Step 2: Build remote config (disabled by default)
    remote_config = RemoteLoggingConfig.from_environment(env_reader)

    # Step 3: Create logger configuration
    log_level = env_reader.get("LOG_LEVEL", "INFO")
    configuration = LoggerConfiguration(
        remote_config=remote_config,
        log_level=log_level
    )

    # Step 4: Create handlers
    handlers = [StdoutLogHandler()]

    if remote_config.enabled:
        handlers.append(RemoteLogHandler(config=remote_config))

    # Step 5: Create and return logger
    return ConfigurableLogger(
        name=name,
        configuration=configuration,
        handlers=handlers
    )
```

### Environment Boolean Parsing

```python
def get_bool(self, key: str, default: bool = False) -> bool:
    """Parse environment variable as boolean."""

    value = os.environ.get(key)

    if value is None:
        return default

    normalized = value.strip().lower()

    if normalized in ("true", "1", "yes"):
        return True
    elif normalized in ("false", "0", "no"):
        return False
    else:
        # Unknown value - return default for safety
        return default
```

---

## Usage Examples

### Default Behavior (Remote Logging Disabled)

```bash
# No environment variable set - remote logging is OFF
python gmail_fetcher.py

# Logs go to stdout only, no HTTP requests to remote server
```

### Explicitly Disable Remote Logging

```bash
# Any of these disable remote logging (also the default)
DISABLE_REMOTE_LOGS=true python gmail_fetcher.py
DISABLE_REMOTE_LOGS=1 python gmail_fetcher.py
DISABLE_REMOTE_LOGS=yes python gmail_fetcher.py
```

### Enable Remote Logging

```bash
# Explicitly enable remote logging
DISABLE_REMOTE_LOGS=false python gmail_fetcher.py
DISABLE_REMOTE_LOGS=0 python gmail_fetcher.py
DISABLE_REMOTE_LOGS=no python gmail_fetcher.py
```

---

## Testing Strategy

### Unit Tests Required

1. **EnvironmentReader Tests**
   - Test `get_bool` with various truthy/falsy values
   - Test default value behavior when env var not set
   - Test case-insensitivity

2. **RemoteLoggingConfig Tests**
   - Test `disabled()` factory method
   - Test `from_environment()` with various env var combinations
   - Test default is disabled

3. **StdoutLogHandler Tests**
   - Test emit writes to stdout
   - Test is_available always returns True

4. **RemoteLogHandler Tests**
   - Test is_available returns False when disabled
   - Test emit is no-op when disabled
   - Test emit makes HTTP request when enabled

5. **Integration Tests**
   - Test full logger creation with default config
   - Test logger only uses stdout when remote disabled
   - Test logger uses both handlers when remote enabled

---

## Migration Notes

### Breaking Changes

- **Default behavior change**: Remote logging is now DISABLED by default
- Applications relying on remote logging must set `DISABLE_REMOTE_LOGS=false`

### Backward Compatibility

- Stdout logging remains unchanged
- Log format remains unchanged
- Log levels remain unchanged
- All existing log calls work without modification

---

## Security Considerations

- No sensitive data should be logged to remote endpoints
- HTTP timeout prevents hanging on network issues
- Failed remote log attempts should not crash the application
- Remote logging failures should be silent (no recursive logging)

---

## File Structure

```
services/
    logging/
        __init__.py
        interfaces.py          # ILoggerConfiguration, ILogHandler, IEnvironmentReader
        models.py              # LogRecord, RemoteLoggingConfig
        environment_reader.py  # OsEnvironmentReader
        handlers/
            __init__.py
            stdout_handler.py  # StdoutLogHandler
            remote_handler.py  # RemoteLogHandler
        logger.py              # ConfigurableLogger
        factory.py             # create_logger() factory function

tests/
    test_logging/
        test_environment_reader.py
        test_remote_logging_config.py
        test_stdout_handler.py
        test_remote_handler.py
        test_logger_integration.py
```

---

**End of DRAFT Specification**
