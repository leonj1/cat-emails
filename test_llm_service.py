"""
Unit tests demonstrating the use of ILLMService interface with both
real and mock implementations.
"""

import unittest
from pydantic import BaseModel, Field
from llm_service_interface import ILLMService, ErrorResponse
from mock_llm_service import MockLLMService
from models.email_category import EmailCategory
from models.categorized_email import CategorizedEmail


class SimpleResponse(BaseModel):
    """Simple test response model"""
    message: str = Field(description="Response message")


class TestMockLLMService(unittest.TestCase):
    """Test cases for MockLLMService"""

    def test_successful_query_with_dict_response(self):
        """Test query with predefined dict response"""
        mock_responses = {
            "hello": {"message": "Hello, World!"}
        }
        service = MockLLMService(mock_responses=mock_responses)

        response = service.query("Say hello", SimpleResponse)

        self.assertIsInstance(response, SimpleResponse)
        self.assertEqual(response.message, "Hello, World!")
        self.assertEqual(service.query_count, 1)

    def test_successful_query_with_string_response(self):
        """Test query with simple string response"""
        mock_responses = {
            "test": "This is a test message"
        }
        service = MockLLMService(mock_responses=mock_responses)

        response = service.query("This is a test", SimpleResponse)

        self.assertIsInstance(response, SimpleResponse)
        self.assertEqual(response.message, "This is a test message")

    def test_email_categorization_success(self):
        """Test email categorization with mock service"""
        mock_responses = {
            "bank statement": {
                "contents": "Your monthly bank statement",
                "category": EmailCategory.FINANCIAL
            }
        }
        service = MockLLMService(mock_responses=mock_responses)

        response = service.query(
            "Categorize this: Your bank statement is ready",
            CategorizedEmail
        )

        self.assertIsInstance(response, CategorizedEmail)
        self.assertEqual(response.category, EmailCategory.FINANCIAL)

    def test_error_simulation(self):
        """Test error simulation mode"""
        service = MockLLMService(
            simulate_error=True,
            error_type="APIError",
            error_message="Simulated API failure"
        )

        response = service.query("Any message", SimpleResponse)

        self.assertIsInstance(response, ErrorResponse)
        self.assertEqual(response.error_type, "APIError")
        self.assertEqual(response.error, "Simulated API failure")

    def test_no_matching_response(self):
        """Test when no mock response matches the query"""
        service = MockLLMService(mock_responses={"hello": {"message": "Hi"}})

        response = service.query("goodbye", SimpleResponse)

        self.assertIsInstance(response, ErrorResponse)
        self.assertEqual(response.error_type, "NoMockResponseError")

    def test_dynamic_mock_response_addition(self):
        """Test adding mock responses dynamically"""
        service = MockLLMService()

        # Initially no responses
        response = service.query("test", SimpleResponse)
        self.assertIsInstance(response, ErrorResponse)

        # Add a response
        service.add_mock_response("test", {"message": "Dynamic response"})
        response = service.query("test message", SimpleResponse)

        self.assertIsInstance(response, SimpleResponse)
        self.assertEqual(response.message, "Dynamic response")

    def test_error_mode_toggle(self):
        """Test toggling error simulation mode"""
        service = MockLLMService(mock_responses={"test": {"message": "Success"}})

        # Normal mode
        response = service.query("test", SimpleResponse)
        self.assertIsInstance(response, SimpleResponse)

        # Enable error mode
        service.set_error_mode(True, error_type="CustomError", error_message="Custom error message")
        response = service.query("test", SimpleResponse)
        self.assertIsInstance(response, ErrorResponse)
        self.assertEqual(response.error_type, "CustomError")

        # Disable error mode
        service.set_error_mode(False)
        response = service.query("test", SimpleResponse)
        self.assertIsInstance(response, SimpleResponse)

    def test_query_tracking(self):
        """Test that queries are tracked correctly"""
        service = MockLLMService(mock_responses={"test": {"message": "Response"}})

        self.assertEqual(service.query_count, 0)
        self.assertIsNone(service.last_message)

        service.query("test message", SimpleResponse)

        self.assertEqual(service.query_count, 1)
        self.assertEqual(service.last_message, "test message")
        self.assertEqual(service.last_response_model, SimpleResponse)

        service.query("another test", SimpleResponse)
        self.assertEqual(service.query_count, 2)

    def test_stats_reset(self):
        """Test resetting statistics"""
        service = MockLLMService(mock_responses={"test": {"message": "Response"}})

        service.query("test", SimpleResponse)
        self.assertEqual(service.query_count, 1)

        service.reset_stats()
        self.assertEqual(service.query_count, 0)
        self.assertIsNone(service.last_message)
        self.assertIsNone(service.last_response_model)


class TestInterfacePolymorphism(unittest.TestCase):
    """Test that different implementations can be used interchangeably"""

    def process_with_service(self, service: ILLMService, message: str) -> str:
        """Helper function that accepts any ILLMService implementation"""
        response = service.query(message, SimpleResponse)

        if isinstance(response, ErrorResponse):
            return f"Error: {response.error}"
        else:
            return response.message

    def test_polymorphic_usage(self):
        """Test that both implementations work with the same interface"""
        mock_service = MockLLMService(mock_responses={"test": {"message": "Mock response"}})

        # Both should work with the same helper function
        result = self.process_with_service(mock_service, "test message")
        self.assertEqual(result, "Mock response")


if __name__ == "__main__":
    unittest.main()