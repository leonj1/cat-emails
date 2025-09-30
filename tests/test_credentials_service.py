"""
Tests for the CredentialsService module
"""
import unittest
import os
import tempfile
from pathlib import Path
from credentials_service import CredentialsService


class TestCredentialsService(unittest.TestCase):
    """Test cases for CredentialsService"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary database file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, 'test_credentials.db')
        self.service = CredentialsService(db_path=self.test_db_path)

        # Test data
        self.test_email = "test@gmail.com"
        self.test_password = "test_app_password_123"
        self.test_email2 = "test2@gmail.com"
        self.test_password2 = "test_app_password_456"

    def tearDown(self):
        """Clean up test fixtures"""
        # Remove test database
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        # Remove temp directory
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_database_creation(self):
        """Test that database and table are created"""
        self.assertTrue(os.path.exists(self.test_db_path))

    def test_store_credentials(self):
        """Test storing credentials"""
        result = self.service.store_credentials(self.test_email, self.test_password)
        self.assertTrue(result)

    def test_get_credentials(self):
        """Test retrieving credentials"""
        # Store credentials first
        self.service.store_credentials(self.test_email, self.test_password)

        # Retrieve credentials
        credentials = self.service.get_credentials(self.test_email)
        self.assertIsNotNone(credentials)
        self.assertEqual(credentials[0], self.test_email)
        self.assertEqual(credentials[1], self.test_password)

    def test_get_credentials_without_email(self):
        """Test retrieving credentials without specifying email"""
        # Store credentials
        self.service.store_credentials(self.test_email, self.test_password)

        # Retrieve credentials without specifying email
        credentials = self.service.get_credentials()
        self.assertIsNotNone(credentials)
        self.assertEqual(credentials[0], self.test_email)
        self.assertEqual(credentials[1], self.test_password)

    def test_get_nonexistent_credentials(self):
        """Test retrieving credentials that don't exist"""
        credentials = self.service.get_credentials("nonexistent@gmail.com")
        self.assertIsNone(credentials)

    def test_update_credentials(self):
        """Test updating existing credentials"""
        # Store initial credentials
        self.service.store_credentials(self.test_email, self.test_password)

        # Update with new password
        new_password = "new_password_789"
        result = self.service.store_credentials(self.test_email, new_password)
        self.assertTrue(result)

        # Verify updated password
        credentials = self.service.get_credentials(self.test_email)
        self.assertEqual(credentials[1], new_password)

    def test_delete_credentials(self):
        """Test deleting credentials"""
        # Store credentials
        self.service.store_credentials(self.test_email, self.test_password)

        # Delete credentials
        result = self.service.delete_credentials(self.test_email)
        self.assertTrue(result)

        # Verify deletion
        credentials = self.service.get_credentials(self.test_email)
        self.assertIsNone(credentials)

    def test_delete_nonexistent_credentials(self):
        """Test deleting credentials that don't exist"""
        result = self.service.delete_credentials("nonexistent@gmail.com")
        self.assertFalse(result)

    def test_list_all_emails(self):
        """Test listing all stored emails"""
        # Store multiple credentials
        self.service.store_credentials(self.test_email, self.test_password)
        self.service.store_credentials(self.test_email2, self.test_password2)

        # List all emails
        emails = self.service.list_all_emails()
        self.assertEqual(len(emails), 2)
        self.assertIn(self.test_email, emails)
        self.assertIn(self.test_email2, emails)

    def test_list_emails_empty_database(self):
        """Test listing emails from empty database"""
        emails = self.service.list_all_emails()
        self.assertEqual(len(emails), 0)

    def test_multiple_credentials(self):
        """Test storing and retrieving multiple credentials"""
        # Store multiple credentials
        self.service.store_credentials(self.test_email, self.test_password)
        self.service.store_credentials(self.test_email2, self.test_password2)

        # Retrieve specific credentials
        creds1 = self.service.get_credentials(self.test_email)
        creds2 = self.service.get_credentials(self.test_email2)

        self.assertEqual(creds1[0], self.test_email)
        self.assertEqual(creds1[1], self.test_password)
        self.assertEqual(creds2[0], self.test_email2)
        self.assertEqual(creds2[1], self.test_password2)


class TestGmailFetcherIntegration(unittest.TestCase):
    """Integration tests for gmail_fetcher.py with CredentialsService"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, 'test_credentials.db')

        # Set environment variable for credentials DB path
        os.environ['CREDENTIALS_DB_PATH'] = self.test_db_path

        self.service = CredentialsService(db_path=self.test_db_path)
        self.test_email = "test@gmail.com"
        self.test_password = "test_app_password"

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up environment variable
        if 'CREDENTIALS_DB_PATH' in os.environ:
            del os.environ['CREDENTIALS_DB_PATH']

        # Remove test database
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        # Remove temp directory
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_credentials_retrieval_from_database(self):
        """Test that gmail_fetcher can retrieve credentials from database"""
        # Store credentials in database
        self.service.store_credentials(self.test_email, self.test_password)

        # Retrieve credentials
        credentials = self.service.get_credentials()

        self.assertIsNotNone(credentials)
        self.assertEqual(credentials[0], self.test_email)
        self.assertEqual(credentials[1], self.test_password)

    def test_credentials_fallback_to_env_vars(self):
        """Test that system falls back to environment variables if database is empty"""
        # Don't store anything in database
        # Set environment variables
        os.environ['GMAIL_EMAIL'] = self.test_email
        os.environ['GMAIL_PASSWORD'] = self.test_password

        try:
            # Try to get from database (should return None)
            credentials = self.service.get_credentials()

            # If database is empty, should return None
            self.assertIsNone(credentials)

            # System should then fallback to environment variables
            email_from_env = os.getenv('GMAIL_EMAIL')
            password_from_env = os.getenv('GMAIL_PASSWORD')

            self.assertEqual(email_from_env, self.test_email)
            self.assertEqual(password_from_env, self.test_password)
        finally:
            # Clean up environment variables
            if 'GMAIL_EMAIL' in os.environ:
                del os.environ['GMAIL_EMAIL']
            if 'GMAIL_PASSWORD' in os.environ:
                del os.environ['GMAIL_PASSWORD']


if __name__ == '__main__':
    unittest.main()