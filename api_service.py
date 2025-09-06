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
from fastapi import FastAPI, HTTPException, Header, status, Query, Path, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from send_emails import send_summary_by_type
from services.account_category_service import AccountCategoryService
from models.account_models import (
    TopCategoriesResponse, AccountListResponse, EmailAccountInfo,
    AccountCategoryStatsRequest
)
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Cat Emails API",
    description="API for email summary reports and account category management",
    version="1.1.0"
)

# Optional API key authentication
API_KEY = os.getenv("API_KEY")

# Background processing configuration
BACKGROUND_PROCESSING_ENABLED = os.getenv("BACKGROUND_PROCESSING", "true").lower() == "true"
BACKGROUND_SCAN_INTERVAL = int(os.getenv("BACKGROUND_SCAN_INTERVAL", "300"))  # 5 minutes default
BACKGROUND_PROCESS_HOURS = int(os.getenv("BACKGROUND_PROCESS_HOURS", "2"))  # Look back 2 hours default

# Global flag for background thread control
background_thread_running = True
background_thread = None


class SummaryResponse(BaseModel):
    """Response model for summary endpoints"""
    status: str
    message: str
    timestamp: str
    report_type: str


class CreateAccountRequest(BaseModel):
    """Request model for creating new accounts"""
    email_address: str
    display_name: Optional[str] = None


class StandardResponse(BaseModel):
    """Standard response model for simple operations"""
    status: str
    message: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: str
    timestamp: str


def get_account_service() -> AccountCategoryService:
    """Dependency to provide AccountCategoryService instance."""
    try:
        return AccountCategoryService()
    except Exception as e:
        logger.error(f"Failed to create AccountCategoryService: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database service unavailable"
        )


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


