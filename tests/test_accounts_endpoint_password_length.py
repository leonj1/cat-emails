"""
Test suite for verifying that the /api/accounts endpoint includes password_length field.
"""
import unittest
import os
import tempfile
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add parent directory to path to import API modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set required environment variables before importing api_service
# This prevents validate_environment() from exiting during module load
os.environ.setdefault('REQUESTYAI_API_KEY', 'test-key-for-unit-tests')

# Mock SettingsService to prevent MySQL initialization during import
with patch('services.settings_service.SettingsService') as mock_settings:
    mock_settings_instance = MagicMock()
    mock_settings.return_value = mock_settings_instance
    from api_service import app, get_account_service
from models.account_models import EmailAccountInfo, AccountListResponse
from tests.fake_account_category_client import FakeAccountCategoryClient


class TestAccountsEndpointPasswordLength(unittest.TestCase):
    """Test suite to verify password_length field is included in accounts listing."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test client for the FastAPI app
        self.client = TestClient(app)
        
        # Set a test API key
        os.environ['API_KEY'] = 'test-api-key'
        
    def tearDown(self):
        """Clean up after tests."""
        if 'API_KEY' in os.environ:
            del os.environ['API_KEY']
            
    def _get_headers(self):
        """Helper to get API headers with auth."""
        return {"X-API-Key": "test-api-key"}
        
    def test_accounts_endpoint_includes_password_length(self):
        """Test that /api/accounts endpoint includes password_length field for each account."""
        # Create fake client with test accounts
        fake_client = FakeAccountCategoryClient()
        
        # Create test accounts with different password scenarios
        account1 = fake_client.get_or_create_account("test1@gmail.com", None, None, None)
        account1.app_password = "abcdefghijklmnop"  # 16 characters
        
        account2 = fake_client.get_or_create_account("test2@gmail.com", None, None, None)
        account2.app_password = None  # No password
        
        account3 = fake_client.get_or_create_account("test3@gmail.com", None, None, None) 
        account3.app_password = "verylongpassword123456"  # 22 characters
        
        # Override the dependency to use our fake client
        app.dependency_overrides[get_account_service] = lambda: fake_client
        
        # Make request to accounts endpoint
        response = self.client.get(
            "/api/accounts",
            headers=self._get_headers()
        )
        
        # Assert successful response
        self.assertEqual(response.status_code, 200)
        
        # Parse response
        data = response.json()
        
        # Verify response structure
        self.assertIn("accounts", data)
        self.assertIn("total_count", data)
        
        # Debug: Print what we actually got
        if data["total_count"] != 3:
            print(f"Expected 3 accounts, got {data['total_count']}")
            print(f"Accounts returned: {data['accounts']}")
            print(f"Fake client has {len(fake_client.accounts)} accounts")
            
        self.assertEqual(data["total_count"], 3)
        
        # Check each account has password_length field
        accounts = data["accounts"]
        self.assertEqual(len(accounts), 3)
        
        # Map accounts by email for easier testing
        accounts_by_email = {acc["email_address"]: acc for acc in accounts}
        
        # Verify password_length for account with password (16 chars)
        test1_account = accounts_by_email.get("test1@gmail.com")
        self.assertIsNotNone(test1_account)
        self.assertIn("password_length", test1_account)
        self.assertEqual(test1_account["password_length"], 16)
        
        # Verify password_length for account without password (should be 0)
        test2_account = accounts_by_email.get("test2@gmail.com")
        self.assertIsNotNone(test2_account)
        self.assertIn("password_length", test2_account)
        self.assertEqual(test2_account["password_length"], 0)
        
        # Verify password_length for account with longer password (22 chars)
        test3_account = accounts_by_email.get("test3@gmail.com")
        self.assertIsNotNone(test3_account)
        self.assertIn("password_length", test3_account)
        self.assertEqual(test3_account["password_length"], 22)
        
        # Clean up dependency override
        app.dependency_overrides.clear()
        
    def test_password_length_zero_when_no_password(self):
        """Test that password_length is 0 when account has no password."""
        # Create a client with only accounts without passwords
        fake_client = FakeAccountCategoryClient()
        account1 = fake_client.get_or_create_account("nopass1@gmail.com", None, None, None)
        account1.app_password = None
        account2 = fake_client.get_or_create_account("nopass2@gmail.com", None, None, None)
        account2.app_password = ""  # Empty string should also be 0
        
        # Override the dependency
        app.dependency_overrides[get_account_service] = lambda: fake_client
        
        response = self.client.get(
            "/api/accounts",
            headers=self._get_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # All accounts should have password_length = 0
        for account in data["accounts"]:
            self.assertIn("password_length", account)
            self.assertEqual(account["password_length"], 0)
            
        # Clean up dependency override
        app.dependency_overrides.clear()
            
    def test_password_length_matches_actual_length(self):
        """Test that password_length accurately reflects the actual password length."""
        # Create client with various password lengths
        fake_client = FakeAccountCategoryClient()
        
        # Test different password lengths
        test_cases = [
            ("short@gmail.com", "12345", 5),
            ("medium@gmail.com", "1234567890", 10),
            ("long@gmail.com", "a" * 50, 50),
            ("unicode@gmail.com", "café123", 7),  # Test with unicode characters
        ]
        
        for email, password, expected_length in test_cases:
            account = fake_client.get_or_create_account(email, None, None, None)
            account.app_password = password
            
        # Override the dependency
        app.dependency_overrides[get_account_service] = lambda: fake_client
        
        response = self.client.get(
            "/api/accounts",
            headers=self._get_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        accounts_by_email = {acc["email_address"]: acc for acc in data["accounts"]}
        
        # Verify each test case
        for email, password, expected_length in test_cases:
            account = accounts_by_email.get(email)
            self.assertIsNotNone(account, f"Account {email} not found")
            self.assertEqual(
                account["password_length"], 
                expected_length,
                f"Password length mismatch for {email}"
            )
            
        # Clean up dependency override
        app.dependency_overrides.clear()
            
    def test_password_length_field_in_model(self):
        """Test that EmailAccountInfo model includes password_length field."""
        # Create an instance of EmailAccountInfo
        account_info = EmailAccountInfo(
            id=1,
            email_address="test@gmail.com",
            display_name="Test Account",
            masked_password="ab********yz",
            password_length=12,
            is_active=True,
            created_at="2024-01-01T00:00:00"
        )
        
        # Verify the field exists and has correct value
        self.assertEqual(account_info.password_length, 12)
        
        # Verify field is in dict representation
        account_dict = account_info.dict()
        self.assertIn("password_length", account_dict)
        self.assertEqual(account_dict["password_length"], 12)
        
    def test_password_length_default_value(self):
        """Test that password_length defaults to 0 when not provided."""
        # Create an instance without specifying password_length
        account_info = EmailAccountInfo(
            id=1,
            email_address="test@gmail.com",
            created_at="2024-01-01T00:00:00"
        )
        
        # Should default to 0
        self.assertEqual(account_info.password_length, 0)
        
    def test_password_length_validation(self):
        """Test that password_length field validates correctly (non-negative)."""
        # Valid password_length
        account_info = EmailAccountInfo(
            id=1,
            email_address="test@gmail.com",
            password_length=10,
            created_at="2024-01-01T00:00:00"
        )
        self.assertEqual(account_info.password_length, 10)
        
        # Test that negative values are rejected
        with self.assertRaises(ValueError):
            EmailAccountInfo(
                id=1,
                email_address="test@gmail.com",
                password_length=-1,  # Invalid negative value
                created_at="2024-01-01T00:00:00"
            )


if __name__ == '__main__':
    unittest.main()
