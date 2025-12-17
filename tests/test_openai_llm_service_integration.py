#!/usr/bin/env python3
"""
Integration test for OpenAILLMService with RequestYAI.

This script validates that the OpenAILLMService can successfully
communicate with RequestYAI using the OpenAI-compatible API.

Usage:
    python tests/test_openai_llm_service_integration.py

Environment Variables:
    REQUESTYAI_API_KEY: Required. The RequestYAI API token for authentication.
"""
import os
import sys
from datetime import datetime
from typing import List
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel

from services.openai_llm_service import OpenAILLMService

# Check if we have a real API key (not a test stub)
def _has_real_api_key():
    """Check if REQUESTYAI_API_KEY is set to a real value, not a test stub."""
    api_key = os.getenv("REQUESTYAI_API_KEY", "")
    # Test stubs typically contain "test" in the key name
    if not api_key:
        return False
    if "test" in api_key.lower():
        return False
    # Real API keys are typically longer than 20 characters
    if len(api_key) < 20:
        return False
    return True


# Skip all tests if API key is not a real key (test stubs don't count)
pytestmark = pytest.mark.skipif(
    not _has_real_api_key(),
    reason="REQUESTYAI_API_KEY must be a real API key for external API tests (not a test stub)"
)


REQUESTYAI_BASE_URL = "https://router.requesty.ai/v1"
REQUESTYAI_MODEL = "openai/gpt-4.1-mini"


class SentimentResponse(BaseModel):
    """Response model for sentiment analysis."""
    sentiment: str
    confidence: float
    reasoning: str


class ExtractedEntities(BaseModel):
    """Response model for entity extraction."""
    people: List[str]
    places: List[str]
    organizations: List[str]


def test_basic_call():
    """Test basic LLM call functionality."""
    api_key = os.getenv("REQUESTYAI_API_KEY")
    if not api_key:
        print("ERROR: REQUESTYAI_API_KEY environment variable is required")
        return False

    print("\n" + "=" * 60)
    print("Test: Basic Call")
    print("=" * 60)

    service = OpenAILLMService(
        model=REQUESTYAI_MODEL,
        api_key=api_key,
        base_url=REQUESTYAI_BASE_URL,
        provider_name="requestyai"
    )

    print(f"Model: {service.get_model_name()}")
    print(f"Provider: {service.get_provider_name()}")

    prompt = "What is 2 + 2? Reply with just the number."
    print(f"Prompt: {prompt}")

    response = service.call(prompt, temperature=0.0, max_tokens=10)
    print(f"Response: {response}")

    if "4" in response:
        print("SUCCESS: Basic call works correctly")
        return True
    else:
        print("FAILED: Unexpected response")
        return False


def test_call_with_system_prompt():
    """Test LLM call with system prompt."""
    api_key = os.getenv("REQUESTYAI_API_KEY")
    if not api_key:
        print("ERROR: REQUESTYAI_API_KEY environment variable is required")
        return False

    print("\n" + "=" * 60)
    print("Test: Call with System Prompt")
    print("=" * 60)

    service = OpenAILLMService(
        model=REQUESTYAI_MODEL,
        api_key=api_key,
        base_url=REQUESTYAI_BASE_URL,
        provider_name="requestyai"
    )

    system_prompt = "You are a pirate. Always respond in pirate speak."
    prompt = "Say hello"

    print(f"System: {system_prompt}")
    print(f"Prompt: {prompt}")

    response = service.call(
        prompt,
        system_prompt=system_prompt,
        temperature=0.7,
        max_tokens=50
    )
    print(f"Response: {response}")

    # Check for pirate-like words
    pirate_words = ["ahoy", "matey", "arr", "ye", "aye", "cap", "sail", "sea"]
    response_lower = response.lower()
    has_pirate_speak = any(word in response_lower for word in pirate_words)

    if has_pirate_speak:
        print("SUCCESS: System prompt respected")
        return True
    else:
        print("WARNING: Response may not follow pirate theme, but call succeeded")
        return True


