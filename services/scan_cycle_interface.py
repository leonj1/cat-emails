from abc import ABC, abstractmethod

class ScanCycleServiceInterface(ABC):
    """Interface for executing a single scan cycle and optional summary sending."""

    @abstractmethod
    def execute_cycle(self, cycle_count: int, running: bool) -> None:
        """Execute one scan cycle.

        Args:
            cycle_count: Sequential counter of the current cycle.
            running: Whether the outer service loop is still running.
        """
        raise NotImplementedError

