from pydantic import BaseModel
from typing import Optional, Dict, List


class ProcessingCurrentStatusResponse(BaseModel):
    """Response model for current processing status endpoint"""
    is_processing: bool
    current_status: Optional[Dict]
    recent_runs: Optional[List[Dict]]
    statistics: Optional[Dict]
    timestamp: str
    websocket_available: bool
