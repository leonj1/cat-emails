#!/usr/bin/env python3
"""
FastAPI service for triggering email summaries on demand and background Gmail account processing.
"""
import os
import sys
import logging
import threading
import time
import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Header, status, Query, Path, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from send_emails import send_summary_by_type
from clients.account_category_client_interface import AccountCategoryClientInterface
from clients.account_category_client import AccountCategoryClient
from services.processing_status_manager import ProcessingStatusManager, ProcessingState
from services.websocket_handler import StatusWebSocketManager
from services.websocket_auth_service import WebSocketAuthService
from services.background_processor_service import BackgroundProcessorService
from services.account_email_processor_service import AccountEmailProcessorService
from services.settings_service import SettingsService
from services.gmail_fetcher_service import GmailFetcher as ServiceGmailFetcher
from services.email_processor_service import EmailProcessorService
from services.logs_collector_service import LogsCollectorService
from services.llm_service_interface import LLMServiceInterface
from services.llm_service_factory import LLMServiceFactory
from services.email_categorizer_service import EmailCategorizerService
from services.openai_llm_service import OpenAILLMService
from services.categorize_emails_llm import LLMCategorizeEmails
from models.account_models import (
    TopCategoriesResponse, AccountListResponse, EmailAccountInfo,
    AccountCategoryStatsRequest
)
from models.summary_response import SummaryResponse
from models.create_account_request import CreateAccountRequest
from models.standard_response import StandardResponse
from models.error_response import ErrorResponse
from models.processing_current_status_response import ProcessingCurrentStatusResponse
from sqlalchemy.exc import SQLAlchemyError
from datetime import date

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app with comprehensive OpenAPI/Swagger configuration
app = FastAPI(
    title="Cat Emails API",
    description="""
# Cat Emails API

An AI-powered Gmail email categorizer API that automatically classifies, labels, and filters emails using machine learning models.

## Features

* **Email Categorization**: Automatically categorize emails into types (Marketing, Advertising, Personal, Work-related, etc.)
* **Background Processing**: Continuous Gmail account scanning and processing
* **Real-time Status**: WebSocket-based real-time processing status updates
* **Summary Reports**: Generate morning, evening, weekly, and monthly email summary reports
* **Account Management**: Track multiple Gmail accounts with category statistics
* **Category Analytics**: Get top email categories and statistics for any time period

## Authentication

Most endpoints require authentication via `X-API-Key` header when API_KEY is configured.

Example:
```
X-API-Key: your-api-key-here
```

## Real-time Updates

Connect to the WebSocket endpoint at `/ws/status` for real-time processing updates.
    """,
    version="1.1.0",
    contact={
        "name": "Terragon Labs",
        "url": "https://github.com/leonj1/cat-emails",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and service status endpoints"
        },
        {
            "name": "background-processing",
            "description": "Background Gmail processing management endpoints"
        },
        {
            "name": "processing-status",
            "description": "Real-time email processing status and monitoring"
        },
        {
            "name": "summaries",
            "description": "Email summary report generation endpoints"
        },
        {
            "name": "accounts",
            "description": "Gmail account management and analytics"
        },
        {
            "name": "testing",
            "description": "Testing and development utilities"
        },
        {
            "name": "websocket",
            "description": "WebSocket endpoints for real-time updates"
        }
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://192.168.1.162:5000",  # Allow your frontend's origin
    "https://cat-emails.netlify.app",  # Production frontend on Netlify
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional API key authentication
API_KEY = os.getenv("API_KEY")
CONTROL_API_TOKEN = os.getenv("CONTROL_API_TOKEN", "")
LLM_MODEL = os.getenv("LLM_MODEL", "vertex/google/gemini-2.5-flash")

# Background processing configuration
BACKGROUND_PROCESSING_ENABLED = os.getenv("BACKGROUND_PROCESSING", "true").lower() == "true"
BACKGROUND_SCAN_INTERVAL = int(os.getenv("BACKGROUND_SCAN_INTERVAL", "300"))  # 5 minutes default
BACKGROUND_PROCESS_HOURS = int(os.getenv("BACKGROUND_PROCESS_HOURS", "2"))  # Look back 2 hours default

# Global flag for background thread control
background_thread_running = True
background_thread = None
next_execution_time = None
background_processor_service: Optional[BackgroundProcessorService] = None

# Global processing status manager instance
processing_status_manager = ProcessingStatusManager(max_history=100)

# Global WebSocket manager instance
websocket_manager: Optional[StatusWebSocketManager] = None

# Global settings service instance
settings_service = SettingsService()

# Global LLM service factory instance
llm_service_factory = LLMServiceFactory()

# Global email categorizer service instance
email_categorizer_service = EmailCategorizerService(llm_service_factory)

# Global WebSocket auth service instance
websocket_auth_service = WebSocketAuthService(API_KEY)

# Global account email processor service instance (will be initialized with dependencies below)
account_email_processor_service: Optional[AccountEmailProcessorService] = None


# Initialize account email processor service after all dependencies are ready
def _initialize_account_email_processor():
    """Initialize the account email processor service with all dependencies."""
    global account_email_processor_service
    if not account_email_processor_service:
        from clients.account_category_client import AccountCategoryClient
        from services.email_deduplication_factory import EmailDeduplicationFactory
        account_email_processor_service = AccountEmailProcessorService(
            processing_status_manager=processing_status_manager,
            settings_service=settings_service,
            email_categorizer_callback=categorize_email_with_resilient_client,
            api_token=CONTROL_API_TOKEN,
            llm_model=LLM_MODEL,
            account_category_client=AccountCategoryClient(),
            deduplication_factory=EmailDeduplicationFactory()
            # create_gmail_fetcher defaults to GmailFetcher constructor
        )
    return account_email_processor_service


# API response models are now imported from models/ directory above


def get_account_service() -> AccountCategoryClientInterface:
    """Dependency to provide AccountCategoryClient instance."""
    try:
        return AccountCategoryClient()
    except Exception as e:
        logger.error(f"Failed to create AccountCategoryClient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database service unavailable"
        )


def _make_llm_service(model: str) -> LLMServiceInterface:
    """Create an LLM service instance for email categorization."""
    return llm_service_factory.create_service(model)


def _make_llm_categorizer(model: str) -> LLMCategorizeEmails:
    """Construct LLMCategorizeEmails using the injected LLM service interface."""
    llm_service = _make_llm_service(model)
    return LLMCategorizeEmails(llm_service=llm_service)


def categorize_email_with_resilient_client(contents: str, model: str) -> str:
    """
    Categorize email using the LLMCategorizeEmails interface (OpenAI-compatible / Ollama gateway).
    """
    return email_categorizer_service.categorize(contents, model)


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """
    Verify API key if it's configured.

    Args:
        x_api_key: API key from header

    Returns:
        True if valid or no API key required
    """
    if API_KEY:
        if not x_api_key or x_api_key != API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key"
            )
    return True


