from pydantic import BaseModel


class StandardResponse(BaseModel):
    """Standard response model for simple operations"""
    status: str
    message: str
    timestamp: str
