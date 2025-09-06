"""
Unit tests for account-related API endpoints.
Provides comprehensive test coverage for FastAPI account management endpoints.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Import the FastAPI app and dependencies
from api_service import app, get_account_service, verify_api_key
from services.account_category_service import AccountCategoryService
from models.database import Base, EmailAccount, AccountCategoryStats, init_database
from models.account_models import TopCategoriesResponse, CategoryStats, DatePeriod, EmailAccountInfo


class TestAccountAPIEndpoints(unittest.TestCase):
    """Test cases for account-related API endpoints."""

    def setUp(self):
        """Set up test fixtures with test database and client."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Initialize test database
        self.engine = init_database(self.db_path)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Create test service
        self.service = AccountCategoryService(db_path=self.db_path)
        
        # Create test client
        self.client = TestClient(app)
        
        # Test data
        self.test_email = "test@gmail.com"
        self.test_display_name = "Test User"
        self.api_headers = {"X-API-Key": "test-api-key"}
        
        # Mock the service dependency to use our test service
        app.dependency_overrides[get_account_service] = lambda: self.service
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Clear dependency overrides
        app.dependency_overrides.clear()
        
        self.session.close()
        self.engine.dispose()
        
        # Remove temp database file
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def _create_test_account_with_stats(self):
        """Helper method to create test account with category statistics."""
        # Create account
        account = self.service.get_or_create_account(self.test_email, self.test_display_name)
        
        # Create test statistics over multiple days
        base_date = date.today()
        for i in range(7):  # 7 days of data
            stats_date = base_date - timedelta(days=i)
            category_stats = {
                "Marketing": {"total": 10 + i, "deleted": 8 + i, "kept": 2, "archived": 0},
                "Personal": {"total": 5, "deleted": 0, "kept": 5, "archived": 0},
                "Work-related": {"total": 3 + (i * 2), "deleted": 1, "kept": 2 + (i * 2), "archived": 0},
                "Advertising": {"total": 2 + i, "deleted": 2 + i, "kept": 0, "archived": 0}
            }
            self.service.record_category_stats(self.test_email, stats_date, category_stats)
        
        return account

    # Tests for GET /api/accounts/{email}/categories/top
    
    def test_get_top_categories_success(self):
        """Test successful retrieval of top categories."""
        # Create test data
        self._create_test_account_with_stats()
        
        # Make request
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top?days=7&limit=10&include_counts=true"
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response structure
        self.assertIn("email_address", data)
        self.assertIn("period", data)
        self.assertIn("total_emails", data)
        self.assertIn("top_categories", data)
        
        # Verify data content
        self.assertEqual(data["email_address"], self.test_email)
        self.assertEqual(data["period"]["days"], 7)
        self.assertGreater(data["total_emails"], 0)
        self.assertGreater(len(data["top_categories"]), 0)
        
        # Verify categories have required fields
        for category in data["top_categories"]:
            self.assertIn("category", category)
            self.assertIn("total_count", category)
            self.assertIn("percentage", category)
            # With include_counts=true, these should be present
            self.assertIn("kept_count", category)
            self.assertIn("deleted_count", category)
            self.assertIn("archived_count", category)

    def test_get_top_categories_without_counts(self):
        """Test getting top categories without detailed counts."""
        self._create_test_account_with_stats()
        
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top?days=7&limit=5&include_counts=false"
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify detailed counts are not included
        for category in data["top_categories"]:
            self.assertIsNone(category.get("kept_count"))
            self.assertIsNone(category.get("deleted_count"))
            self.assertIsNone(category.get("archived_count"))

    def test_get_top_categories_limit_applied(self):
        """Test that limit parameter is properly applied."""
        self._create_test_account_with_stats()
        
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top?days=7&limit=2"
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertLessEqual(len(data["top_categories"]), 2)

    def test_get_top_categories_invalid_email_format(self):
        """Test with invalid email format."""
        invalid_email = "not-an-email"
        response = self.client.get(
            f"/api/accounts/{invalid_email}/categories/top?days=7"
        )
        
        self.assertEqual(response.status_code, 422)  # Validation error

    def test_get_top_categories_nonexistent_account(self):
        """Test with non-existent account."""
        response = self.client.get(
            "/api/accounts/nonexistent@gmail.com/categories/top?days=7"
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)

    def test_get_top_categories_invalid_days(self):
        """Test with invalid days parameter."""
        self._create_test_account_with_stats()
        
        # Test days too low
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top?days=0"
        )
        self.assertEqual(response.status_code, 422)
        
        # Test days too high
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top?days=366"
        )
        self.assertEqual(response.status_code, 422)

    def test_get_top_categories_invalid_limit(self):
        """Test with invalid limit parameter."""
        self._create_test_account_with_stats()
        
        # Test limit too low
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top?days=7&limit=0"
        )
        self.assertEqual(response.status_code, 422)
        
        # Test limit too high
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top?days=7&limit=51"
        )
        self.assertEqual(response.status_code, 422)

    def test_get_top_categories_missing_required_param(self):
        """Test with missing required days parameter."""
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top"
        )
        
        self.assertEqual(response.status_code, 422)

    @patch.dict(os.environ, {"API_KEY": "required-api-key"})
    def test_get_top_categories_with_api_key_valid(self):
        """Test endpoint with valid API key when API key is required."""
        self._create_test_account_with_stats()
        
        headers = {"X-API-Key": "required-api-key"}
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top?days=7",
            headers=headers
        )
        
        self.assertEqual(response.status_code, 200)

    @patch.dict(os.environ, {"API_KEY": "required-api-key"})
    def test_get_top_categories_with_api_key_invalid(self):
        """Test endpoint with invalid API key when API key is required."""
        self._create_test_account_with_stats()
        
        headers = {"X-API-Key": "wrong-key"}
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top?days=7",
            headers=headers
        )
        
        self.assertEqual(response.status_code, 401)

    @patch.dict(os.environ, {"API_KEY": "required-api-key"})
    def test_get_top_categories_with_api_key_missing(self):
        """Test endpoint with missing API key when API key is required."""
        self._create_test_account_with_stats()
        
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top?days=7"
        )
        
        self.assertEqual(response.status_code, 401)

    # Tests for GET /api/accounts
    
    def test_get_all_accounts_success(self):
        """Test successful retrieval of all accounts."""
        # Create multiple accounts
        accounts_data = [
            ("user1@gmail.com", "User 1"),
            ("user2@gmail.com", "User 2"),
            ("user3@gmail.com", "User 3"),
        ]
        
        for email, name in accounts_data:
            self.service.get_or_create_account(email, name)
        
        response = self.client.get("/api/accounts")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response structure
        self.assertIn("accounts", data)
        self.assertIn("total_count", data)
        
        # Verify data content
        self.assertEqual(len(data["accounts"]), 3)
        self.assertEqual(data["total_count"], 3)
        
        # Verify account structure
        for account in data["accounts"]:
            self.assertIn("id", account)
            self.assertIn("email_address", account)
            self.assertIn("display_name", account)
            self.assertIn("is_active", account)
            self.assertIn("created_at", account)

    def test_get_all_accounts_active_only_filter(self):
        """Test filtering to active accounts only."""
        # Create accounts and deactivate one
        self.service.get_or_create_account("active@gmail.com", "Active User")
        self.service.get_or_create_account("inactive@gmail.com", "Inactive User")
        self.service.deactivate_account("inactive@gmail.com")
        
        # Test active only (default)
        response = self.client.get("/api/accounts?active_only=true")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["accounts"]), 1)
        self.assertEqual(data["accounts"][0]["email_address"], "active@gmail.com")
        
        # Test including inactive
        response = self.client.get("/api/accounts?active_only=false")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["accounts"]), 2)

    def test_get_all_accounts_empty_result(self):
        """Test getting accounts when none exist."""
        response = self.client.get("/api/accounts")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["accounts"]), 0)
        self.assertEqual(data["total_count"], 0)

    # Tests for POST /api/accounts
    
    def test_create_account_success(self):
        """Test successful account creation."""
        request_data = {
            "email_address": self.test_email,
            "display_name": self.test_display_name
        }
        
        response = self.client.post("/api/accounts", json=request_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response
        self.assertIn("status", data)
        self.assertIn("message", data)
        self.assertIn("timestamp", data)
        self.assertEqual(data["status"], "success")
        
        # Verify account was created in database
        account = self.service.get_account_by_email(self.test_email)
        self.assertIsNotNone(account)
        self.assertEqual(account.email_address, self.test_email)
        self.assertEqual(account.display_name, self.test_display_name)

    def test_create_account_without_display_name(self):
        """Test creating account without display name."""
        request_data = {
            "email_address": self.test_email
        }
        
        response = self.client.post("/api/accounts", json=request_data)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify account was created
        account = self.service.get_account_by_email(self.test_email)
        self.assertIsNotNone(account)
        self.assertIsNone(account.display_name)

    def test_create_account_duplicate(self):
        """Test creating duplicate account (should update existing)."""
        # Create account first
        self.service.get_or_create_account(self.test_email, "Original Name")
        
        # Try to create again with different name
        request_data = {
            "email_address": self.test_email,
            "display_name": "Updated Name"
        }
        
        response = self.client.post("/api/accounts", json=request_data)
        self.assertEqual(response.status_code, 200)
        
        # Verify account was updated, not duplicated
        account = self.service.get_account_by_email(self.test_email)
        self.assertEqual(account.display_name, "Updated Name")
        
        # Verify only one account exists
        all_accounts = self.service.get_all_accounts(active_only=False)
        matching_accounts = [acc for acc in all_accounts if acc.email_address == self.test_email]
        self.assertEqual(len(matching_accounts), 1)

    def test_create_account_invalid_email(self):
        """Test creating account with invalid email."""
        request_data = {
            "email_address": "invalid-email",
            "display_name": "Test User"
        }
        
        response = self.client.post("/api/accounts", json=request_data)
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertIn("detail", data)

    def test_create_account_missing_email(self):
        """Test creating account with missing email address."""
        request_data = {
            "display_name": "Test User"
        }
        
        response = self.client.post("/api/accounts", json=request_data)
        self.assertEqual(response.status_code, 422)  # Validation error

    def test_create_account_empty_request(self):
        """Test creating account with empty request body."""
        response = self.client.post("/api/accounts", json={})
        self.assertEqual(response.status_code, 422)  # Validation error

    # Tests for PUT /api/accounts/{email}/deactivate
    
    def test_deactivate_account_success(self):
        """Test successful account deactivation."""
        # Create account first
        self.service.get_or_create_account(self.test_email, self.test_display_name)
        
        response = self.client.put(f"/api/accounts/{self.test_email}/deactivate")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response
        self.assertEqual(data["status"], "success")
        self.assertIn("deactivated", data["message"].lower())
        
        # Verify account was deactivated
        account = self.service.get_account_by_email(self.test_email)
        self.assertFalse(account.is_active)

    def test_deactivate_account_nonexistent(self):
        """Test deactivating non-existent account."""
        response = self.client.put("/api/accounts/nonexistent@gmail.com/deactivate")
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)

    def test_deactivate_account_invalid_email(self):
        """Test deactivating account with invalid email."""
        response = self.client.put("/api/accounts/invalid-email/deactivate")
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("detail", data)

    def test_deactivate_account_already_inactive(self):
        """Test deactivating already inactive account."""
        # Create and deactivate account
        self.service.get_or_create_account(self.test_email, self.test_display_name)
        self.service.deactivate_account(self.test_email)
        
        response = self.client.put(f"/api/accounts/{self.test_email}/deactivate")
        
        # Should still return success (idempotent operation)
        self.assertEqual(response.status_code, 200)

    # Error handling tests
    
    @patch('api_service.get_account_service')
    def test_database_service_unavailable(self, mock_get_service):
        """Test handling when database service is unavailable."""
        mock_get_service.side_effect = Exception("Database connection failed")
        
        response = self.client.get("/api/accounts")
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("detail", data)

    @patch('services.account_category_service.AccountCategoryService.get_top_categories')
    def test_service_method_error(self, mock_get_top):
        """Test handling service method errors."""
        self._create_test_account_with_stats()
        mock_get_top.side_effect = SQLAlchemyError("Database error")
        
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top?days=7"
        )
        
        self.assertEqual(response.status_code, 500)

    # Content type and format tests
    
    def test_get_top_categories_response_content_type(self):
        """Test that response has correct content type."""
        self._create_test_account_with_stats()
        
        response = self.client.get(
            f"/api/accounts/{self.test_email}/categories/top?days=7"
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/json")

    def test_create_account_request_content_type(self):
        """Test that endpoint accepts JSON content type."""
        request_data = {
            "email_address": self.test_email,
            "display_name": self.test_display_name
        }
        
        response = self.client.post(
            "/api/accounts", 
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)

    # Edge case tests
    
    def test_get_top_categories_special_characters_in_email(self):
        """Test with email containing special characters."""
        special_email = "test+tag@gmail.com"
        self.service.get_or_create_account(special_email, "Test User")
        
        # URL encode the email
        import urllib.parse
        encoded_email = urllib.parse.quote(special_email, safe='')
        
        response = self.client.get(
            f"/api/accounts/{encoded_email}/categories/top?days=7"
        )
        
        self.assertEqual(response.status_code, 200)

    def test_very_long_display_name(self):
        """Test creating account with very long display name."""
        long_name = "A" * 300  # Very long display name
        
        request_data = {
            "email_address": self.test_email,
            "display_name": long_name
        }
        
        response = self.client.post("/api/accounts", json=request_data)
        
        # Should handle gracefully (exact behavior depends on database constraints)
        self.assertIn(response.status_code, [200, 400])

    def test_case_sensitivity_in_email(self):
        """Test that email addresses are handled case-insensitively."""
        # Create account with lowercase email
        self.service.get_or_create_account(self.test_email.lower(), "Test User")
        
        # Query with uppercase email
        response = self.client.get(
            f"/api/accounts/{self.test_email.upper()}/categories/top?days=7"
        )
        
        # Should work because emails are normalized to lowercase
        self.assertEqual(response.status_code, 200)


class TestAPIKeyAuthentication(unittest.TestCase):
    """Test API key authentication functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_verify_api_key_no_key_required(self):
        """Test when no API key is required (default behavior)."""
        # When API_KEY env var is not set, any request should pass
        result = verify_api_key(x_api_key=None)
        self.assertTrue(result)
        
        result = verify_api_key(x_api_key="any-key")
        self.assertTrue(result)
    
    @patch.dict(os.environ, {"API_KEY": "test-key"})
    def test_verify_api_key_valid(self):
        """Test with valid API key."""
        result = verify_api_key(x_api_key="test-key")
        self.assertTrue(result)
    
    @patch.dict(os.environ, {"API_KEY": "test-key"})
    def test_verify_api_key_invalid(self):
        """Test with invalid API key."""
        with self.assertRaises(HTTPException) as context:
            verify_api_key(x_api_key="wrong-key")
        
        self.assertEqual(context.exception.status_code, 401)
    
    @patch.dict(os.environ, {"API_KEY": "test-key"})
    def test_verify_api_key_missing(self):
        """Test with missing API key when required."""
        with self.assertRaises(HTTPException) as context:
            verify_api_key(x_api_key=None)
        
        self.assertEqual(context.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()