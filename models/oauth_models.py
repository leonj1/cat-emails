"""
OAuth-related Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class OAuthAuthorizeRequest(BaseModel):
    """Request to initiate OAuth flow"""
    customer_email: Optional[str] = Field(None, description="Email hint for Google login")
    account_email: Optional[str] = Field(None, description="Specific Gmail account to add after authorization")


class OAuthCallbackRequest(BaseModel):
    """OAuth callback parameters from Google"""
    code: str = Field(..., description="Authorization code from Google")
    state: str = Field(..., description="CSRF protection state parameter")
    error: Optional[str] = Field(None, description="Error code if authorization failed")
    error_description: Optional[str] = Field(None, description="Human-readable error description")


class OAuthCallbackResponse(BaseModel):
    """Response after processing OAuth callback"""
    status: str = Field(..., description="Status: 'success' or 'error'")
    message: str = Field(..., description="Human-readable message")
    customer_id: Optional[int] = Field(None, description="Created/updated customer ID")
    customer_email: Optional[str] = Field(None, description="Customer email address")
    account_id: Optional[int] = Field(None, description="Created/updated account ID")
    account_email: Optional[str] = Field(None, description="Email account address")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class OAuthStateData(BaseModel):
    """Data encoded in OAuth state parameter (JWT payload)"""
    nonce: str = Field(..., description="Random UUID for uniqueness")
    timestamp: datetime = Field(..., description="When state was created")
    customer_email: Optional[str] = Field(None, description="Email hint passed to Google")
    account_email: Optional[str] = Field(None, description="Specific account to link after auth")
    exp: Optional[datetime] = Field(None, description="Expiration time for JWT")


class OAuthTokenResponse(BaseModel):
    """Response from Google OAuth token endpoint"""
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token (only on first auth)")
    expires_in: int = Field(..., description="Access token lifetime in seconds")
    scope: str = Field(..., description="Granted scopes")
    token_type: str = Field(default="Bearer", description="Token type")
    id_token: Optional[str] = Field(None, description="JWT with user identity")


class OAuthUserInfo(BaseModel):
    """User information decoded from id_token"""
    sub: str = Field(..., description="Google user ID (unique identifier)")
    email: str = Field(..., description="User email address")
    email_verified: bool = Field(..., description="Whether email is verified")
    name: Optional[str] = Field(None, description="Full name")
    given_name: Optional[str] = Field(None, description="First name")
    family_name: Optional[str] = Field(None, description="Last name")
    picture: Optional[str] = Field(None, description="Profile picture URL")
