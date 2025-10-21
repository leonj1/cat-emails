"""
Service for validating user data structure and content.

This service was extracted from UserDataProcessor.validate_user_data
to follow the single responsibility principle and keep functions under 30 lines.
"""

from typing import Dict, Protocol
from datetime import datetime


class LoggerInterface(Protocol):
    """Protocol for logger dependency injection."""

    def log(self, message: str) -> None:
        """Log a message."""
        ...


class ValidateUserDataService:
    """
    Service class for validating user data.

    All dependencies are injected via constructor to avoid direct
    environment variable access or client instantiation.
    """

    def __init__(self, logger: LoggerInterface = None):
        """
        Initialize the validation service.

        Args:
            logger: Optional logger interface for logging validation messages
        """
        self.logger = logger

    def validate(self, user: Dict) -> bool:
        """
        Validate user data structure and content.

        Args:
            user: Dictionary containing user data to validate

        Returns:
            bool: True if validation passes, False otherwise
        """
        if not self._validate_required_fields(user):
            return False

        if not self._validate_email(user):
            return False

        if not self._validate_name(user):
            return False

        if not self._validate_created_at(user):
            return False

        if not self._validate_optional_fields(user):
            return False

        self._log("User data validated successfully")
        return True

    def _validate_required_fields(self, user: Dict) -> bool:
        """Validate that all required fields are present."""
        required_fields = ["id", "email", "name", "created_at"]
        for field in required_fields:
            if field not in user:
                self._log(f"Missing required field: {field}")
                return False
        return True

    def _validate_email(self, user: Dict) -> bool:
        """Validate email format."""
        email = user.get("email", "")
        if "@" not in email or "." not in email:
            self._log(f"Invalid email format: {email}")
            return False
        return True

    def _validate_name(self, user: Dict) -> bool:
        """Validate name length."""
        name = user.get("name", "")
        if len(name) < 2:
            self._log(f"Name too short: {name}")
            return False
        return True

    def _validate_created_at(self, user: Dict) -> bool:
        """Validate creation date format."""
        try:
            datetime.fromisoformat(user["created_at"])
            return True
        except (ValueError, TypeError):
            self._log(f"Invalid created_at date: {user.get('created_at')}")
            return False

    def _validate_optional_fields(self, user: Dict) -> bool:
        """Validate optional fields if present."""
        if not self._validate_age(user):
            return False

        if not self._validate_phone(user):
            return False

        return True

    def _validate_age(self, user: Dict) -> bool:
        """Validate age if present."""
        if "age" in user:
            age = user["age"]
            if not isinstance(age, int) or age < 0 or age > 150:
                self._log(f"Invalid age: {age}")
                return False
        return True

    def _validate_phone(self, user: Dict) -> bool:
        """Validate phone number if present."""
        if "phone" in user:
            phone = user["phone"]
            if not phone.replace("-", "").replace(" ", "").isdigit():
                self._log(f"Invalid phone: {phone}")
                return False
        return True

    def _log(self, message: str) -> None:
        """Log a message using the injected logger or print."""
        if self.logger:
            self.logger.log(message)
        else:
            print(message)
