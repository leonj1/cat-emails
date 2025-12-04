import os
from services.llm_service_factory_interface import LLMServiceFactoryInterface
from services.llm_service_interface import LLMServiceInterface
from services.openai_llm_service import OpenAILLMService


class LLMServiceFactory(LLMServiceFactoryInterface):
    """Default implementation of LLMServiceFactoryInterface for creating LLM services."""

    def create_service(self, model: str) -> LLMServiceInterface:
        """
        Create an LLM service instance for email categorization.

        Args:
            model: The model identifier to use

        Returns:
            LLMServiceInterface: An initialized LLM service instance configured
                                 with RequestYAI/OpenAI settings from environment
        """
        base_url = (
            os.environ.get("REQUESTYAI_BASE_URL")
            or os.environ.get("REQUESTY_BASE_URL")
            or "https://router.requesty.ai/v1"
        )
        api_key = (
            os.environ.get("REQUESTYAI_API_KEY")
            or os.environ.get("REQUESTY_API_KEY")
            or os.environ.get("OPENAI_API_KEY", "")
        )
        return OpenAILLMService(
            model=model,
            api_key=api_key,
            base_url=base_url,
            provider_name="requestyai"
        )
