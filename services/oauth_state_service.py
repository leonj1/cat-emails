"""
OAuth State Parameter Service

Generates and validates state parameters for OAuth CSRF protection.
Uses JWT for secure, signed state tokens with expiration.
"""
import os
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
import base64
import hashlib
import hmac

from utils.logger import get_logger
from models.oauth_models import OAuthStateData

logger = get_logger(__name__)


class OAuthStateService:
    """
    Service for managing OAuth state parameters (CSRF protection).

    State parameters are JWT-like tokens that:
    - Contain metadata about the OAuth request
    - Are signed to prevent tampering
    - Expire after a short time (10 minutes)
    - Include nonce for uniqueness
    """

    def __init__(self):
        """Initialize OAuth state service."""
        self.secret = os.getenv("OAUTH_STATE_SECRET")
        self.expiry_minutes = int(os.getenv("OAUTH_STATE_EXPIRY_MINUTES", "10"))

        if not self.secret:
            error_msg = (
                "OAUTH_STATE_SECRET not configured. "
                "Set OAUTH_STATE_SECRET environment variable for secure OAuth state management."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

    def generate_state(
        self,
        customer_email: Optional[str] = None,
        account_email: Optional[str] = None
    ) -> str:
        """
        Generate a secure state parameter for OAuth authorization.

        The state parameter contains:
        - Nonce: Random UUID for uniqueness
        - Timestamp: When state was created
        - Expiration: When state expires
        - Customer email: Optional hint for login
        - Account email: Optional specific account to link

        Args:
            customer_email: Email hint for Google login
            account_email: Specific Gmail account to add after auth

        Returns:
            str: Base64url-encoded signed state token
        """
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=self.expiry_minutes)

        # Create state data
        state_data = OAuthStateData(
            nonce=secrets.token_urlsafe(16),
            timestamp=now,
            customer_email=customer_email,
            account_email=account_email,
            exp=expiry
        )

        # Convert to JSON using Pydantic serialization
        payload = state_data.model_dump(mode='json', exclude_none=True)

        # Encode payload
        payload_json = json.dumps(payload, separators=(',', ':'))
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')

        # Sign payload
        signature = self._sign(payload_b64)

        # Combine: payload.signature
        state_token = f"{payload_b64}.{signature}"

        logger.debug(f"Generated OAuth state token (expires at {expiry})")
        return state_token

    def validate_and_decode_state(self, state: str) -> dict:
        """
        Validate and decode OAuth state parameter.

        Validates:
        - State format (payload.signature)
        - Signature authenticity
        - Expiration time
        - Required fields present

        Args:
            state: State token from OAuth callback

        Returns:
            dict: Decoded state data

        Raises:
            ValueError: If state is invalid, tampered, or expired
        """
        if not state:
            raise ValueError("State parameter is required")

        # Split into payload and signature
        parts = state.split('.')
        if len(parts) != 2:
            raise ValueError("Invalid state format. Expected: payload.signature")

        payload_b64, signature = parts

        # Verify signature
        expected_signature = self._sign(payload_b64)
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("State signature verification failed. Possible CSRF attack.")

        # Decode payload
        try:
            # Add padding if needed (correct calculation using modulo)
            padding = '=' * (-len(payload_b64) % 4)
            payload_json = base64.urlsafe_b64decode(payload_b64 + padding).decode()
            payload = json.loads(payload_json)
        except Exception as e:
            raise ValueError(f"Failed to decode state payload: {e}") from e

        # Validate required fields
        if "nonce" not in payload or "timestamp" not in payload or "exp" not in payload:
            raise ValueError("State missing required fields (nonce, timestamp, exp)")

        # Parse timestamps
        try:
            timestamp = datetime.fromisoformat(payload["timestamp"])
            expiry = datetime.fromisoformat(payload["exp"])
        except Exception as e:
            raise ValueError(f"Invalid timestamp format in state: {e}") from e

        # Check expiration
        now = datetime.now(timezone.utc)
        if now >= expiry:
            raise ValueError(
                f"State expired at {expiry}. Current time: {now}. "
                "Please restart OAuth flow."
            )

        # Check if state is from the future (clock skew attack)
        if timestamp > now + timedelta(minutes=5):
            raise ValueError("State timestamp is in the future. Possible tampering.")

        logger.debug(f"Successfully validated OAuth state (nonce: {payload['nonce'][:8]}...)")

        return payload

    def _sign(self, data: str) -> str:
        """
        Sign data with HMAC-SHA256.

        Args:
            data: Data to sign

        Returns:
            str: Base64url-encoded signature
        """
        signature_bytes = hmac.new(
            self.secret.encode(),
            data.encode(),
            hashlib.sha256
        ).digest()

        signature_b64 = base64.urlsafe_b64encode(signature_bytes).decode().rstrip('=')
        return signature_b64

    def extract_customer_email(self, state_data: dict) -> Optional[str]:
        """
        Extract customer email hint from decoded state.

        Args:
            state_data: Decoded state dictionary

        Returns:
            Customer email or None
        """
        return state_data.get("customer_email")

    def extract_account_email(self, state_data: dict) -> Optional[str]:
        """
        Extract account email from decoded state.

        Args:
            state_data: Decoded state dictionary

        Returns:
            Account email or None
        """
        return state_data.get("account_email")
