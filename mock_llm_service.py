from typing import Union, Dict, Any
from pydantic import BaseModel
from llm_service_interface import ILLMService, ErrorResponse


class MockLLMService(ILLMService):
    """
    Mock implementation of ILLMService for testing purposes.
    Allows predefined responses without making actual LLM API calls.
    """

    def __init__(self, mock_responses: Dict[str, Any] = None, simulate_error: bool = False,
                 error_type: str = "APIError", error_message: str = "Mock error"):
        """
        Initialize the Mock LLM Service.

        Args:
            mock_responses: Dictionary mapping message substrings to mock response data
            simulate_error: If True, always return an error response
            error_type: Type of error to simulate
            error_message: Error message to return when simulating errors
        """
        self.mock_responses = mock_responses or {}
        self.simulate_error = simulate_error
        self.error_type = error_type
        self.error_message = error_message
        self.query_count = 0
        self.last_message = None
        self.last_response_model = None

    def query(self, message: str, response_model: type[BaseModel]) -> Union[BaseModel, ErrorResponse]:
        """
        Query the mock LLM service with a message.

        Args:
            message: The message/prompt to send to the LLM
            response_model: Pydantic model class to parse the response into

        Returns:
            Union[BaseModel, ErrorResponse]: Either the mocked response or an error response
        """
        # Track query for testing/debugging
        self.query_count += 1
        self.last_message = message
        self.last_response_model = response_model

        # Simulate error if configured
        if self.simulate_error:
            return ErrorResponse(
                error=self.error_message,
                error_type=self.error_type
            )

        # Find matching mock response
        for key, mock_data in self.mock_responses.items():
            if key.lower() in message.lower():
                try:
                    # If mock_data is already a dict with the right structure
                    if isinstance(mock_data, dict):
                        return response_model(**mock_data)
                    # If mock_data is a string (for simple responses)
                    elif isinstance(mock_data, str):
                        return response_model(contents=mock_data)
                    # If mock_data is already an instance of the response model
                    elif isinstance(mock_data, BaseModel):
                        return mock_data
                except Exception as e:
                    return ErrorResponse(
                        error=f"Failed to create mock response: {str(e)}",
                        error_type="MockDataError"
                    )

        # No matching response found - return default error
        return ErrorResponse(
            error=f"No mock response configured for message: {message[:50]}...",
            error_type="NoMockResponseError"
        )

    def reset_stats(self):
        """Reset tracking statistics."""
        self.query_count = 0
        self.last_message = None
        self.last_response_model = None

    def add_mock_response(self, key: str, response_data: Any):
        """Add a new mock response mapping."""
        self.mock_responses[key] = response_data

    def set_error_mode(self, enabled: bool, error_type: str = None, error_message: str = None):
        """Enable or disable error simulation mode."""
        self.simulate_error = enabled
        if error_type:
            self.error_type = error_type
        if error_message:
            self.error_message = error_message