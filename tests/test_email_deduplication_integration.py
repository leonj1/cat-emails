#!/usr/bin/env python3

"""
Integration tests for EmailDeduplicationService with real SQLite persistence.

These tests verify that email deduplication works correctly with actual
database operations, container restarts, and persistence scenarios.
"""

import unittest
import sys
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Base, ProcessedEmailLog
from services.email_deduplication_service import EmailDeduplicationService


class TestEmailDeduplicationIntegration(unittest.TestCase):
    """Integration tests with real SQLite database persistence."""
    
    def setUp(self):
        """Set up test database and service."""
        # Create temporary directory for test database
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_deduplication.db")
        
        # Create database engine and session
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Test data
        self.test_account = "test@example.com"
        self.service = EmailDeduplicationService(self.session, self.test_account)
        
        # Sample email data
        self.sample_emails = [
            {
                'Message-ID': 'email-1@example.com',
                'Subject': 'Test Email 1',
                'From': 'sender1@example.com'
            },
            {
                'Message-ID': 'email-2@example.com',
                'Subject': 'Test Email 2',
                'From': 'sender2@example.com'
            },
            {
                'Message-ID': 'email-3@example.com',
                'Subject': 'Test Email 3',
                'From': 'sender3@example.com'
            }
        ]
    
    def tearDown(self):
        """Clean up test database."""
        self.session.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_basic_deduplication_cycle(self):
        """Test complete deduplication cycle: check -> process -> mark -> verify."""
        message_id = "test-message-123@example.com"
        
        # Step 1: Initially not processed
        self.assertFalse(self.service.is_email_processed(message_id))
        
        # Step 2: Mark as processed
        result = self.service.mark_email_as_processed(message_id)
        self.assertTrue(result)
        
        # Step 3: Should now be detected as processed
        self.assertTrue(self.service.is_email_processed(message_id))
        
        # Step 4: Verify database persistence
        self.assertEqual(self.service.get_processed_count(), 1)
    
    def test_filter_new_emails_functionality(self):
        """Test filtering emails to exclude already processed ones."""
        # Initially all emails should be new
        new_emails = self.service.filter_new_emails(self.sample_emails)
        self.assertEqual(len(new_emails), 3)
        
        # Mark one email as processed
        self.service.mark_email_as_processed('email-1@example.com')
        
        # Should now filter out the processed email
        new_emails = self.service.filter_new_emails(self.sample_emails)
        self.assertEqual(len(new_emails), 2)
        
        # Verify correct emails remain
        remaining_ids = {email['Message-ID'] for email in new_emails}
        expected_ids = {'email-2@example.com', 'email-3@example.com'}
        self.assertEqual(remaining_ids, expected_ids)
    
    def test_database_persistence_across_service_instances(self):
        """Test that processed emails persist across service restarts."""
        message_id = "persistent-test@example.com"
        
        # Service instance 1: Mark email as processed
        self.service.mark_email_as_processed(message_id)
        self.assertTrue(self.service.is_email_processed(message_id))
        
        # "Restart" - create new service instance with same database
        new_session = sessionmaker(bind=self.engine)()
        new_service = EmailDeduplicationService(new_session, self.test_account)
        
        # Should still be marked as processed
        self.assertTrue(new_service.is_email_processed(message_id))
        
        # Verify counts match
        self.assertEqual(new_service.get_processed_count(), 1)
        
        new_session.close()
    
    def test_container_rebuild_simulation(self):
        """Simulate Docker container rebuild with persistent volume."""
        # Phase 1: Initial processing
        initial_emails = self.sample_emails[:2]  # Process 2 emails
        
        for email in initial_emails:
            self.service.mark_email_as_processed(email['Message-ID'])
        
        # Verify initial state
        self.assertEqual(self.service.get_processed_count(), 2)
        
        # Phase 2: "Container rebuild" - new engine, same database file
        new_engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        new_session = sessionmaker(bind=new_engine)()
        new_service = EmailDeduplicationService(new_session, self.test_account)
        
        # Should remember previously processed emails
        self.assertEqual(new_service.get_processed_count(), 2)
        
        # New emails should be detected correctly
        all_emails_after_restart = self.sample_emails
        new_emails = new_service.filter_new_emails(all_emails_after_restart)
        
        # Should only have 1 new email (the 3rd one)
        self.assertEqual(len(new_emails), 1)
        self.assertEqual(new_emails[0]['Message-ID'], 'email-3@example.com')
        
        new_session.close()
    
    def test_bulk_processing_performance(self):
        """Test bulk marking for better performance."""
        message_ids = [f"bulk-email-{i}@example.com" for i in range(100)]
        
        # Bulk mark as processed
        successful, errors = self.service.bulk_mark_as_processed(message_ids)
        
        # Verify results
        self.assertEqual(successful, 100)
        self.assertEqual(errors, 0)
        self.assertEqual(self.service.get_processed_count(), 100)
        
        # Verify individual lookups work
        self.assertTrue(self.service.is_email_processed("bulk-email-50@example.com"))
        self.assertFalse(self.service.is_email_processed("non-bulk-email@example.com"))
    
    def test_different_accounts_isolation(self):
        """Test that different accounts don't interfere with each other."""
        account1 = "user1@example.com"
        account2 = "user2@example.com"
        shared_message_id = "shared-message@example.com"
        
        # Create services for different accounts
        service1 = EmailDeduplicationService(self.session, account1)
        service2 = EmailDeduplicationService(self.session, account2)
        
        # Mark email as processed for account1 only
        service1.mark_email_as_processed(shared_message_id)
        
        # Account1 should see it as processed, account2 should not
        self.assertTrue(service1.is_email_processed(shared_message_id))
        self.assertFalse(service2.is_email_processed(shared_message_id))
        
        # Counts should be separate
        self.assertEqual(service1.get_processed_count(), 1)
        self.assertEqual(service2.get_processed_count(), 0)
    
    def test_error_handling_and_recovery(self):
        """Test error handling with invalid data."""
        # Test empty message IDs
        self.assertFalse(self.service.is_email_processed(""))
        self.assertFalse(self.service.is_email_processed(None))
        self.assertFalse(self.service.mark_email_as_processed(""))
        
        # Test whitespace-only message IDs
        self.assertFalse(self.service.is_email_processed("   "))
        self.assertFalse(self.service.mark_email_as_processed("   "))
        
        # Verify stats track errors
        stats = self.service.get_stats()
        self.assertGreater(stats['errors'], 0)
    
    def test_duplicate_marking_idempotency(self):
        """Test that marking same email multiple times is safe."""
        message_id = "duplicate-test@example.com"
        
        # Mark same email multiple times
        result1 = self.service.mark_email_as_processed(message_id)
        result2 = self.service.mark_email_as_processed(message_id)
        result3 = self.service.mark_email_as_processed(message_id)
        
        # All should succeed (idempotent)
        self.assertTrue(result1)
        self.assertTrue(result2)
        self.assertTrue(result3)
        
        # Should only have one record in database
        direct_count = self.session.query(ProcessedEmailLog).filter_by(
            account_email=self.test_account,
            message_id=message_id
        ).count()
        self.assertEqual(direct_count, 1)
    
    def test_statistics_tracking(self):
        """Test that service tracks statistics correctly."""
        # Process some emails
        test_emails = self.sample_emails
        
        # Check some emails (mix of processed and new)
        self.service.mark_email_as_processed(test_emails[0]['Message-ID'])
        
        new_emails = self.service.filter_new_emails(test_emails)
        
        # Verify stats
        stats = self.service.get_stats()
        self.assertEqual(stats['checked'], 3)  # Checked all 3 emails
        self.assertEqual(stats['duplicates_found'], 1)  # Found 1 already processed
        self.assertEqual(stats['new_emails'], 2)  # 2 were new
        self.assertGreaterEqual(stats['logged'], 1)  # At least 1 logged
    
    def test_cleanup_functionality(self):
        """Test cleanup of old processed email records."""
        # Create old and recent records
        old_date = datetime.utcnow() - timedelta(days=95)
        recent_date = datetime.utcnow() - timedelta(days=5)
        
        # Add records manually with specific dates
        old_record = ProcessedEmailLog(
            account_email=self.test_account,
            message_id="old-email@example.com",
            processed_at=old_date
        )
        recent_record = ProcessedEmailLog(
            account_email=self.test_account,
            message_id="recent-email@example.com",
            processed_at=recent_date
        )
        
        self.session.add_all([old_record, recent_record])
        self.session.commit()
        
        # Verify both exist
        self.assertEqual(self.service.get_processed_count(), 2)
        
        # Cleanup records older than 90 days
        deleted = self.service.cleanup_old_records(days_to_keep=90)
        
        # Should have deleted 1 old record
        self.assertEqual(deleted, 1)
        self.assertEqual(self.service.get_processed_count(), 1)
        
        # Recent record should still exist
        self.assertTrue(self.service.is_email_processed("recent-email@example.com"))
        self.assertFalse(self.service.is_email_processed("old-email@example.com"))
    
    def test_real_world_gmail_scenario(self):
        """Test realistic Gmail processing scenario."""
        # Simulate first run with 10 emails
        first_batch = [
            {'Message-ID': f'gmail-msg-{i}@gmail.com', 'Subject': f'Email {i}'}
            for i in range(1, 11)
        ]
        
        # Process first batch
        new_emails_first = self.service.filter_new_emails(first_batch)
        self.assertEqual(len(new_emails_first), 10)  # All new
        
        # Mark them as processed
        message_ids = [email['Message-ID'] for email in new_emails_first]
        successful, errors = self.service.bulk_mark_as_processed(message_ids)
        self.assertEqual(successful, 10)
        self.assertEqual(errors, 0)
        
        # Simulate container restart with overlapping emails (7 old + 5 new)
        second_batch = [
            {'Message-ID': f'gmail-msg-{i}@gmail.com', 'Subject': f'Email {i}'}
            for i in range(6, 16)  # Messages 6-15 (overlaps with 6-10)
        ]
        
        # Create new service instance to simulate restart
        new_session = sessionmaker(bind=self.engine)()
        restart_service = EmailDeduplicationService(new_session, self.test_account)
        
        # Filter should only return the 5 truly new emails (11-15)
        new_emails_second = restart_service.filter_new_emails(second_batch)
        self.assertEqual(len(new_emails_second), 5)
        
        # Verify correct emails were filtered
        new_message_ids = {email['Message-ID'] for email in new_emails_second}
        expected_new_ids = {f'gmail-msg-{i}@gmail.com' for i in range(11, 16)}
        self.assertEqual(new_message_ids, expected_new_ids)
        
        new_session.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
