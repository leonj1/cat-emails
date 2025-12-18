from pydantic import BaseModel, Field, validator
from typing import Optional


class CreateAccountRequest(BaseModel):
    """Request model for creating new accounts"""
    email_address: str = Field(..., description="Gmail email address")
    app_password: Optional[str] = Field(
        None,
        description="Gmail app-specific password for IMAP access (required if auth_method is 'imap')"
    )
    display_name: Optional[str] = Field(None, description="Optional display name for the account")
    auth_method: str = Field(
        default="imap",
        description="Authentication method: 'imap' for app password or 'oauth' for OAuth 2.0"
    )
    oauth_refresh_token: Optional[str] = Field(
        None,
        description="OAuth refresh token (only used if auth_method is 'oauth')"
    )

    @validator('auth_method')
    def validate_auth_method(cls, v):
        """Ensure auth_method is valid."""
        valid_methods = ['imap', 'oauth']
        if v not in valid_methods:
            raise ValueError(f"auth_method must be one of: {valid_methods}")
        return v

    @validator('app_password', always=True)
    def validate_app_password(cls, v, values):
        """Ensure app_password is provided for IMAP auth."""
        auth_method = values.get('auth_method', 'imap')
        if auth_method == 'imap' and not v:
            raise ValueError("app_password is required when auth_method is 'imap'")
        return v

    @validator('oauth_refresh_token', always=True)
    def validate_oauth_refresh_token(cls, v, values):
        """Ensure oauth_refresh_token is provided for OAuth auth."""
        auth_method = values.get('auth_method', 'imap')
        if auth_method == 'oauth' and not v:
            raise ValueError("oauth_refresh_token is required when auth_method is 'oauth'")
        return v
