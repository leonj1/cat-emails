from __future__ import annotations

import logging
from typing import Optional

from openai import OpenAI

from services.categorize_emails_interface import (
    CategorizeEmails,
    SimpleEmailCategory,
    CategoryResult,
    CategoryError,
)

logger = logging.getLogger(__name__)


class LLMCategorizeEmails(CategorizeEmails):
    """
    Concrete implementation of CategorizeEmails using an LLM provider.

    Construction requires:
      - provider: one of {'openai', 'anthropic', 'google', 'requestyai', 'ollama'}
      - api_token: API token for the LLM provider
      - model: model name to use for categorization

    Optionally, base_url can be provided to target non-default OpenAI-compatible endpoints
    (e.g., an Ollama/OpenAI-compatible gateway). Provide the full API root as required by
    your provider (often includes a version path), for example:
      - http://localhost:11434/v1 (Ollama)
      - https://api.requesty.ai/openai/v1 (RequestYAI)
    If not provided, defaults to the provider's SDK default where applicable.
    """

    def __init__(self, provider: str, api_token: str, model: str, *, base_url: Optional[str] = None):
        if not isinstance(provider, str) or not provider.strip():
            raise ValueError("provider is required and must be a non-empty string")
        if not isinstance(api_token, str) or not api_token.strip():
            raise ValueError("api_token is required and must be a non-empty string")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model is required and must be a non-empty string")

        provider_norm = provider.strip().lower()
        supported = {"openai", "anthropic", "google", "requestyai", "ollama"}
        if provider_norm not in supported:
            raise ValueError(f"Unsupported provider: {provider}. Supported: {sorted(supported)}")

        self.provider = provider_norm
        self.model = model

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

        # If we don't have an OpenAI-compatible client wired, indicate unsupported provider for now
        if self.client is None:
            return CategoryError(
                error="UnsupportedProvider",
                detail=(
                    f"Provider '{self.provider}' is recognized but not yet wired to category(); "
                    "install and configure 'pydantic-ai' or use an OpenAI-compatible provider (openai/ollama)."
                ),
            )

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
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )
            content = (resp.choices[0].message.content or "").strip().strip('"\'')

            # Normalize and map to enum
            normalized = content.lower().replace(" ", "").replace("-", "")
            if normalized == "advertising":
                return SimpleEmailCategory.ADVERTISING
            if normalized == "marketing":
                return SimpleEmailCategory.MARKETING
            if normalized == "wantsmoney":
                return SimpleEmailCategory.WANTS_MONEY

            logger.warning(f"LLM returned unexpected category output: {content!r}")
            return CategoryError(
                error="InvalidModelOutput",
                detail=f"Expected one of Advertising|Marketing|Wants-Money, got: {content!r}",
            )
        except Exception as e:
            logger.error(f"LLM provider error: {e}")
            return CategoryError(error="ProviderError", detail=str(e))
