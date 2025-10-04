from pydantic import BaseModel
from typing import Optional


class CreateAccountRequest(BaseModel):
    """Request model for creating new accounts"""
    email_address: str
    display_name: Optional[str] = None
