"""
Example: Using a custom LLM implementation with the email categorizer

This example demonstrates how to create a custom LLM service implementation
and use it with the email categorization system.
"""

import os
from constants import DEFAULT_REQUESTYAI_BASE_URL
from services.llm_service_interface import LLMServiceInterface
from services.categorize_emails_llm import LLMCategorizeEmails
from services.openai_llm_service import OpenAILLMService
from services.categorize_emails_interface import SimpleEmailCategory


# Example 1: Custom Mock LLM Service (for testing)
class MockLLMService(LLMServiceInterface):
    """A mock LLM service that always returns 'Marketing'"""

    def __init__(self):
        self.call_count = 0

    def call(self, prompt, system_prompt=None, temperature=0.0, max_tokens=None, **kwargs):
        """Return a fixed response for testing"""
        self.call_count += 1
        return "Marketing"

    def is_available(self):
        return True

    def get_model_name(self):
        return "mock-model-v1"

    def get_provider_name(self):
        return "mock"


# Example 2: Custom LLM with custom logic
class CustomRuleLLMService(LLMServiceInterface):
    """
    A custom LLM service that uses simple rules instead of calling an actual LLM.
    Useful for testing or when you want deterministic categorization.
    """

    def call(self, prompt, system_prompt=None, temperature=0.0, max_tokens=None, **kwargs):
        """Apply simple rules to categorize emails"""
        prompt_lower = prompt.lower()

        if any(word in prompt_lower for word in ["buy now", "shop", "sale", "discount"]):
            return "Advertising"
        elif any(word in prompt_lower for word in ["newsletter", "update", "blog"]):
            return "Marketing"
        elif any(word in prompt_lower for word in ["payment", "invoice", "donate", "subscription"]):
            return "Wants-Money"
        else:
            return "Other"

    def is_available(self):
        return True

    def get_model_name(self):
        return "custom-rules-v1"

    def get_provider_name(self):
        return "custom"


def example_with_mock_llm():
    """Example using the mock LLM service"""
    print("=== Example 1: Using Mock LLM Service ===\n")

    # Create mock LLM service
    mock_llm = MockLLMService()

    # Create categorizer with mock LLM
    categorizer = LLMCategorizeEmails(llm_service=mock_llm)

    # Test categorization
    test_email = "Check out our amazing deals on laptops!"
    result = categorizer.category(test_email)

    print(f"Email: {test_email}")
    print(f"Category: {result.value if isinstance(result, SimpleEmailCategory) else result}")
    print(f"LLM calls made: {mock_llm.call_count}")
    print()


def example_with_custom_rules():
    """Example using the custom rule-based LLM service"""
    print("=== Example 2: Using Custom Rule-Based LLM Service ===\n")

    # Create custom LLM service
    custom_llm = CustomRuleLLMService()

    # Create categorizer with custom LLM
    categorizer = LLMCategorizeEmails(llm_service=custom_llm)

    # Test multiple emails
    test_emails = [
        "Buy now! 50% off all products!",
        "Here's our weekly newsletter with updates",
        "Please pay your invoice by end of month",
        "Hi, how are you doing today?"
    ]

    for email in test_emails:
        result = categorizer.category(email)
        category = result.value if isinstance(result, SimpleEmailCategory) else "Other"
        print(f"Email: {email}")
        print(f"Category: {category}\n")


def example_with_real_llm():
    """Example using the real OpenAI-compatible LLM service"""
    print("=== Example 3: Using Real LLM Service (OpenAI/RequestYAI) ===\n")

    # Get API credentials from environment
    api_key = os.environ.get("REQUESTYAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("REQUESTYAI_BASE_URL", DEFAULT_REQUESTYAI_BASE_URL)
    model = "vertex/google/gemini-2.5-flash"

    if not api_key:
        print("⚠️  Skipping real LLM example: No API key found in environment")
        print("Set REQUESTYAI_API_KEY or OPENAI_API_KEY to run this example\n")
        return

    # Create OpenAI-compatible LLM service
    llm_service = OpenAILLMService(
        model=model,
        api_key=api_key,
        base_url=base_url,
        provider_name="requestyai"
    )

    # Create categorizer with real LLM
    categorizer = LLMCategorizeEmails(llm_service=llm_service)

    # Test categorization
    test_email = "Don't miss out on our exclusive summer sale! Get 30% off all items."
    result = categorizer.category(test_email)

    print(f"Email: {test_email}")
    print(f"Category: {result.value if isinstance(result, SimpleEmailCategory) else result}")
    print(f"Provider: {llm_service.get_provider_name()}")
    print(f"Model: {llm_service.get_model_name()}\n")


def example_swapping_llm_at_runtime():
    """Example showing how to swap LLM implementations at runtime"""
    print("=== Example 4: Swapping LLM Implementations ===\n")

    test_email = "Subscribe to our premium service for just $9.99/month"

    # Test with mock LLM
    mock_llm = MockLLMService()
    categorizer1 = LLMCategorizeEmails(llm_service=mock_llm)
    result1 = categorizer1.category(test_email)
    print(f"Mock LLM result: {result1.value if isinstance(result1, SimpleEmailCategory) else result1}")

    # Test with custom rules LLM
    custom_llm = CustomRuleLLMService()
    categorizer2 = LLMCategorizeEmails(llm_service=custom_llm)
    result2 = categorizer2.category(test_email)
    print(f"Custom LLM result: {result2.value if isinstance(result2, SimpleEmailCategory) else result2}")

    print("\n✅ Successfully swapped between different LLM implementations!\n")


if __name__ == "__main__":
    print("Custom LLM Implementation Examples\n")
    print("=" * 60)
    print()

    example_with_mock_llm()
    example_with_custom_rules()
    example_swapping_llm_at_runtime()
    example_with_real_llm()

    print("=" * 60)
    print("\n✅ All examples completed!")
    print("\nKey takeaways:")
    print("1. You can create custom LLM implementations by extending LLMServiceInterface")
    print("2. Swap implementations by passing different llm_service instances to LLMCategorizeEmails")
    print("3. Use mock services for testing without API calls")
    print("4. Use custom rule-based services for deterministic behavior")