def verify_websocket_api_key(websocket: WebSocket) -> bool:
    """
    Verify API key for WebSocket connections.

    Args:
        websocket: WebSocket connection to check

    Returns:
        True if valid or no API key required, False otherwise
    """
    return websocket_auth_service.verify_api_key(websocket)


# Removed process_account_emails function - use account_email_processor_service.process_account() directly


def background_gmail_processor():
    """
    Background thread function that continuously processes Gmail accounts.
    """
    global background_processor_service, next_execution_time

    if background_processor_service:
        background_processor_service.run()
        # Update global next_execution_time for API compatibility
        next_execution_time = background_processor_service.get_next_execution_time()


def start_background_processor():
    """Start the background processing thread."""
    global background_thread, background_processor_service, next_execution_time

    if BACKGROUND_PROCESSING_ENABLED and not background_thread:
        logger.info("🎬 Starting background Gmail processor...")

        # Initialize account email processor service
        processor_service = _initialize_account_email_processor()

        # Create background processor service instance
        background_processor_service = BackgroundProcessorService(
            process_account_callback=processor_service.process_account,
            settings_service=settings_service,
            scan_interval=BACKGROUND_SCAN_INTERVAL,
            background_enabled=BACKGROUND_PROCESSING_ENABLED
        )

        background_thread = threading.Thread(
            target=background_gmail_processor,
            name="GmailProcessor",
            daemon=True
        )
        background_thread.start()
        next_execution_time = datetime.now() + timedelta(seconds=BACKGROUND_SCAN_INTERVAL)
        logger.info("✅ Background Gmail processor thread launched")
    elif not BACKGROUND_PROCESSING_ENABLED:
        logger.info("⏸️  Background processing is disabled (BACKGROUND_PROCESSING=false)")
    else:
        logger.warning("⚠️  Background processor thread already running")


def stop_background_processor():
    """Stop the background processing thread."""
    global background_thread_running, background_thread, background_processor_service, next_execution_time

    if background_thread and background_thread.is_alive():
        logger.info("🛑 Stopping background Gmail processor...")

        # Signal the service to stop
        if background_processor_service:
            background_processor_service.stop()

        background_thread_running = False
        background_thread.join(timeout=30)  # Wait up to 30 seconds for clean shutdown

        if background_thread.is_alive():
            logger.warning("⚠️  Background thread did not stop gracefully")
        else:
            logger.info("✅ Background Gmail processor stopped cleanly")

        background_thread = None
        background_processor_service = None
        next_execution_time = None


