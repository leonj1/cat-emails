"""
Unit tests for ValidateUserDataService.

Tests cover happy path and edge cases for user data validation.
"""

import unittest
from datetime import datetime
from services.userdataprocessor_validate_user_data_service import (
    ValidateUserDataService,
    LoggerInterface
)


class MockLogger:
    """Mock logger for testing."""

    def __init__(self):
        self.messages = []

    def log(self, message: str) -> None:
        """Capture log messages."""
        self.messages.append(message)


class TestValidateUserDataService(unittest.TestCase):
    """Test cases for ValidateUserDataService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_logger = MockLogger()
        self.service = ValidateUserDataService(logger=self.mock_logger)
        self.service_no_logger = ValidateUserDataService()

    def test_valid_user_data_minimal(self):
        """Test validation with minimal valid user data."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00"
        }
        result = self.service.validate(user)
        self.assertTrue(result)
        self.assertIn("User data validated successfully", self.mock_logger.messages)

    def test_valid_user_data_with_optional_fields(self):
        """Test validation with optional fields."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00",
            "age": 30,
            "phone": "123-456-7890"
        }
        result = self.service.validate(user)
        self.assertTrue(result)

    def test_missing_id_field(self):
        """Test validation fails when id is missing."""
        user = {
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00"
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertIn("Missing required field: id", self.mock_logger.messages)

    def test_missing_email_field(self):
        """Test validation fails when email is missing."""
        user = {
            "id": "123",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00"
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertIn("Missing required field: email", self.mock_logger.messages)

    def test_missing_name_field(self):
        """Test validation fails when name is missing."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "created_at": "2023-01-01T00:00:00"
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertIn("Missing required field: name", self.mock_logger.messages)

    def test_missing_created_at_field(self):
        """Test validation fails when created_at is missing."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe"
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertIn("Missing required field: created_at", self.mock_logger.messages)

    def test_invalid_email_no_at_symbol(self):
        """Test validation fails for email without @ symbol."""
        user = {
            "id": "123",
            "email": "userexample.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00"
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertTrue(any("Invalid email format" in msg for msg in self.mock_logger.messages))

    def test_invalid_email_no_dot(self):
        """Test validation fails for email without dot."""
        user = {
            "id": "123",
            "email": "user@examplecom",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00"
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertTrue(any("Invalid email format" in msg for msg in self.mock_logger.messages))

    def test_invalid_name_too_short(self):
        """Test validation fails for name less than 2 characters."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "J",
            "created_at": "2023-01-01T00:00:00"
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertTrue(any("Name too short" in msg for msg in self.mock_logger.messages))

    def test_invalid_name_empty(self):
        """Test validation fails for empty name."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "",
            "created_at": "2023-01-01T00:00:00"
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertTrue(any("Name too short" in msg for msg in self.mock_logger.messages))

    def test_invalid_created_at_format(self):
        """Test validation fails for invalid date format."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "not-a-date"
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertTrue(any("Invalid created_at date" in msg for msg in self.mock_logger.messages))

    def test_invalid_created_at_none(self):
        """Test validation fails for None created_at."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": None
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertTrue(any("Invalid created_at date" in msg for msg in self.mock_logger.messages))

    def test_invalid_age_negative(self):
        """Test validation fails for negative age."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00",
            "age": -5
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertTrue(any("Invalid age" in msg for msg in self.mock_logger.messages))

    def test_invalid_age_too_high(self):
        """Test validation fails for age over 150."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00",
            "age": 200
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertTrue(any("Invalid age" in msg for msg in self.mock_logger.messages))

    def test_invalid_age_not_integer(self):
        """Test validation fails for non-integer age."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00",
            "age": "thirty"
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertTrue(any("Invalid age" in msg for msg in self.mock_logger.messages))

    def test_valid_age_boundary_zero(self):
        """Test validation passes for age 0."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00",
            "age": 0
        }
        result = self.service.validate(user)
        self.assertTrue(result)

    def test_valid_age_boundary_150(self):
        """Test validation passes for age 150."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00",
            "age": 150
        }
        result = self.service.validate(user)
        self.assertTrue(result)

    def test_invalid_phone_with_letters(self):
        """Test validation fails for phone with letters."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00",
            "phone": "123-ABC-7890"
        }
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertTrue(any("Invalid phone" in msg for msg in self.mock_logger.messages))

    def test_valid_phone_with_dashes(self):
        """Test validation passes for phone with dashes."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00",
            "phone": "123-456-7890"
        }
        result = self.service.validate(user)
        self.assertTrue(result)

    def test_valid_phone_with_spaces(self):
        """Test validation passes for phone with spaces."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00",
            "phone": "123 456 7890"
        }
        result = self.service.validate(user)
        self.assertTrue(result)

    def test_valid_phone_with_mixed_separators(self):
        """Test validation passes for phone with mixed separators."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00",
            "phone": "123 456-7890"
        }
        result = self.service.validate(user)
        self.assertTrue(result)

    def test_service_without_logger(self):
        """Test service works without logger (uses print)."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00"
        }
        result = self.service_no_logger.validate(user)
        self.assertTrue(result)

    def test_empty_user_dict(self):
        """Test validation fails for empty user dict."""
        user = {}
        result = self.service.validate(user)
        self.assertFalse(result)
        self.assertTrue(any("Missing required field" in msg for msg in self.mock_logger.messages))

    def test_valid_iso_date_with_timezone(self):
        """Test validation passes for ISO date with timezone."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00+00:00"
        }
        result = self.service.validate(user)
        self.assertTrue(result)

    def test_valid_iso_date_with_microseconds(self):
        """Test validation passes for ISO date with microseconds."""
        user = {
            "id": "123",
            "email": "user@example.com",
            "name": "John Doe",
            "created_at": "2023-01-01T00:00:00.123456"
        }
        result = self.service.validate(user)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
