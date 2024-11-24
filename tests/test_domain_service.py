import unittest
from unittest.mock import patch, MagicMock
import requests
from domain_service import DomainService, AllowedDomain

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
        mock_get.assert_called_once_with(f"{self.base_url}/api/v1/domains/allowed")
    
    @patch('requests.get')
    def test_fetch_allowed_domains_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        # Configure mock to raise an exception
        mock_get.side_effect = requests.exceptions.HTTPError("404 Client Error")
        
        # Verify that the appropriate exception is raised
        with self.assertRaises(requests.RequestException) as context:
            self.service.fetch_allowed_domains()
        
        self.assertIn("404", str(context.exception))
    
    @patch('requests.get')
    def test_fetch_allowed_domains_invalid_response(self, mock_get):
        """Test handling of invalid response data."""
        # Mock response with invalid data structure
        mock_response = [{"invalid_key": "value"}]
        
        # Configure mock
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_get.return_value = mock_response_obj
        
        # Verify that the appropriate exception is raised
        with self.assertRaises(ValueError) as context:
            self.service.fetch_allowed_domains()
        
        self.assertIn("Invalid response format", str(context.exception))
    
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
