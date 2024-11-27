import unittest
from unittest.mock import Mock, MagicMock, patch
from collections import Counter
import sys
from pathlib import Path

# Add the tests directory to the Python path so we can import mock modules
tests_dir = str(Path(__file__).parent)
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

# Mock the ell and email_scanner_consumer modules
sys.modules['ell'] = __import__('mock_ell')
sys.modules['email_scanner_consumer'] = __import__('mock_email_scanner_consumer')

# Now we can safely import from email_processor
from email_processor import process_single_email

class TestEmailProcessor(unittest.TestCase):
    def setUp(self):
        # Create mock fetcher
        self.fetcher = Mock()
        self.fetcher.remove_http_links = lambda x: x
        self.fetcher.remove_images_from_email = lambda x: x
        self.fetcher.remove_encoded_content = lambda x: x
        self.fetcher.add_label = MagicMock(return_value=True)
        
        # Create mock message
        self.msg = MagicMock()
        self.msg.get.side_effect = lambda x, default='': {
            'From': 'test@example.com',
            'Subject': 'Test Subject',
            'Message-ID': 'test-id-123'
        }.get(x, default)

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
                    'deletion': True,
                    'category': 'Blocked_Domain'
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
                    'deletion': False,
                    'category': 'Allowed_Domain'
                }
            },
            {
                'name': 'normal categorization',
                'setup': {
                    '_is_domain_blocked': False,
                    '_is_domain_allowed': False,
                    '_is_category_blocked': False,
                    'get_email_body': 'Test body'
                },
                'expected': {
                    'deletion': False,
                    'category': 'Newsletter'
                }
            },
            {
                'name': 'blocked category',
                'setup': {
                    '_is_domain_blocked': False,
                    '_is_domain_allowed': False,
                    '_is_category_blocked': True,
                    'get_email_body': 'Test body'
                },
                'expected': {
                    'deletion': True,
                    'category': 'Newsletter'
                }
            },
            {
                'name': 'long category not blocked',
                'setup': {
                    '_is_domain_blocked': False,
                    '_is_domain_allowed': False,
                    '_is_category_blocked': False,
                    'get_email_body': 'This is a very long test body that exceeds thirty characters'
                },
                'expected': {
                    'deletion': False,
                    'category': 'Newsletter'
                }
            },
            {
                'name': 'long category blocked',
                'setup': {
                    '_is_domain_blocked': False,
                    '_is_domain_allowed': False,
                    '_is_category_blocked': True,
                    'get_email_body': 'This is a very long test body that exceeds thirty characters'
                },
                'expected': {
                    'deletion': True,
                    'category': 'Newsletter'
                }
            }
        ]

        for tc in test_cases:
            with self.subTest(name=tc['name']):
                # Reset the fetcher for this test case
                self.fetcher.stats = {'categories': Counter()}
                
                # Configure mock fetcher for this test case
                self.fetcher._is_domain_blocked.return_value = tc['setup']['_is_domain_blocked']
                self.fetcher._is_domain_allowed.return_value = tc['setup']['_is_domain_allowed']
                self.fetcher._is_category_blocked.return_value = tc['setup']['_is_category_blocked']
                self.fetcher.get_email_body.return_value = tc['setup']['get_email_body']

                # Run the processor
                result = process_single_email(self.fetcher, self.msg)

                # Verify results
                self.assertEqual(result, tc['expected']['deletion'], 
                               f"Test case '{tc['name']}' failed: expected deletion={tc['expected']['deletion']}")
                
                self.assertEqual(
                    self.fetcher.stats['categories'][tc['expected']['category']], 
                    1,
                    f"Test case '{tc['name']}' failed: category counter not incremented correctly"
                )
                
                self.fetcher.add_label.assert_called_with('test-id-123', tc['expected']['category'])

if __name__ == '__main__':
    unittest.main()
