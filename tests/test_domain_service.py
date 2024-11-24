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

    def test_missing_api_token(self):
        """Test that service raises error when API token is not provided."""
        service = DomainService()
        with self.assertRaises(ValueError) as context:
            service.fetch_allowed_domains()
        self.assertIn("API token is required", str(context.exception))

    @patch('requests.get')
    def test_fetch_allowed_domains_success(self, mock_get):
        """Test successful fetch of allowed domains."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"domain": "example.com", "is_active": True},
            {"domain": "test.com", "is_active": False}
        ]
        mock_get.return_value = mock_response

        domains = self.service.fetch_allowed_domains()
        self.assertEqual(len(domains), 2)
        self.assertEqual(domains[0].domain, "example.com")
        self.assertTrue(domains[0].is_active)

        mock_get.assert_called_with(
            "https://control-api.joseserver.com/api/v1/domains/allowed",
            timeout=10,
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_token}'
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
        mock_response.json.return_value = {"error": "not a list"}
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            self.service.fetch_allowed_domains()

    @patch('requests.get')
    def test_fetch_allowed_domains_invalid_domain_data(self, mock_get):
        """Test handling of invalid domain data within the array."""
        mock_response = Mock()
        mock_response.json.return_value = [{"invalid": "data"}]
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            self.service.fetch_allowed_domains()

    @patch('requests.get')
    def test_fetch_blocked_domains_success(self, mock_get):
        """Test successful fetch of blocked domains."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"domain": "spam.com", "reason": "Spam source"},
            {"domain": "malware.com", "reason": "Malware host"}
        ]
        mock_get.return_value = mock_response

        domains = self.service.fetch_blocked_domains()
        self.assertEqual(len(domains), 2)
        self.assertEqual(domains[0].domain, "spam.com")
        self.assertEqual(domains[0].reason, "Spam source")

        mock_get.assert_called_with(
            "https://control-api.joseserver.com/api/v1/domains/blocked",
            timeout=10,
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_token}'
            }
        )

    @patch('requests.get')
    def test_fetch_blocked_domains_http_error(self, mock_get):
        """Test handling of HTTP errors for blocked domains."""
        mock_get.side_effect = requests.RequestException("API error")
        with self.assertRaises(requests.RequestException):
            self.service.fetch_blocked_domains()

    @patch('requests.get')
    def test_fetch_blocked_domains_invalid_response(self, mock_get):
        """Test handling of invalid response data for blocked domains."""
        mock_response = Mock()
        mock_response.json.return_value = {"error": "not a list"}
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            self.service.fetch_blocked_domains()

    @patch('requests.get')
    def test_fetch_blocked_domains_invalid_domain_data(self, mock_get):
        """Test handling of invalid domain data within the array for blocked domains."""
        mock_response = Mock()
        mock_response.json.return_value = [{"invalid": "data"}]
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            self.service.fetch_blocked_domains()

    @patch('requests.get')
    def test_fetch_blocked_categories_success(self, mock_get):
        """Test successful fetch of blocked categories."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "name": "Malware",
                "description": "Known malware distribution sites",
                "severity": "high"
            },
            {
                "name": "Phishing",
                "description": "Phishing attempt sites",
                "severity": "critical"
            }
        ]
        mock_get.return_value = mock_response

        categories = self.service.fetch_blocked_categories()
        self.assertEqual(len(categories), 2)
        self.assertEqual(categories[0].name, "Malware")
        self.assertEqual(categories[0].description, "Known malware distribution sites")
        self.assertEqual(categories[0].severity, "high")

        mock_get.assert_called_with(
            "https://control-api.joseserver.com/api/v1/categories/blocked",
            timeout=10,
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_token}'
            }
        )

    @patch('requests.get')
    def test_fetch_blocked_categories_http_error(self, mock_get):
        """Test handling of HTTP errors for blocked categories."""
        mock_get.side_effect = requests.RequestException("API error")
        with self.assertRaises(requests.RequestException):
            self.service.fetch_blocked_categories()

    @patch('requests.get')
    def test_fetch_blocked_categories_invalid_response(self, mock_get):
        """Test handling of invalid response data for blocked categories."""
        mock_response = Mock()
        mock_response.json.return_value = {"error": "not a list"}
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            self.service.fetch_blocked_categories()

    @patch('requests.get')
    def test_fetch_blocked_categories_invalid_category_data(self, mock_get):
        """Test handling of invalid category data within the array."""
        mock_response = Mock()
        mock_response.json.return_value = [{"invalid": "data"}]
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError):
            self.service.fetch_blocked_categories()

if __name__ == '__main__':
    unittest.main()
