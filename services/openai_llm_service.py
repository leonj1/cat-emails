"""
OpenAI LLM Service - Concrete implementation using OpenAI-compatible APIs

This service works with OpenAI API and OpenAI-compatible endpoints like
Ollama, RequestYAI, etc.
"""

import logging
from typing import Optional, Any

from openai import OpenAI

from services.llm_service_interface import LLMServiceInterface

logger = logging.getLogger(__name__)


class OpenAILLMService(LLMServiceInterface):
    """
    LLM service implementation using OpenAI or OpenAI-compatible APIs.

    This service can connect to:
    - OpenAI API
    - Ollama (with OpenAI-compatible endpoint)
    - RequestYAI (OpenAI-compatible gateway)
    - Any other OpenAI-compatible endpoint
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        provider_name: str = "openai"
    ):
        """
        Initialize the OpenAI LLM service.

        Args:
            model: Model name to use (e.g., 'gpt-4', 'llama3.2', 'gemma2')
            api_key: API key for authentication
            base_url: Optional base URL for OpenAI-compatible endpoints
            provider_name: Name of the provider for logging
        """
        self.model = model
        self.provider_name = provider_name
        self.base_url = base_url

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url.rstrip("/")

        self.client = OpenAI(**client_kwargs)

        logger.info(
            f"Initialized {provider_name} LLM service: "
            f"model={model}, base_url={base_url or '(default)'}"
        )

    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> str:
        """
        Call the OpenAI-compatible LLM and return the response.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Temperature for randomness
            max_tokens: Maximum response tokens
            **kwargs: Additional OpenAI API parameters

        Returns:
            str: The LLM's response text

        Raises:
            Exception: If the API call fails
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        call_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            call_kwargs["max_tokens"] = max_tokens

        # Merge in any additional kwargs
        call_kwargs.update(kwargs)

        try:
            response = self.client.chat.completions.create(**call_kwargs)
            content = (response.choices[0].message.content or "").strip()
            return content
        except Exception as e:
            logger.error(f"OpenAI-compatible API call failed: {e}")
            raise

    def is_available(self) -> bool:
        """
        Check if the LLM service is available by making a simple test call.

        Returns:
            bool: True if service is available
        """
        try:
            # Make a minimal test call
            self.call("test", temperature=0, max_tokens=1)
            return True
        except Exception as e:
            logger.warning(f"LLM service availability check failed: {e}")
            return False

    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model

    def get_provider_name(self) -> str:
        """Get the provider name."""
        return self.provider_name