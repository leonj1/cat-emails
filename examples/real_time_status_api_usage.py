#!/usr/bin/env python3
"""
Example usage of the real-time processing status API endpoints in Cat-Emails

This script demonstrates how to:
1. Check current processing status
2. Monitor processing progress
3. Get processing history
4. Retrieve processing statistics

Prerequisites:
- Cat-Emails API service running (python api_service.py)
- Optional: API key if configured (set API_KEY environment variable)

Usage:
    python examples/real_time_status_api_usage.py
"""
import requests
import time
import json
import os
from datetime import datetime

# API configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY")  # Optional - if your API requires authentication

# Headers for API requests
headers = {}
if API_KEY:
    headers["X-API-Key"] = API_KEY

def make_api_request(endpoint: str) -> dict:
    """Make an API request and return the JSON response"""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {str(e)}")
        return {}

def check_current_status():
    """Check the current processing status"""
    print("🔍 Checking current processing status...")
    
    response = make_api_request("/api/processing/status")
    
    if response:
        is_processing = response.get("is_processing", False)
        current_status = response.get("current_status")
        
        if is_processing and current_status:
            print(f"✅ Processing is ACTIVE for: {current_status['email_address']}")
            print(f"   State: {current_status['state']}")
            print(f"   Step: {current_status['current_step']}")
            
            if current_status.get('progress'):
                progress = current_status['progress']
                if 'current' in progress and 'total' in progress:
                    percentage = (progress['current'] / progress['total']) * 100
                    print(f"   Progress: {progress['current']}/{progress['total']} ({percentage:.1f}%)")
            
            print(f"   Started: {current_status['start_time']}")
            print(f"   Last Update: {current_status['last_updated']}")
        else:
            print("💤 No processing is currently active")
    
    return response

def monitor_processing_progress(check_interval: int = 2, max_checks: int = 30):
    """Monitor processing progress with periodic checks"""
    print(f"📊 Starting processing monitor (checking every {check_interval}s, max {max_checks} checks)...")
    
    for i in range(max_checks):
        print(f"\n--- Check {i+1}/{max_checks} at {datetime.now().strftime('%H:%M:%S')} ---")
        
        status = check_current_status()
        
        if not status or not status.get("is_processing"):
            print("✅ Processing completed or not active")
            break
            
        time.sleep(check_interval)
    else:
        print("⏰ Maximum monitoring time reached")

def get_processing_history(limit: int = 5):
    """Get recent processing history"""
    print(f"\n📝 Getting last {limit} processing runs...")
    
    response = make_api_request(f"/api/processing/history?limit={limit}")
    
    if response and response.get("recent_runs"):
        runs = response["recent_runs"]
        print(f"✅ Retrieved {len(runs)} recent runs:")
        
        for i, run in enumerate(runs, 1):
            print(f"\n   Run #{i}:")
            print(f"     Account: {run['email_address']}")
            print(f"     Status: {run['final_state']}")
            print(f"     Duration: {run.get('duration_seconds', 0):.2f} seconds")
            print(f"     Start: {run['start_time']}")
            print(f"     End: {run['end_time']}")
            
            if run.get('error_message'):
                print(f"     Error: {run['error_message']}")
            
            if run.get('final_progress'):
                progress = run['final_progress']
                if 'total' in progress:
                    print(f"     Progress: {progress.get('current', 0)}/{progress['total']}")
    else:
        print("📭 No processing history found")

def get_processing_statistics():
    """Get processing statistics"""
    print("\n📈 Getting processing statistics...")
    
    response = make_api_request("/api/processing/statistics")
    
    if response and response.get("statistics"):
        stats = response["statistics"]
        print(f"✅ Processing statistics:")
        print(f"   Total runs: {stats['total_runs']}")
        print(f"   Successful runs: {stats['successful_runs']}")
        print(f"   Failed runs: {stats['failed_runs']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
        print(f"   Average duration: {stats['average_duration_seconds']:.2f} seconds")
    else:
        print("📊 No statistics available")

def get_background_processor_status():
    """Check the background processor status"""
    print("\n⚙️  Checking background processor status...")
    
    response = make_api_request("/api/background/status")
    
    if response:
        enabled = response.get("enabled", False)
        running = response.get("running", False)
        
        print(f"   Enabled: {'✅ Yes' if enabled else '❌ No'}")
        print(f"   Running: {'✅ Yes' if running else '❌ No'}")
        
        config = response.get("configuration", {})
        print(f"   Scan interval: {config.get('scan_interval_seconds', 0)} seconds")
        print(f"   Process hours: {config.get('process_hours', 0)} hours")

def main():
    """Main demonstration function"""
    print("Real-Time Processing Status API Demo")
    print("=" * 50)
    
    # Check if API is accessible
    try:
        health_response = requests.get(f"{API_BASE_URL}/api/health")
        if health_response.status_code != 200:
            print(f"❌ API health check failed: {health_response.status_code}")
            return
        print("✅ API is accessible")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API: {str(e)}")
        print("   Make sure the API service is running: python api_service.py")
        return
    
    # Run demonstrations
    get_background_processor_status()
    check_current_status()
    get_processing_history()
    get_processing_statistics()
    
    # Optional: Monitor processing if active
    response = make_api_request("/api/processing/status")
    if response and response.get("is_processing"):
        print(f"\n🔍 Processing is active - starting monitor...")
        monitor_processing_progress()
    
    print(f"\n🎉 Demo completed at {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()