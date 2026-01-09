"""
Unit tests for State Token Validator.

Tests derived from Gherkin scenarios for OAuth State Init Endpoint feature.
These tests define the expected behavior for state token validation.

Scenarios covered:
- State token with minimum valid length is accepted (16 chars)
- State token with maximum valid length is accepted (64 chars)
- State token too short is rejected (<16 chars)
- State token too long is rejected (>64 chars)
- State token with spaces is rejected
- State token with special characters is rejected
- State token with underscores is rejected
- Empty state token is rejected
- Missing state token is rejected (None)
- Whitespace-only state token is rejected
"""

import pytest
from typing import Protocol, Tuple, Optional


class StateTokenValidatorProtocol(Protocol):
    """Protocol for state token validation.

    The implementation should:
    - Accept tokens 16-64 characters long
    - Only allow alphanumeric characters and dashes (^[a-zA-Z0-9-]+$)
    - Return (error_code, error_message) tuple for failures
    - Return (None, None) for valid tokens
    """

    def validate(self, token: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Validate a state token.

        Args:
            token: The state token to validate (may be None)

        Returns:
            Tuple of (error_code, error_message) if invalid
            Tuple of (None, None) if valid
        """
        ...


class TestStateTokenValidatorHappyPath:
    """Tests for valid state tokens - should all return (None, None)."""

    def test_valid_state_token_minimum_length_16_chars(self):
        """
        Scenario: State token with minimum valid length is accepted

        Given a state token exactly 16 characters long "abcdefghij123456"
        When validating the state token
        Then validation should succeed with no errors
        """
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "abcdefghij123456"  # Exactly 16 characters

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code is None, f"Expected no error code, got '{error_code}'"
        assert error_message is None, f"Expected no error message, got '{error_message}'"

    def test_valid_state_token_maximum_length_64_chars(self):
        """
        Scenario: State token with maximum valid length is accepted

        Given a state token exactly 64 characters long
        When validating the state token
        Then validation should succeed with no errors
        """
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "a" * 64  # Exactly 64 characters

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code is None, f"Expected no error code, got '{error_code}'"
        assert error_message is None, f"Expected no error message, got '{error_message}'"

    def test_valid_state_token_with_dashes(self):
        """
        Scenario: State token with dashes is accepted

        Given a valid state token "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        When validating the state token
        Then validation should succeed with no errors
        """
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code is None, f"Expected no error code, got '{error_code}'"
        assert error_message is None, f"Expected no error message, got '{error_message}'"

    def test_valid_state_token_alphanumeric_only(self):
        """
        State token with only alphanumeric characters should be valid.
        """
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "validStateToken1234567890"

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code is None, f"Expected no error code, got '{error_code}'"
        assert error_message is None, f"Expected no error message, got '{error_message}'"


class TestStateTokenValidatorLengthValidation:
    """Tests for state token length validation."""

    def test_state_token_too_short_rejected(self):
        """
        Scenario: State token too short is rejected

        Given a state token "short12345" that is only 10 characters
        When validating the state token
        Then validation should fail with error code "invalid_state_token"
        And error message "State token must be at least 16 characters"
        """
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "short12345"  # Only 10 characters

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token", f"Expected 'invalid_state_token', got '{error_code}'"
        assert error_message == "State token must be at least 16 characters", f"Unexpected message: {error_message}"

    def test_state_token_15_chars_rejected(self):
        """State token with 15 characters (just below minimum) should be rejected."""
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "a" * 15

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token"
        assert error_message == "State token must be at least 16 characters"

    def test_state_token_too_long_rejected(self):
        """
        Scenario: State token too long is rejected

        Given a state token that is 65 characters long
        When validating the state token
        Then validation should fail with error code "invalid_state_token"
        And error message "State token must not exceed 64 characters"
        """
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "a" * 65  # 65 characters

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token", f"Expected 'invalid_state_token', got '{error_code}'"
        assert error_message == "State token must not exceed 64 characters", f"Unexpected message: {error_message}"

    def test_state_token_100_chars_rejected(self):
        """State token with 100 characters should be rejected."""
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "a" * 100

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token"
        assert error_message == "State token must not exceed 64 characters"


class TestStateTokenValidatorCharacterValidation:
    """Tests for state token character validation."""

    def test_state_token_with_spaces_rejected(self):
        """
        Scenario: State token with spaces is rejected

        Given a state token "invalid state token 123"
        When validating the state token
        Then validation should fail with error code "invalid_state_token"
        And error message "State token must contain only alphanumeric characters and dashes"
        """
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "invalid state token 123"

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token", f"Expected 'invalid_state_token', got '{error_code}'"
        assert error_message == "State token must contain only alphanumeric characters and dashes", f"Unexpected message: {error_message}"

    def test_state_token_with_special_characters_rejected(self):
        """
        Scenario: State token with special characters is rejected

        Given a state token "invalid!@#$%token123456"
        When validating the state token
        Then validation should fail with error code "invalid_state_token"
        And error message "State token must contain only alphanumeric characters and dashes"
        """
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "invalid!@#$%token123456"

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token", f"Expected 'invalid_state_token', got '{error_code}'"
        assert error_message == "State token must contain only alphanumeric characters and dashes", f"Unexpected message: {error_message}"

    def test_state_token_with_underscores_rejected(self):
        """
        Scenario: State token with underscores is rejected

        Given a state token "invalid_underscore_123456"
        When validating the state token
        Then validation should fail with error code "invalid_state_token"
        And error message "State token must contain only alphanumeric characters and dashes"
        """
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "invalid_underscore_123456"

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token", f"Expected 'invalid_state_token', got '{error_code}'"
        assert error_message == "State token must contain only alphanumeric characters and dashes", f"Unexpected message: {error_message}"

    def test_state_token_with_dots_rejected(self):
        """State token with dots should be rejected."""
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "invalid.dots.token12345"

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token"
        assert error_message == "State token must contain only alphanumeric characters and dashes"

    def test_state_token_with_plus_rejected(self):
        """State token with plus signs should be rejected."""
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "invalid+plus+token12345"

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token"
        assert error_message == "State token must contain only alphanumeric characters and dashes"


class TestStateTokenValidatorEmptyAndMissing:
    """Tests for empty and missing state tokens."""

    def test_empty_state_token_rejected(self):
        """
        Scenario: Empty state token is rejected

        Given an empty state token ""
        When validating the state token
        Then validation should fail with error code "invalid_state_token"
        And error message "State token is required"
        """
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = ""

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token", f"Expected 'invalid_state_token', got '{error_code}'"
        assert error_message == "State token is required", f"Unexpected message: {error_message}"

    def test_missing_state_token_rejected(self):
        """
        Scenario: Missing state token field is rejected

        Given a request body without a state_token field (None)
        When validating the state token
        Then validation should fail with error code "invalid_request"
        And error message "State token is required"
        """
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = None

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_request", f"Expected 'invalid_request', got '{error_code}'"
        assert error_message == "State token is required", f"Unexpected message: {error_message}"

    def test_whitespace_only_state_token_rejected(self):
        """
        Scenario: Whitespace-only state token is rejected

        Given a state token "                " containing only spaces
        When validating the state token
        Then validation should fail with error code "invalid_state_token"
        And error message "State token is required"
        """
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "                "  # 16 spaces

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token", f"Expected 'invalid_state_token', got '{error_code}'"
        assert error_message == "State token is required", f"Unexpected message: {error_message}"

    def test_tab_only_state_token_rejected(self):
        """State token containing only tabs should be rejected."""
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "\t\t\t\t"

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token"
        assert error_message == "State token is required"

    def test_newline_only_state_token_rejected(self):
        """State token containing only newlines should be rejected."""
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "\n\n\n\n"

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code == "invalid_state_token"
        assert error_message == "State token is required"


class TestStateTokenValidatorEdgeCases:
    """Edge case tests for state token validation."""

    def test_valid_token_with_leading_dash(self):
        """Token starting with a dash should be valid."""
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "-abcdefghij12345"  # 16 chars, starts with dash

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_valid_token_with_trailing_dash(self):
        """Token ending with a dash should be valid."""
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "abcdefghij12345-"  # 16 chars, ends with dash

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_valid_token_all_dashes(self):
        """Token with only dashes should be valid if length is correct."""
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "-" * 16

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_valid_token_uppercase_letters(self):
        """Token with uppercase letters should be valid."""
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "ABCDEFGHIJ123456"

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_valid_token_mixed_case(self):
        """Token with mixed case should be valid."""
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "AbCdEfGhIj123456"

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code is None
        assert error_message is None

    def test_valid_token_all_numbers(self):
        """Token with only numbers should be valid if length is correct."""
        from validators.state_token_validator import StateTokenValidator

        # Arrange
        validator = StateTokenValidator()
        token = "1234567890123456"

        # Act
        error_code, error_message = validator.validate(token)

        # Assert
        assert error_code is None
        assert error_message is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