@app.get("/", tags=["health"])
async def root():
    """
    Root endpoint with API information

    Returns basic API information including version, available endpoints, and configuration details.
    """
    return {
        "service": "Cat Emails Summary API with Background Gmail Processing",
        "version": "1.1.0",
        "endpoints": {
            "health": "GET /api/health",
            "background_start": "POST /api/background/start",
            "background_stop": "POST /api/background/stop",
            "background_status": "GET /api/background/status",
            "background_next_execution": "GET /api/background/next-execution",
            "morning_summary": "POST /api/summaries/morning",
            "evening_summary": "POST /api/summaries/evening",
            "weekly_summary": "POST /api/summaries/weekly",
            "monthly_summary": "POST /api/summaries/monthly",
            "top_categories": "GET /api/accounts/{email_address}/categories/top",
            "list_accounts": "GET /api/accounts",
            "create_account": "POST /api/accounts",
            "deactivate_account": "PUT /api/accounts/{email_address}/deactivate",
            "processing_status": "GET /api/processing/status",
            "processing_history": "GET /api/processing/history",
            "processing_statistics": "GET /api/processing/statistics",
            "processing_current_status": "GET /api/processing/current-status (comprehensive status with polling support)",
            "websocket_status": "WS /ws/status (real-time processing status updates)"
        },
        "authentication": "Optional via X-API-Key header or api_key query param" if API_KEY else "None",
        "websocket_info": {
            "endpoint": "/ws/status",
            "authentication": "api_key query parameter or X-API-Key header" if API_KEY else "None required",
            "features": [
                "Real-time processing status updates",
                "Connection heartbeat",
                "Client message handling",
                "Automatic reconnection support"
            ]
        }
    }


@app.get("/api/health", tags=["health"])
async def health_check():
    """
    Health check endpoint

    Returns the health status of the API service and background processor information.
    """
    global background_thread, background_thread_running
    
    background_status = "disabled"
    if BACKGROUND_PROCESSING_ENABLED:
        if background_thread and background_thread.is_alive():
            background_status = "running"
        else:
            background_status = "stopped"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Cat Emails Summary API",
        "background_processor": {
            "enabled": BACKGROUND_PROCESSING_ENABLED,
            "status": background_status,
            "scan_interval_seconds": BACKGROUND_SCAN_INTERVAL,
            "process_hours": settings_service.get_lookback_hours()
        }
    }


