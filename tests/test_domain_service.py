import unittest
from unittest.mock import patch, MagicMock
import requests
from domain_service import DomainService, AllowedDomain, BlockedDomain

class TestDomainService(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.base_url = "https://control-api.joseserver.com"
        self.service = DomainService(self.base_url)
        
    @patch('requests.get')
    def test_fetch_allowed_domains_success(self, mock_get):
        """Test successful fetch of allowed domains."""
        # Mock data that matches expected API response
        mock_response = [
            {"domain": "example.com", "is_active": True},
            {"domain": "test.com", "is_active": False}
        ]
        
        # Configure mock
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_get.return_value = mock_response_obj
        
        # Call the service
        domains = self.service.fetch_allowed_domains()
        
        # Verify the response
        self.assertEqual(len(domains), 2)
        self.assertIsInstance(domains[0], AllowedDomain)
        self.assertEqual(domains[0].domain, "example.com")
        self.assertTrue(domains[0].is_active)
        self.assertEqual(domains[1].domain, "test.com")
        self.assertFalse(domains[1].is_active)
        
        # Verify the request
        mock_get.assert_called_once_with(
            f"{self.base_url}/api/v1/domains/allowed",
            timeout=10,
            headers={'Accept': 'application/json'}
        )
    
    @patch('requests.get')
    def test_fetch_blocked_domains_success(self, mock_get):
        """Test successful fetch of blocked domains."""
        # Mock data that matches expected API response
        mock_response = [
            {"domain": "spam.com", "reason": "Known spam source"},
            {"domain": "malware.com", "reason": "Security threat"}
        ]
        
        # Configure mock
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_get.return_value = mock_response_obj
        
        # Call the service
        domains = self.service.fetch_blocked_domains()
        
        # Verify the response
        self.assertEqual(len(domains), 2)
        self.assertIsInstance(domains[0], BlockedDomain)
        self.assertEqual(domains[0].domain, "spam.com")
        self.assertEqual(domains[0].reason, "Known spam source")
        self.assertEqual(domains[1].domain, "malware.com")
        self.assertEqual(domains[1].reason, "Security threat")
        
        # Verify the request
        mock_get.assert_called_once_with(
            f"{self.base_url}/api/v1/domains/blocked",
            timeout=10,
            headers={'Accept': 'application/json'}
        )
    
    @patch('requests.get')
    def test_fetch_allowed_domains_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        # Configure mock to raise an exception
        mock_get.side_effect = requests.exceptions.HTTPError("404 Client Error")
        
        # Verify that the appropriate exception is raised
        with self.assertRaises(requests.RequestException) as context:
            self.service.fetch_allowed_domains()
        
        self.assertIn("404", str(context.exception))
        
        # Verify the request parameters
        mock_get.assert_called_once_with(
            f"{self.base_url}/api/v1/domains/allowed",
            timeout=10,
            headers={'Accept': 'application/json'}
        )
    
    @patch('requests.get')
    def test_fetch_blocked_domains_http_error(self, mock_get):
        """Test handling of HTTP errors for blocked domains."""
        # Configure mock to raise an exception
        mock_get.side_effect = requests.exceptions.HTTPError("404 Client Error")
        
        # Verify that the appropriate exception is raised
        with self.assertRaises(requests.RequestException) as context:
            self.service.fetch_blocked_domains()
        
        self.assertIn("404", str(context.exception))
        
        # Verify the request parameters
        mock_get.assert_called_once_with(
            f"{self.base_url}/api/v1/domains/blocked",
            timeout=10,
            headers={'Accept': 'application/json'}
        )
    
    @patch('requests.get')
    def test_fetch_allowed_domains_invalid_response(self, mock_get):
        """Test handling of invalid response data."""
        # Mock response with invalid data structure (not a list)
        mock_response = {"invalid": "not a list"}
        
        # Configure mock
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_get.return_value = mock_response_obj
        
        # Verify that the appropriate exception is raised
        with self.assertRaises(ValueError) as context:
            self.service.fetch_allowed_domains()
        
        self.assertIn("Expected array response", str(context.exception))
        
        # Verify the request parameters
        mock_get.assert_called_once_with(
            f"{self.base_url}/api/v1/domains/allowed",
            timeout=10,
            headers={'Accept': 'application/json'}
        )
    
    @patch('requests.get')
    def test_fetch_blocked_domains_invalid_response(self, mock_get):
        """Test handling of invalid response data for blocked domains."""
        # Mock response with invalid data structure (not a list)
        mock_response = {"invalid": "not a list"}
        
        # Configure mock
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_get.return_value = mock_response_obj
        
        # Verify that the appropriate exception is raised
        with self.assertRaises(ValueError) as context:
            self.service.fetch_blocked_domains()
        
        self.assertIn("Expected array response", str(context.exception))
        
        # Verify the request parameters
        mock_get.assert_called_once_with(
            f"{self.base_url}/api/v1/domains/blocked",
            timeout=10,
            headers={'Accept': 'application/json'}
        )
    
    @patch('requests.get')
    def test_fetch_allowed_domains_invalid_domain_data(self, mock_get):
        """Test handling of invalid domain data within the array."""
        # Mock response with invalid domain data
        mock_response = [{"invalid_key": "value"}]
        
        # Configure mock
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_get.return_value = mock_response_obj
        
        # Verify that the appropriate exception is raised
        with self.assertRaises(ValueError) as context:
            self.service.fetch_allowed_domains()
        
        self.assertIn("Invalid response format", str(context.exception))
        
        # Verify the request parameters
        mock_get.assert_called_once_with(
            f"{self.base_url}/api/v1/domains/allowed",
            timeout=10,
            headers={'Accept': 'application/json'}
        )
    
    @patch('requests.get')
    def test_fetch_blocked_domains_invalid_domain_data(self, mock_get):
        """Test handling of invalid domain data within the array for blocked domains."""
        # Mock response with invalid domain data
        mock_response = [{"invalid_key": "value"}]
        
        # Configure mock
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_get.return_value = mock_response_obj
        
        # Verify that the appropriate exception is raised
        with self.assertRaises(ValueError) as context:
            self.service.fetch_blocked_domains()
        
        self.assertIn("Invalid response format", str(context.exception))
        
        # Verify the request parameters
        mock_get.assert_called_once_with(
            f"{self.base_url}/api/v1/domains/blocked",
            timeout=10,
            headers={'Accept': 'application/json'}
        )
    
    def test_base_url_normalization(self):
        """Test that base URL is properly normalized."""
        # Test with trailing slash
        service = DomainService(f"{self.base_url}/")
        self.assertEqual(service.base_url, self.base_url)
        
        # Test without trailing slash
        service = DomainService(self.base_url)
        self.assertEqual(service.base_url, self.base_url)

if __name__ == '__main__':
    unittest.main()
