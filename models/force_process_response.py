from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ProcessingInfo(BaseModel):
    """Information about the processing operation"""
    hours: Optional[int] = Field(None, description="Lookback hours for email processing")
    status_url: Optional[str] = Field(None, description="URL to poll for processing status")
    websocket_url: Optional[str] = Field(None, description="WebSocket URL for real-time updates")
    state: Optional[str] = Field(None, description="Current processing state if already running")
    current_step: Optional[str] = Field(None, description="Current processing step if already running")


class ForceProcessResponse(BaseModel):
    """Response model for force processing endpoint"""
    status: str = Field(..., description="Status of the request: 'success', 'error', or 'already_processing'")
    message: str = Field(..., description="Human-readable message describing the result")
    email_address: str = Field(..., description="Email address that was requested for processing")
    timestamp: str = Field(..., description="ISO timestamp when the response was generated")
    processing_info: Optional[ProcessingInfo] = Field(None, description="Additional processing information")