def process_account_emails(email_address: str) -> Dict:
    """
    Process emails for a single Gmail account.
    This is a placeholder - in a real implementation, this would:
    1. Connect to Gmail via IMAP
    2. Fetch recent emails
    3. Categorize them using AI
    4. Apply labels and actions
    
    Args:
        email_address: The Gmail account to process
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"🔍 Processing emails for account: {email_address}")
    
    try:
        # Simulate email processing work
        start_time = time.time()
        
        # Get account service to check if account exists in database
        service = AccountCategoryService()
        
        # This would be the actual Gmail processing logic
        # For now, we'll simulate with some realistic processing steps
        logger.info(f"  📬 Connecting to Gmail IMAP for {email_address}...")
        time.sleep(1)  # Simulate connection time
        
        logger.info(f"  🔎 Fetching emails from last {BACKGROUND_PROCESS_HOURS} hours...")
        time.sleep(2)  # Simulate email fetching
        
        # Simulate finding some emails
        simulated_email_count = 15  # In real implementation, this would be actual count
        logger.info(f"  📧 Found {simulated_email_count} emails to process")
        
        processed_count = 0
        categorized_count = 0
        labeled_count = 0
        
        # Simulate processing each email
        for i in range(simulated_email_count):
            logger.info(f"    ⚡ Processing email {i+1}/{simulated_email_count}")
            
            # Simulate AI categorization
            time.sleep(0.5)  # Simulate AI processing time
            categorized_count += 1
            
            # Simulate applying Gmail labels
            time.sleep(0.2)  # Simulate Gmail API call
            labeled_count += 1
            
            processed_count += 1
            
            if i % 5 == 4:  # Log progress every 5 emails
                logger.info(f"    📊 Progress: {processed_count}/{simulated_email_count} emails processed")
        
        processing_time = time.time() - start_time
        
        result = {
            "account": email_address,
            "emails_found": simulated_email_count,
            "emails_processed": processed_count,
            "emails_categorized": categorized_count,
            "emails_labeled": labeled_count,
            "processing_time_seconds": round(processing_time, 2),
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
        
        logger.info(f"✅ Successfully processed {email_address}: {processed_count} emails in {processing_time:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error processing emails for {email_address}: {str(e)}")
        return {
            "account": email_address,
            "error": str(e),
            "success": False,
            "timestamp": datetime.now().isoformat()
        }


def background_gmail_processor():
    """
    Background thread function that continuously processes Gmail accounts.
    """
    global background_thread_running
    
    logger.info("🚀 Background Gmail processor thread started")
    logger.info(f"⚙️  Configuration:")
    logger.info(f"   - Scan interval: {BACKGROUND_SCAN_INTERVAL} seconds")
    logger.info(f"   - Process emails from last: {BACKGROUND_PROCESS_HOURS} hours")
    logger.info(f"   - Background processing enabled: {BACKGROUND_PROCESSING_ENABLED}")
    
    cycle_count = 0
    
    while background_thread_running:
        try:
            cycle_count += 1
            logger.info(f"🔄 Starting background processing cycle #{cycle_count}")
            
            # Get list of active Gmail accounts from database
            try:
                service = AccountCategoryService()
                accounts = service.list_accounts()
                
                if not accounts or len(accounts.accounts) == 0:
                    logger.info("📭 No Gmail accounts found in database to process")
                    logger.info("💡 Tip: Add accounts via POST /api/accounts endpoint")
                else:
                    logger.info(f"👥 Found {len(accounts.accounts)} Gmail accounts to process")
                    
                    # Process each account
                    total_processed = 0
                    total_errors = 0
                    
                    for account in accounts.accounts:
                        if not background_thread_running:
                            logger.info("🛑 Background processing stopped during account processing")
                            break
                            
                        logger.info(f"🏃 Processing account: {account.email_address}")
                        result = process_account_emails(account.email_address)
                        
                        if result["success"]:
                            total_processed += result.get("emails_processed", 0)
                        else:
                            total_errors += 1
                            
                        # Small delay between accounts to prevent overwhelming Gmail API
                        time.sleep(5)
                    
                    logger.info(f"📈 Cycle #{cycle_count} completed:")
                    logger.info(f"   - Accounts processed: {len(accounts.accounts)}")
                    logger.info(f"   - Total emails processed: {total_processed}")
                    logger.info(f"   - Errors: {total_errors}")
                        
            except Exception as e:
                logger.error(f"❌ Error in background processing cycle: {str(e)}")
            
            if background_thread_running:
                next_run = datetime.now() + timedelta(seconds=BACKGROUND_SCAN_INTERVAL)
                logger.info(f"💤 Sleeping {BACKGROUND_SCAN_INTERVAL} seconds. Next cycle at {next_run.strftime('%H:%M:%S')}")
                
                # Sleep in smaller intervals to allow for graceful shutdown
                sleep_interval = 10  # Check for shutdown every 10 seconds
                remaining_sleep = BACKGROUND_SCAN_INTERVAL
                
                while remaining_sleep > 0 and background_thread_running:
                    sleep_time = min(sleep_interval, remaining_sleep)
                    time.sleep(sleep_time)
                    remaining_sleep -= sleep_time
                    
        except Exception as e:
            logger.error(f"💥 Fatal error in background processor: {str(e)}")
            logger.info("⏸️  Background processor will retry in 30 seconds...")
            time.sleep(30)
    
    logger.info("🏁 Background Gmail processor thread stopped")


def start_background_processor():
    """Start the background processing thread."""
    global background_thread
    
    if BACKGROUND_PROCESSING_ENABLED and not background_thread:
        logger.info("🎬 Starting background Gmail processor...")
        background_thread = threading.Thread(
            target=background_gmail_processor,
            name="GmailProcessor",
            daemon=True
        )
        background_thread.start()
        logger.info("✅ Background Gmail processor thread launched")
    elif not BACKGROUND_PROCESSING_ENABLED:
        logger.info("⏸️  Background processing is disabled (BACKGROUND_PROCESSING=false)")
    else:
        logger.warning("⚠️  Background processor thread already running")


def stop_background_processor():
    """Stop the background processing thread."""
    global background_thread_running, background_thread
    
    if background_thread and background_thread.is_alive():
        logger.info("🛑 Stopping background Gmail processor...")
        background_thread_running = False
        background_thread.join(timeout=30)  # Wait up to 30 seconds for clean shutdown
        
        if background_thread.is_alive():
            logger.warning("⚠️  Background thread did not stop gracefully")
        else:
            logger.info("✅ Background Gmail processor stopped cleanly")
        
        background_thread = None


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Cat Emails Summary API with Background Gmail Processing",
        "version": "1.1.0",
        "endpoints": {
            "health": "GET /api/health",
            "background_start": "POST /api/background/start",
            "background_stop": "POST /api/background/stop",
            "background_status": "GET /api/background/status",
            "morning_summary": "POST /api/summaries/morning",
            "evening_summary": "POST /api/summaries/evening",
            "weekly_summary": "POST /api/summaries/weekly",
            "monthly_summary": "POST /api/summaries/monthly",
            "top_categories": "GET /api/accounts/{email_address}/categories/top",
            "list_accounts": "GET /api/accounts",
            "create_account": "POST /api/accounts",
            "deactivate_account": "PUT /api/accounts/{email_address}/deactivate"
        },
        "authentication": "Optional via X-API-Key header" if API_KEY else "None"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint with background processor status"""
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
            "process_hours": BACKGROUND_PROCESS_HOURS
        }
    }


