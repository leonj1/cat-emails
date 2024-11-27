import unittest
from unittest.mock import Mock, patch
from email_processor import process_single_email
from email_scanner_consumer import categorize_email_ell_marketing, categorize_email_ell_marketing2

class TestProcessSingleEmail(unittest.TestCase):
    def setUp(self):
        self.fetcher = Mock()
        self.fetcher.stats = {'categories': Mock(dict)}
        self.fetcher.stats['categories'].__getitem__ = lambda _, x: 0
        self.fetcher.stats['categories'].__setitem__ = lambda _, x, y: None
        self.msg = Mock()

    @patch('email_scanner_consumer.categorize_email_ell_marketing')
    @patch('email_scanner_consumer.categorize_email_ell_marketing2')
    def test_process_single_email_table_driven(self, mock_cat2, mock_cat1):
        test_cases = [
            # Test case structure:
            # (name, from_header, is_blocked_domain, is_allowed_domain, 
            #  cat1_result, cat2_result, is_cat_blocked, expected_deletion)
            (
                "blocked_domain",
                "user@blocked.com",
                True,   # is_blocked_domain
                False,  # is_allowed_domain
                None,   # cat1 not called
                None,   # cat2 not called
                False,  # is_cat_blocked not called
                True    # expected deletion
            ),
            (
                "allowed_domain",
                "user@allowed.com",
                False,  # is_blocked_domain
                True,   # is_allowed_domain
                None,   # cat1 not called
                None,   # cat2 not called
                False,  # is_cat_blocked not called
                False   # expected deletion
            ),
            (
                "normal_categorization",
                "user@example.com",
                False,  # is_blocked_domain
                False,  # is_allowed_domain
                "Newsletter",  # cat1 result
                None,    # cat2 not called
                False,   # is_cat_blocked
                False    # expected deletion
            ),
            (
                "blocked_category",
                "user@example.com",
                False,  # is_blocked_domain
                False,  # is_allowed_domain
                "Spam",  # cat1 result
                None,    # cat2 not called
                True,    # is_cat_blocked
                True     # expected deletion
            ),
            (
                "long_category_not_blocked",
                "user@example.com",
                False,  # is_blocked_domain
                False,  # is_allowed_domain
                "This is a very long category name that exceeds thirty chars",  # cat1 result
                "Short",  # cat2 result
                False,    # is_cat_blocked
                False     # expected deletion
            ),
            (
                "long_category_blocked",
                "user@example.com",
                False,  # is_blocked_domain
                False,  # is_allowed_domain
                "This is a very long category name that exceeds thirty chars",  # cat1 result
                "Blocked",  # cat2 result
                True,      # is_cat_blocked
                True       # expected deletion
            ),
        ]

        for name, from_header, is_blocked, is_allowed, cat1, cat2, cat_blocked, expected in test_cases:
            with self.subTest(name=name):
                # Reset mocks
                self.fetcher.reset_mock()
                mock_cat1.reset_mock()
                mock_cat2.reset_mock()
                
                # Setup message
                self.msg.get.side_effect = lambda x, default='': {
                    'From': from_header,
                    'Subject': 'Test Subject',
                    'Message-ID': 'test-id'
                }.get(x, default)

                # Setup fetcher behavior
                self.fetcher._is_domain_blocked.return_value = is_blocked
                self.fetcher._is_domain_allowed.return_value = is_allowed
                self.fetcher._is_category_blocked.return_value = cat_blocked
                self.fetcher.get_email_body.return_value = "Test body"
                self.fetcher.remove_http_links.return_value = "Clean body"
                self.fetcher.remove_images_from_email.return_value = "Clean body"
                self.fetcher.remove_encoded_content.return_value = "Clean body"

                # Setup categorization mocks
                if cat1:
                    mock_cat1.return_value = cat1
                if cat2:
                    mock_cat2.return_value = cat2

                # Run the function
                result = process_single_email(self.fetcher, self.msg)

                # Assertions
                self.assertEqual(result, expected, f"Test case '{name}' failed: expected deletion={expected}")

                # Verify domain checks
                self.fetcher._is_domain_blocked.assert_called_once_with(from_header)
                if not is_blocked:
                    self.fetcher._is_domain_allowed.assert_called_once_with(from_header)

                # Verify categorization calls
                if not (is_blocked or is_allowed):
                    mock_cat1.assert_called_once()
                    if cat1 and len(cat1) > 30:
                        mock_cat2.assert_called_once()
                    else:
                        mock_cat2.assert_not_called()

                # Verify label was added
                self.fetcher.add_label.assert_called_once()

if __name__ == '__main__':
    unittest.main()
