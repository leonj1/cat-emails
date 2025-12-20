# LLM Service Interface Refactoring

## Overview

The email categorization system has been refactored to use a flexible `LLMServiceInterface` abstraction layer. This allows the background service to swap between different LLM providers (OpenAI, Ollama, Anthropic, custom implementations) without modifying core business logic.

## Changes Made

### 1. New Files Created

#### `services/llm_service_interface.py`
- Abstract base class defining the interface for LLM services
- Methods: `call()`, `is_available()`, `get_model_name()`, `get_provider_name()`
- Allows any LLM provider to be plugged in by implementing this interface

#### `services/openai_llm_service.py`
- Concrete implementation of `LLMServiceInterface`
- Works with OpenAI, Ollama, RequestYAI, and any OpenAI-compatible API
- Configurable model, API key, and base URL

#### `examples/custom_llm_example.py`
- Comprehensive examples showing how to:
  - Create custom LLM implementations
  - Use mock LLMs for testing
  - Implement rule-based categorization
  - Swap LLM providers at runtime

### 2. Modified Files

#### `services/categorize_emails_llm.py`
- **Before**: Directly instantiated OpenAI client in constructor
- **After**: Accepts optional `llm_service` parameter for dependency injection
- Maintains backward compatibility with legacy approach
- Now uses injected `LLMServiceInterface` when available

**Key changes:**
```python
# New approach (recommended)
llm_service = OpenAILLMService(model="gpt-4", api_key="...")
categorizer = LLMCategorizeEmails(llm_service=llm_service)

# Legacy approach (still supported)
categorizer = LLMCategorizeEmails(
    provider="openai",
    api_token="...",
    model="gpt-4"
)
```

#### `gmail_fetcher.py`
- Added new `_make_llm_service()` function to construct LLM service instances
- Updated `_make_llm_categorizer()` to use dependency injection
- Updated `categorize_email_ell_marketing()` and `categorize_email_ell_marketing2()`
- Imports new LLM service classes

#### `CLAUDE.md`
- Added comprehensive documentation on LLM Service Interface
- Included usage examples
- Documented how to create custom implementations
- Added reference to example file

## Benefits

### 1. **Flexibility**
- Easy to swap between LLM providers (OpenAI, Ollama, Anthropic, custom)
- No need to modify core categorization logic when changing providers

### 2. **Testability**
- Can inject mock LLM services for unit testing
- No need for actual API calls during tests
- Deterministic testing possible with rule-based implementations

### 3. **Extensibility**
- Add new LLM providers by implementing `LLMServiceInterface`
- Support for custom business logic (rules, caching, fallbacks)
- Can implement provider-specific optimizations

### 4. **Maintainability**
- Clear separation of concerns
- Single Responsibility Principle: LLM logic separate from categorization logic
- Easier to debug and update individual components

### 5. **Backward Compatibility**
- Existing code continues to work without changes
- Gradual migration path to new approach
- Legacy `ell` framework still supported

## Usage Examples

### Example 1: Using the Default Implementation
```python
from services.openai_llm_service import OpenAILLMService
from services.categorize_emails_llm import LLMCategorizeEmails

# Create LLM service
llm_service = OpenAILLMService(
    model="vertex/google/gemini-2.5-flash",
    api_key=os.environ["REQUESTYAI_API_KEY"],
    base_url="https://router.requesty.ai/v1",
    provider_name="requestyai"
)

# Create categorizer with injected service
categorizer = LLMCategorizeEmails(llm_service=llm_service)

# Categorize an email
result = categorizer.category("Buy now! 50% off!")
print(result.value)  # "Advertising"
```

### Example 2: Custom Mock LLM for Testing
```python
from services.llm_service_interface import LLMServiceInterface
from services.categorize_emails_llm import LLMCategorizeEmails

class MockLLMService(LLMServiceInterface):
    def call(self, prompt, **kwargs):
        return "Marketing"

    def is_available(self):
        return True

    def get_model_name(self):
        return "mock-v1"

    def get_provider_name(self):
        return "mock"

# Use mock in tests
mock_llm = MockLLMService()
categorizer = LLMCategorizeEmails(llm_service=mock_llm)
```

### Example 3: Custom Rule-Based LLM
```python
class RuleBasedLLMService(LLMServiceInterface):
    def call(self, prompt, **kwargs):
        if "buy now" in prompt.lower():
            return "Advertising"
        elif "newsletter" in prompt.lower():
            return "Marketing"
        else:
            return "Other"

    # ... implement other methods

# Use custom rules
rule_llm = RuleBasedLLMService()
categorizer = LLMCategorizeEmails(llm_service=rule_llm)
```

## Migration Guide

### For New Code
Use the dependency injection approach:
```python
from services.openai_llm_service import OpenAILLMService
from services.categorize_emails_llm import LLMCategorizeEmails

llm_service = OpenAILLMService(model="...", api_key="...")
categorizer = LLMCategorizeEmails(llm_service=llm_service)
```

### For Existing Code
No changes required - legacy approach still works:
```python
categorizer = LLMCategorizeEmails(
    provider="requestyai",
    api_token="...",
    model="..."
)
```

## Architecture Diagram

```
┌─────────────────────────────────────┐
│     gmail_fetcher.py                │
│  (Email Processing Logic)           │
└──────────────┬──────────────────────┘
               │
               │ uses
               ▼
┌─────────────────────────────────────┐
│  LLMCategorizeEmails                │
│  (Categorization Logic)             │
└──────────────┬──────────────────────┘
               │
               │ uses (via injection)
               ▼
┌─────────────────────────────────────┐
│  LLMServiceInterface                │
│  (Abstract Interface)               │
└──────────────┬──────────────────────┘
               │
               │ implemented by
               ▼
┌─────────────────────────────────────┐
│  OpenAILLMService                   │
│  (OpenAI-compatible APIs)           │
└─────────────────────────────────────┘
               │
┌──────────────┼──────────────────────┐
│              │                       │
▼              ▼                       ▼
OpenAI       Ollama              Custom Impl
```

## Testing

Run the examples to verify the implementation:
```bash
cd /root/repo
PYTHONPATH=. python3 examples/custom_llm_example.py
```

## Future Enhancements

Potential improvements:
1. **Caching Layer**: Implement caching LLM service to reduce API calls
2. **Retry Logic**: Add automatic retry with exponential backoff
3. **Provider Fallback**: Automatic failover between multiple LLM providers
4. **Cost Tracking**: Track API usage and costs across providers
5. **Rate Limiting**: Implement rate limiting per provider
6. **Batch Processing**: Support batch categorization for efficiency

## Conclusion

The LLM service interface refactoring provides a clean, flexible architecture that:
- ✅ Maintains backward compatibility
- ✅ Enables easy LLM provider swapping
- ✅ Improves testability
- ✅ Follows SOLID principles
- ✅ Allows custom implementations

The background service can now swap to any concrete implementation of `LLMServiceInterface` by simply passing a different instance to `LLMCategorizeEmails`.