@app.post("/api/background/start", tags=["background-processing"])
async def start_background_processing(x_api_key: Optional[str] = Header(None)):
    """
    Start the background Gmail processor

    Starts the background processing thread that continuously scans and processes Gmail accounts.
    Requires API key authentication if configured.
    """
    verify_api_key(x_api_key)
    
    global background_thread, background_thread_running
    
    if not BACKGROUND_PROCESSING_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Background processing is disabled via configuration"
        )
    
    if background_thread and background_thread.is_alive():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Background processor is already running"
        )
    
    # Reset the running flag and start the processor
    background_thread_running = True
    start_background_processor()
    
    return {
        "status": "success",
        "message": "Background Gmail processor started",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/background/stop", tags=["background-processing"])
async def stop_background_processing(x_api_key: Optional[str] = Header(None)):
    """
    Stop the background Gmail processor

    Stops the background processing thread gracefully. Requires API key authentication if configured.
    """
    verify_api_key(x_api_key)
    
    global background_thread
    
    if not background_thread or not background_thread.is_alive():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Background processor is not running"
        )
    
    stop_background_processor()
    
    return {
        "status": "success",
        "message": "Background Gmail processor stopped",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/background/status", tags=["background-processing"])
async def get_background_status(x_api_key: Optional[str] = Header(None)):
    """
    Get detailed background processor status

    Returns comprehensive status information about the background Gmail processor thread.
    """
    verify_api_key(x_api_key)
    
    global background_thread, background_thread_running
    
    thread_info = None
    if background_thread:
        thread_info = {
            "name": background_thread.name,
            "is_alive": background_thread.is_alive(),
            "daemon": background_thread.daemon,
            "ident": background_thread.ident
        }
    
    return {
        "enabled": BACKGROUND_PROCESSING_ENABLED,
        "running": background_thread_running,
        "thread": thread_info,
        "configuration": {
            "scan_interval_seconds": BACKGROUND_SCAN_INTERVAL,
            "process_hours": settings_service.get_lookback_hours()
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/background/next-execution", tags=["background-processing"])
async def get_next_execution_time(x_api_key: Optional[str] = Header(None)):
    """
    Get the next scheduled execution time

    Returns when the background service will execute its next processing cycle.
    """
    verify_api_key(x_api_key)
    
    global next_execution_time, background_thread_running
    
    if not BACKGROUND_PROCESSING_ENABLED:
        return {
            "error": "Background processing is disabled",
            "next_execution": None,
            "enabled": False,
            "timestamp": datetime.now().isoformat()
        }
    
    if not background_thread_running or next_execution_time is None:
        return {
            "error": "Background service is not running",
            "next_execution": None,
            "running": False,
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "next_execution": next_execution_time.isoformat(),
        "next_execution_formatted": next_execution_time.strftime('%Y-%m-%d %H:%M:%S'),
        "seconds_until_next": max(0, int((next_execution_time - datetime.now()).total_seconds())),
        "scan_interval_seconds": BACKGROUND_SCAN_INTERVAL,
        "running": background_thread_running,
        "enabled": BACKGROUND_PROCESSING_ENABLED,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/processing/status", tags=["processing-status"])
async def get_processing_status(x_api_key: Optional[str] = Header(None)):
    """
    Get current email processing status

    Returns the current processing status including active state and current processing details.
    """
    verify_api_key(x_api_key)
    
    global processing_status_manager
    
    current_status = processing_status_manager.get_current_status()
    is_active = processing_status_manager.is_processing()
    
    return {
        "is_processing": is_active,
        "current_status": current_status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/processing/history", tags=["processing-status"])
async def get_processing_history(
    limit: int = Query(10, ge=1, le=100, description="Number of recent runs to retrieve (1-100)"),
    x_api_key: Optional[str] = Header(None)
):
    """
    Get recent processing history

    Returns a list of recent email processing runs with their details and results.
    """
    verify_api_key(x_api_key)
    
    global processing_status_manager
    
    recent_runs = processing_status_manager.get_recent_runs(limit=limit)
    
    return {
        "recent_runs": recent_runs,
        "total_retrieved": len(recent_runs),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/processing/statistics", tags=["processing-status"])
async def get_processing_statistics(x_api_key: Optional[str] = Header(None)):
    """
    Get processing statistics

    Returns aggregate statistics about email processing including success rates and performance metrics.
    """
    verify_api_key(x_api_key)
    
    global processing_status_manager
    
    stats = processing_status_manager.get_statistics()
    
    return {
        "statistics": stats,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/processing/current-status", response_model=ProcessingCurrentStatusResponse, tags=["processing-status"])
async def get_current_processing_status(
    include_recent: bool = Query(True, description="Include recent processing runs"),
    recent_limit: int = Query(5, ge=1, le=50, description="Number of recent runs to return (1-50)"),
    include_stats: bool = Query(False, description="Include processing statistics"),
    x_api_key: Optional[str] = Header(None)
):
    """
    Get comprehensive current processing status

    REST API fallback for WebSocket functionality. Provides comprehensive processing status suitable for polling-based clients.
    
    This endpoint provides the same real-time processing information available via WebSocket
    in a traditional REST API format, suitable for polling-based clients that cannot use WebSockets.
    
    Query Parameters:
        include_recent: Whether to include recent processing runs (default: True)
        recent_limit: Number of recent runs to return, 1-50 (default: 5)
        include_stats: Whether to include processing statistics (default: False)
    
    Returns:
        ProcessingCurrentStatusResponse containing:
        - is_processing: Boolean indicating if processing is currently active
        - current_status: Current processing status object (or None if idle)
        - recent_runs: Array of recent processing runs (if include_recent=True)
        - statistics: Processing statistics (if include_stats=True)
        - timestamp: When the status was retrieved
        - websocket_available: Boolean indicating if WebSocket endpoint is available
    
    Authentication:
        Requires X-API-Key header if API key is configured
    
    Raises:
        400: Invalid query parameters
        401: Invalid or missing API key
        500: Internal server error
    
    Example Response:
        {
            "is_processing": true,
            "current_status": {
                "email_address": "user@example.com",
                "state": "PROCESSING",
                "current_step": "Processing email 15 of 30",
                "progress": {"current": 15, "total": 30},
                "start_time": "2025-01-15T10:30:00Z",
                "last_updated": "2025-01-15T10:32:15Z"
            },
            "recent_runs": [
                {
                    "email_address": "user@example.com",
                    "start_time": "2025-01-15T09:00:00Z",
                    "end_time": "2025-01-15T09:05:30Z",
                    "duration_seconds": 330.5,
                    "final_state": "COMPLETED",
                    "final_step": "Successfully processed 25 emails"
                }
            ],
            "statistics": {
                "total_runs": 50,
                "successful_runs": 48,
                "failed_runs": 2,
                "average_duration_seconds": 285.4,
                "success_rate": 96.0
            },
            "timestamp": "2025-01-15T10:32:20Z",
            "websocket_available": true
        }
    
    Use Cases:
        - Polling-based status monitoring for web dashboards
        - Mobile apps that don't support WebSockets reliably
        - Simple integrations that prefer REST over WebSocket complexity
        - Debugging and testing processing status without WebSocket setup
        
    Polling Recommendations:
        - For active processing: Poll every 2-5 seconds
        - For idle monitoring: Poll every 30-60 seconds
        - Use include_stats=False for frequent polling to reduce response size
        - Consider WebSocket endpoint for true real-time updates when possible
    """
    verify_api_key(x_api_key)
    
    try:
        global processing_status_manager, websocket_manager
        
        # Validate query parameters
        if recent_limit < 1 or recent_limit > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="recent_limit must be between 1 and 50"
            )
        
        # Get current processing status
        is_processing = processing_status_manager.is_processing()
        current_status = processing_status_manager.get_current_status()
        
        # Get recent runs if requested
        recent_runs = None
        if include_recent:
            recent_runs = processing_status_manager.get_recent_runs(limit=recent_limit)
        
        # Get statistics if requested
        statistics = None
        if include_stats:
            statistics = processing_status_manager.get_statistics()
        
        # Check if WebSocket is available
        websocket_available = websocket_manager is not None
        
        response = ProcessingCurrentStatusResponse(
            is_processing=is_processing,
            current_status=current_status,
            recent_runs=recent_runs,
            statistics=statistics,
            timestamp=datetime.now().isoformat(),
            websocket_available=websocket_available
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error in get_current_processing_status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve processing status: {str(e)}"
        )


@app.websocket("/ws/status", name="WebSocket Status Updates")
async def websocket_status_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time processing status updates

    Provides real-time updates about email processing status via WebSocket connection.
    
    This endpoint provides real-time updates about email processing status,
    including current processing state, recent runs, and statistics.
    
    Authentication:
        - If API_KEY is configured, provide it via:
          - Query parameter: /ws/status?api_key=your-key
          - Header: X-API-Key: your-key
        - If no API_KEY configured, no authentication required
    
    Message Types:
        - status_update: Regular processing status broadcasts
        - connection_confirmed: Connection establishment confirmation
        - heartbeat: Connection health checks
        - error: Error messages
        - pong: Response to ping messages
    
    Client Messages:
        - {"type": "ping"}: Request heartbeat response
        - {"type": "get_current_status"}: Request current status
        - {"type": "get_recent_runs", "limit": 10}: Request recent runs
        - {"type": "get_statistics"}: Request processing statistics
    """
    global websocket_manager
    
    # Verify authentication before accepting connection
    if not verify_websocket_api_key(websocket):
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    # Ensure WebSocket manager is initialized
    if websocket_manager is None:
        logger.error("WebSocket manager not initialized")
        await websocket.close(code=1011, reason="Internal server error")
        return
    
    # Handle the client connection
    try:
        await websocket_manager.handle_client(websocket)
    except Exception as e:
        logger.error(f"Error in WebSocket endpoint: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass


@app.websocket("/ws")
async def websocket_status_alias(websocket: WebSocket):
    """
    Backward-compatible alias for /ws/status to support clients requesting `/ws`.
    """
    await websocket_status_endpoint(websocket)


@app.post("/api/test/create-sample-data", tags=["testing"])
async def create_sample_data(x_api_key: Optional[str] = Header(None), report_type: Optional[str] = "Daily"):
    """
    Create sample tracking data for testing

    Creates dummy email data to test the summary functionality. Useful for development and testing.
    
    Args:
        report_type: Type of report to generate data for (Daily/Weekly/Monthly)
    """
    verify_api_key(x_api_key)
    
    try:
        from services.email_summary_service import EmailSummaryService
        from models.email_summary import ProcessedEmail, EmailAction
        import json
        from pathlib import Path
        import random
        
        # Initialize summary service
        gmail_email = os.getenv('GMAIL_EMAIL')
        summary_service = EmailSummaryService(gmail_email=gmail_email)
        
        # Determine number of emails based on report type
        if report_type == "Monthly":
            num_emails = random.randint(800, 1200)  # Monthly: 800-1200 emails
        elif report_type == "Weekly":
            num_emails = random.randint(150, 250)   # Weekly: 150-250 emails
        else:  # Daily/Morning/Evening
            num_emails = random.randint(20, 40)     # Daily: 20-40 emails
        
        # Create sample emails with realistic distribution
        categories = [
            ("Marketing", 0.25),
            ("Advertising", 0.20),
            ("Personal", 0.15),
            ("Wants-Money", 0.10),
            ("Financial-Notification", 0.10),
            ("Work-related", 0.10),
            ("Service-Updates", 0.05),
            ("Appointment-Reminder", 0.03),
            ("Other", 0.02)
        ]
        
        senders = [
            ("newsletter@company.com", "company.com"),
            ("promo@shop.com", "shop.com"),
            ("friend@gmail.com", "gmail.com"),
            ("billing@service.com", "service.com"),
            ("noreply@bank.com", "bank.com"),
            ("updates@tech.com", "tech.com"),
            ("info@store.com", "store.com"),
            ("support@app.com", "app.com"),
            ("hello@startup.com", "startup.com"),
            ("contact@business.com", "business.com")
        ]
        
        sample_emails = []
        
        # Generate emails based on distribution
        for i in range(num_emails):
            # Select category based on distribution
            rand = random.random()
            cumulative = 0
            selected_category = "Other"
            for category, probability in categories:
                cumulative += probability
                if rand <= cumulative:
                    selected_category = category
                    break
            
            # Select random sender
            sender, domain = random.choice(senders)
            
            # Determine action based on category
            if selected_category in ["Advertising", "Marketing", "Wants-Money"]:
                action = "deleted" if random.random() > 0.3 else "kept"  # 70% deleted
            else:
                action = "kept" if random.random() > 0.2 else "deleted"  # 80% kept
            
            # Generate email
            email = {
                "message_id": f"test{i+1}_{report_type.lower()}@example.com",
                "sender": sender,
                "subject": f"{selected_category} email #{i+1}",
                "category": selected_category,
                "action": action,
                "sender_domain": domain,
                "was_pre_categorized": random.random() > 0.7,  # 30% pre-categorized
                "processed_at": (datetime.now() - timedelta(minutes=random.randint(0, 60))).isoformat()
            }
            sample_emails.append(email)
        
        # Save to current tracking file
        tracking_file = Path(summary_service.current_file)
        tracking_file.parent.mkdir(exist_ok=True)
        
        with open(tracking_file, 'w') as f:
            json.dump(sample_emails, f, indent=2)
        
        return {
            "status": "success",
            "message": f"Created {len(sample_emails)} sample emails for {report_type} report testing",
            "timestamp": datetime.now().isoformat(),
            "email_count": len(sample_emails),
            "report_type": report_type
        }
        
    except Exception as e:
        logger.error(f"Error creating sample data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sample data: {str(e)}"
        )


@app.post("/api/summaries/morning", response_model=SummaryResponse, tags=["summaries"])
async def trigger_morning_summary(x_api_key: Optional[str] = Header(None)):
    """
    Trigger a morning summary report

    Forces the generation and sending of a morning summary report regardless of the current time.
    """
    verify_api_key(x_api_key)
    
    try:
        logger.info("Triggering morning summary via API")
        success, message = send_summary_by_type("Morning")
        
        if success:
            return SummaryResponse(
                status="success",
                message=message,
                timestamp=datetime.now().isoformat(),
                report_type="Morning"
            )
        else:
            if "No data to summarize" in message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )
            
    except Exception as e:
        logger.error(f"Error triggering morning summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger morning summary: {str(e)}"
        )


@app.post("/api/summaries/evening", response_model=SummaryResponse, tags=["summaries"])
async def trigger_evening_summary(x_api_key: Optional[str] = Header(None)):
    """
    Trigger an evening summary report

    Forces the generation and sending of an evening summary report regardless of the current time.
    """
    verify_api_key(x_api_key)
    
    try:
        logger.info("Triggering evening summary via API")
        success, message = send_summary_by_type("Evening")
        
        if success:
            return SummaryResponse(
                status="success",
                message=message,
                timestamp=datetime.now().isoformat(),
                report_type="Evening"
            )
        else:
            if "No data to summarize" in message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )
            
    except Exception as e:
        logger.error(f"Error triggering evening summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger evening summary: {str(e)}"
        )


@app.post("/api/summaries/weekly", response_model=SummaryResponse, tags=["summaries"])
async def trigger_weekly_summary(x_api_key: Optional[str] = Header(None)):
    """
    Trigger a weekly summary report

    Forces the generation and sending of a weekly summary report regardless of the current day or time.
    """
    verify_api_key(x_api_key)
    
    try:
        logger.info("Triggering weekly summary via API")
        success, message = send_summary_by_type("Weekly")
        
        if success:
            return SummaryResponse(
                status="success",
                message=message,
                timestamp=datetime.now().isoformat(),
                report_type="Weekly"
            )
        else:
            if "No data to summarize" in message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )
            
    except Exception as e:
        logger.error(f"Error triggering weekly summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger weekly summary: {str(e)}"
        )


@app.post("/api/summaries/monthly", response_model=SummaryResponse, tags=["summaries"])
async def trigger_monthly_summary(x_api_key: Optional[str] = Header(None)):
    """
    Trigger a monthly summary report

    Forces the generation and sending of a monthly summary report with data from the last 30 days.
    """
    verify_api_key(x_api_key)
    
    try:
        logger.info("Triggering monthly summary via API")
        success, message = send_summary_by_type("Monthly")
        
        if success:
            return SummaryResponse(
                status="success",
                message=message,
                timestamp=datetime.now().isoformat(),
                report_type="Monthly"
            )
        else:
            if "No data to summarize" in message:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )
            
    except Exception as e:
        logger.error(f"Error triggering monthly summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger monthly summary: {str(e)}"
        )


@app.get("/api/accounts/{email_address}/categories/top", response_model=TopCategoriesResponse, tags=["accounts"])
async def get_top_categories(
    email_address: str = Path(..., description="Gmail email address"),
    days: int = Query(..., ge=1, le=365, description="Number of days to look back (1-365)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of categories to return (1-50)"),
    include_counts: bool = Query(False, description="Include detailed counts breakdown"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryClientInterface = Depends(get_account_service)
):
    """
    Get top email categories for a specific account

    Returns the most frequent email categories for an account over a specified time period.
    
    Returns the most frequent email categories processed for the given account,
    ranked by email volume. Supports filtering by time range and category count limits.
    
    Args:
        email_address: Gmail account email address
        days: Number of days to look back from today (1-365 days)
        limit: Maximum number of top categories to return (1-50, default: 10)
        include_counts: Whether to include detailed action counts (kept/deleted/archived)
        
    Returns:
        TopCategoriesResponse with category statistics and metadata
        
    Raises:
        400: Invalid parameters or email format
        401: Invalid or missing API key
        404: Account not found
        422: Validation errors
        500: Internal server error
    """
    verify_api_key(x_api_key)
    
    try:
        # Validate request parameters using Pydantic model
        request_data = AccountCategoryStatsRequest(
            days=days,
            limit=limit,
            include_counts=include_counts
        )
        
        logger.info(f"Getting top categories for {email_address}: {days} days, limit {limit}, counts {include_counts}")
        
        response = service.get_top_categories(
            email_address=email_address,
            days=request_data.days,
            limit=request_data.limit,
            include_counts=request_data.include_counts
        )
        
        logger.info(f"Successfully retrieved {len(response.top_categories)} categories for {email_address}")
        return response
        
    except ValidationError as e:
        logger.warning(f"Validation error for top categories request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid request parameters: {str(e)}"
        )
    except ValueError as e:
        error_msg = str(e)
        if "No account found" in error_msg:
            logger.warning(f"Account not found: {email_address}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {email_address}"
            )
        elif "Invalid email address" in error_msg or "must be" in error_msg:
            logger.warning(f"Invalid parameter for top categories: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        else:
            logger.error(f"Value error in get_top_categories: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve category statistics"
            )
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_top_categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_top_categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@app.get("/api/accounts", response_model=AccountListResponse, tags=["accounts"])
async def get_all_accounts(
    active_only: bool = Query(True, description="Filter to only active accounts"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryClientInterface = Depends(get_account_service)
):
    """
    List all tracked email accounts

    Returns a list of all Gmail accounts being tracked by the system.
    
    Returns a list of all Gmail accounts being tracked by the system,
    with optional filtering to show only active accounts.
    
    Args:
        active_only: If True, only returns accounts marked as active (default: True)
        
    Returns:
        AccountListResponse containing list of accounts and total count
        
    Raises:
        401: Invalid or missing API key
        500: Internal server error
    """
    verify_api_key(x_api_key)
    
    try:
        logger.info(f"Retrieving all accounts (active_only: {active_only})")
        
        accounts = service.get_all_accounts(active_only=active_only)
        
        # Convert to response format
        account_infos = [
            EmailAccountInfo(
                id=account.id,
                email_address=account.email_address,
                display_name=account.display_name,
                is_active=account.is_active,
                last_scan_at=account.last_scan_at,
                created_at=account.created_at
            )
            for account in accounts
        ]
        
        response = AccountListResponse(
            accounts=account_infos,
            total_count=len(account_infos)
        )
        
        logger.info(f"Successfully retrieved {len(account_infos)} accounts")
        return response
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_all_accounts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_all_accounts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@app.post("/api/accounts", response_model=StandardResponse, tags=["accounts"])
async def create_account(
    request: CreateAccountRequest,
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryClientInterface = Depends(get_account_service)
):
    """
    Register a new email account for tracking

    Creates a new account entry in the system for email category tracking.
    
    Creates a new account entry in the system for email category tracking.
    If the account already exists, it will be reactivated and updated.
    
    Args:
        request: Account creation request containing email_address and optional display_name
        
    Returns:
        StandardResponse with success status and details
        
    Raises:
        400: Invalid email address format
        401: Invalid or missing API key
        422: Validation errors in request body
        500: Internal server error
    """
    verify_api_key(x_api_key)
    
    try:
        logger.info(f"Creating account for {request.email_address}")
        
        account = service.get_or_create_account(
            email_address=request.email_address,
            display_name=request.display_name
        )
        
        response = StandardResponse(
            status="success",
            message=f"Account registered successfully: {account.email_address}",
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Successfully created/updated account: {account.email_address} (ID: {account.id})")
        return response
        
    except ValidationError as e:
        logger.warning(f"Validation error for create account request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid request format: {str(e)}"
        )
    except ValueError as e:
        error_msg = str(e)
        if "Invalid email address" in error_msg:
            logger.warning(f"Invalid email address format: {request.email_address}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        else:
            logger.error(f"Value error in create_account: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create account"
            )
    except SQLAlchemyError as e:
        error_msg = f"Database error in create_account: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )
    except Exception as e:
        error_msg = f"Unexpected error in create_account: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@app.put("/api/accounts/{email_address}/deactivate", response_model=StandardResponse, tags=["accounts"])
async def deactivate_account(
    email_address: str = Path(..., description="Gmail email address to deactivate"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryClientInterface = Depends(get_account_service)
):
    """
    Deactivate an email account

    Marks an account as inactive, excluding it from active scanning but preserving historical data.
    
    Marks an account as inactive, which will exclude it from active scanning
    but preserve historical data. The account can be reactivated later.
    
    Args:
        email_address: Gmail email address to deactivate
        
    Returns:
        StandardResponse with operation status
        
    Raises:
        400: Invalid email address format
        401: Invalid or missing API key
        404: Account not found
        500: Internal server error
    """
    verify_api_key(x_api_key)
    
    try:
        logger.info(f"Deactivating account: {email_address}")
        
        success = service.deactivate_account(email_address)
        
        if success:
            response = StandardResponse(
                status="success",
                message=f"Account deactivated successfully: {email_address}",
                timestamp=datetime.now().isoformat()
            )
            logger.info(f"Successfully deactivated account: {email_address}")
            return response
        else:
            logger.warning(f"Account not found for deactivation: {email_address}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {email_address}"
            )
            
    except ValueError as e:
        error_msg = str(e)
        if "Invalid email address" in error_msg:
            logger.warning(f"Invalid email address format: {email_address}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        else:
            logger.error(f"Value error in deactivate_account: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate account"
            )
    except SQLAlchemyError as e:
        logger.error(f"Database error in deactivate_account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Unexpected error in deactivate_account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@app.delete("/api/accounts/{email_address}", response_model=StandardResponse, tags=["accounts"])
async def delete_account(
    email_address: str = Path(..., description="Gmail email address to delete"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryClientInterface = Depends(get_account_service)
):
    """
    Delete an email account and all associated data

    Permanently removes an account and all its associated data. This operation cannot be undone.
    
    Permanently removes an account and all its associated category statistics
    from the system. This operation cannot be undone.
    
    Args:
        email_address: Gmail email address to delete
        
    Returns:
        StandardResponse with operation status
        
    Raises:
        400: Invalid email address format
        401: Invalid or missing API key
        404: Account not found
        500: Internal server error
    """
    verify_api_key(x_api_key)
    
    try:
        logger.info(f"Deleting account: {email_address}")
        
        # Validate email address
        email_address = service._validate_email_address(email_address)
        
        # Get account to verify it exists
        account = service.get_account_by_email(email_address)
        if not account:
            logger.warning(f"Account not found for deletion: {email_address}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {email_address}"
            )
        
        # Delete account and associated data
        if service.owns_session:
            with service._get_session() as session:
                session.delete(account)
                session.commit()
        else:
            service.session.delete(account)
            service.session.commit()
        
        response = StandardResponse(
            status="success",
            message=f"Account and all associated data deleted successfully: {email_address}",
            timestamp=datetime.now().isoformat()
        )
        logger.info(f"Successfully deleted account: {email_address}")
        return response
        
    except ValueError as e:
        error_msg = str(e)
        if "Invalid email address" in error_msg:
            logger.warning(f"Invalid email address format: {email_address}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        else:
            logger.error(f"Value error in delete_account: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete account"
            )
    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Unexpected error in delete_account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

    


@app.on_event("startup")
async def startup_event():
    """Initialize WebSocket manager and start background tasks on server startup"""
    global websocket_manager
    
    try:
        # Initialize WebSocket manager
        websocket_manager = StatusWebSocketManager(
            status_manager=processing_status_manager,
            max_clients=50  # Configure max clients as needed
        )
        
        # Start background broadcasting task
        websocket_manager.broadcast_task = asyncio.create_task(
            websocket_manager.start_broadcasting()
        )
        
        # Start heartbeat task
        websocket_manager.heartbeat_task = asyncio.create_task(
            websocket_manager.start_heartbeat()
        )
        
        logger.info("WebSocket manager initialized and background tasks started")
        
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket manager: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown WebSocket manager and background tasks"""
    global websocket_manager
    
    try:
        if websocket_manager:
            logger.info("Shutting down WebSocket manager...")
            await websocket_manager.shutdown()
            websocket_manager = None
            logger.info("WebSocket manager shutdown completed")
        
        # Stop background processor if running
        stop_background_processor()
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


@app.exception_handler(404)
async def not_found(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "status": "error",
            "message": "Endpoint not found",
            "available_endpoints": {
                "health": "GET /api/health",
                "morning_summary": "POST /api/summaries/morning",
                "evening_summary": "POST /api/summaries/evening",
                "weekly_summary": "POST /api/summaries/weekly",
                "monthly_summary": "POST /api/summaries/monthly",
                "top_categories": "GET /api/accounts/{email_address}/categories/top",
                "list_accounts": "GET /api/accounts",
                "create_account": "POST /api/accounts",
                "deactivate_account": "PUT /api/accounts/{email_address}/deactivate",
                "delete_account": "DELETE /api/accounts/{email_address}",
                "processing_status": "GET /api/processing/status",
                "processing_history": "GET /api/processing/history",
                "processing_statistics": "GET /api/processing/statistics",
                "processing_current_status": "GET /api/processing/current-status",
                "websocket_status": "WS /ws/status"
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    import signal
    
    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        stop_background_processor()
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get configuration from environment
    # Railway sets PORT environment variable, fallback to API_PORT then 8001
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("API_PORT", "8001")))
    
    logger.info(f"Starting Cat Emails Summary API on {host}:{port}")
    if API_KEY:
        logger.info("API key authentication is enabled")
    else:
        logger.warning("API key authentication is disabled - endpoints are publicly accessible")
    
    # Start background processor if enabled
    start_background_processor()
    
    try:
        # Run the API
        uvicorn.run(app, host=host, port=port)
    finally:
        # Ensure background processor is stopped on exit
        logger.info("Shutting down API server...")
        stop_background_processor()
