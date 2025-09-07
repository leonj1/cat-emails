from abc import ABC, abstractmethod

class EmailProcessingConfigurationInterface(ABC):
    """Interface for email processing configuration."""

    @property
    @abstractmethod
    def email_address(self) -> str: ...

    @property
    @abstractmethod
    def app_password(self) -> str: ...

    @property
    @abstractmethod
    def api_token(self) -> str: ...

    @property
    @abstractmethod
    def hours(self) -> int: ...

    @property
    @abstractmethod
    def scan_interval(self) -> int: ...

    @property
    @abstractmethod
    def enable_summaries(self) -> bool: ...

    @property
    @abstractmethod
    def summary_recipient(self) -> str: ...

    @property
    @abstractmethod
    def morning_hour(self) -> int: ...

    @property
    @abstractmethod
    def morning_minute(self) -> int: ...

    @property
    @abstractmethod
    def evening_hour(self) -> int: ...

    @property
    @abstractmethod
    def evening_minute(self) -> int: ...

    @abstractmethod
    def validate_or_exit(self) -> None: ...

