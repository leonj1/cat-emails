from pydantic import BaseModel


class SummaryResponse(BaseModel):
    """Response model for summary endpoints"""
    status: str
    message: str
    timestamp: str
    report_type: str
