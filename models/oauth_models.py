"""
Models for OAuth authentication flow and token management.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class OAuthAuthorizeResponse(BaseModel):
    """Response containing the Google OAuth authorization URL."""
    authorization_url: str = Field(
        description="URL to redirect user to for Google OAuth consent"
    )
    state: str = Field(
        description="CSRF protection state token to validate callback"
    )


class OAuthCallbackRequest(BaseModel):
    """Request model for OAuth callback after user consent."""
    code: str = Field(
        description="Authorization code from Google OAuth callback"
    )
    state: str = Field(
        description="State token to validate against CSRF attacks"
    )


class OAuthCallbackResponse(BaseModel):
    """Response after successful OAuth token exchange."""
    success: bool = Field(
        description="Whether the OAuth flow completed successfully"
    )
    email_address: str = Field(
        description="Email address of the authenticated account"
    )
    scopes: List[str] = Field(
        description="List of granted OAuth scopes"
    )


class OAuthStatusResponse(BaseModel):
    """Response containing OAuth connection status for an account."""
    connected: bool = Field(
        description="Whether OAuth is configured and tokens are present"
    )
    auth_method: str = Field(
        description="Authentication method: 'imap' or 'oauth'"
    )
    scopes: Optional[List[str]] = Field(
        None,
        description="Granted OAuth scopes (only present if connected via OAuth)"
    )
    token_expiry: Optional[datetime] = Field(
        None,
        description="When the current access token expires (only present if connected via OAuth)"
    )


class OAuthTokens(BaseModel):
    """Internal model for OAuth token data."""
    access_token: str = Field(
        description="Short-lived access token for API calls"
    )
    refresh_token: str = Field(
        description="Long-lived refresh token for obtaining new access tokens"
    )
    token_expiry: datetime = Field(
        description="When the access token expires"
    )
    scopes: List[str] = Field(
        description="Granted OAuth scopes"
    )


class OAuthRevokeResponse(BaseModel):
    """Response after revoking OAuth access."""
    success: bool = Field(
        description="Whether the revocation was successful"
    )
    message: str = Field(
        description="Human-readable status message"
    )
