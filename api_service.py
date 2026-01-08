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
import json
import urllib.parse
import urllib.request
from urllib.error import URLError, HTTPError
from typing import Optional, Dict, List, Callable, Awaitable
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Header, status, Query, Path, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import DEFAULT_REQUESTYAI_BASE_URL

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
from services.llm_service_interface import LLMServiceInterface
from services.llm_service_factory import LLMServiceFactory
from services.email_categorizer_service import EmailCategorizerService
from services.openai_llm_service import OpenAILLMService
from services.categorize_emails_llm import LLMCategorizeEmails
from services.rate_limiter_service import RateLimiterService
from services.blocking_recommendation_service import BlockingRecommendationService
from services.category_aggregation_config import CategoryAggregationConfig
from services.category_aggregator_service import CategoryAggregator
from services.tally_cleanup_service import TallyCleanupService
from repositories.category_tally_repository import CategoryTallyRepository
from domain_service import DomainService
from models.account_models import (
    TopCategoriesResponse, AccountListResponse, EmailAccountInfo,
    AccountCategoryStatsRequest
)
from models.summary_response import SummaryResponse
from models.create_account_request import CreateAccountRequest
from models.oauth_models import (
    OAuthAuthorizeResponse, OAuthCallbackRequest, OAuthCallbackResponse,
    OAuthStatusResponse, OAuthRevokeResponse
)
from services.oauth_flow_service import OAuthFlowService
from repositories.oauth_state_repository import OAuthStateRepository
from models.standard_response import StandardResponse
from models.error_response import ErrorResponse
from models.processing_current_status_response import (
    ProcessingCurrentStatusResponse,
    UnifiedStatusResponse,
    BackgroundStatus,
    BackgroundConfiguration,
    BackgroundThreadInfo
)
from models.force_process_response import ForceProcessResponse, ProcessingInfo
from models.recommendation_models import (
    BlockingRecommendationResult,
    RecommendationReason
)
from models.category_tally_models import AggregatedCategoryTally
from models.config_response import (
    ConfigurationResponse, DatabaseConfig, DatabaseEnvVars, LLMConfig,
    BackgroundProcessingConfig, APIServiceConfig
)
from sqlalchemy.exc import SQLAlchemyError
from datetime import date
from utils.password_utils import mask_password

# Configure centralized logging
from utils.logger import initialize_central_logging, get_logger, shutdown_logging

# Initialize central logging service at application startup
# This replaces logging.basicConfig() and ensures all logs go to both stdout and remote service
initialize_central_logging(
    log_level=logging.INFO,
    enable_remote=True  # Enable sending logs to remote collector if configured
)

# Get logger instance - same API as before but now uses CentralLoggingService
logger = get_logger(__name__)

# API version
API_VERSION = "1.1.0"

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
    version=API_VERSION,
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


# OAuth callback debugging middleware
# Logs raw request details BEFORE Pydantic parsing
# OAuth debug preview length (configurable via environment variable)
try:
    OAUTH_DEBUG_PREVIEW_LENGTH = int(
        os.getenv("OAUTH_DEBUG_PREVIEW_LENGTH", "10")
    )
except ValueError:
    logger.warning(
        "Invalid OAUTH_DEBUG_PREVIEW_LENGTH value, using default of 10"
    )
    OAUTH_DEBUG_PREVIEW_LENGTH = 10


@app.middleware("http")
async def oauth_callback_debug_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Debug middleware to log raw OAuth callback request details."""
    is_oauth_callback = (
        request.url.path == "/api/auth/gmail/callback"
        and request.method == "POST"
    )
    if is_oauth_callback:
        # Log URL path only (no sensitive query params)
        logger.info(f"[OAuth Debug] Path: {request.url.path}")

        param_keys = list(request.query_params.keys())
        logger.info(f"[OAuth Debug] Query keys: {param_keys}")

        header_keys = list(request.headers.keys())
        logger.info(f"[OAuth Debug] Headers: {header_keys}")

        # Read and log raw body (safely, without exposing full tokens)
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8') if body_bytes else ''

        # Parse body to check structure without exposing sensitive values
        try:
            body_json = json.loads(body_str) if body_str else {}
            # Log structure: keys present and their lengths
            body_structure = {}
            for key, value in body_json.items():
                if isinstance(value, str):
                    value_len = len(value)
                    max_len = OAUTH_DEBUG_PREVIEW_LENGTH
                    if value_len > max_len:
                        preview = value[:max_len] + '...'
                    else:
                        preview = value
                    is_empty = not bool(value)
                    body_structure[key] = (
                        f"string(len={value_len}, "
                        f"empty={is_empty}, "
                        f"preview='{preview}')"
                    )
                else:
                    body_structure[key] = f"{type(value).__name__}"
            logger.info(
                f"[OAuth Debug] Body structure: {body_structure}"
            )

            # Specifically check for 'state' field issues
            if 'state' in body_json:
                state_val = body_json['state']
                if isinstance(state_val, str):
                    state_len = len(state_val)
                else:
                    state_len = 'N/A'
                max_preview = OAUTH_DEBUG_PREVIEW_LENGTH
                state_preview = repr(state_val)[:max_preview]
                state_empty = not bool(state_val)
                state_type = type(state_val).__name__
                logger.info(
                    f"[OAuth Debug] state - "
                    f"type: {state_type}, "
                    f"len: {state_len}, "
                    f"empty: {state_empty}, "
                    f"preview: {state_preview}"
                )
            else:
                logger.warning(
                    "[OAuth Debug] 'state' MISSING from body!"
                )

            if 'code' in body_json:
                code_val = body_json['code']
                if isinstance(code_val, str):
                    code_len = len(code_val)
                else:
                    code_len = 'N/A'
                code_empty = not bool(code_val)
                code_type = type(code_val).__name__
                logger.info(
                    f"[OAuth Debug] code - "
                    f"type: {code_type}, "
                    f"len: {code_len}, "
                    f"empty: {code_empty}"
                )
            else:
                logger.warning(
                    "[OAuth Debug] 'code' MISSING from body!"
                )

        except json.JSONDecodeError:
            logger.exception("[OAuth Debug] Parse failed")
            body_preview = body_str[:200]
            logger.info(
                f"[OAuth Debug] Raw body (200 chars): "
                f"{body_preview}"
            )
        except (KeyError, AttributeError, TypeError, ValueError):
            logger.exception("[OAuth Debug] Inspection error")
        except Exception:
            logger.exception(
                "[OAuth Debug] Unexpected error during body inspection"
            )
            # Re-raise to avoid masking critical errors
            raise

        # IMPORTANT: We need to make the body available again
        # Create a new request with the body we read
        async def receive():
            return {"type": "http.request", "body": body_bytes}
        request = Request(scope=request.scope, receive=receive)

    response = await call_next(request)
    return response


# Optional API key authentication
API_KEY = os.getenv("API_KEY")
CONTROL_TOKEN = os.getenv("CONTROL_TOKEN", "")
LLM_MODEL = os.getenv("LLM_MODEL", "vertex/google/gemini-2.5-flash")


# Validate critical environment variables at startup
def validate_environment():
    """Validate that all required environment variables are set."""
    missing_vars = []

    # Check for at least one LLM API key
    requestyai_key = os.getenv("REQUESTYAI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not requestyai_key and not openai_key:
        missing_vars.append("REQUESTYAI_API_KEY or OPENAI_API_KEY")

    if missing_vars:
        error_msg = f"""
