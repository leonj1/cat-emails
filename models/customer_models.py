"""
Customer-related Pydantic models for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CustomerInfo(BaseModel):
    """Customer information for API responses"""
    id: int = Field(..., description="Customer ID")
    google_user_id: str = Field(..., description="Google user ID (sub claim)")
    email_address: str = Field(..., description="Customer email address")
    display_name: Optional[str] = Field(None, description="Customer display name")
    is_active: bool = Field(..., description="Whether customer is active")
    account_count: int = Field(..., description="Number of linked email accounts")
    created_at: datetime = Field(..., description="When customer was created")
    last_login_at: Optional[datetime] = Field(None, description="Last OAuth login time")

    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy models


class CustomerListResponse(BaseModel):
    """List of customers response"""
    customers: List[CustomerInfo] = Field(..., description="List of customers")
    total_count: int = Field(..., description="Total number of customers")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class CustomerAccountsResponse(BaseModel):
    """Customer with their email accounts"""
    customer: CustomerInfo = Field(..., description="Customer information")
    accounts: List["EmailAccountInfo"] = Field(..., description="List of email accounts")
    total_count: int = Field(..., description="Total number of accounts")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class CreateCustomerRequest(BaseModel):
    """Create new customer (internal use, typically created via OAuth flow)"""
    google_user_id: str = Field(..., description="Google user ID from OAuth id_token")
    email_address: str = Field(..., description="Customer email address")
    display_name: Optional[str] = Field(None, description="Customer display name")


class CustomerDeleteResponse(BaseModel):
    """Response after deleting a customer"""
    status: str = Field(..., description="Status: 'success' or 'error'")
    message: str = Field(..., description="Human-readable message")
    customer_id: int = Field(..., description="Deleted customer ID")
    accounts_deleted: int = Field(..., description="Number of accounts deleted (cascade)")
    tokens_revoked: int = Field(..., description="Number of OAuth tokens revoked")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


# Forward reference resolution for circular imports
from models.account_models import EmailAccountInfo
CustomerAccountsResponse.model_rebuild()
