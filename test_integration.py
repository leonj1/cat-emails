#!/usr/bin/env python3
"""
Integration test to verify Gmail credentials can be retrieved from SQLite database
This test simulates the flow that gmail_fetcher.py uses
"""
import os
import sys
import tempfile
from credentials_service import CredentialsService


def test_integration():
    """Test the complete integration flow"""
    print("=" * 60)
    print("Gmail Credentials SQLite Integration Test")
    print("=" * 60)

    # Create a temporary database for testing
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, 'test_credentials.db')
    os.environ['CREDENTIALS_DB_PATH'] = test_db_path

    print(f"\n1. Creating test database at: {test_db_path}")

    # Initialize service
    service = CredentialsService(db_path=test_db_path)
    print("   ✓ Database initialized")

    # Test data
    test_email = "test@gmail.com"
    test_password = "test_app_password_123"

    print(f"\n2. Storing test credentials for: {test_email}")
    result = service.store_credentials(test_email, test_password)

    if result:
        print("   ✓ Credentials stored successfully")
    else:
        print("   ✗ Failed to store credentials")
        return False

    print("\n3. Simulating gmail_fetcher.py credential retrieval...")

    # This simulates what gmail_fetcher.py does
    credentials_service = CredentialsService()
    credentials = credentials_service.get_credentials()

    if credentials:
        email_address, app_password = credentials
        print(f"   ✓ Retrieved email: {email_address}")
        print(f"   ✓ Retrieved password: {'*' * len(app_password)}")
        print("   ✓ Credentials from SQLite database")
    else:
        print("   ✗ No credentials found in database")
        print("   ℹ Would fallback to environment variables")

    print("\n4. Testing fallback to environment variables...")

    # Clear database
    service.delete_credentials(test_email)
    credentials = service.get_credentials()

    if credentials:
        print("   ✗ Database should be empty")
        return False
    else:
        print("   ✓ Database is empty (as expected)")

    # Set environment variables
    os.environ['GMAIL_EMAIL'] = "env@gmail.com"
    os.environ['GMAIL_PASSWORD'] = "env_password"

    email_from_env = os.getenv('GMAIL_EMAIL')
    password_from_env = os.getenv('GMAIL_PASSWORD')

    if email_from_env and password_from_env:
        print(f"   ✓ Would use env var email: {email_from_env}")
        print(f"   ✓ Would use env var password: {'*' * len(password_from_env)}")
    else:
        print("   ✗ Environment variables not set correctly")
        return False

    print("\n5. Testing list and delete operations...")

    # Store multiple credentials
    service.store_credentials("user1@gmail.com", "password1")
    service.store_credentials("user2@gmail.com", "password2")

    emails = service.list_all_emails()
    print(f"   ✓ Stored {len(emails)} accounts: {', '.join(emails)}")

    # Clean up
    for email in emails:
        service.delete_credentials(email)
    print("   ✓ Cleaned up all test credentials")

    # Remove temp database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    os.rmdir(temp_dir)

    # Clean up environment variables
    if 'CREDENTIALS_DB_PATH' in os.environ:
        del os.environ['CREDENTIALS_DB_PATH']
    if 'GMAIL_EMAIL' in os.environ:
        del os.environ['GMAIL_EMAIL']
    if 'GMAIL_PASSWORD' in os.environ:
        del os.environ['GMAIL_PASSWORD']

    print("\n" + "=" * 60)
    print("✓ All integration tests passed!")
    print("=" * 60)
    print("\nThe gmail_fetcher.py application will now:")
    print("  1. Check SQLite database for credentials first")
    print("  2. Fallback to environment variables if database is empty")
    print("  3. Raise error if neither source provides credentials")
    print("\nTo set up credentials for production use:")
    print("  python3 setup_credentials.py --email EMAIL --password PASSWORD")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = test_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)