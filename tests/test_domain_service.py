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
        with self.assertRaises(ValueError) as context:
            service = DomainService()
            service.fetch_allowed_domains()
        self.assertIn("API token is required", str(context.exception))

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

    def test_mock_mode(self):
        """Test that mock mode returns empty lists."""
        service = DomainService()  # No API token = mock mode
        self.assertTrue(service.mock_mode)
        with self.assertRaises(ValueError):
            service.fetch_allowed_domains()

if __name__ == '__main__':
    unittest.main()
