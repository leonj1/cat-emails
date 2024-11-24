import unittest
from unittest.mock import patch, Mock
import requests

from domain_service import DomainService, AllowedDomain, BlockedDomain, BlockedCategory

class TestDomainService(unittest.TestCase):
    def setUp(self):
        self.api_token = "test-token-123"
        self.service = DomainService(api_token=self.api_token)

    def test_base_url_normalization(self):
        """Test that base URL is properly normalized."""
        service = DomainService("https://control-api.joseserver.com/", api_token=self.api_token)
        self.assertEqual(service.base_url, "https://control-api.joseserver.com")

    def test_mock_mode_behavior(self):
        """Test service behavior in mock mode (no API token).
        
        In mock mode (when no API token is provided), the service should:
        1. Set mock_mode to True
        2. Return empty lists for all fetch operations
        3. Not make any actual API calls
        """
        # Create service without API token to enable mock mode
        service = DomainService()
        
        # Verify mock mode is enabled
        self.assertTrue(service.mock_mode)
        
        # Verify all fetch methods return empty lists without making API calls
        self.assertEqual(service.fetch_allowed_domains(), [])
        self.assertEqual(service.fetch_blocked_domains(), [])
        self.assertEqual(service.fetch_blocked_categories(), [])

    def test_non_mock_mode_behavior(self):
        """Test service behavior in non-mock mode (with API token).
        
        When an API token is provided, the service should:
        1. Set mock_mode to False
        2. Make actual API calls
        3. Raise errors for invalid responses
        """
        # Create service with API token
        service = DomainService(api_token=self.api_token)
        
        # Verify mock mode is disabled
        self.assertFalse(service.mock_mode)
        
        # Verify service attempts API calls (will raise RequestException due to no mock)
        with self.assertRaises(requests.RequestException):
            service.fetch_allowed_domains()

    @patch('requests.get')
    def test_fetch_allowed_domains_success(self, mock_get):
        """Test successful fetch of allowed domains."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "domains": ["example.com", "test.com"]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        domains = self.service.fetch_allowed_domains()
        self.assertEqual(len(domains), 2)
        self.assertEqual(domains[0].domain, "example.com")
        self.assertTrue(domains[0].is_active)

        mock_get.assert_called_with(
            "https://control-api.joseserver.com/domains/allowed",
            timeout=10,
            headers={
                'Accept': 'application/json',
                'X-API-Token': self.api_token
            }
        )

    @patch('requests.get')
    def test_fetch_allowed_domains_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        mock_get.side_effect = requests.RequestException("API error")
        with self.assertRaises(requests.RequestException):
            self.service.fetch_allowed_domains()

    @patch('requests.get')
    def test_fetch_allowed_domains_invalid_response(self, mock_get):
        """Test handling of invalid response data."""
        mock_response = Mock()
        mock_response.json.return_value = {"error": "not a dictionary"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            self.service.fetch_allowed_domains()

    @patch('requests.get')
    def test_fetch_blocked_domains_success(self, mock_get):
        """Test successful fetch of blocked domains."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"domain": "spam.com", "reason": "Spam source"},
                {"domain": "malware.com", "reason": "Malware host"}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        domains = self.service.fetch_blocked_domains()
        self.assertEqual(len(domains), 2)
        self.assertEqual(domains[0].domain, "spam.com")
        self.assertEqual(domains[0].reason, "Spam source")

        mock_get.assert_called_with(
            "https://control-api.joseserver.com/domains/blocked",
            timeout=10,
            headers={
                'Accept': 'application/json',
                'X-API-Token': self.api_token
            }
        )

    @patch('requests.get')
    def test_fetch_blocked_domains_http_error(self, mock_get):
        """Test handling of HTTP errors for blocked domains."""
        mock_get.side_effect = requests.RequestException("API error")
        with self.assertRaises(requests.RequestException):
            self.service.fetch_blocked_domains()

    @patch('requests.get')
    def test_fetch_blocked_categories_success(self, mock_get):
        """Test successful fetch of blocked categories."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"category": "spam", "reason": "Unwanted mail"},
                {"category": "phishing", "reason": "Security risk"}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        categories = self.service.fetch_blocked_categories()
        self.assertEqual(len(categories), 2)
        self.assertEqual(categories[0].category, "spam")
        self.assertEqual(categories[0].reason, "Unwanted mail")

        mock_get.assert_called_with(
            "https://control-api.joseserver.com/categories/blocked",
            timeout=10,
            headers={
                'Accept': 'application/json',
                'X-API-Token': self.api_token
            }
        )

if __name__ == '__main__':
    unittest.main()
