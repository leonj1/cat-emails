import unittest
from unittest.mock import MagicMock, patch
from collections import defaultdict
from email.message import Message
from cat_emails.email_processors.email_processor import process_single_email
from cat_emails.email_scanner_consumer import set_mock_mode

# Mock the ell module
import ell
import sys
sys.modules['ell'] = ell

class MockFetcher:
    def __init__(self):
        self.stats = {'categories': defaultdict(int)}
        self.transform_calls = []
        self._is_domain_blocked = MagicMock(return_value=False)
        self._is_domain_allowed = MagicMock(return_value=False)
        self._is_category_blocked = MagicMock(return_value=False)
        self.get_email_body = MagicMock(return_value="Test body")
        self.delete_email = MagicMock(return_value=True)
        self.add_label = MagicMock()
        self.remove_http_links = MagicMock(return_value="Test content without links")
        self.remove_images_from_email = MagicMock(return_value="Test content without images")
        self.remove_encoded_content = MagicMock(return_value="Test content without encoded content")

    def reset_mock(self):
        self._is_domain_blocked.reset_mock()
        self._is_domain_allowed.reset_mock()
        self._is_category_blocked.reset_mock()
        self.get_email_body.reset_mock()
        self.delete_email.reset_mock()
        self.add_label.reset_mock()
        self.remove_http_links.reset_mock()
        self.remove_images_from_email.reset_mock()
        self.remove_encoded_content.reset_mock()

class TestEmailProcessor(unittest.TestCase):
    def setUp(self):
        set_mock_mode(True)  # Enable mock mode for OpenAI client
        self.fetcher = MockFetcher()
        self.base_msg_data = {
            'From': 'test@example.com',
            'Subject': 'Test Subject',
            'Body': 'Test body'
        }
        self.msg = Message()
        self.msg.add_header('Message-ID', 'test-id-123')
        for k, v in self.base_msg_data.items():
            self.msg[k] = v

    def test_email_processing_cases(self):
        test_cases = [
            {
                'name': 'blocked domain',
                'setup': {
                    '_is_domain_blocked': True,
                    '_is_domain_allowed': False,
                    '_is_category_blocked': False,
                    'get_email_body': 'Test body'
                },
                'expected': {
                    'delete_email': True,
                    'add_label': False
                }
            },
            {
                'name': 'allowed domain',
                'setup': {
                    '_is_domain_blocked': False,
                    '_is_domain_allowed': True,
                    '_is_category_blocked': False,
                    'get_email_body': 'Test body'
                },
                'expected': {
                    'delete_email': False,
                    'add_label': True
                }
            }
        ]

        for case in test_cases:
            with self.subTest(case['name']):
                # Reset mock calls
                self.fetcher.reset_mock()

                # Setup mock behavior
                self.fetcher._is_domain_blocked.return_value = case['setup']['_is_domain_blocked']
                self.fetcher._is_domain_allowed.return_value = case['setup']['_is_domain_allowed']
                self.fetcher._is_category_blocked.return_value = case['setup']['_is_category_blocked']
                self.fetcher.get_email_body.return_value = case['setup']['get_email_body']

                # Process email
                process_single_email(self.fetcher, self.msg)

                # Check if email was deleted or kept
                if case['expected']['delete_email']:
                    self.fetcher.delete_email.assert_called_once()
                else:
                    self.fetcher.delete_email.assert_not_called()

                # Check if label was added
                if case['expected']['add_label']:
                    self.fetcher.add_label.assert_called_once()
                else:
                    self.fetcher.add_label.assert_not_called()

class TestEmailDeletionAndStats(unittest.TestCase):
    def setUp(self):
        set_mock_mode(True)  # Enable mock mode for OpenAI client
        # Import and mock the ell module
        import ell
        import sys
        sys.modules['ell'] = ell

        self.fetcher = MockFetcher()
        self.base_msg_data = {
            'Message-ID': 'test-id-123',
            'From': 'test@example.com',
            'Subject': 'Test Subject',
            'Body': 'Test body'
        }
        self.msg = Message()
        for k, v in self.base_msg_data.items():
            self.msg[k] = v

    def test_successful_email_deletion(self):
        """Test successful email deletion scenario."""
        self.fetcher._is_domain_blocked.return_value = True
        self.fetcher.delete_email.return_value = True
        process_single_email(self.fetcher, self.msg)
        self.fetcher.delete_email.assert_called_once()

    def test_failed_email_deletion(self):
        """Test failed email deletion scenario."""
        self.fetcher._is_domain_blocked.return_value = True
        self.fetcher.delete_email.return_value = False
        process_single_email(self.fetcher, self.msg)
        self.fetcher.delete_email.assert_called_once()

    def test_email_kept_no_deletion_candidate(self):
        """Test email kept when not marked for deletion."""
        self.fetcher._is_domain_blocked.return_value = False
        process_single_email(self.fetcher, self.msg)
        self.fetcher.delete_email.assert_not_called()

    @patch('cat_emails.email_processors.email_processor.categorize_email_ell_marketing')
    def test_category_stats_tracking(self, mock_categorize):
        """Test category stats tracking for multiple emails."""
        mock_categorize.return_value = "Other"

        # Process first email
        process_single_email(self.fetcher, self.msg)
        self.assertEqual(self.fetcher.stats['categories']['Other'], 1)

        # Process second email
        process_single_email(self.fetcher, self.msg)
        self.assertEqual(self.fetcher.stats['categories']['Other'], 2)

if __name__ == '__main__':
    unittest.main()
