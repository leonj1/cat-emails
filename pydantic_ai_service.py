from typing import Union
import openai
from pydantic import BaseModel, Field, ValidationError


class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: str = Field(description="Error message describing what went wrong")
    error_type: str = Field(description="Type of error that occurred")


class PydanticAIService:
    """
    Service class for interacting with LLM providers using OpenAI-compatible API.
    Uses Pydantic models for structured responses and typed error handling.
    """

    def __init__(self, model: str, api_token: str, base_url: str = "https://router.requesty.ai/v1"):
        """
        Initialize the Pydantic AI Service.

        Args:
            model: The model identifier (e.g., "openai/gpt-4o", "llama3.2:latest")
            api_token: API token for authentication
            base_url: Base URL for the OpenAI-compatible API endpoint
        """
        self.model = model
        self.api_token = api_token
        self.base_url = base_url

        # Initialize OpenAI client
        self.client = openai.OpenAI(
            api_key=api_token,
            base_url=base_url,
        )

    def query(self, message: str, response_model: type[BaseModel]) -> Union[BaseModel, ErrorResponse]:
        """
        Query the LLM with a message and return a structured Pydantic response.

        Args:
            message: The message/prompt to send to the LLM
            response_model: Pydantic model class to parse the response into

        Returns:
            Union[BaseModel, ErrorResponse]: Either the parsed response model or an error response
        """
        try:
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": message}],
                temperature=0.1,
            )

            # Extract the content from response
            content = response.choices[0].message.content

            if not content:
                return ErrorResponse(
                    error="Empty response received from LLM",
                    error_type="EmptyResponseError"
                )

            # Try to parse the response into the expected Pydantic model
            try:
                # If the response is JSON, parse it directly
                parsed_response = response_model.model_validate_json(content)
                return parsed_response
            except ValidationError as ve:
                # If direct JSON parsing fails, try to extract structured data
                # This handles cases where LLM returns text instead of pure JSON
                try:
                    # Attempt to create model from the text content
                    parsed_response = response_model(contents=content)
                    return parsed_response
                except Exception:
                    return ErrorResponse(
                        error=f"Failed to validate response: {str(ve)}",
                        error_type="ValidationError"
                    )

        except openai.APIError as e:
            return ErrorResponse(
                error=f"API error: {str(e)}",
                error_type="APIError"
            )
        except openai.APIConnectionError as e:
            return ErrorResponse(
                error=f"Connection error: {str(e)}",
                error_type="ConnectionError"
            )
        except openai.RateLimitError as e:
            return ErrorResponse(
                error=f"Rate limit exceeded: {str(e)}",
                error_type="RateLimitError"
            )
        except openai.AuthenticationError as e:
            return ErrorResponse(
                error=f"Authentication failed: {str(e)}",
                error_type="AuthenticationError"
            )
        except Exception as e:
            return ErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_type="UnexpectedError"
            )