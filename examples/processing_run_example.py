#!/usr/bin/env python3
"""
Example usage of the ProcessingRun model for tracking email processing sessions.

This demonstrates how to use the ProcessingRun model to track the state
and progress of email processing operations.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from models.database import ProcessingRun, init_database, get_session

def create_processing_run_example():
    """Example of creating and managing a processing run"""
    
    # Initialize database connection
    engine = init_database()
    session = get_session(engine)
    
    try:
        # 1. Start a new processing run
        processing_run = ProcessingRun(
            email_address="user@example.com",
            start_time=datetime.utcnow(),
            state="starting",
            current_step="Initializing connection to Gmail"
        )
        
        session.add(processing_run)
        session.commit()
        print(f"Started processing run {processing_run.id} for {processing_run.email_address}")
        
        # 2. Update progress during processing
        processing_run.state = "connecting"
        processing_run.current_step = "Authenticating with Gmail IMAP"
        session.commit()
        
        # 3. Begin email processing
        processing_run.state = "processing"
        processing_run.current_step = "Fetching emails from INBOX"
        processing_run.emails_found = 150
        session.commit()
        
        # 4. Continue processing updates
        processing_run.current_step = "Categorizing emails with AI"
        processing_run.emails_processed = 75
        session.commit()
        
        # 5. Complete the processing
        processing_run.state = "completed"
        processing_run.current_step = "Finished processing all emails"
        processing_run.end_time = datetime.utcnow()
        processing_run.emails_processed = processing_run.emails_found
        session.commit()
        
        print(f"Completed processing run {processing_run.id}")
        print(f"  - Processed {processing_run.emails_processed}/{processing_run.emails_found} emails")
        print(f"  - Duration: {processing_run.end_time - processing_run.start_time}")
        
        return processing_run.id
        
    except Exception as e:
        print(f"Error during processing: {e}")
        # Handle error case
        if 'processing_run' in locals():
            processing_run.state = "error"
            processing_run.error_message = str(e)
            processing_run.end_time = datetime.utcnow()
            session.commit()
        session.rollback()
        raise
    finally:
        session.close()

def query_processing_runs_example():
    """Example of querying processing runs"""
    
    engine = init_database()
    session = get_session(engine)
    
    try:
        # Query recent runs for an account
        recent_runs = session.query(ProcessingRun).filter_by(
            email_address="user@example.com"
        ).order_by(ProcessingRun.start_time.desc()).limit(10).all()
        
        print(f"\nFound {len(recent_runs)} recent runs for user@example.com:")
        for run in recent_runs:
            status = f"{run.state}"
            if run.current_step:
                status += f" - {run.current_step}"
            print(f"  Run {run.id}: {status}")
            print(f"    Started: {run.start_time}")
            if run.end_time:
                print(f"    Ended: {run.end_time}")
            print(f"    Progress: {run.emails_processed}/{run.emails_found} emails")
            if run.error_message:
                print(f"    Error: {run.error_message}")
            print()
        
        # Query currently running processes
        running_runs = session.query(ProcessingRun).filter_by(state="processing").all()
        print(f"Currently running processes: {len(running_runs)}")
        
    finally:
        session.close()

def handle_error_scenario():
    """Example of handling an error during processing"""
    
    engine = init_database()
    session = get_session(engine)
    
    try:
        # Start processing
        processing_run = ProcessingRun(
            email_address="error@example.com",
            start_time=datetime.utcnow(),
            state="processing",
            current_step="Processing emails"
        )
        
        session.add(processing_run)
        session.commit()
        
        # Simulate an error
        raise Exception("Failed to connect to Gmail IMAP server")
        
    except Exception as e:
        # Record the error
        processing_run.state = "error"
        processing_run.error_message = str(e)
        processing_run.end_time = datetime.utcnow()
        session.commit()
        
        print(f"Error recorded for processing run {processing_run.id}: {e}")
        
    finally:
        session.close()

if __name__ == "__main__":
    print("ProcessingRun Model Example")
    print("=" * 50)
    
    # Example 1: Normal processing flow
    print("1. Creating and completing a processing run...")
    create_processing_run_example()
    
    # Example 2: Querying processing runs
    print("\n2. Querying processing runs...")
    query_processing_runs_example()
    
    # Example 3: Error handling
    print("\n3. Error handling example...")
    handle_error_scenario()
    
    print("\nExample completed successfully!")