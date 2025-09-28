#!/usr/bin/env python3
"""
Simple script to run the Cat-Emails Web Dashboard
Handles environment setup and provides better error messages
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path (parent of frontend directory)
frontend_dir = Path(__file__).parent
project_root = frontend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(frontend_dir))

def check_dependencies():
    """Check if required dependencies are installed"""
    missing_deps = []
    
    try:
        import flask
    except ImportError:
        missing_deps.append('flask')
    
    try:
        from services.database_service import DatabaseService
    except ImportError:
        missing_deps.append('Database service (check if services/ directory exists)')
    
    if missing_deps:
        print("❌ Missing dependencies:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n💡 Install with: pip install flask")
        print("💡 Or install web requirements: pip install -r requirements-web.txt")
        return False
    
    return True

def setup_environment():
    """Set up default environment variables"""
    defaults = {
        'FLASK_HOST': '0.0.0.0',
        'FLASK_PORT': '5000',
        'FLASK_DEBUG': 'False',
        'DB_PATH': '../email_summaries/summaries.db',
        'SECRET_KEY': 'dev-secret-key-change-in-production'
    }
    
    for key, default_value in defaults.items():
        if key not in os.environ:
            os.environ[key] = default_value
    
    # Check if database exists
    db_path = os.environ['DB_PATH']
    if not os.path.exists(db_path):
        print(f"⚠️  Database not found at: {db_path}")
        print("💡 The dashboard will create an empty database, but you may need to run")
        print("   the email processing service first to populate it with data.")
        print()

def main():
    """Main entry point"""
    print("🐱 Starting Cat-Emails Web Dashboard...")
    print()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    # Import and run the Flask app
    try:
        from web_dashboard import app
        
        host = os.environ['FLASK_HOST']
        port = int(os.environ['FLASK_PORT'])
        debug = os.environ['FLASK_DEBUG'].lower() == 'true'
        
        print(f"🚀 Dashboard starting on http://{host}:{port}")
        print(f"📊 Database: {os.environ['DB_PATH']}")
        print(f"🐛 Debug mode: {debug}")
        print()
        print("Press Ctrl+C to stop the server")
        print()
        
        app.run(host=host, port=port, debug=debug)
        
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        logging.exception("Dashboard startup error")
        sys.exit(1)

if __name__ == '__main__':
    main()