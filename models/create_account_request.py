from pydantic import BaseModel, Field
from typing import Optional


class CreateAccountRequest(BaseModel):
    """Request model for creating new accounts"""
    email_address: str = Field(..., description="Gmail email address")
    app_password: str = Field(..., description="Gmail app-specific password for IMAP access")
    display_name: Optional[str] = Field(None, description="Optional display name for the account")
