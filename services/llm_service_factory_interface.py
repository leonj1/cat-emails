from abc import ABC, abstractmethod
from services.llm_service_interface import LLMServiceInterface


class LLMServiceFactoryInterface(ABC):
    """Interface for creating LLM service instances."""

    @abstractmethod
    def create_service(self, model: str) -> LLMServiceInterface:
        """
        Create an LLM service instance for the specified model.

        Args:
            model: The model identifier to use

        Returns:
            LLMServiceInterface: An initialized LLM service instance
        """
        pass
