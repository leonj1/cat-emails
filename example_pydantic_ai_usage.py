"""
Example usage of PydanticAIService for email categorization.
This demonstrates how to use the service with the existing email models.
"""

from pydantic_ai_service import PydanticAIService, ErrorResponse
from models.categorized_email import CategorizedEmail
from models.email_category import EmailCategory


def categorize_email_example():
    """Example: Categorize an email using PydanticAIService"""

    # Initialize the service
    service = PydanticAIService(
        model="openai/gpt-4o",  # or "llama3.2:latest" for Ollama
        api_token="YOUR_API_TOKEN",
        base_url="https://router.requesty.ai/v1"
    )

    # Example email content
    email_subject = "Your monthly bank statement is ready"
    email_body = "Dear customer, your bank statement for January is now available in your online banking portal."

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


def example_with_ollama():
    """Example: Using the service with local Ollama"""

    service = PydanticAIService(
        model="llama3.2:latest",
        api_token="ollama",  # Ollama doesn't validate this
        base_url="http://10.1.1.74:11434/v1"
    )

    email_content = "Buy now! 50% off all products this weekend only!"
    prompt = f"Categorize this email: {email_content}"

    response = service.query(prompt, CategorizedEmail)

    if isinstance(response, ErrorResponse):
        print(f"Error: {response.error}")
    else:
        print(f"Successfully categorized as: {response.category}")


if __name__ == "__main__":
    print("Example 1: Categorize email with Requesty API")
    print("-" * 50)
    categorize_email_example()

    print("\n\nExample 2: Categorize with local Ollama")
    print("-" * 50)
    example_with_ollama()