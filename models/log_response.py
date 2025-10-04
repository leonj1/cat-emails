from pydantic import BaseModel, Field


class LogResponse(BaseModel):
    """Response from the logging service."""
    message: str = Field(description="Response message")
    status: str = Field(description="Response status")
