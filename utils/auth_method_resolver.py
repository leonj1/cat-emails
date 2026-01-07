"""Auth Method Resolution Logic.

This module provides utilities for determining authentication context based on
connection type (OAuth via connection_service or IMAP via app_password).

The resolver determines:
- Whether OAuth or IMAP authentication is being used
- What values should be used to update database fields
- Whether database fields should be updated at all

Pattern: None values mean "don't update this field" (preserves existing values)
"""
from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class AuthMethodContext:
    """Authentication method context resolved from connection parameters.

    This dataclass encapsulates the authentication resolution logic result,
    providing all information needed to correctly handle OAuth vs IMAP auth.

    Attributes:
        has_connection_service: Whether a connection_service was provided
        is_oauth: Whether this is an OAuth authentication
        should_update_auth_method: Whether to update auth_method in database
        auth_method: The auth_method value to set (None = don't update)
        app_password: The app_password value to set (None = don't update)
    """
    has_connection_service: bool
    is_oauth: bool
    should_update_auth_method: bool
    auth_method: Optional[str]
    app_password: Optional[str]


class AuthMethodResolver:
    """Resolves authentication method context from connection parameters.

    The resolver uses connection_service presence as the sole determinant of
    authentication type:
    - connection_service present -> OAuth (don't update auth_method/app_password)
    - connection_service absent -> IMAP (set auth_method='imap', preserve app_password)

    This prevents the bug where OAuth accounts get their auth_method
    overwritten to 'imap' during registration.
    """

    @staticmethod
    def resolve(
        connection_service: Optional[Any],
        app_password: Optional[str]
    ) -> AuthMethodContext:
        """Resolve authentication context from connection parameters.

        Args:
            connection_service: OAuth connection service object (or None)
            app_password: IMAP app password (or None/empty string)

        Returns:
            AuthMethodContext with resolution results

        Resolution Logic:
            - If connection_service is not None:
                * OAuth mode: Don't update auth_method or app_password
                * Returns: auth_method=None, app_password=None
            - If connection_service is None:
                * IMAP mode: Set auth_method='imap', preserve app_password value
                * Returns: auth_method='imap', app_password=<original value>

        Examples:
            # OAuth registration
            >>> context = AuthMethodResolver.resolve(
            ...     connection_service=oauth_service,
            ...     app_password=None
            ... )
            >>> context.is_oauth
            True
            >>> context.auth_method  # None means "don't update"
            >>> context.app_password  # None means "don't update"

            # IMAP registration
            >>> context = AuthMethodResolver.resolve(
            ...     connection_service=None,
            ...     app_password="my-app-password"
            ... )
            >>> context.is_oauth
            False
            >>> context.auth_method
            'imap'
            >>> context.app_password
            'my-app-password'
        """
        # Connection service presence is the sole determinant
        has_connection_service = connection_service is not None
        is_oauth = has_connection_service

        if is_oauth:
            # OAuth mode: Don't update auth_method or app_password
            # Return None values to preserve existing database values
            return AuthMethodContext(
                has_connection_service=True,
                is_oauth=True,
                should_update_auth_method=False,
                auth_method=None,  # Don't overwrite existing value
                app_password=None,  # Don't overwrite existing value
            )
        else:
            # IMAP mode: Set auth_method to 'imap', preserve app_password value
            # Even if app_password is None or empty string, still set auth_method
            return AuthMethodContext(
                has_connection_service=False,
                is_oauth=False,
                should_update_auth_method=True,
                auth_method='imap',
                app_password=app_password,  # Preserve original value (None, '', or actual password)
            )
