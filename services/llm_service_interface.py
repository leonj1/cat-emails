"""
LLM Service Interface - Abstract interface for LLM providers

This interface allows the email categorization system to swap between different
LLM implementations (OpenAI, Ollama, Anthropic, etc.) without changing the core logic.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class LLMServiceInterface(ABC):
    """
    Abstract interface for LLM service providers.

    Implementations should handle the specifics of connecting to and calling
    different LLM providers (OpenAI, Ollama, Anthropic, etc.).
    """

    @abstractmethod
    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> str:
        """
        Call the LLM with the given prompt and return the response.

        Args:
            prompt: The user prompt to send to the LLM
            system_prompt: Optional system prompt to set context
            temperature: Temperature for response randomness (0.0 = deterministic)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Returns:
            str: The LLM's response text

        Raises:
            Exception: If the LLM call fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the LLM service is available and healthy.

        Returns:
            bool: True if the service is available, False otherwise
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the name of the model being used.

        Returns:
            str: Model name/identifier
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of the LLM provider.

        Returns:
            str: Provider name (e.g., 'openai', 'ollama', 'anthropic')
        """
        pass