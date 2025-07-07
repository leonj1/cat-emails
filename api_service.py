#!/usr/bin/env python3
"""
FastAPI service for triggering email summaries on demand.
"""
import os
import sys
import logging
from typing import Optional, Dict
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from send_emails import send_summary_by_type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Cat Emails Summary API",
    description="API for triggering email summary reports on demand",
    version="1.0.0"
)

# Optional API key authentication
API_KEY = os.getenv("API_KEY")


class SummaryResponse(BaseModel):
    """Response model for summary endpoints"""
    status: str
    message: str
    timestamp: str
    report_type: str


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


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Cat Emails Summary API",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /api/health",
            "morning_summary": "POST /api/summaries/morning",
            "evening_summary": "POST /api/summaries/evening",
            "weekly_summary": "POST /api/summaries/weekly",
            "monthly_summary": "POST /api/summaries/monthly"
        },
        "authentication": "Optional via X-API-Key header" if API_KEY else "None"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Cat Emails Summary API"
    }


@app.post("/api/test/create-sample-data")
async def create_sample_data(x_api_key: Optional[str] = Header(None)):
    """
    Create sample tracking data for testing purposes.
    This endpoint creates dummy email data to test the summary functionality.
    """
    verify_api_key(x_api_key)
    
    try:
        from services.email_summary_service import EmailSummaryService
        from models.email_summary import ProcessedEmail, EmailAction
        import json
        from pathlib import Path
        
        # Initialize summary service
        summary_service = EmailSummaryService()
        
        # Create sample emails
        sample_emails = [
            {
                "message_id": "test1@example.com",
                "sender": "newsletter@company.com",
                "subject": "Weekly Newsletter",
                "category": "Marketing",
                "action": "kept",
                "sender_domain": "company.com",
                "was_pre_categorized": False,
                "processed_at": datetime.now().isoformat()
            },
            {
                "message_id": "test2@example.com",
                "sender": "promo@shop.com",
                "subject": "50% Off Sale!",
                "category": "Advertising",
                "action": "deleted",
                "sender_domain": "shop.com",
                "was_pre_categorized": False,
                "processed_at": datetime.now().isoformat()
            },
            {
                "message_id": "test3@example.com",
                "sender": "friend@gmail.com",
                "subject": "Let's catch up",
                "category": "Personal",
                "action": "kept",
                "sender_domain": "gmail.com",
                "was_pre_categorized": False,
                "processed_at": datetime.now().isoformat()
            },
            {
                "message_id": "test4@example.com",
                "sender": "billing@service.com",
                "subject": "Your invoice is ready",
                "category": "Wants-Money",
                "action": "deleted",
                "sender_domain": "service.com",
                "was_pre_categorized": True,
                "processed_at": datetime.now().isoformat()
            },
            {
                "message_id": "test5@example.com",
                "sender": "noreply@bank.com",
                "subject": "Account statement",
                "category": "Financial-Notification",
                "action": "kept",
                "sender_domain": "bank.com",
                "was_pre_categorized": False,
                "processed_at": datetime.now().isoformat()
            }
        ]
        
        # Save to current tracking file
        tracking_file = Path(summary_service.current_file)
        tracking_file.parent.mkdir(exist_ok=True)
        
        with open(tracking_file, 'w') as f:
            json.dump(sample_emails, f, indent=2)
        
        return {
            "status": "success",
            "message": f"Created {len(sample_emails)} sample emails for testing",
            "timestamp": datetime.now().isoformat()
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
                "monthly_summary": "POST /api/summaries/monthly"
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    logger.info(f"Starting Cat Emails Summary API on {host}:{port}")
    if API_KEY:
        logger.info("API key authentication is enabled")
    else:
        logger.warning("API key authentication is disabled - endpoints are publicly accessible")
    
    # Run the API
    uvicorn.run(app, host=host, port=port)