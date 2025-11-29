from pydantic import BaseModel
from typing import Optional, Dict, List


class BackgroundThreadInfo(BaseModel):
    """Background thread information"""
    name: Optional[str] = None
    is_alive: Optional[bool] = None
    daemon: Optional[bool] = None
    ident: Optional[int] = None


class BackgroundConfiguration(BaseModel):
    """Background processing configuration"""
    scan_interval_seconds: int
    process_hours: int


class BackgroundStatus(BaseModel):
    """Background processing status"""
    enabled: bool
    running: bool
    thread: Optional[BackgroundThreadInfo] = None
    configuration: BackgroundConfiguration


class ProcessingCurrentStatusResponse(BaseModel):
    """Response model for current processing status endpoint"""
    is_processing: bool
    current_status: Optional[Dict]
    recent_runs: Optional[List[Dict]]
    statistics: Optional[Dict]
    timestamp: str
    websocket_available: bool


class UnifiedStatusResponse(BaseModel):
    """
    Unified response model combining all status endpoints.

    This consolidates:
    - /api/processing/status (is_processing, current_status)
    - /api/background/status (background thread info)
    - /api/processing/current-status (comprehensive status)
    """
    # Processing status
    is_processing: bool
    current_status: Optional[Dict] = None

    # Background status
    background: BackgroundStatus

    # Optional detailed information
    recent_runs: Optional[List[Dict]] = None
    statistics: Optional[Dict] = None

    # Metadata
    timestamp: str
    websocket_available: bool
