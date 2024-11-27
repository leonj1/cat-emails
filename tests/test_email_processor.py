import unittest
from unittest.mock import Mock, MagicMock, patch
from collections import Counter, defaultdict
import sys
from pathlib import Path

# Add the tests directory to the Python path so we can import mock modules
tests_dir = str(Path(__file__).parent)
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mock the ell and email_scanner_consumer modules
sys.modules['ell'] = __import__('mock_ell')
sys.modules['email_scanner_consumer'] = __import__('mock_email_scanner_consumer')

# Now we can safely import from email_processor
from cat_emails.email_processors.email_processor import process_single_email

class TestEmailProcessor(unittest.TestCase):
    def setUp(self):
        # Create mock fetcher
        self.fetcher = Mock()
        self.fetcher.stats = {'categories': defaultdict(int)}
        self.fetcher.transform_calls = []
        
        # Create spy functions for email transformation methods
        def track_transform(name):
            def transform_fn(*args):
                self.fetcher.transform_calls.append(name)
                return args[0]
            return transform_fn
        
        self.fetcher.remove_http_links = track_transform('remove_http_links')
        self.fetcher.remove_images_from_email = track_transform('remove_images_from_email')
        self.fetcher.remove_encoded_content = track_transform('remove_encoded_content')
        self.fetcher.add_label = MagicMock(return_value=True)
        
        # Create mock message
        self.msg = MagicMock()
        self.base_msg_data = {
            'From': 'test@example.com',
            'Subject': 'Test Subject',
            'Message-ID': 'test-id-123'
        }
        self.msg.get.side_effect = lambda x, default='': self.base_msg_data.get(x, default)

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
                    'category': 'Blocked_Domain',
                    'skip_transforms': True
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
                    'category': 'Allowed_Domain',
                    'skip_transforms': True
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
            },
            {
                'name': 'malformed_email_no_body',
                'setup': {
                    '_is_domain_blocked': False,
                    '_is_domain_allowed': False,
                    '_is_category_blocked': False,
                    'get_email_body': None  # Simulate missing body
                },
                'expected': {
                    'deletion': False,
                    'category': 'Uncategorized',
                    'skip_transforms': True
                }
            },
            {
                'name': 'malformed_email_no_message_id',
                'setup': {
                    '_is_domain_blocked': False,
                    '_is_domain_allowed': False,
                    '_is_category_blocked': False,
                    'get_email_body': 'Test body'
                },
                'expected': {
                    'deletion': False,
                    'category': 'Newsletter',
                    'skip_label': True
                },
                'message_id': None
            },
            {
                'name': 'empty_body',
                'setup': {
                    '_is_domain_blocked': False,
                    '_is_domain_allowed': False,
                    '_is_category_blocked': False,
                    'get_email_body': ''  # Empty body
                },
                'expected': {
                    'deletion': False,
                    'category': 'Uncategorized',
                    'skip_transforms': True
                }
            }
        ]

        for tc in test_cases:
            with self.subTest(name=tc['name']):
                # Reset mocks and counters for each test
                self.fetcher.reset_mock()
                self.fetcher.stats = {'categories': defaultdict(int)}
                self.fetcher.transform_calls = []
                
                # Configure mock fetcher for this test case
                self.fetcher._is_domain_blocked.return_value = tc['setup']['_is_domain_blocked']
                self.fetcher._is_domain_allowed.return_value = tc['setup']['_is_domain_allowed']
                self.fetcher._is_category_blocked.return_value = tc['setup']['_is_category_blocked']
                self.fetcher.get_email_body.return_value = tc['setup']['get_email_body']

                # Configure message ID if specified
                if 'message_id' in tc:
                    self.base_msg_data['Message-ID'] = tc['message_id']
                else:
                    self.base_msg_data['Message-ID'] = 'test-id-123'

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
                
                # Verify label addition
                if tc['expected'].get('skip_label', False):
                    self.fetcher.add_label.assert_not_called()
                else:
                    self.fetcher.add_label.assert_called_once_with(
                        self.base_msg_data['Message-ID'], 
                        tc['expected']['category']
                    )

                # For normal processing, verify transformation methods are called in correct order
                if not tc.get('expected', {}).get('skip_transforms', False):
                    self.assertEqual(
                        self.fetcher.transform_calls,
                        ['remove_http_links', 'remove_images_from_email', 'remove_encoded_content'],
                        f"Test case '{tc['name']}' failed: transforms not called in correct order"
                    )
                else:
                    self.assertEqual(
                        self.fetcher.transform_calls, [],
                        f"Test case '{tc['name']}' failed: transforms should not have been called"
                    )

    def test_transformation_methods(self):
        """Test that email transformation methods are called in the correct order"""
        self.fetcher._is_domain_blocked.return_value = False
        self.fetcher._is_domain_allowed.return_value = False
        self.fetcher._is_category_blocked.return_value = False
        self.fetcher.get_email_body.return_value = "Test body with http://example.com and <img> tags"

        process_single_email(self.fetcher, self.msg)

        expected_transforms = [
            'remove_http_links',
            'remove_images_from_email',
            'remove_encoded_content'
        ]
        self.assertEqual(
            self.fetcher.transform_calls,
            expected_transforms,
            "Email transformation methods not called in correct order"
        )

if __name__ == '__main__':
    unittest.main()
