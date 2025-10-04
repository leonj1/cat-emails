from abc import ABC, abstractmethod
from typing import Callable, Dict


class BackgroundProcessorInterface(ABC):
    """Interface for background email processing services."""

    @abstractmethod
    def run(self) -> None:
        """
        Run the background processor loop.

        This method should run continuously until stopped,
        processing Gmail accounts at configured intervals.
        """
        pass

    @abstractmethod
    def should_continue(self) -> bool:
        """
        Check if the processor should continue running.

        Returns:
            bool: True if processor should continue, False to stop
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Signal the processor to stop running.
        """
        pass
