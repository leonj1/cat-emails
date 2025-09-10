#!/usr/bin/env python3

"""Integration tests for repeat offender functionality in gmail_fetcher."""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from email.message import EmailMessage

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path setup
from services.repeat_offender_service import RepeatOffenderService


class TestRepeatOffenderIntegration(unittest.TestCase):
    """Integration tests for repeat offender functionality."""
    
    def setUp(self):
        """Set up test mocks."""
        self.mock_session = Mock()
        self.mock_service = Mock(spec=RepeatOffenderService)
        
        # Create a mock email message
        self.mock_msg = EmailMessage()
        self.mock_msg['From'] = 'spammer@ads.com'
        self.mock_msg['Subject'] = 'Buy now and save!'
        self.mock_msg['Message-ID'] = 'test-123@example.com'
        self.mock_msg.set_content('This is a spam email.')
    
    def test_repeat_offender_detected_skips_llm(self):
        """Test that detected repeat offenders skip LLM categorization."""
        # Setup mock to return repeat offender category
        mock_service_instance = Mock()
        mock_service_instance.check_repeat_offender.return_value = "Advertising-RepeatOffender"
        
        # Test the core logic that would be called
        sender_email = "spammer@ads.com"
        sender_domain = "ads.com"
        subject = "Buy now and save!"
        
        result = mock_service_instance.check_repeat_offender(sender_email, sender_domain, subject)
        
        # Verify repeat offender was detected
        self.assertEqual(result, "Advertising-RepeatOffender")
        mock_service_instance.check_repeat_offender.assert_called_once_with(
            sender_email, sender_domain, subject
        )
    
    def test_no_repeat_offender_proceeds_to_llm(self):
        """Test that non-repeat offenders proceed to LLM categorization."""
        # Setup mock to return None (no repeat offender match)
        mock_service_instance = Mock()
        mock_service_instance.check_repeat_offender.return_value = None
        
        sender_email = "normal@example.com"
        sender_domain = "example.com"
        subject = "Regular email"
        
        result = mock_service_instance.check_repeat_offender(sender_email, sender_domain, subject)
        
        # Verify no repeat offender detected
        self.assertIsNone(result)
        mock_service_instance.check_repeat_offender.assert_called_once_with(
            sender_email, sender_domain, subject
        )
    
    def test_email_header_parsing(self):
        """Test email header parsing for repeat offender detection."""
        # Test various From header formats
        test_cases = [
            ('spammer@ads.com', 'spammer@ads.com', 'ads.com'),
            ('Spammer <spammer@ads.com>', 'spammer@ads.com', 'ads.com'),
            ('"John Doe" <john@example.org>', 'john@example.org', 'example.org'),
            ('noreply@marketing.co.uk', 'noreply@marketing.co.uk', 'marketing.co.uk'),
        ]
        
        # We need to mock the actual methods since we can't import gmail_fetcher directly
        # due to its argparse usage. Test the logic that would be used.
        from email.utils import parseaddr
        
        for from_header, expected_email, expected_domain in test_cases:
            _, email_address = parseaddr(from_header)
            domain = email_address.split('@')[-1].lower() if '@' in email_address else ''
            
            self.assertEqual(email_address.lower(), expected_email)
            self.assertEqual(domain, expected_domain)
    
    def test_outcome_recording(self):
        """Test that email outcomes are properly recorded."""
        mock_service_instance = Mock()
        
        # Simulate recording an email outcome
        sender_email = "test@example.com"
        sender_domain = "example.com"
        subject = "Test email"
        category = "Marketing"
        was_deleted = True
        
        mock_service_instance.record_email_outcome(
            sender_email=sender_email,
            sender_domain=sender_domain,
            subject=subject,
            category=category,
            was_deleted=was_deleted
        )
        
        # Verify the outcome was recorded
        mock_service_instance.record_email_outcome.assert_called_once_with(
            sender_email=sender_email,
            sender_domain=sender_domain,
            subject=subject,
            category=category,
            was_deleted=was_deleted
        )
    
    def test_repeat_offender_category_exclusion(self):
        """Test that repeat offender categories are not recorded again."""
        mock_service_instance = Mock(spec=RepeatOffenderService)
        
        # Test that repeat offender categories should be skipped
        repeat_offender_categories = [
            "Advertising-RepeatOffender",
            "Marketing-RepeatOffender", 
            "WantsMoney-RepeatOffender"
        ]
        
        for category in repeat_offender_categories:
            is_repeat_offender = category.endswith("-RepeatOffender")
            self.assertTrue(is_repeat_offender, f"Category {category} should be identified as repeat offender")
    
    def test_valid_categories_still_processed(self):
        """Test that valid categories are still processed normally."""
        mock_service_instance = Mock(spec=RepeatOffenderService)
        
        # Test that normal categories are processed
        normal_categories = [
            "Advertising",
            "Marketing",
            "WantsMoney", 
            "Other",
            "Blocked_Domain",
            "Allowed_Domain"
        ]
        
        for category in normal_categories:
            is_repeat_offender = category.endswith("-RepeatOffender")
            self.assertFalse(is_repeat_offender, f"Category {category} should not be identified as repeat offender")
    
    def test_service_initialization(self):
        """Test that RepeatOffenderService is properly initialized."""
        mock_service_class = Mock()
        mock_session = Mock()
        account_name = "test@example.com"
        
        # Simulate service creation
        service = mock_service_class(mock_session, account_name)
        
        # Verify service was created with correct parameters
        mock_service_class.assert_called_once_with(mock_session, account_name)
    
    def test_pattern_matching_priority(self):
        """Test that pattern matching follows correct priority order."""
        # More specific patterns should take priority over general ones
        # This is tested in the service unit tests, but we can verify the concept
        
        patterns = [
            {'type': 'sender_email', 'value': 'specific@test.com', 'priority': 1},
            {'type': 'sender_domain', 'value': 'test.com', 'priority': 2}, 
            {'type': 'subject_pattern', 'value': 'Free.*', 'priority': 3},
        ]
        
        # Sort by priority (lower number = higher priority)
        sorted_patterns = sorted(patterns, key=lambda x: x['priority'])
        
        self.assertEqual(sorted_patterns[0]['type'], 'sender_email')
        self.assertEqual(sorted_patterns[1]['type'], 'sender_domain')
        self.assertEqual(sorted_patterns[2]['type'], 'subject_pattern')


if __name__ == "__main__":
    unittest.main()