@app.post("/api/background/start")
async def start_background_processing(x_api_key: Optional[str] = Header(None)):
    """Start the background Gmail processor"""
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


@app.post("/api/background/stop")
async def stop_background_processing(x_api_key: Optional[str] = Header(None)):
    """Stop the background Gmail processor"""
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


@app.get("/api/background/status")
async def get_background_status(x_api_key: Optional[str] = Header(None)):
    """Get detailed background processor status"""
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
            "process_hours": BACKGROUND_PROCESS_HOURS
        },
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/test/create-sample-data")
async def create_sample_data(x_api_key: Optional[str] = Header(None), report_type: Optional[str] = "Daily"):
    """
    Create sample tracking data for testing purposes.
    This endpoint creates dummy email data to test the summary functionality.
    
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


@app.post("/api/summaries/morning", response_model=SummaryResponse)
async def trigger_morning_summary(x_api_key: Optional[str] = Header(None)):
    """
    Trigger a morning (8am) summary report.
    
    This endpoint forces the generation and sending of a morning summary report
    regardless of the current time.
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


@app.post("/api/summaries/evening", response_model=SummaryResponse)
async def trigger_evening_summary(x_api_key: Optional[str] = Header(None)):
    """
    Trigger an evening (8pm) summary report.
    
    This endpoint forces the generation and sending of an evening summary report
    regardless of the current time.
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


@app.post("/api/summaries/weekly", response_model=SummaryResponse)
async def trigger_weekly_summary(x_api_key: Optional[str] = Header(None)):
    """
    Trigger a weekly summary report.
    
    This endpoint forces the generation and sending of a weekly summary report
    regardless of the current day or time.
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


@app.post("/api/summaries/monthly", response_model=SummaryResponse)
async def trigger_monthly_summary(x_api_key: Optional[str] = Header(None)):
    """
    Trigger a monthly summary report.
    
    This endpoint forces the generation and sending of a monthly summary report
    with data from the last 30 days.
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


@app.get("/api/accounts/{email_address}/categories/top", response_model=TopCategoriesResponse)
async def get_top_categories(
    email_address: str = Path(..., description="Gmail email address"),
    days: int = Query(..., ge=1, le=365, description="Number of days to look back (1-365)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of categories to return (1-50)"),
    include_counts: bool = Query(False, description="Include detailed counts breakdown"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryService = Depends(get_account_service)
):
    """
    Get top email categories for a specific account over a specified time period.
    
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


@app.get("/api/accounts", response_model=AccountListResponse)
async def get_all_accounts(
    active_only: bool = Query(True, description="Filter to only active accounts"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryService = Depends(get_account_service)
):
    """
    List all tracked email accounts.
    
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


@app.post("/api/accounts", response_model=StandardResponse)
async def create_account(
    request: CreateAccountRequest,
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryService = Depends(get_account_service)
):
    """
    Register a new email account for tracking.
    
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
        logger.error(f"Database error in create_account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Unexpected error in create_account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@app.put("/api/accounts/{email_address}/deactivate", response_model=StandardResponse)
async def deactivate_account(
    email_address: str = Path(..., description="Gmail email address to deactivate"),
    x_api_key: Optional[str] = Header(None),
    service: AccountCategoryService = Depends(get_account_service)
):
    """
    Deactivate an email account.
    
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
                "deactivate_account": "PUT /api/accounts/{email_address}/deactivate"
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
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
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