from __future__ import annotations

import logging
from utils.logger import get_logger
from typing import Optional

from openai import OpenAI

from services.categorize_emails_interface import (
    CategorizeEmails,
    SimpleEmailCategory,
    CategoryResult,
    CategoryError,
)
from services.llm_service_interface import LLMServiceInterface

logger = get_logger(__name__)


class LLMCategorizeEmails(CategorizeEmails):
    """
    Concrete implementation of CategorizeEmails using an LLM service.

    This class now accepts an LLMServiceInterface implementation, allowing
    any LLM provider to be used without modifying this class.

    Construction options:
      1. Pass an llm_service instance directly (recommended)
      2. Legacy: Pass provider, api_token, model, and base_url (for backward compatibility)
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_token: Optional[str] = None,
        model: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        llm_service: Optional[LLMServiceInterface] = None
    ):
        # New approach: use injected LLM service
        if llm_service is not None:
            self.llm_service = llm_service
            self.model = llm_service.get_model_name()
            self.provider = llm_service.get_provider_name()
            logger.info(
                f"LLM categorizer initialized with injected service: "
                f"provider={self.provider}, model={self.model}"
            )
            # Legacy attributes for backward compatibility
            self.client = None
            self.agent = None
            return

        # Legacy approach: construct OpenAI client directly (for backward compatibility)
        if not isinstance(provider, str) or not provider.strip():
            raise ValueError("provider is required and must be a non-empty string (or pass llm_service)")
        if not isinstance(api_token, str) or not api_token.strip():
            raise ValueError("api_token is required and must be a non-empty string (or pass llm_service)")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model is required and must be a non-empty string (or pass llm_service)")

        provider_norm = provider.strip().lower()
        supported = {"openai", "anthropic", "google", "requestyai", "ollama"}
        if provider_norm not in supported:
            raise ValueError(f"Unsupported provider: {provider}. Supported: {sorted(supported)}")

        self.provider = provider_norm
        self.model = model
        self.llm_service = None  # Not using injected service

        logger.info(f"LLM configuration: provider={self.provider}, model={self.model}, base_url={'(default SDK)' if not base_url else base_url}")

        self.client = None  # OpenAI-compatible client when applicable
        self.agent = None   # pydantic-ai Agent when applicable

        # Provider-specific client/agent creation
        if provider_norm in {"openai", "ollama", "requestyai"}:
            # Use OpenAI SDK for OpenAI-compatible endpoints. Expect base_url to be full root (may include version path).
            client_kwargs = {"api_key": api_token}
            if base_url:
                client_kwargs["base_url"] = base_url.rstrip("/")
            self.client = OpenAI(**client_kwargs)
        else:
            # Prefer pydantic-ai Agent clients for non-OpenAI providers
            try:
                from pydantic_ai import Agent  # type: ignore
                if provider_norm == "anthropic":
                    from pydantic_ai.models.anthropic import AnthropicModel  # type: ignore
                    model_provider = AnthropicModel(model, api_key=api_token)
                elif provider_norm == "google":
                    # Gemini/Google provider in pydantic-ai
                    from pydantic_ai.models.gemini import GeminiModel  # type: ignore
                    model_provider = GeminiModel(model, api_key=api_token)
                elif provider_norm == "requestyai":
                    # Treat RequestYAI as OpenAI-compatible if using pydantic-ai
                    from pydantic_ai.models.openai import OpenAIModel  # type: ignore
                    base = base_url.rstrip("/") if base_url else None
                    model_provider = OpenAIModel(model, api_key=api_token, base_url=base)
                else:
                    raise ValueError(f"Unhandled provider: {provider}")

                # Create the agent (system prompt provided at call-time)
                self.agent = Agent(model_provider)
            except Exception as e:
                # Defer wiring until dependency is available; clearly log the situation.
                logger.warning(
                    f"pydantic-ai agent initialization failed for provider '{provider_norm}': {e}. "
                    "Install and configure 'pydantic-ai' to enable this provider."
                )

    def category(self, email_contents: str) -> CategoryResult:
        # Validate input
        if not isinstance(email_contents, str) or not email_contents.strip():
            return CategoryError(error="InvalidInput", detail="email_contents must be a non-empty string")

        # Prompt design: force a single token from the allowed set
        system_prompt = (
            "You categorize emails into commercial-intent classes. "
            "Respond with EXACTLY one of these labels and nothing else: "
            "Advertising | Marketing | Wants-Money."
        )
        user_prompt = (
            "Classify the following email strictly as one of: Advertising, Marketing, or Wants-Money.\n\n"
            f"Email:\n{email_contents}\n\n"
            "Answer with only the label, no punctuation or explanation."
        )

        try:
            # Use LLM service if available (new approach)
            if self.llm_service is not None:
                content = self.llm_service.call(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0
                )
            # Fall back to legacy OpenAI client (backward compatibility)
            elif self.client is not None:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0,
                )
                content = (resp.choices[0].message.content or "").strip()
            else:
                return CategoryError(
                    error="UnsupportedProvider",
                    detail=(
                        f"Provider '{self.provider}' is recognized but not yet wired to category(); "
                        "install and configure 'pydantic-ai' or use an OpenAI-compatible provider (openai/ollama)."
                    ),
                )

            # Clean up the response
            content = content.strip().strip('"\'')

            # Normalize and map to enum
            normalized = content.lower().replace(" ", "").replace("-", "")
            if normalized == "advertising":
                return SimpleEmailCategory.ADVERTISING
            if normalized == "marketing":
                return SimpleEmailCategory.MARKETING
            if normalized == "wants-money":
                return SimpleEmailCategory.WANTS_MONEY1
            if normalized == "wantsmoney":
                return SimpleEmailCategory.WANTS_MONEY2

            # Check for "Wants-Money" with a hyphen, in case the model returns it
            if "wants-money" in content.lower():
                return SimpleEmailCategory.WANTS_MONEY1
            if "wantsmoney" in content.lower():
                return SimpleEmailCategory.WANTS_MONEY2

            logger.warning(f"LLM returned unexpected category output: {content!r}")
            return CategoryError(
                error="InvalidModelOutput",
                detail=f"Expected one of Advertising|Marketing|Wants-Money, got: {content!r}",
            )
        except Exception as e:
            logger.error(f"LLM provider error: {e}")
            return CategoryError(error="ProviderError", detail=str(e))
