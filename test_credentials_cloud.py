#!/usr/bin/env python3
"""
Quick test script to verify CredentialsService works with SQLITE_URL
"""
import os
import logging
from credentials_service import CredentialsService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_credentials_service():
    """Test CredentialsService initialization and connection"""

    sqlite_url = os.getenv('SQLITE_URL')

    if not sqlite_url:
        logger.info("SQLITE_URL not set, testing with local database")
    else:
        logger.info(f"SQLITE_URL is set: {sqlite_url[:50]}...")

    try:
        # Initialize service (will use SQLITE_URL if available)
        service = CredentialsService()
        logger.info(f"✓ CredentialsService initialized successfully")
        logger.info(f"  Database path: {service.db_path[:50]}...")
        logger.info(f"  Is cloud: {service.is_cloud}")

        # Try to get credentials
        credentials = service.get_credentials()

        if credentials:
            email, password = credentials
            logger.info(f"✓ Found credentials for: {email}")
            logger.info(f"  Password length: {len(password)} characters")
        else:
            logger.warning("⚠ No credentials found in database")
            logger.info("  This is expected if the database is empty")

        logger.info("\n✅ All tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_credentials_service()
    exit(0 if success else 1)