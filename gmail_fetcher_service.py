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
from datetime import datetime
from gmail_fetcher import main as gmail_fetcher_main
from credentials_service import CredentialsService

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

def run_service():
    """Main service loop"""
    # Get credentials from SQLite database first, fallback to environment variables
    credentials_service = CredentialsService()
    credentials = credentials_service.get_credentials()

    if credentials:
        email_address, app_password = credentials
        logger.info("Using Gmail credentials from SQLite database")
    else:
        # Fallback to environment variables if not in database
        email_address = os.getenv("GMAIL_EMAIL")
        app_password = os.getenv("GMAIL_PASSWORD")

        if email_address and app_password:
            logger.info("Using Gmail credentials from environment variables")
        else:
            logger.error("Please provide GMAIL_EMAIL and GMAIL_PASSWORD either in SQLite database or as environment variables")
            sys.exit(1)

    # Get other configuration from environment
    api_token = os.getenv("CONTROL_API_TOKEN")
    hours = int(os.getenv("HOURS", "2"))
    scan_interval = int(os.getenv("SCAN_INTERVAL", "2"))  # minutes

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
            logger.info(f"Scan cycle #{cycle_count} completed successfully in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error in scan cycle #{cycle_count}: {str(e)}", exc_info=True)
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