#!/usr/bin/env python3
"""
Gmail Fetcher Service - Continuous email processing service
Runs gmail_fetcher.main() function at regular intervals
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime, time as datetime_time
import pytz
from gmail_fetcher import main as gmail_fetcher_main
from send_emails import main as send_summary_main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    running = False

def should_send_summary(last_morning_sent: datetime, last_evening_sent: datetime, last_weekly_sent: datetime) -> str:
    """
    Check if it's time to send a summary report.
    
    Args:
        last_morning_sent: When morning report was last sent
        last_evening_sent: When evening report was last sent
        last_weekly_sent: When weekly report was last sent
        
    Returns:
        "morning", "evening", "weekly", or "" if no report needed
    """
    # Get current time in Eastern Time
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    current_time = now_et.time()
    current_day = now_et.strftime('%A')
    
    # Convert last sent times to ET for comparison
    if last_morning_sent.tzinfo is None:
        last_morning_sent = pytz.utc.localize(last_morning_sent).astimezone(et_tz)
    else:
        last_morning_sent = last_morning_sent.astimezone(et_tz)
        
    if last_evening_sent.tzinfo is None:
        last_evening_sent = pytz.utc.localize(last_evening_sent).astimezone(et_tz)
    else:
        last_evening_sent = last_evening_sent.astimezone(et_tz)
        
    if last_weekly_sent.tzinfo is None:
        last_weekly_sent = pytz.utc.localize(last_weekly_sent).astimezone(et_tz)
    else:
        last_weekly_sent = last_weekly_sent.astimezone(et_tz)
    
    # Morning report at 8 AM ET
    morning_start = datetime_time(8, 0)
    morning_end = datetime_time(8, 30)
    
    # Evening report at 8 PM ET
    evening_start = datetime_time(20, 0)
    evening_end = datetime_time(20, 30)
    
    # Check weekly report window (Friday 8 PM ET)
    if current_day == 'Friday' and evening_start <= current_time <= evening_end:
        # Check if we haven't sent weekly report this week
        days_since_weekly = (now_et.date() - last_weekly_sent.date()).days
        if days_since_weekly >= 7:
            return "weekly"
    
    # Check morning window
    if morning_start <= current_time <= morning_end:
        # Check if we haven't sent morning report today
        if last_morning_sent.date() < now_et.date():
            return "morning"
    
    # Check evening window (non-Friday or after weekly check)
    if evening_start <= current_time <= evening_end:
        # Check if we haven't sent evening report today
        if last_evening_sent.date() < now_et.date():
            return "evening"
    
    return ""

def run_service():
    """Main service loop"""
    # Get configuration from environment
    email_address = os.getenv("GMAIL_EMAIL")
    app_password = os.getenv("GMAIL_PASSWORD")
    api_token = os.getenv("CONTROL_API_TOKEN")
    hours = int(os.getenv("HOURS", "2"))
    scan_interval = int(os.getenv("SCAN_INTERVAL", "2"))  # minutes
    enable_summaries = os.getenv("ENABLE_SUMMARIES", "true").lower() == "true"
    summary_recipient = os.getenv("SUMMARY_RECIPIENT_EMAIL", email_address)
    
    # Validate required environment variables
    if not email_address or not app_password:
        logger.error("GMAIL_EMAIL and GMAIL_PASSWORD environment variables are required")
        sys.exit(1)
    
    if not api_token:
        logger.error("CONTROL_API_TOKEN environment variable is required")
        sys.exit(1)
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("Gmail Fetcher Service starting...")
    logger.info(f"Configuration:")
    logger.info(f"  - Email: {email_address}")
    logger.info(f"  - Hours to scan: {hours}")
    logger.info(f"  - Scan interval: {scan_interval} minutes")
    logger.info(f"  - Summaries enabled: {enable_summaries}")
    if enable_summaries:
        logger.info(f"  - Summary recipient: {summary_recipient}")
    
    # Track when summaries were last sent
    # Use a date far in the past but not datetime.min to avoid timezone conversion issues
    last_morning_sent = datetime(2000, 1, 1, tzinfo=pytz.utc)
    last_evening_sent = datetime(2000, 1, 1, tzinfo=pytz.utc)
    last_weekly_sent = datetime(2000, 1, 1, tzinfo=pytz.utc)
    
    # Main service loop
    cycle_count = 0
    while running:
        cycle_count += 1
        logger.info(f"Starting scan cycle #{cycle_count}")
        
        try:
            # Run the email fetcher
            start_time = time.time()
            gmail_fetcher_main(email_address, app_password, api_token, hours)
            duration = time.time() - start_time
            
            # Convert duration to human-readable format
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            
            if minutes > 0:
                logger.info(f"Scan cycle #{cycle_count} completed successfully in {minutes} minutes and {seconds} seconds")
            else:
                logger.info(f"Scan cycle #{cycle_count} completed successfully in {seconds} seconds")
            
        except Exception as e:
            logger.error(f"Error in scan cycle #{cycle_count}: {str(e)}", exc_info=True)
            logger.info("Service will continue running despite the error")
        
        # Check if we should send a summary
        if running and enable_summaries:
            report_type = should_send_summary(last_morning_sent, last_evening_sent, last_weekly_sent)
            if report_type:
                logger.info(f"Time to send {report_type} summary report")
                try:
                    # Set environment variables for the summary script
                    os.environ['GMAIL_EMAIL'] = summary_recipient
                    os.environ['SUMMARY_RECIPIENT_EMAIL'] = summary_recipient
                    
                    # Send summary using the new send_emails.py
                    send_summary_main()
                    
                    # Update last sent time
                    if report_type == "morning":
                        last_morning_sent = datetime.now()
                    elif report_type == "evening":
                        last_evening_sent = datetime.now()
                    elif report_type == "weekly":
                        last_weekly_sent = datetime.now()
                    
                    logger.info(f"{report_type.capitalize()} summary sent successfully")
                except Exception as e:
                    logger.error(f"Failed to send {report_type} summary: {str(e)}", exc_info=True)
                    logger.info("Service will continue running despite the error")
        
        if running:
            # Calculate next run time
            next_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Next scan will run in {scan_interval} minutes at approximately {next_run}")
            
            # Sleep in small intervals to allow for quick shutdown
            sleep_seconds = scan_interval * 60
            sleep_interval = 5  # Check for shutdown every 5 seconds
            
            for _ in range(0, sleep_seconds, sleep_interval):
                if not running:
                    break
                time.sleep(min(sleep_interval, sleep_seconds))
    
    logger.info("Gmail Fetcher Service shutting down gracefully")

if __name__ == "__main__":
    run_service()