╔════════════════════════════════════════════════════════════════╗
║                  CRITICAL CONFIGURATION ERROR                   ║
╚════════════════════════════════════════════════════════════════╝

Missing required environment variables:
{chr(10).join(f'  ✗ {var}' for var in missing_vars)}

The Cat-Emails API requires an LLM service API key to function.
Please set one of the following environment variables:

  • REQUESTYAI_API_KEY - For RequestYAI service
  • OPENAI_API_KEY     - For OpenAI service

Example:
  export REQUESTYAI_API_KEY="your-api-key-here"

For Railway deployment:
  railway variables set REQUESTYAI_API_KEY "your-api-key-here"

See docs/RAILWAY_DEPLOYMENT.md for more information.
"""
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)

    logger.info("✓ All required environment variables are set")

# Validate environment on module load
validate_environment()

# Background processing configuration
BACKGROUND_PROCESSING_ENABLED = os.getenv("BACKGROUND_PROCESSING", "true").lower() == "true"
BACKGROUND_SCAN_INTERVAL = int(os.getenv("BACKGROUND_SCAN_INTERVAL", "300"))  # 5 minutes default
BACKGROUND_PROCESS_HOURS = int(os.getenv("BACKGROUND_PROCESS_HOURS", "2"))  # Look back 2 hours default

# Category aggregation configuration
ENABLE_CATEGORY_AGGREGATION = os.getenv("ENABLE_CATEGORY_AGGREGATION", "true").lower() == "true"
CATEGORY_AGGREGATION_BUFFER_SIZE = int(os.getenv("CATEGORY_AGGREGATION_BUFFER_SIZE", "100"))

# Minimum delay to ensure healthchecks pass (seconds)
MIN_BACKGROUND_START_DELAY = 1

# Delay before starting background processor (seconds)
try:
    delay_value = int(os.getenv("BACKGROUND_START_DELAY_SECONDS", "5"))
    if delay_value < MIN_BACKGROUND_START_DELAY:
        logger.warning(
            f"BACKGROUND_START_DELAY_SECONDS value {delay_value} is below minimum {MIN_BACKGROUND_START_DELAY}, "
            f"using minimum value of {MIN_BACKGROUND_START_DELAY}"
        )
        BACKGROUND_START_DELAY = MIN_BACKGROUND_START_DELAY
    else:
        BACKGROUND_START_DELAY = delay_value
except (ValueError, TypeError):
    logger.warning("Invalid BACKGROUND_START_DELAY_SECONDS value, using default of 5 seconds")
    BACKGROUND_START_DELAY = 5

# Default database path when DATABASE_PATH env var is not set
DEFAULT_DB_PATH = "./email_summaries/summaries.db"

# Global flag for background thread control
background_thread_running = True
background_thread = None
next_execution_time = None
background_processor_service: Optional[BackgroundProcessorService] = None

# Global background processor startup task
background_startup_task: Optional[asyncio.Task] = None

# Global processing status manager instance
processing_status_manager = ProcessingStatusManager(max_history=100)

# Global WebSocket manager instance
websocket_manager: Optional[StatusWebSocketManager] = None

# Global settings service instance
# Use DATABASE_PATH from env, or default to ./email_summaries/summaries.db
default_db_path = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
settings_service = SettingsService(db_path=default_db_path)

# Global LLM service factory instance
llm_service_factory = LLMServiceFactory()

# Global email categorizer service instance
email_categorizer_service = EmailCategorizerService(llm_service_factory)

# Global WebSocket auth service instance
websocket_auth_service = WebSocketAuthService(API_KEY)

# Global account email processor service instance (will be initialized with dependencies below)
account_email_processor_service: Optional[AccountEmailProcessorService] = None

# Global rate limiter for force processing endpoint (5 minutes default)
force_process_rate_limiter = RateLimiterService(default_interval_seconds=300)

# Global recommendation service instance (will be initialized on first use)
recommendation_service: Optional[BlockingRecommendationService] = None

# Global category aggregation components (initialized on startup if enabled)
category_aggregator = None
category_tally_repository: Optional[CategoryTallyRepository] = None
tally_cleanup_service = None


# Initialize category aggregation components
def _initialize_category_aggregation():
    """Initialize category aggregation components if enabled."""
    global category_aggregator, category_tally_repository, tally_cleanup_service

    if not ENABLE_CATEGORY_AGGREGATION:
        logger.info("⏸️  Category aggregation is disabled")
        return None

    if category_aggregator:
        return category_aggregator

    try:
        logger.info("🎬 Initializing category aggregation components...")

        # Initialize repository for tallies using the SQLAlchemy session
        # CategoryTallyRepository requires a Session object, not a db_path string
        session = settings_service.repository._get_session()
        category_tally_repository = CategoryTallyRepository(session)

        # Initialize config
        config = CategoryAggregationConfig()

        # Initialize aggregator
        category_aggregator = CategoryAggregator(
            repository=category_tally_repository,
            buffer_size=CATEGORY_AGGREGATION_BUFFER_SIZE
        )

        # Initialize cleanup service
        tally_cleanup_service = TallyCleanupService(
            repository=category_tally_repository,
            config=config
        )

        logger.info(f"✅ Category aggregation initialized (buffer size: {CATEGORY_AGGREGATION_BUFFER_SIZE})")
        return category_aggregator

    except Exception as e:
        logger.exception("Failed to initialize category aggregation")
        return None


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
            email_categorizer=email_categorizer_service,
            api_token=CONTROL_TOKEN,
            llm_model=LLM_MODEL,
            account_category_client=AccountCategoryClient(repository=settings_service.repository),
            deduplication_factory=EmailDeduplicationFactory()
            # create_gmail_fetcher defaults to GmailFetcher constructor
        )
    return account_email_processor_service


# API response models are now imported from models/ directory above


def get_account_service() -> AccountCategoryClientInterface:
    """Dependency to provide AccountCategoryClient instance."""
    try:
        return AccountCategoryClient(repository=settings_service.repository)
    except Exception as e:
        logger.error(f"Failed to create AccountCategoryClient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database service unavailable"
        )


def get_recommendation_service() -> BlockingRecommendationService:
    """Dependency to provide BlockingRecommendationService instance."""
    global recommendation_service
    if not recommendation_service:
        try:
            # Initialize domain service
            # Use mock mode when no CONTROL_TOKEN is configured
            use_mock = not bool(CONTROL_TOKEN)
            domain_service = DomainService(
                api_token=CONTROL_TOKEN or None,
                mock_mode=use_mock
            )
            if use_mock:
                logger.info("BlockingRecommendationService using DomainService in mock mode (no CONTROL_TOKEN configured)")

            # Initialize category aggregation config
            config = CategoryAggregationConfig()

            # Create recommendation service
            recommendation_service = BlockingRecommendationService(
                repository=settings_service.repository,
                config=config,
                domain_service=domain_service
            )
        except Exception as e:
            logger.exception("Failed to create BlockingRecommendationService")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Recommendation service unavailable"
            ) from e
    return recommendation_service


def get_category_tally_repository() -> CategoryTallyRepository:
    """Dependency to provide CategoryTallyRepository instance."""
    global category_tally_repository
    if not category_tally_repository:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Category aggregation service not available"
        )
    return category_tally_repository


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

        # Initialize category aggregation if enabled
        aggregator = _initialize_category_aggregation()

        # Create background processor service instance
        background_processor_service = BackgroundProcessorService(
            process_account_callback=processor_service.process_account,
            settings_service=settings_service,
            scan_interval=BACKGROUND_SCAN_INTERVAL,
            background_enabled=BACKGROUND_PROCESSING_ENABLED,
            category_aggregator=aggregator
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
        "version": API_VERSION,
        "endpoints": {
            "health": "GET /api/health",
            "config": "GET /api/config",
            "status": "GET /api/status (unified processing and background status)",
            "background_start": "POST /api/background/start",
            "background_stop": "POST /api/background/stop",
            "background_next_execution": "GET /api/background/next-execution",
            "morning_summary": "POST /api/summaries/morning",
            "evening_summary": "POST /api/summaries/evening",
            "weekly_summary": "POST /api/summaries/weekly",
            "monthly_summary": "POST /api/summaries/monthly",
            "top_categories": "GET /api/accounts/{email_address}/categories/top",
            "list_accounts": "GET /api/accounts",
            "create_account": "POST /api/accounts",
            "verify_password": "GET /api/accounts/{email_address}/verify-password",
            "deactivate_account": "PUT /api/accounts/{email_address}/deactivate",
            "force_process_account": "POST /api/accounts/{email_address}/process",
            "processing_history": "GET /api/processing/history",
            "processing_statistics": "GET /api/processing/statistics",
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

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Cat Emails Summary API",
        "version": API_VERSION
    }

    # Background processor status
    try:
        background_status = "disabled"
        if BACKGROUND_PROCESSING_ENABLED:
            if background_thread and background_thread.is_alive():
                background_status = "running"
            else:
                background_status = "stopped"

        health_status["background_processor"] = {
            "enabled": BACKGROUND_PROCESSING_ENABLED,
            "status": background_status,
            "scan_interval_seconds": BACKGROUND_SCAN_INTERVAL,
            "process_hours": settings_service.get_lookback_hours() if settings_service else None
        }
    except Exception as e:
        logger.error(f"Error getting background processor status: {e}")
        health_status["background_processor"] = {"error": str(e)}

    # Database status
    try:
        from clients.account_category_client import AccountCategoryClient
        test_client = AccountCategoryClient(repository=settings_service.repository)
        health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


@app.get("/api/config", response_model=ConfigurationResponse, tags=["health"])
async def get_configuration(x_api_key: Optional[str] = Header(None)):
    """
    Get complete project configuration
    
    Returns all current configuration settings including:
    - Database type and connection details (MySQL, SQLite local, SQLite cloud)
    - LLM provider and model information
    - Background processing settings
    - API service configuration
    
    Requires API key authentication if configured.
    """
    verify_api_key(x_api_key)
    
    # Determine database configuration
    database_config = _get_database_config()
    
    # Determine LLM configuration
    llm_config = _get_llm_config()
    
    # Background processing configuration
    background_config = BackgroundProcessingConfig(
        enabled=BACKGROUND_PROCESSING_ENABLED,
        scan_interval_seconds=BACKGROUND_SCAN_INTERVAL,
        lookback_hours=BACKGROUND_PROCESS_HOURS
    )
    
    # API service configuration
    api_config = APIServiceConfig(
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8001")),
        api_key_required=API_KEY is not None
    )
    
    # Determine environment
    environment = os.getenv("ENVIRONMENT", os.getenv("RAILWAY_ENVIRONMENT", "development"))
    
    # Get total Gmail accounts count
    total_accounts = 0
    try:
        # Use AccountCategoryClient which has the get_all_accounts method
        account_client = AccountCategoryClient(repository=settings_service.repository)
        accounts = account_client.get_all_accounts(active_only=False)
        total_accounts = len(accounts)
    except Exception as e:
        logger.error(f"Error getting account count for config: {str(e)}")
    
    return ConfigurationResponse(
        database=database_config,
        llm=llm_config,
        background_processing=background_config,
        api_service=api_config,
        environment=environment,
        version=API_VERSION,
        total_gmail_accounts=total_accounts
    )


def _safe_int_env(var_name: str, default: int) -> int:
    """
    Safely parse an integer environment variable.

    Args:
        var_name: Name of the environment variable
        default: Default value to return if variable is missing or invalid

    Returns:
        Integer value of the environment variable or default
    """
    value = os.getenv(var_name)
    if not value or value.strip() == "":
        # Railway sometimes sets env vars to empty string; treat same as unset
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("Invalid value for %s=%r; falling back to %d", var_name, value, default)
        return default


def _get_database_config() -> DatabaseConfig:
    """Determine database configuration from environment variables."""
    # Check for MySQL configuration (MYSQL_* env vars only)
    db_host = os.getenv("MYSQL_HOST")
    db_user = os.getenv("MYSQL_USER")
    db_url = os.getenv("MYSQL_URL")
    db_path = os.getenv("DATABASE_PATH")
    db_name = os.getenv("MYSQL_DATABASE", "cat_emails")

    # Get connection status from the settings_service repository
    connection_status = {
        "connected": False,
        "status": "Unknown",
        "error": None,
        "details": {}
    }

    try:
        if settings_service and hasattr(settings_service, 'repository'):
            status = settings_service.repository.get_connection_status()
            connection_status = {
                "connected": status.get("connected", False),
                "status": status.get("status", "Unknown"),
                "error": status.get("error"),
                "details": status.get("details", {})
            }
    except Exception as e:
        logger.exception("Error checking database connection status for /api/config")
        connection_status = {
            "connected": False,
            "status": "Error checking connection",
            "error": str(e),
            "details": {}
        }

    # Build env_vars for MySQL configurations (excludes password and port)
    env_vars = DatabaseEnvVars(
        host_var="MYSQL_HOST",
        host_value=db_host,
        name_var="MYSQL_DATABASE",
        name_value=db_name,
        user_var="MYSQL_USER",
        user_value=db_user
    )

    # Check if MySQL is active (either via env vars or successful connection)
    is_mysql_connected = connection_status["connected"] and connection_status.get("details", {}).get("engine_initialized", False)
    
    # Always default to MySQL configuration since SQLite fallback is removed
    details = connection_status.get("details", {})
    
    # Use values from active connection if available (handles MYSQL_URL case), otherwise env vars
    final_host = details.get("host") or db_host
    final_port = details.get("port") or _safe_int_env("MYSQL_PORT", 3306)
    final_database = details.get("database") or db_name
    pool_size = details.get("pool_size") or _safe_int_env("MYSQL_POOL_SIZE", 5)

    return DatabaseConfig(
        type="mysql",
        host=final_host,
        port=final_port,
        database_name=final_database,
        connection_pool_size=pool_size,
        connected=connection_status["connected"],
        connection_status=connection_status["status"],
        connection_error=connection_status["error"],
        env_vars=env_vars
    )


def _get_llm_config() -> LLMConfig:
    """Determine LLM service configuration from environment variables."""
    requestyai_key = os.getenv("REQUESTYAI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("REQUESTYAI_BASE_URL", DEFAULT_REQUESTYAI_BASE_URL)
    
    if requestyai_key:
        provider = "RequestYAI"
        api_key_configured = True
    elif openai_key:
        provider = "OpenAI"
        api_key_configured = True
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    else:
        provider = "Unknown"
        api_key_configured = False
    
    return LLMConfig(
        provider=provider,
        model=LLM_MODEL,
        base_url=base_url,
        api_key_configured=api_key_configured
    )


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


@app.get("/api/status", response_model=UnifiedStatusResponse, tags=["processing-status"])
async def get_unified_status(
    include_recent: bool = Query(True, description="Include recent processing runs"),
    recent_limit: int = Query(5, ge=1, le=50, description="Number of recent runs to return (1-50)"),
    include_stats: bool = Query(False, description="Include processing statistics"),
    x_api_key: Optional[str] = Header(None)
):
    """
    Get unified processing and background status

    Single endpoint that consolidates all status information:
    - Current processing state (is a job running?)
    - Background processor status (is the thread alive?)
    - Recent processing runs (optional)
    - Processing statistics (optional)

    This replaces the need to call multiple endpoints:
    - /api/processing/status
    - /api/background/status
    - /api/processing/current-status

    Query Parameters:
        include_recent: Whether to include recent processing runs (default: True)
        recent_limit: Number of recent runs to return, 1-50 (default: 5)
        include_stats: Whether to include processing statistics (default: False)

    Returns:
        UnifiedStatusResponse containing all status information

    Authentication:
        Requires X-API-Key header if API key is configured
    """
    verify_api_key(x_api_key)

    try:
        global processing_status_manager, websocket_manager, background_thread, background_thread_running

        # Validate query parameters
        if recent_limit < 1 or recent_limit > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="recent_limit must be between 1 and 50"
            )

        # Get processing status
        is_processing = processing_status_manager.is_processing()
        current_status = processing_status_manager.get_current_status()

        # Get background thread info
        thread_info = None
        if background_thread:
            thread_info = BackgroundThreadInfo(
                name=background_thread.name,
                is_alive=background_thread.is_alive(),
                daemon=background_thread.daemon,
                ident=background_thread.ident
            )

        background_status = BackgroundStatus(
            enabled=BACKGROUND_PROCESSING_ENABLED,
            running=background_thread_running,
            thread=thread_info,
            configuration=BackgroundConfiguration(
                scan_interval_seconds=BACKGROUND_SCAN_INTERVAL,
                process_hours=settings_service.get_lookback_hours()
            )
        )

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

        return UnifiedStatusResponse(
            is_processing=is_processing,
            current_status=current_status,
            background=background_status,
            recent_runs=recent_runs,
            statistics=statistics,
            timestamp=datetime.now().isoformat(),
            websocket_available=websocket_available
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_unified_status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve status: {str(e)}"
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
        from pathlib import Path
        import random
        
        # Initialize summary service
        gmail_email = os.getenv('GMAIL_EMAIL')
        summary_service = EmailSummaryService(gmail_email=gmail_email, repository=settings_service.repository)
        
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


# ==================== OAuth Endpoints ====================

def get_oauth_service() -> OAuthFlowService:
    """Get OAuth flow service instance."""
    return OAuthFlowService()


def get_oauth_state_repository() -> OAuthStateRepository:
    """Get OAuth state repository instance."""
    return OAuthStateRepository()


@app.get("/api/auth/gmail/authorize", response_model=OAuthAuthorizeResponse, tags=["oauth"])
async def initiate_oauth(
    redirect_uri: str = Query(..., description="URL to redirect to after Google OAuth consent"),
    login_hint: Optional[str] = Query(None, description="Optional email address to pre-fill in consent screen"),
    x_api_key: Optional[str] = Header(None),
    oauth_service: OAuthFlowService = Depends(get_oauth_service),
    state_repo: OAuthStateRepository = Depends(get_oauth_state_repository),
):
    """
    Initiate Google OAuth authorization flow.

    Returns an authorization URL that the frontend should redirect the user to.
    The user will complete consent on Google's site, then be redirected back
    to the specified redirect_uri with an authorization code.

    Args:
        redirect_uri: URL to redirect to after consent (must match Google Cloud Console config)
        login_hint: Optional email to pre-fill in consent screen

    Returns:
        OAuthAuthorizeResponse with authorization_url and state token
    """
    verify_api_key(x_api_key)

    try:
        # Clean up expired state tokens to prevent database bloat
        state_repo.cleanup_expired_states()

        # Generate state token for CSRF protection
        state = oauth_service.generate_state_token()
        state_len = len(state)
        preview_len = OAUTH_DEBUG_PREVIEW_LENGTH
        state_preview = state[:preview_len]
        logger.info(
            f"[OAuth Debug] Generated state - "
            f"len: {state_len}, "
            f"preview: {state_preview}..."
        )

        # Store state in database for callback validation
        state_repo.store_state(
            state_token=state, redirect_uri=redirect_uri
        )
        logger.info(
            f"[OAuth Debug] Stored state with "
            f"redirect_uri: {redirect_uri}"
        )

        # Generate authorization URL
        authorization_url = oauth_service.generate_authorization_url(
            redirect_uri=redirect_uri,
            state=state,
            login_hint=login_hint,
        )

        # Verify state parameter in URL
        parsed = urllib.parse.urlparse(authorization_url)
        params = urllib.parse.parse_qs(parsed.query)
        url_state = params.get('state', [''])[0]
        if url_state:
            url_state_len = len(url_state)
            matches = url_state == state
            logger.info(
                f"[OAuth Debug] URL state - "
                f"len: {url_state_len}, "
                f"matches: {matches}"
            )
        else:
            logger.warning(
                "[OAuth Debug] State NOT in auth URL!"
            )

        logger.info(
            f"Generated OAuth URL for "
            f"redirect: {redirect_uri}"
        )

        return OAuthAuthorizeResponse(
            authorization_url=authorization_url,
            state=state,
        )

    except ValueError as e:
        logger.exception("OAuth configuration error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth not configured: {e!r}"
        ) from e
    except Exception as e:
        logger.exception("Error initiating OAuth")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OAuth: {e!r}"
        ) from e


@app.post("/api/auth/gmail/callback", response_model=OAuthCallbackResponse, tags=["oauth"])
async def oauth_callback(
    request: OAuthCallbackRequest,
    redirect_uri: Optional[str] = Query(None, description="Same redirect_uri used in authorization request (optional, retrieved from state if not provided)"),
    x_api_key: Optional[str] = Header(None),
    oauth_service: OAuthFlowService = Depends(get_oauth_service),
    account_service: AccountCategoryClientInterface = Depends(get_account_service),
    state_repo: OAuthStateRepository = Depends(get_oauth_state_repository),
):
    """
    Handle OAuth callback after user consent.

    Exchanges the authorization code for access and refresh tokens,
    then stores them in the database for the account.

    Args:
        request: Contains authorization code and state token
        redirect_uri: Same redirect_uri used in authorization request (optional, retrieved from state if not provided)

    Returns:
        OAuthCallbackResponse with success status and granted scopes
    """
    # Log OAuth callback parameters (sanitized - no sensitive data)
    state_len = len(request.state) if request.state else 0
    logger.info(
        f"OAuth callback received - "
        f"redirect_uri: {'provided' if redirect_uri else 'omitted'}, "
        f"code: {'present' if request.code else 'missing'}, "
        f"state: {'present (' + str(state_len) + ' chars)' if request.state else 'missing/empty'}"
    )

    # Additional debug logging for state issues
    if not request.state:
        logger.warning(
            f"OAuth callback state is empty/missing - "
            f"type: {type(request.state).__name__}, "
            f"value: {request.state!r}"
        )

    verify_api_key(x_api_key)

    try:
        # Validate state token from database
        state_data = state_repo.get_state(request.state)
        if not state_data:
            logger.warning("OAuth callback failed - state token not found or expired")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired state token. Please restart the OAuth flow."
            )

        # Use redirect_uri from state data if not provided in query
        effective_redirect_uri = redirect_uri or state_data.get('redirect_uri')
        if not effective_redirect_uri:
            logger.error("OAuth callback failed - no redirect_uri in query or state")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No redirect_uri found. Please restart the OAuth flow."
            )

        # Exchange authorization code for tokens
        logger.info(f"Exchanging authorization code - redirect_uri source: {'query' if redirect_uri else 'state'}")
        token_response = oauth_service.exchange_code_for_tokens(
            code=request.code,
            redirect_uri=effective_redirect_uri,
        )

        access_token = token_response.get('access_token')
        refresh_token = token_response.get('refresh_token')
        expires_in = token_response.get('expires_in', 3600)
        scope_string = token_response.get('scope', '')

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No refresh token received. User may need to revoke access and re-authorize with prompt=consent."
            )

        # Parse scopes
        scopes = oauth_service.parse_scopes(scope_string)

        # Calculate token expiry
        token_expiry = oauth_service.calculate_token_expiry(expires_in)

        # Get user's email from Google's userinfo endpoint
        try:
            userinfo_request = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            with urllib.request.urlopen(
                userinfo_request, timeout=10
            ) as response:
                userinfo = json.loads(
                    response.read().decode('utf-8')
                )
                email_address = userinfo.get('email')
        except (URLError, HTTPError) as e:
            logger.exception(
                f"Failed to retrieve user info from Google: {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to retrieve user information from Google"
            ) from e

        if not email_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Could not retrieve email address from "
                    "OAuth response"
                )
            )

        # Create or update account with OAuth tokens
        account_service.get_or_create_account(
            email_address=email_address,
            display_name=None,
            app_password=None,
            auth_method='oauth',
            oauth_refresh_token=refresh_token,
        )

        # Update OAuth tokens
        account_service.update_oauth_tokens(
            email_address=email_address,
            refresh_token=refresh_token,
            access_token=access_token,
            token_expiry=token_expiry,
            scopes=scopes,
        )

        # Delete the used state token
        state_repo.delete_state(request.state)

        logger.info(f"Successfully completed OAuth flow for: {email_address}")

        return OAuthCallbackResponse(
            success=True,
            email_address=email_address,
            scopes=scopes,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.exception("OAuth token exchange failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token exchange failed: {e!r}"
        ) from e
    except Exception as e:
        logger.exception("Error in OAuth callback")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {e!r}"
        ) from e


@app.get("/api/accounts/{email_address}/oauth-status", response_model=OAuthStatusResponse, tags=["oauth"])
async def get_oauth_status(
    email_address: str = Path(..., description="Gmail email address"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryClientInterface = Depends(get_account_service),
):
    """
    Get OAuth connection status for an account.

    Returns whether OAuth is configured and the granted scopes.

    Args:
        email_address: Gmail email address

    Returns:
        OAuthStatusResponse with connection status and scopes
    """
    verify_api_key(x_api_key)

    try:
        # URL decode the email address
        from urllib.parse import unquote
        email_address = unquote(email_address)

        status_data = service.get_oauth_status(email_address)

        if status_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {email_address}"
            )

        return OAuthStatusResponse(
            connected=status_data['connected'],
            auth_method=status_data['auth_method'],
            scopes=status_data['scopes'],
            token_expiry=status_data['token_expiry'],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting OAuth status for {email_address}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get OAuth status: {e!r}"
        ) from e


@app.delete("/api/accounts/{email_address}/oauth", response_model=OAuthRevokeResponse, tags=["oauth"])
async def revoke_oauth(
    email_address: str = Path(..., description="Gmail email address"),
    x_api_key: Optional[str] = Header(None),
    oauth_service: OAuthFlowService = Depends(get_oauth_service),
    account_service: AccountCategoryClientInterface = Depends(get_account_service),
):
    """
    Revoke OAuth access for an account.

    Revokes the OAuth tokens with Google and clears them from the database.
    The account will revert to requiring IMAP authentication.

    Args:
        email_address: Gmail email address

    Returns:
        OAuthRevokeResponse with success status
    """
    verify_api_key(x_api_key)

    try:
        # URL decode the email address
        from urllib.parse import unquote
        email_address = unquote(email_address)

        # Get current OAuth status to retrieve tokens
        status_data = account_service.get_oauth_status(email_address)

        if status_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {email_address}"
            )

        if not status_data['connected']:
            return OAuthRevokeResponse(
                success=True,
                message="Account is not using OAuth authentication"
            )

        # Get account to retrieve refresh token
        account = account_service.get_account_by_email(email_address)
        if account and account.oauth_refresh_token:
            # Revoke token with Google
            oauth_service.revoke_token(account.oauth_refresh_token)

        # Clear OAuth tokens from database
        cleared = account_service.clear_oauth_tokens(email_address)

        if cleared:
            logger.info(f"Revoked OAuth access for: {email_address}")
            return OAuthRevokeResponse(
                success=True,
                message=f"OAuth access revoked for {email_address}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear OAuth tokens from database"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error revoking OAuth for {email_address}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke OAuth: {e!r}"
        ) from e


# ==================== Account Endpoints ====================

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
                masked_password=mask_password(account.app_password),
                password_length=len(account.app_password) if account.app_password else 0,
                is_active=account.is_active,
                last_scan_at=account.last_scan_at,
                created_at=account.created_at,
                auth_method=account.auth_method
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
            display_name=request.display_name,
            app_password=request.app_password,
            auth_method=request.auth_method,
            oauth_refresh_token=request.oauth_refresh_token,
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


@app.get("/api/accounts/{email_address}/verify-password", response_model=StandardResponse, tags=["accounts"])
async def verify_account_password(
    email_address: str = Path(..., description="Gmail email address to verify"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryClientInterface = Depends(get_account_service)
):
    """
    Verify the password status for an email account

    Tests whether the account has a password configured and attempts to verify
    if it can authenticate with Gmail. This helps diagnose authentication issues.

    Args:
        email_address: Gmail email address to verify

    Returns:
        StandardResponse with verification status and details

    Raises:
        401: Invalid or missing API key
        404: Account not found
        500: Internal server error
    """
    verify_api_key(x_api_key)

    try:
        logger.info(f"Verifying password for account: {email_address}")

        # Get the account from database
        accounts = service.get_all_accounts(active_only=False)
        account = None
        for acc in accounts:
            if acc.email_address.lower() == email_address.lower():
                account = acc
                break

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {email_address}"
            )

        # Check if password exists
        if not account.app_password:
            response = StandardResponse(
                status="error",
                message=f"No app password configured for {email_address}. Please add an app password using POST /api/accounts with app_password field.",
                timestamp=datetime.now().isoformat()
            )
            logger.warning(f"No app password found for account: {email_address}")
            return response

        # Try to connect to Gmail to verify the password
        from services.gmail_connection_service import GmailConnectionService
        connection_service = GmailConnectionService(
            email_address=account.email_address,
            password=account.app_password
        )

        try:
            conn = connection_service.connect()
            conn.logout()

            response = StandardResponse(
                status="success",
                message=f"Password verified successfully for {email_address}. Authentication with Gmail succeeded.",
                timestamp=datetime.now().isoformat()
            )
            logger.info(f"Password verified successfully for account: {email_address}")
            return response

        except Exception as auth_error:
            error_msg = str(auth_error)

            # Determine if it's an authentication error or other issue
            if "authentication failed" in error_msg.lower() or "AUTHENTICATIONFAILED" in error_msg:
                response = StandardResponse(
                    status="error",
                    message=f"Password verification failed for {email_address}. The app password appears to be incorrect. Error: {error_msg}",
                    timestamp=datetime.now().isoformat()
                )
                logger.error(f"Invalid password for account {email_address}: {error_msg}")
            else:
                response = StandardResponse(
                    status="error",
                    message=f"Connection test failed for {email_address}. This may be a network issue or Gmail service problem. Error: {error_msg}",
                    timestamp=datetime.now().isoformat()
                )
                logger.error(f"Connection error for account {email_address}: {error_msg}")

            return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in verify_account_password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
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

        # Use the delete_account method from the service
        success = service.delete_account(email_address)

        if success:
            response = StandardResponse(
                status="success",
                message=f"Account and all associated data deleted successfully: {email_address}",
                timestamp=datetime.now().isoformat()
            )
            logger.info(f"Successfully deleted account: {email_address}")
            return response
        else:
            logger.warning(f"Account not found for deletion: {email_address}")
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


@app.post("/api/accounts/{email_address}/process", response_model=ForceProcessResponse, tags=["accounts"], status_code=status.HTTP_202_ACCEPTED)
async def force_process_account(
    email_address: str = Path(..., description="Gmail email address to process"),
    hours: Optional[int] = Query(None, ge=1, le=168, description="Override lookback hours (1-168, default from settings)"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryClientInterface = Depends(get_account_service)
):
    """
    Force immediate email processing for a specific account

    Triggers immediate email processing for a specific Gmail account outside the regular
    background scan cycle. This is useful for on-demand processing or catching up on
    missed emails.

    **Concurrency Protection:**
    - Returns 409 Conflict if the account is already being processed
    - Returns 409 Conflict if a different account is currently being processed
    - Only one account can be processed at a time

    **Async Execution:**
    - Returns 202 Accepted immediately without waiting for completion
    - Processing happens asynchronously in the background
    - Use WebSocket (/ws/status) or polling (/api/processing/current-status) to monitor progress

    Args:
        email_address: Gmail email address to process
        hours: Optional override for lookback hours (1-168 hours, default from settings)

    Returns:
        ForceProcessResponse with processing status and monitoring information

    Raises:
        400: Invalid email address or parameters
        401: Invalid or missing API key
        404: Account not found in database
        409: Account is already being processed
        500: Failed to start processing

    Example Response (202 Accepted):
        {
            "status": "success",
            "message": "Email processing started for user@gmail.com",
            "email_address": "user@gmail.com",
            "timestamp": "2025-10-07T10:30:00Z",
            "processing_info": {
                "hours": 2,
                "status_url": "/api/status",
                "websocket_url": "/ws/status"
            }
        }

    Example Response (409 Conflict):
        {
            "status": "already_processing",
            "message": "Account user@gmail.com is currently being processed",
            "email_address": "user@gmail.com",
            "timestamp": "2025-10-07T10:30:00Z",
            "processing_info": {
                "state": "PROCESSING",
                "current_step": "Processing email 5 of 20"
            }
        }
    """
    verify_api_key(x_api_key)

    try:
        logger.info(f"Force processing request for account: {email_address}")

        # Validate email address format (basic validation)
        if not email_address or '@' not in email_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid email address format: {email_address}"
            )

        # Check rate limit for this account
        global force_process_rate_limiter
        allowed, seconds_remaining = force_process_rate_limiter.check_rate_limit(email_address.lower())

        if not allowed:
            minutes_remaining = seconds_remaining / 60
            logger.warning(
                f"Rate limit exceeded for {email_address}: "
                f"{seconds_remaining:.0f}s remaining ({minutes_remaining:.1f} minutes)"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Please wait {minutes_remaining:.1f} minutes before processing {email_address} again",
                    "seconds_remaining": round(seconds_remaining, 1),
                    "retry_after": round(seconds_remaining)
                }
            )

        # Check if any processing is currently active
        global processing_status_manager

        if processing_status_manager.is_processing():
            current_email = processing_status_manager.get_processing_email()
            current_status = processing_status_manager.get_current_status()

            # Check if it's the same account being requested
            if current_email and current_email.lower() == email_address.lower():
                logger.warning(f"Account {email_address} is already being processed")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=ForceProcessResponse(
                        status="already_processing",
                        message=f"Account {email_address} is currently being processed",
                        email_address=email_address,
                        timestamp=datetime.now().isoformat(),
                        processing_info=ProcessingInfo(
                            state=current_status.get('state') if current_status else None,
                            current_step=current_status.get('current_step') if current_status else None,
                            status_url="/api/status",
                            websocket_url="/ws/status"
                        )
                    ).model_dump()
                )
            else:
                # Different account is being processed
                logger.warning(f"Cannot process {email_address}: {current_email} is currently being processed")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=ForceProcessResponse(
                        status="already_processing",
                        message=f"Cannot process {email_address}: another account ({current_email}) is currently being processed",
                        email_address=email_address,
                        timestamp=datetime.now().isoformat(),
                        processing_info=ProcessingInfo(
                            state=current_status.get('state') if current_status else None,
                            current_step=f"Processing {current_email}",
                            status_url="/api/status",
                            websocket_url="/ws/status"
                        )
                    ).model_dump()
                )

        # Check if account exists in database
        account = service.get_account_by_email(email_address)
        if not account:
            logger.warning(f"Account not found for force processing: {email_address}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {email_address}. Please create the account first via POST /api/accounts"
            )

        # Check if account has app password
        if not account.app_password:
            logger.error(f"No app password configured for account: {email_address}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No app password configured for {email_address}. Please update the account with a valid app password."
            )

        # Determine lookback hours
        lookback_hours = hours if hours is not None else settings_service.get_lookback_hours()

        # Initialize account email processor service if not already initialized
        processor_service = _initialize_account_email_processor()

        # Temporarily override lookback hours if specified
        original_hours = settings_service.get_lookback_hours()
        if hours is not None:
            settings_service.set_lookback_hours(hours)

        # Start processing asynchronously in a background thread
        def process_in_background():
            try:
                logger.info(f"Starting background processing for {email_address} with {lookback_hours} hours lookback")
                processor_service.process_account(email_address)
            except Exception as e:
                logger.error(f"Error in background processing for {email_address}: {str(e)}")
            finally:
                # Restore original lookback hours if it was overridden
                if hours is not None:
                    settings_service.set_lookback_hours(original_hours)

        # Launch in background thread
        thread = threading.Thread(
            target=process_in_background,
            name=f"ForceProcess-{email_address}",
            daemon=True
        )
        thread.start()

        logger.info(f"Successfully started force processing for {email_address}")

        # Return 202 Accepted immediately
        return ForceProcessResponse(
            status="success",
            message=f"Email processing started for {email_address}",
            email_address=email_address,
            timestamp=datetime.now().isoformat(),
            processing_info=ProcessingInfo(
                hours=lookback_hours,
                status_url="/api/status",
                websocket_url="/ws/status"
            )
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"Validation error in force_process_account: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        logger.error(f"Unexpected error in force_process_account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start email processing: {str(e)}"
        )


@app.get(
    "/api/accounts/{email_address}/recommendations",
    response_model=BlockingRecommendationResult,
    tags=["recommendations"]
)
async def get_blocking_recommendations(
    email_address: str = Path(..., description="Gmail email address"),
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze (1-30, default: 7)"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryClientInterface = Depends(get_account_service),
    rec_service: BlockingRecommendationService = Depends(get_recommendation_service)
):
    """
    Get blocking recommendations for an email account

    Analyzes category tallies over a rolling window period and generates
    recommendations for categories that should be considered for blocking.

    Recommendations are based on:
    - Percentage thresholds (HIGH: >=25%, MEDIUM: >=15%, LOW: >=threshold)
    - Volume minimums (minimum_count)
    - Category exclusions (Personal, Work-related, Financial-Notification)

    Args:
        email_address: Gmail email address to analyze
        days: Number of days to look back (1-30, default: 7)

    Returns:
        BlockingRecommendationResult with recommendations and metadata

    Raises:
        400: Invalid parameters (days out of range)
        401: Invalid or missing API key
        404: Account not found
        500: Internal server error
    """
    verify_api_key(x_api_key)

    try:
        # Verify account exists
        account = service.get_account_by_email(email_address)
        if not account:
            logger.warning(f"Account not found for recommendations: {email_address}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {email_address}"
            )

        # Get recommendations from service
        logger.info(f"Getting recommendations for {email_address} (days={days})")
        result = rec_service.get_recommendations(email_address, days=days)

        logger.info(
            f"Generated {len(result.recommendations)} recommendations for {email_address}"
        )
        return result

    except HTTPException:
        raise
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"Validation error in get_blocking_recommendations: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        ) from e
    except Exception as e:
        logger.exception("Error in get_blocking_recommendations")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations"
        ) from e


@app.get(
    "/api/accounts/{email_address}/recommendations/{category}/details",
    response_model=RecommendationReason,
    tags=["recommendations"]
)
async def get_recommendation_details(
    email_address: str = Path(..., description="Gmail email address"),
    category: str = Path(..., description="Email category name"),
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze (1-30, default: 7)"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryClientInterface = Depends(get_account_service),
    rec_service: BlockingRecommendationService = Depends(get_recommendation_service)
):
    """
    Get detailed reasons why a category is recommended for blocking

    Provides comprehensive breakdown including:
    - Daily tallies
    - Trend analysis (increasing/decreasing/stable)
    - Comparable categories
    - Recommendation factors

    Args:
        email_address: Gmail email address
        category: Category to analyze
        days: Number of days to look back (1-30, default: 7)

    Returns:
        RecommendationReason with detailed breakdown

    Raises:
        400: Invalid parameters
        401: Invalid or missing API key
        404: Account not found or category has no data
        500: Internal server error
    """
    verify_api_key(x_api_key)

    try:
        # Verify account exists
        account = service.get_account_by_email(email_address)
        if not account:
            logger.warning(f"Account not found for recommendation details: {email_address}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {email_address}"
            )

        # Get detailed reasons from service
        logger.info(f"Getting recommendation details for {email_address}/{category} (days={days})")
        reason = rec_service.get_recommendation_reasons(email_address, category, days=days)

        # Check if category has any data
        if reason.total_count == 0:
            logger.warning(f"No data found for category {category} in account {email_address}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category}' not found or has no data"
            )

        logger.info(
            f"Generated recommendation details for {email_address}/{category}: "
            f"{reason.total_count} emails ({reason.percentage}%)"
        )
        return reason

    except HTTPException:
        raise
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"Validation error in get_recommendation_details: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        ) from e
    except Exception as e:
        logger.exception("Error in get_recommendation_details")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendation details"
        ) from e


@app.get(
    "/api/accounts/{email_address}/category-stats",
    response_model=AggregatedCategoryTally,
    tags=["recommendations"]
)
async def get_category_statistics(
    email_address: str = Path(..., description="Gmail email address"),
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze (1-365, default: 7)"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryClientInterface = Depends(get_account_service),
    tally_repo: CategoryTallyRepository = Depends(get_category_tally_repository)
):
    """
    Get raw category statistics for an email account

    Returns aggregated category statistics across a date range without
    applying recommendation logic. Provides pure statistical data including:
    - Total emails and days with data
    - Per-category counts, percentages, and daily averages
    - Trend information (increasing/decreasing/stable)

    Args:
        email_address: Gmail email address
        days: Number of days to look back (1-365, default: 7)

    Returns:
        AggregatedCategoryTally with category statistics

    Raises:
        400: Invalid parameters
        401: Invalid or missing API key
        404: Account not found
        503: Category aggregation service not available
        500: Internal server error
    """
    verify_api_key(x_api_key)

    try:
        # Verify account exists
        account = service.get_account_by_email(email_address)
        if not account:
            logger.warning(f"Account not found for category stats: {email_address}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {email_address}"
            )

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Get aggregated stats from global CategoryTallyRepository instance
        logger.info(f"Getting category stats for {email_address} (days={days})")
        stats = tally_repo.get_aggregated_tallies(
            email_address,
            start_date,
            end_date
        )

        logger.info(
            f"Retrieved category stats for {email_address}: "
            f"{stats.total_emails} emails across {stats.days_with_data} days"
        )
        return stats

    except HTTPException:
        raise
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"Validation error in get_category_statistics: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        ) from e
    except Exception as e:
        logger.exception("Error in get_category_statistics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category statistics"
        ) from e


@app.on_event("startup")
async def startup_event():
    """Initialize WebSocket manager and start background tasks on server startup"""
    global websocket_manager, background_startup_task

    logger.info("=== API Service Startup ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")

    # Log critical environment variables (without sensitive values)
    env_vars = {
        "API_KEY": "***" if API_KEY else None,
        "CONTROL_TOKEN": "***" if CONTROL_TOKEN else None,
        "LLM_MODEL": LLM_MODEL,
        "BACKGROUND_PROCESSING_ENABLED": BACKGROUND_PROCESSING_ENABLED,
        "BACKGROUND_SCAN_INTERVAL": BACKGROUND_SCAN_INTERVAL,
        "DATABASE_PATH": os.getenv("DATABASE_PATH", DEFAULT_DB_PATH),
        "REQUESTYAI_API_KEY": "***" if os.getenv("REQUESTYAI_API_KEY") else None,
        "OPENAI_API_KEY": "***" if os.getenv("OPENAI_API_KEY") else None,
    }
    logger.info(f"Environment configuration: {env_vars}")

    try:
        # Test database initialization
        logger.info("Testing database connection...")
        from clients.account_category_client import AccountCategoryClient
        test_client = AccountCategoryClient(repository=settings_service.repository)
        logger.info("Database connection successful")

        # Initialize WebSocket manager
        logger.info("Initializing WebSocket manager...")
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

        logger.info("=== API Service Startup Complete ===")

    except Exception as e:
        logger.error(f"FATAL: Failed to initialize during startup: {e}")
        logger.exception("Full traceback:")
        # Terminate the service - cannot function without proper initialization
        logger.error("Service cannot start. Exiting...")
        sys.exit(1)

    # Start background processor AFTER server is ready to accept requests
    # This prevents healthcheck failures during initialization
    # Schedule background processor to start after a short delay to ensure server is fully ready
    async def delayed_background_start() -> None:
        """Start background processor after a delay to ensure server is ready"""
        await asyncio.sleep(BACKGROUND_START_DELAY)  # Wait for server to be fully ready
        try:
            logger.info("Starting background processor (delayed start after server ready)...")
            start_background_processor()
            logger.info("Background processor started successfully")
        except Exception:
            logger.exception("Failed to start background processor")
            # Don't exit - allow the API to run even if background processor fails
            logger.warning("API service will continue without background processing")

    # Schedule the delayed start as a background task
    background_startup_task = asyncio.create_task(delayed_background_start())


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown WebSocket manager, background tasks, and logging service"""
    global websocket_manager, background_startup_task

    try:
        # Cancel background startup task if still running
        if background_startup_task and not background_startup_task.done():
            logger.info("Cancelling background startup task...")
            background_startup_task.cancel()
            try:
                await background_startup_task
            except asyncio.CancelledError:
                logger.info("Background startup task cancelled successfully")

        if websocket_manager:
            logger.info("Shutting down WebSocket manager...")
            await websocket_manager.shutdown()
            websocket_manager = None
            logger.info("WebSocket manager shutdown completed")

        # Stop background processor if running
        stop_background_processor()

        # Flush category aggregator if enabled
        if category_aggregator:
            try:
                logger.info("Flushing category aggregator...")
                category_aggregator.flush()
                logger.info("Category aggregator flushed successfully")
            except Exception as e:
                logger.exception("Error flushing category aggregator")

        # Disconnect settings service repository to dispose of MySQL connection pool
        try:
            logger.info("Disconnecting settings service repository...")
            settings_service.repository.disconnect()
            logger.info("Settings service repository disconnected successfully")
        except Exception as e:
            logger.exception("Error disconnecting settings service repository")

        # Gracefully shutdown central logging service
        logger.info("Shutting down central logging service...")
        shutdown_logging(timeout=5.0)

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
                "status": "GET /api/status (unified processing and background status)",
                "morning_summary": "POST /api/summaries/morning",
                "evening_summary": "POST /api/summaries/evening",
                "weekly_summary": "POST /api/summaries/weekly",
                "monthly_summary": "POST /api/summaries/monthly",
                "top_categories": "GET /api/accounts/{email_address}/categories/top",
                "list_accounts": "GET /api/accounts",
                "create_account": "POST /api/accounts",
                "verify_password": "GET /api/accounts/{email_address}/verify-password",
                "deactivate_account": "PUT /api/accounts/{email_address}/deactivate",
                "delete_account": "DELETE /api/accounts/{email_address}",
                "force_process_account": "POST /api/accounts/{email_address}/process",
                "processing_history": "GET /api/processing/history",
                "processing_statistics": "GET /api/processing/statistics",
                "websocket_status": "WS /ws/status"
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation error handler with verbose logging for debugging."""
    # Log detailed information about the validation error
    logger.error(f"Request validation error on {request.method} {request.url.path}")
    logger.error(f"Validation errors: {exc.errors()}")

    # Log request details for OAuth callback specifically (sanitized - no sensitive data)
    if "/api/auth/gmail/callback" in str(request.url.path):
        logger.error(f"OAuth callback validation failed - path: {request.url.path}")
        # Log presence of query params without exposing values
        logger.error(f"OAuth callback query params present: {list(request.query_params.keys())}")
        # Do not log request body for OAuth callback as it contains sensitive tokens
        logger.error("OAuth callback request body not logged (contains sensitive tokens)")

    # Return the standard validation error response
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
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

    # Note: Background processor is now started in startup_event() instead of here to prevent blocking
    # server startup. This ensures Railway deployment healthchecks can pass before the processor
    # initializes, allowing the service to be marked as healthy and receive traffic sooner.

    try:
        # Run the API
        uvicorn.run(app, host=host, port=port)
    finally:
        # Ensure background processor is stopped on exit
        logger.info("Shutting down API server...")
        stop_background_processor()
