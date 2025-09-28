#!/usr/bin/env python3

"""Test script for repeat offender functionality."""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
sys.path.insert(0, os.path.abspath('.'))

from models.database import RepeatOffenderPattern, Base
from services.repeat_offender_service import RepeatOffenderService


def test_repeat_offender_service():
    """Test the repeat offender service functionality."""
    
    # Use in-memory SQLite for testing
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create service instance
    service = RepeatOffenderService(session, "test@example.com")
    
    print("Testing Repeat Offender Service")
    print("=" * 50)
    
    # Test 1: Record multiple emails from same sender with deletion
    print("\n1. Recording emails from spammer@ads.com (should become repeat offender)")
    
    for i in range(4):  # 4 emails, all deleted
        service.record_email_outcome(
            sender_email="spammer@ads.com",
            sender_domain="ads.com", 
            subject=f"Special Offer #{i}!",
            category="Advertising",
            was_deleted=True
        )
        print(f"   Recorded email #{i+1} - deleted")
    
    # Check if it became a repeat offender
    result = service.check_repeat_offender("spammer@ads.com", "ads.com", "Special Offer #5!")
    print(f"   Check result: {result}")
    
    # Test 2: Record emails from domain with mixed results
    print("\n2. Recording emails from marketing.com domain (mixed results)")
    
    # 2 deleted, 1 kept - should not be repeat offender yet
    for i in range(2):
        service.record_email_outcome(
            sender_email="promo@marketing.com",
            sender_domain="marketing.com",
            subject="Buy now!",
            category="Marketing", 
            was_deleted=True
        )
        print(f"   Recorded email #{i+1} from promo@marketing.com - deleted")
    
    service.record_email_outcome(
        sender_email="info@marketing.com",
        sender_domain="marketing.com",
        subject="Newsletter",
        category="Marketing",
        was_deleted=False
    )
    print("   Recorded email from info@marketing.com - kept")
    
    result = service.check_repeat_offender("sales@marketing.com", "marketing.com", "New offer")
    print(f"   Check result for marketing.com domain: {result}")
    
    # Test 3: Add more deleted emails to push over threshold
    print("\n3. Adding more deleted emails from marketing.com")
    
    for i in range(3):  # 3 more deleted emails
        service.record_email_outcome(
            sender_email=f"sales{i}@marketing.com",
            sender_domain="marketing.com",
            subject="Limited time offer!",
            category="Marketing",
            was_deleted=True
        )
        print(f"   Recorded email #{i+1} from sales{i}@marketing.com - deleted")
    
    result = service.check_repeat_offender("newguy@marketing.com", "marketing.com", "Another offer")
    print(f"   Check result for marketing.com domain: {result}")
    
    # Test 4: Test subject pattern matching
    print("\n4. Testing subject pattern matching")
    
    subjects = [
        "Free money now!",
        "Free credit check!",
        "Free vacation!",
        "Free gift card!"
    ]
    
    for i, subject in enumerate(subjects):
        service.record_email_outcome(
            sender_email=f"sender{i}@random.com",
            sender_domain="random.com",
            subject=subject,
            category="WantsMoney",
            was_deleted=True
        )
        print(f"   Recorded email with subject: '{subject}' - deleted")
    
    # Check if pattern matching works
    result = service.check_repeat_offender("new@somewhere.com", "somewhere.com", "Free trial now!")
    print(f"   Check result for 'Free trial now!' subject: {result}")
    
    # Test 5: Get stats
    print("\n5. Getting repeat offender stats")
    stats = service.get_repeat_offender_stats()
    print(f"   Total patterns: {stats['total_patterns']}")
    print(f"   By type: {stats['by_type']}")
    print(f"   Total emails saved: {stats['total_emails_saved']}")
    
    # Test 6: Show all patterns in database
    print("\n6. All patterns in database:")
    patterns = session.query(RepeatOffenderPattern).all()
    for pattern in patterns:
        print(f"   Pattern ID {pattern.id}:")
        print(f"     Sender: {pattern.sender_email or pattern.sender_domain or 'N/A'}")
        print(f"     Subject: {pattern.subject_pattern or 'N/A'}")
        print(f"     Category: {pattern.category}")
        print(f"     Occurrences: {pattern.total_occurrences}, Deletions: {pattern.deletion_count}")
        print(f"     Confidence: {pattern.confidence_score:.2f}")
        print(f"     Repeat Offender: {'Yes' if pattern.marked_as_repeat_offender else 'No'}")
        print()
    
    session.close()
    print("Test completed!")


if __name__ == "__main__":
    test_repeat_offender_service()