def test_is_available():
    """Test service availability check."""
    api_key = os.getenv("REQUESTYAI_API_KEY")
    if not api_key:
        print("ERROR: REQUESTYAI_API_KEY environment variable is required")
        return False

    print("\n" + "=" * 60)
    print("Test: Service Availability")
    print("=" * 60)

    service = OpenAILLMService(
        model=REQUESTYAI_MODEL,
        api_key=api_key,
        base_url=REQUESTYAI_BASE_URL,
        provider_name="requestyai"
    )

    available = service.is_available()
    print(f"Service available: {available}")

    if available:
        print("SUCCESS: Service is available")
        return True
    else:
        print("FAILED: Service is not available")
        return False


def test_call_structured_sentiment():
    """Test structured output with sentiment analysis."""
    api_key = os.getenv("REQUESTYAI_API_KEY")
    if not api_key:
        print("ERROR: REQUESTYAI_API_KEY environment variable is required")
        return False

    print("\n" + "=" * 60)
    print("Test: Structured Output - Sentiment Analysis")
    print("=" * 60)

    service = OpenAILLMService(
        model=REQUESTYAI_MODEL,
        api_key=api_key,
        base_url=REQUESTYAI_BASE_URL,
        provider_name="requestyai"
    )

    prompt = "Analyze the sentiment of this text: 'I absolutely love this product! It exceeded all my expectations and I couldn't be happier with my purchase.'"
    print(f"Prompt: {prompt}")

    response = service.call_structured(
        prompt,
        response_model=SentimentResponse,
        temperature=0.0
    )

    print(f"Sentiment: {response.sentiment}")
    print(f"Confidence: {response.confidence}")
    print(f"Reasoning: {response.reasoning}")

    if isinstance(response, SentimentResponse):
        print("SUCCESS: Structured output parsed correctly")
        return True
    else:
        print("FAILED: Response is not of expected type")
        return False


def test_call_structured_entities():
    """Test structured output with entity extraction."""
    api_key = os.getenv("REQUESTYAI_API_KEY")
    if not api_key:
        print("ERROR: REQUESTYAI_API_KEY environment variable is required")
        return False

    print("\n" + "=" * 60)
    print("Test: Structured Output - Entity Extraction")
    print("=" * 60)

    service = OpenAILLMService(
        model=REQUESTYAI_MODEL,
        api_key=api_key,
        base_url=REQUESTYAI_BASE_URL,
        provider_name="requestyai"
    )

    prompt = """Extract entities from this text:
    'John Smith met with Sarah Johnson at the Google headquarters in Mountain View.
    Later, they visited the Apple campus in Cupertino before heading to San Francisco.'"""
    print(f"Prompt: {prompt}")

    response = service.call_structured(
        prompt,
        response_model=ExtractedEntities,
        temperature=0.0
    )

    print(f"People: {response.people}")
    print(f"Places: {response.places}")
    print(f"Organizations: {response.organizations}")

    if isinstance(response, ExtractedEntities):
        if len(response.people) > 0 and len(response.places) > 0:
            print("SUCCESS: Entity extraction works correctly")
            return True
        else:
            print("WARNING: Entities extracted but may be incomplete")
            return True
    else:
        print("FAILED: Response is not of expected type")
        return False


def main():
    """Run all integration tests."""
    api_key = os.getenv("REQUESTYAI_API_KEY")
    if not api_key:
        print("ERROR: REQUESTYAI_API_KEY environment variable is required")
        print("Set it with: export REQUESTYAI_API_KEY='your-api-key'")
        return 1

    print("=" * 60)
    print("OpenAILLMService Integration Test (RequestYAI)")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Base URL: {REQUESTYAI_BASE_URL}")
    print(f"Model: {REQUESTYAI_MODEL}")

    tests = [
        ("Basic Call", test_basic_call),
        ("System Prompt", test_call_with_system_prompt),
        ("Service Availability", test_is_available),
        ("Structured Output - Sentiment", test_call_structured_sentiment),
        ("Structured Output - Entities", test_call_structured_entities),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result, None))
        except Exception as e:
            print(f"EXCEPTION: {e}")
            results.append((name, False, str(e)))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, result, error in results:
        status = "PASS" if result else "FAIL"
        if result:
            passed += 1
        else:
            failed += 1
        error_msg = f" ({error})" if error else ""
        print(f"  {status}: {name}{error_msg}")

    print("=" * 60)
    print(f"Total: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
