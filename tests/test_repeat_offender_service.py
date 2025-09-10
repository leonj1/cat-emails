#!/usr/bin/env python3

"""Unit tests for RepeatOffenderService."""

import unittest
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import RepeatOffenderPattern, Base
from services.repeat_offender_service import RepeatOffenderService


class TestRepeatOffenderService(unittest.TestCase):
    """Test cases for RepeatOffenderService."""
    
    def setUp(self):
        """Set up test database and service."""
        # Use in-memory SQLite for testing
        self.engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(self.engine)
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.account_name = "test@example.com"
        self.service = RepeatOffenderService(self.session, self.account_name)
    
    def tearDown(self):
        """Clean up test database."""
        self.session.close()
    
    def test_no_repeat_offender_initially(self):
        """Test that no repeat offenders exist initially."""
        result = self.service.check_repeat_offender(
            "test@spam.com", "spam.com", "Test Subject"
        )
        self.assertIsNone(result)
    
    def test_single_email_not_repeat_offender(self):
        """Test that single email doesn't create repeat offender."""
        # Record one deleted email
        self.service.record_email_outcome(
            sender_email="spam@ads.com",
            sender_domain="ads.com",
            subject="Buy now!",
            category="Advertising",
            was_deleted=True
        )
        
        # Should not be repeat offender yet
        result = self.service.check_repeat_offender(
            "spam@ads.com", "ads.com", "Buy now!"
        )
        self.assertIsNone(result)
    
    def test_sender_email_becomes_repeat_offender(self):
        """Test that sender email becomes repeat offender after threshold."""
        sender_email = "spammer@ads.com"
        sender_domain = "ads.com"
        
        # Record 4 deleted emails (above threshold)
        for i in range(4):
            self.service.record_email_outcome(
                sender_email=sender_email,
                sender_domain=sender_domain,
                subject=f"Special Offer #{i}!",
                category="Advertising",
                was_deleted=True
            )
        
        # Should now be repeat offender
        result = self.service.check_repeat_offender(
            sender_email, sender_domain, "Another offer!"
        )
        self.assertEqual(result, "Advertising-RepeatOffender")
    
    def test_sender_domain_becomes_repeat_offender(self):
        """Test that sender domain becomes repeat offender after threshold."""
        domain = "marketing.com"
        
        # Record emails from different senders in same domain
        senders = ["promo@marketing.com", "sales@marketing.com", "deals@marketing.com"]
        
        for i, sender in enumerate(senders):
            self.service.record_email_outcome(
                sender_email=sender,
                sender_domain=domain,
                subject=f"Marketing email #{i}",
                category="Marketing",
                was_deleted=True
            )
        
        # Add one more to exceed threshold
        self.service.record_email_outcome(
            sender_email="info@marketing.com",
            sender_domain=domain,
            subject="Final offer",
            category="Marketing", 
            was_deleted=True
        )
        
        # Should now be repeat offender for domain
        result = self.service.check_repeat_offender(
            "newguy@marketing.com", domain, "New offer"
        )
        self.assertEqual(result, "Marketing-RepeatOffender")
    
    def test_mixed_outcomes_no_repeat_offender(self):
        """Test that mixed deletion outcomes don't create repeat offender."""
        sender_email = "mixed@test.com"
        
        # 2 deleted, 2 kept (50% deletion rate, below 80% threshold)
        for i in range(2):
            self.service.record_email_outcome(
                sender_email=sender_email,
                sender_domain="test.com",
                subject=f"Email {i}",
                category="Marketing",
                was_deleted=True
            )
        
        for i in range(2, 4):
            self.service.record_email_outcome(
                sender_email=sender_email,
                sender_domain="test.com",
                subject=f"Email {i}",
                category="Marketing",
                was_deleted=False
            )
        
        # Should not be repeat offender (50% < 80% threshold)
        result = self.service.check_repeat_offender(
            sender_email, "test.com", "New email"
        )
        self.assertIsNone(result)
    
    def test_subject_pattern_detection(self):
        """Test that subject patterns are detected as repeat offenders."""
        # Create multiple emails with 'free' promotional pattern
        subjects = ["Free money!", "Free vacation!", "Free gift!", "Free trial!"]
        
        for i, subject in enumerate(subjects):
            self.service.record_email_outcome(
                sender_email=f"sender{i}@random.com",
                sender_domain="random.com",
                subject=subject,
                category="WantsMoney",
                was_deleted=True
            )
        
        # Test if similar subject pattern is detected
        result = self.service.check_repeat_offender(
            "new@somewhere.com", "somewhere.com", "Free offer now!"
        )
        self.assertEqual(result, "WantsMoney-RepeatOffender")
    
    def test_skip_repeat_offender_category_recording(self):
        """Test that repeat offender categories are not recorded again."""
        # This should not create new patterns
        self.service.record_email_outcome(
            sender_email="test@example.com",
            sender_domain="example.com",
            subject="Test",
            category="Marketing-RepeatOffender",  # Already repeat offender
            was_deleted=True
        )
        
        # Verify no patterns were created
        patterns = self.session.query(RepeatOffenderPattern).all()
        self.assertEqual(len(patterns), 0)
    
    def test_confidence_score_calculation(self):
        """Test that confidence scores are calculated correctly."""
        sender_email = "test@example.com"
        
        # 3 deleted, 1 kept = 75% confidence
        for i in range(3):
            self.service.record_email_outcome(
                sender_email=sender_email,
                sender_domain="example.com",
                subject=f"Email {i}",
                category="Marketing",
                was_deleted=True
            )
        
        self.service.record_email_outcome(
            sender_email=sender_email,
            sender_domain="example.com",
            subject="Email kept",
            category="Marketing",
            was_deleted=False
        )
        
        # Check confidence score
        pattern = self.session.query(RepeatOffenderPattern).filter(
            RepeatOffenderPattern.sender_email == sender_email
        ).first()
        
        self.assertIsNotNone(pattern)
        self.assertEqual(pattern.confidence_score, 0.75)  # 3/4 = 75%
    
    def test_get_stats(self):
        """Test getting repeat offender statistics."""
        # Create some patterns
        self.service.record_email_outcome(
            sender_email="spam1@test.com",
            sender_domain="test.com",
            subject="Spam email",
            category="Advertising",
            was_deleted=True
        )
        
        # Get initial stats (should be empty since no repeat offenders yet)
        stats = self.service.get_repeat_offender_stats()
        self.assertEqual(stats['total_patterns'], 0)
        
        # Create enough to become repeat offender
        for i in range(3):
            self.service.record_email_outcome(
                sender_email="spam2@test.com",
                sender_domain="test.com", 
                subject=f"More spam {i}",
                category="Advertising",
                was_deleted=True
            )
        
        # Now should have repeat offender stats
        stats = self.service.get_repeat_offender_stats()
        self.assertGreater(stats['total_patterns'], 0)
    
    def test_pattern_ordering_priority(self):
        """Test that more specific patterns are matched first."""
        sender_email = "specific@test.com"
        sender_domain = "test.com"
        
        # Create domain-level pattern
        for i in range(4):
            self.service.record_email_outcome(
                sender_email=f"user{i}@test.com",
                sender_domain=sender_domain,
                subject=f"Domain email {i}",
                category="Marketing",
                was_deleted=True
            )
        
        # Create more specific sender email pattern with different category
        for i in range(4):
            self.service.record_email_outcome(
                sender_email=sender_email,
                sender_domain=sender_domain,
                subject=f"Specific email {i}",
                category="Advertising",  # Different category
                was_deleted=True
            )
        
        # Should match the more specific sender email pattern
        result = self.service.check_repeat_offender(
            sender_email, sender_domain, "New email"
        )
        self.assertEqual(result, "Advertising-RepeatOffender")
    
    def test_lookback_days_filter(self):
        """Test that old patterns are not considered."""
        sender_email = "old@test.com"
        
        # Create pattern with old timestamps
        old_date = datetime.now() - timedelta(days=35)  # Beyond 30-day lookback
        
        pattern = RepeatOffenderPattern(
            account_name=self.account_name,
            sender_email=sender_email,
            category="Advertising",
            total_occurrences=5,
            deletion_count=5,
            confidence_score=1.0,
            first_seen=old_date,
            last_seen=old_date,
            marked_as_repeat_offender=old_date,
            is_active=True
        )
        self.session.add(pattern)
        self.session.commit()
        
        # Should not match due to old last_seen date
        result = self.service.check_repeat_offender(
            sender_email, "test.com", "New email"
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
