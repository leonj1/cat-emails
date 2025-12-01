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
    Currently empty as the send_logs flag has been removed.
    Additional feature flags can be added as needed.
    """

    @classmethod
    def from_environment(cls, env_vars: dict) -> "FeatureFlags":
        """
        Create FeatureFlags from a dictionary of environment variables.

        Args:
            env_vars (dict): Dictionary of environment variables

        Returns:
            FeatureFlags: Immutable instance with parsed feature flags
        """
        return cls()
