from pydantic import BaseModel, Field
from typing import Optional


class CreateAccountRequest(BaseModel):
    """
    Request model for creating new accounts.

    DEPRECATED: Direct account creation is deprecated. Use OAuth flow instead.
    Accounts should be created via /api/oauth/authorize and /api/oauth/callback endpoints.

    This endpoint is kept for backward compatibility during migration period.
    """
    email_address: str = Field(..., description="Gmail email address")
    customer_id: int = Field(..., description="Customer ID who owns this account")
    display_name: Optional[str] = Field(None, description="Optional display name for the account")

    # app_password removed - OAuth only authentication supported
