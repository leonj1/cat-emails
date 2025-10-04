from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: str
    timestamp: str
