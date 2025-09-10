#!/usr/bin/env python3

"""Tests for email processing deduplication and persistence."""

import unittest
import sys
import os
import tempfile
import shutil
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Base, ProcessedEmailLog
from services.database_service import DatabaseService
from services.email_summary_service import EmailSummaryService


class TestProcessedEmailTracking(unittest.TestCase):
    """Test processed email deduplication and persistence."""
    
    def setUp(self):
        """Set up test database."""
        # Create temporary directory for test database
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_summaries.db")
        
        # Initialize database service
        self.db_service = DatabaseService(db_path=self.db_path)
        
        # Test data
        self.test_account = "test@example.com"
        self.test_message_id = "test-message-123@example.com"
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_database_path_configuration(self):
        """Test that database path is correctly configured."""
        # Test default path
        default_service = DatabaseService()
        self.assertTrue(default_service.db_path.endswith("summaries.db"))
        
        # Test custom path
        custom_path = "/custom/path/test.db"
        custom_service = DatabaseService(db_path=custom_path)
        self.assertEqual(custom_service.db_path, custom_path)
        
        # Test environment variable
        os.environ["DATABASE_PATH"] = "/env/path/test.db"
        try:
            env_service = DatabaseService()
            self.assertEqual(env_service.db_path, "/env/path/test.db")
        finally:
            del os.environ["DATABASE_PATH"]
    
    def test_log_processed_email(self):
        """Test logging processed emails."""
        # Initially not processed
        self.assertFalse(
            self.db_service.is_message_processed(self.test_account, self.test_message_id)
        )
        
        # Log as processed
        self.db_service.log_processed_email(self.test_account, self.test_message_id)
        
        # Should now be processed
        self.assertTrue(
            self.db_service.is_message_processed(self.test_account, self.test_message_id)
        )
    
    def test_duplicate_processing_prevention(self):
        """Test that duplicate processing is prevented."""
        # Log same message twice - should not raise error
        self.db_service.log_processed_email(self.test_account, self.test_message_id)
        self.db_service.log_processed_email(self.test_account, self.test_message_id)
        
        # Should still be marked as processed
        self.assertTrue(
            self.db_service.is_message_processed(self.test_account, self.test_message_id)
        )
        
        # Check only one record exists
        with self.db_service.Session() as session:
            count = session.query(ProcessedEmailLog).filter_by(
                account_email=self.test_account,
                message_id=self.test_message_id
            ).count()
            self.assertEqual(count, 1)
    
    def test_different_accounts_separate_tracking(self):
        """Test that different accounts track messages separately."""
        account1 = "user1@example.com"
        account2 = "user2@example.com"
        same_message_id = "shared-message@example.com"
        
        # Log for account1 only
        self.db_service.log_processed_email(account1, same_message_id)
        
        # Account1 should show processed, account2 should not
        self.assertTrue(self.db_service.is_message_processed(account1, same_message_id))
        self.assertFalse(self.db_service.is_message_processed(account2, same_message_id))
    
    def test_empty_inputs_handling(self):
        """Test handling of empty/None inputs."""
        # Empty inputs should not cause errors and return False
        self.assertFalse(self.db_service.is_message_processed("", self.test_message_id))
        self.assertFalse(self.db_service.is_message_processed(self.test_account, ""))
        self.assertFalse(self.db_service.is_message_processed(None, self.test_message_id))
        self.assertFalse(self.db_service.is_message_processed(self.test_account, None))
        
        # Log with empty inputs should not do anything
        self.db_service.log_processed_email("", self.test_message_id)
        self.db_service.log_processed_email(self.test_account, "")
        
        # Should not create any records
        with self.db_service.Session() as session:
            count = session.query(ProcessedEmailLog).count()
            self.assertEqual(count, 0)
    
    def test_database_persistence_across_sessions(self):
        """Test that processed emails persist across database service instances."""
        # Log with first service instance
        self.db_service.log_processed_email(self.test_account, self.test_message_id)
        
        # Create new service instance pointing to same database
        new_service = DatabaseService(db_path=self.db_path)
        
        # Should still be processed
        self.assertTrue(
            new_service.is_message_processed(self.test_account, self.test_message_id)
        )
    
    def test_email_summary_service_database_integration(self):
        """Test that EmailSummaryService properly uses database for tracking."""
        # Create EmailSummaryService with custom database path
        email_service = EmailSummaryService(
            data_dir=self.test_dir, 
            use_database=True
        )
        
        # Verify database service is initialized
        self.assertIsNotNone(email_service.db_service)
        
        # Test that it can track processed emails
        email_service.db_service.log_processed_email(self.test_account, self.test_message_id)
        
        self.assertTrue(
            email_service.db_service.is_message_processed(self.test_account, self.test_message_id)
        )
    
    def test_database_file_location_persistence(self):
        """Test that the database file actually exists and persists."""
        # Check database file exists
        self.assertTrue(os.path.exists(self.db_path))
        
        # Log a processed email
        self.db_service.log_processed_email(self.test_account, self.test_message_id)
        
        # File should still exist and have data
        self.assertTrue(os.path.exists(self.db_path))
        self.assertGreater(os.path.getsize(self.db_path), 0)
        
        # Test with direct SQLite connection to verify data
        engine = create_engine(f'sqlite:///{self.db_path}')
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            record = session.query(ProcessedEmailLog).filter_by(
                account_email=self.test_account,
                message_id=self.test_message_id
            ).first()
            self.assertIsNotNone(record)
            self.assertEqual(record.account_email, self.test_account)
            self.assertEqual(record.message_id, self.test_message_id)
    
    def test_docker_volume_simulation(self):
        """Simulate Docker container restart scenario."""
        # Phase 1: Initial processing (simulating first container run)
        self.db_service.log_processed_email(self.test_account, self.test_message_id)
        self.assertTrue(
            self.db_service.is_message_processed(self.test_account, self.test_message_id)
        )
        
        # Phase 2: Container "restart" (new service instance, same database file)
        # This simulates what happens when Docker container restarts with persistent volume
        new_service = DatabaseService(db_path=self.db_path)
        
        # Should still remember processed emails
        self.assertTrue(
            new_service.is_message_processed(self.test_account, self.test_message_id)
        )
        
        # Add new message in "restarted" container
        new_message_id = "new-message-456@example.com"
        new_service.log_processed_email(self.test_account, new_message_id)
        
        # Both old and new should be tracked
        self.assertTrue(
            new_service.is_message_processed(self.test_account, self.test_message_id)
        )
        self.assertTrue(
            new_service.is_message_processed(self.test_account, new_message_id)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
