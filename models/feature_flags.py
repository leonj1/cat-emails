"""
Feature flags module for managing application-wide feature toggles.

This module provides a FeatureFlags dataclass that loads feature toggles
from environment variables. The dataclass is immutable (frozen) to prevent
accidental modification of feature flags during runtime.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureFlags:
    """
    Feature flags parsed from environment variables.

    Frozen (immutable) dataclass that holds feature flag values.

    Attributes:
        send_logs (bool): Whether to send logs. Parsed from SEND_LOGS env var.
    """
    send_logs: bool

    @classmethod
    def from_environment(cls, env_vars: dict) -> "FeatureFlags":
        """
        Create FeatureFlags from a dictionary of environment variables.

        Args:
            env_vars (dict): Dictionary of environment variables

        Returns:
            FeatureFlags: Immutable instance with parsed feature flags

        SEND_LOGS parsing rules:
            - Truthy values: "true", "1", "yes" (case-insensitive)
            - All other values default to False (including missing, empty, "false", "0", "no", invalid strings)
            - Whitespace is stripped before comparison

        Examples:
            >>> flags = FeatureFlags.from_environment({"SEND_LOGS": "true"})
            >>> flags.send_logs
            True

            >>> flags = FeatureFlags.from_environment({"SEND_LOGS": "false"})
            >>> flags.send_logs
            False

            >>> flags = FeatureFlags.from_environment({})
            >>> flags.send_logs
            False
        """
        send_logs_raw = env_vars.get("SEND_LOGS", "").lower().strip()
        send_logs = send_logs_raw in ("true", "1", "yes")
        return cls(send_logs=send_logs)
