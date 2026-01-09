"""
State Token Validator for OAuth State Init Endpoint.

Validates state tokens according to the following rules:
- Length: 16-64 characters
- Characters: alphanumeric and dashes only (^[a-zA-Z0-9-]+$)
- Required: non-empty, non-whitespace
"""

import re
from typing import Optional, Tuple


class StateTokenValidator:
    """Validates OAuth state tokens for format and security requirements."""

    MIN_LENGTH = 16
    MAX_LENGTH = 64
    VALID_PATTERN = re.compile(r'^[a-zA-Z0-9-]+$')

    def validate(self, token: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Validate a state token.

        Args:
            token: The state token to validate (may be None)

        Returns:
            Tuple of (error_code, error_message) if invalid
            Tuple of (None, None) if valid

        Error codes:
            - invalid_request: Missing token (None)
            - invalid_state_token: Format validation failed
        """
        # Check if token is None (missing field)
        if token is None:
            return "invalid_request", "State token is required"

        # Check if token is empty or whitespace-only
        if not token.strip():
            return "invalid_state_token", "State token is required"

        # Check minimum length
        if len(token) < self.MIN_LENGTH:
            return "invalid_state_token", f"State token must be at least {self.MIN_LENGTH} characters"

        # Check maximum length
        if len(token) > self.MAX_LENGTH:
            return "invalid_state_token", f"State token must not exceed {self.MAX_LENGTH} characters"

        # Check character pattern (alphanumeric and dashes only)
        if not self.VALID_PATTERN.match(token):
            return "invalid_state_token", "State token must contain only alphanumeric characters and dashes"

        return None, None
