"""
Example usage of PydanticAIService for email categorization.
This demonstrates how to use the service with the existing email models,
and shows the interface pattern for easy testing and mocking.
"""

from llm_service_interface import ILLMService, ErrorResponse
from pydantic_ai_service import PydanticAIService
from mock_llm_service import MockLLMService
from models.categorized_email import CategorizedEmail
from models.email_category import EmailCategory


def categorize_email_with_service(service: ILLMService, email_subject: str, email_body: str):
    """
    Generic function that works with any ILLMService implementation.
    This demonstrates the power of the interface pattern.
    """
    # Construct the prompt
    prompt = f"""
Categorize this email into one of these categories: {EmailCategory.all_categories()}

Email Subject: {email_subject}
Email Body: {email_body}

Return a JSON response with the category.
"""

    # Query the LLM
    response = service.query(prompt, CategorizedEmail)

    # Handle the response using type checking
    if isinstance(response, ErrorResponse):
        print(f"Error occurred: {response.error}")
        print(f"Error type: {response.error_type}")
        return None
    else:
        print(f"Category: {response.category}")
        print(f"Contents: {response.contents}")
        return response


def categorize_email_example():
    """Example: Categorize an email using PydanticAIService"""

    # Initialize the real service
    service = PydanticAIService(
        model="openai/gpt-4o",  # or "llama3.2:latest" for Ollama
        api_token="YOUR_API_TOKEN",
        base_url="https://router.requesty.ai/v1"
    )

    # Example email content
    email_subject = "Your monthly bank statement is ready"
    email_body = "Dear customer, your bank statement for January is now available in your online banking portal."

    # Use the generic function that works with any ILLMService
    return categorize_email_with_service(service, email_subject, email_body)


def example_with_ollama():
    """Example: Using the service with local Ollama"""

    service = PydanticAIService(
        model="llama3.2:latest",
        api_token="ollama",  # Ollama doesn't validate this
        base_url="http://10.1.1.74:11434/v1"
    )

    email_subject = "Limited Time Offer!"
    email_body = "Buy now! 50% off all products this weekend only!"

    return categorize_email_with_service(service, email_subject, email_body)


def example_with_mock():
    """Example: Using MockLLMService for testing without API calls"""

    # Setup mock responses
    mock_responses = {
        "bank statement": {
            "contents": "Your monthly bank statement is ready",
            "category": EmailCategory.FINANCIAL
        },
        "50% off": {
            "contents": "Buy now! 50% off all products",
            "category": EmailCategory.CONSUMER_ACTION
        }
    }

    service = MockLLMService(mock_responses=mock_responses)

    # Test with financial email
    print("\nTest 1: Financial email")
    email_subject = "Your monthly bank statement"
    email_body = "Your statement is ready for review."
    categorize_email_with_service(service, email_subject, email_body)

    # Test with marketing email
    print("\nTest 2: Marketing email")
    email_subject = "Limited Time Offer!"
    email_body = "Buy now! 50% off all products this weekend only!"
    categorize_email_with_service(service, email_subject, email_body)

    # Show query statistics
    print(f"\nTotal queries made: {service.query_count}")


if __name__ == "__main__":
    print("Example 1: Categorize email with Requesty API")
    print("-" * 50)
    categorize_email_example()

    print("\n\nExample 2: Categorize with local Ollama")
    print("-" * 50)
    example_with_ollama()

    print("\n\nExample 3: Using Mock Service for Testing")
    print("-" * 50)
    example_with_mock()