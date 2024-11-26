import unittest
from unittest.mock import Mock, MagicMock
from email_processor import process_single_email
from collections import Counter

class TestEmailProcessor(unittest.TestCase):
    def setUp(self):
        # Create mock fetcher
        self.fetcher = Mock()
        self.fetcher.stats = {'categories': Counter()}
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
                'name': 'blocked category',
                'setup': {
                    '_is_domain_blocked': False,
                    '_is_domain_allowed': False,
                    '_is_category_blocked': True,
                    'get_email_body': 'Test body'
                },
                'expected': {
                    'deletion': True,
                    'category': 'Marketing'  # Assuming default categorization
                }
            }
        ]

        for tc in test_cases:
            with self.subTest(name=tc['name']):
                # Configure mock fetcher for this test case
                self.fetcher._is_domain_blocked.return_value = tc['setup']['_is_domain_blocked']
                self.fetcher._is_domain_allowed.return_value = tc['setup']['_is_domain_allowed']
                self.fetcher._is_category_blocked.return_value = tc['setup']['_is_category_blocked']
                self.fetcher.get_email_body.return_value = tc['setup']['get_email_body']

                # Run the processor
                result = process_single_email(self.fetcher, self.msg)

                # Verify results
                self.assertEqual(result, tc['expected']['deletion'])
                self.assertEqual(
                    self.fetcher.stats['categories'][tc['expected']['category']], 
                    1
                )
                self.fetcher.add_label.assert_called_with('test-id-123', tc['expected']['category'])

if __name__ == '__main__':
    unittest.main()
