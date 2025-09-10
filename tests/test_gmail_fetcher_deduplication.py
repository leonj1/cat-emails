#!/usr/bin/env python3

"""
Tests for email deduplication integration in gmail_fetcher.py

These tests verify that the gmail_fetcher properly uses EmailDeduplicationService
and that the integration works correctly for preventing duplicate processing.
"""

import unittest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Base
from services.email_deduplication_service import EmailDeduplicationService
from services.database_service import DatabaseService


class TestGmailFetcherDeduplication(unittest.TestCase):
    """Test gmail_fetcher integration with EmailDeduplicationService."""
    
    def setUp(self):
        """Set up test database and mocks."""
        # Create temporary database
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")
        
        # Create real database for integration testing
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        
        # Create sample email data
        self.sample_emails = [
            {
                'Message-ID': 'msg-1@example.com',
                'Subject': 'Test Email 1',
                'From': 'sender1@test.com',
                'body': 'Email content 1'
            },
            {
                'Message-ID': 'msg-2@example.com',
                'Subject': 'Test Email 2',
                'From': 'sender2@test.com',
                'body': 'Email content 2'
            },
            {
                'Message-ID': 'msg-3@example.com',
                'Subject': 'Test Email 3',
                'From': 'sender3@test.com',
                'body': 'Email content 3'
            }
        ]
        
        self.test_account = "test@gmail.com"
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_deduplication_service_integration(self):
        """Test that EmailDeduplicationService integrates correctly with database."""
        # Create database service
        db_service = DatabaseService(db_path=self.db_path)
        
        # Test the integration path used by gmail_fetcher
        with db_service.Session() as session:
            dedup_service = EmailDeduplicationService(session, self.test_account)
            
            # Filter emails (should all be new initially)
            new_emails = dedup_service.filter_new_emails(self.sample_emails)
            self.assertEqual(len(new_emails), 3)
            
            # Mark one as processed
            success = dedup_service.mark_email_as_processed('msg-1@example.com')
            self.assertTrue(success)
            
            # Filter again (should have 2 new emails)
            new_emails_second = dedup_service.filter_new_emails(self.sample_emails)
            self.assertEqual(len(new_emails_second), 2)
            
            # Verify stats
            stats = dedup_service.get_stats()
            self.assertEqual(stats['checked'], 6)  # 3 + 3 checks
            self.assertEqual(stats['duplicates_found'], 1)  # 1 duplicate found
            self.assertEqual(stats['logged'], 1)  # 1 email logged
    
    @patch('gmail_fetcher.ServiceGmailFetcher')
    @patch('gmail_fetcher.DomainService')
    @patch('gmail_fetcher.categorize_email_with_resilient_client')
    def test_gmail_fetcher_deduplication_flow(self, mock_categorize, mock_domain_service, mock_fetcher_class):
        """Test the actual deduplication flow in gmail_fetcher main function."""
        
        # Create real database service
        db_service = DatabaseService(db_path=self.db_path)
        
        # Set up fetcher mock
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher
        
        # Set up summary service with our real database
        mock_summary_service = Mock()
        mock_summary_service.db_service = db_service
        mock_fetcher.summary_service = mock_summary_service
        
        # Set up other required mocks
        mock_fetcher.connect.return_value = None
        mock_fetcher.get_recent_emails.return_value = self.sample_emails
        mock_fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': {}}
        
        # Domain service mock
        mock_domain_service.return_value.fetch_allowed_domains.return_value = []
        
        # Categorization mock
        mock_categorize.return_value = "Other"
        
        # Mock other required methods
        mock_fetcher.get_email_body.return_value = "Test body"
        mock_fetcher._extract_domain.return_value = "test.com"
        mock_fetcher._is_domain_blocked.return_value = False
        mock_fetcher._is_domain_allowed.return_value = False
        mock_fetcher._is_category_blocked.return_value = False
        mock_fetcher.add_label.return_value = None
        mock_fetcher.delete_email.return_value = False  # Don't delete in test
        
        # Test first run - should process all emails
        with patch('gmail_fetcher.tabulate'):  # Mock tabulate to avoid import error
            try:
                # Mock sys.argv to avoid argparse issues
                original_argv = sys.argv
                sys.argv = ['gmail_fetcher.py']
                
                from gmail_fetcher import main
                
                # First run
                main(
                    email_address=self.test_account,
                    app_password="fake_password",
                    api_token="fake_token", 
                    hours=1
                )
                
                # Verify all emails were processed
                with db_service.Session() as session:
                    dedup_service = EmailDeduplicationService(session, self.test_account)
                    processed_count = dedup_service.get_processed_count()
                    self.assertEqual(processed_count, 3)
                
                # Reset mocks for second run
                mock_fetcher.reset_mock()
                mock_fetcher.summary_service = mock_summary_service
                mock_fetcher.connect.return_value = None
                mock_fetcher.get_recent_emails.return_value = self.sample_emails  # Same emails
                mock_fetcher.stats = {'deleted': 0, 'kept': 0, 'categories': {}}
                
                # Second run - should process no emails (all duplicates)
                main(
                    email_address=self.test_account,
                    app_password="fake_password",
                    api_token="fake_token",
                    hours=1
                )
                
                # Verify deduplication worked - no additional processing should have occurred
                # The get_email_body should not have been called since no new emails
                with db_service.Session() as session:
                    dedup_service = EmailDeduplicationService(session, self.test_account)
                    final_count = dedup_service.get_processed_count()
                    self.assertEqual(final_count, 3)  # Still same count
                
            except ImportError:
                self.skipTest("Cannot import gmail_fetcher due to missing dependencies")
            finally:
                sys.argv = original_argv
    
    def test_bulk_processing_scenario(self):
        """Test bulk email processing and deduplication."""
        # Create large batch of emails
        bulk_emails = [
            {
                'Message-ID': f'bulk-msg-{i}@example.com',
                'Subject': f'Bulk Email {i}',
                'From': f'sender{i}@test.com'
            }
            for i in range(50)
        ]
        
        db_service = DatabaseService(db_path=self.db_path)
        
        with db_service.Session() as session:
            dedup_service = EmailDeduplicationService(session, self.test_account)
            
            # First batch - all should be new
            new_emails_1 = dedup_service.filter_new_emails(bulk_emails)
            self.assertEqual(len(new_emails_1), 50)
            
            # Mark them as processed in bulk
            message_ids = [email['Message-ID'] for email in new_emails_1]
            successful, errors = dedup_service.bulk_mark_as_processed(message_ids)
            self.assertEqual(successful, 50)
            self.assertEqual(errors, 0)
            
            # Second batch with overlap (30 old + 20 new)
            overlapping_batch = bulk_emails[30:] + [
                {
                    'Message-ID': f'new-msg-{i}@example.com',
                    'Subject': f'New Email {i}',
                    'From': f'newsender{i}@test.com'
                }
                for i in range(20)
            ]
            
            new_emails_2 = dedup_service.filter_new_emails(overlapping_batch)
            self.assertEqual(len(new_emails_2), 20)  # Only the 20 new ones
            
            # Verify the correct emails were filtered out
            new_message_ids = {email['Message-ID'] for email in new_emails_2}
            expected_new_ids = {f'new-msg-{i}@example.com' for i in range(20)}
            self.assertEqual(new_message_ids, expected_new_ids)
    
    def test_error_handling_in_deduplication(self):
        """Test error handling when deduplication service fails."""
        # Test with corrupted database path
        bad_db_service = DatabaseService(db_path="/invalid/path/db.sqlite")
        
        with self.assertLogs(level='WARNING') as log:
            try:
                with bad_db_service.Session() as session:
                    dedup_service = EmailDeduplicationService(session, self.test_account)
                    # This might fail due to bad database path
                    new_emails = dedup_service.filter_new_emails(self.sample_emails)
            except Exception:
                # Expected to fail with bad path
                pass
        
        # Should have logged warnings about database issues
        self.assertTrue(any('error' in record.message.lower() for record in log.records))
    
    def test_message_id_edge_cases(self):
        """Test edge cases with Message-ID handling."""
        edge_case_emails = [
            {'Message-ID': '', 'Subject': 'Empty ID'},  # Empty ID
            {'Message-ID': '   ', 'Subject': 'Whitespace ID'},  # Whitespace only
            {'Message-ID': None, 'Subject': 'None ID'},  # None
            {'Subject': 'Missing ID'},  # Missing Message-ID key
            {'Message-ID': 'normal-id@example.com', 'Subject': 'Normal'},  # Normal
        ]
        
        db_service = DatabaseService(db_path=self.db_path)
        
        with db_service.Session() as session:
            dedup_service = EmailDeduplicationService(session, self.test_account)
            
            # Should handle all edge cases gracefully
            new_emails = dedup_service.filter_new_emails(edge_case_emails)
            
            # Should have 5 emails (including problematic ones treated as new)
            self.assertEqual(len(new_emails), 5)
            
            # Stats should reflect the issues
            stats = dedup_service.get_stats()
            self.assertGreater(stats['errors'], 0)  # Should have recorded errors


if __name__ == "__main__":
    unittest.main(verbosity=2)
