from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol


class SummarySenderInterface(ABC):
    """Interface for sending scheduled summaries and tracking last sent times."""

    @property
    @abstractmethod
    def last_morning_sent(self) -> datetime: ...

    @property
    @abstractmethod
    def last_evening_sent(self) -> datetime: ...

    @property
    @abstractmethod
    def last_weekly_sent(self) -> datetime: ...

    @abstractmethod
    def handle_scheduled_summary(self, report_type: str) -> bool:
        """Send the summary for the given report_type and update last sent times.
        Returns True if sent successfully, False otherwise.
        """
        raise NotImplementedError

