#!/usr/bin/env python3

"""Display repeat offender statistics and patterns."""

import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
sys.path.insert(0, os.path.abspath('.'))

from models.database import RepeatOffenderPattern
from services.repeat_offender_service import RepeatOffenderService


def main():
    """Show repeat offender stats for all accounts."""
    
    # Connect to the database
    db_path = "./email_summaries/summaries.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get all unique accounts
        accounts = session.query(RepeatOffenderPattern.account_name).distinct().all()
        
        if not accounts:
            print("No repeat offender patterns found.")
            return
        
        print("Repeat Offender Statistics")
        print("=" * 80)
        
        total_patterns = 0
        total_emails_saved = 0
        
        for (account_name,) in accounts:
            print(f"\nAccount: {account_name}")
            print("-" * 50)
            
            service = RepeatOffenderService(session, account_name)
            stats = service.get_repeat_offender_stats()
            
            print(f"Active Patterns: {stats['total_patterns']}")
            print(f"  - By Email: {stats['by_type']['sender_email']}")
            print(f"  - By Domain: {stats['by_type']['sender_domain']}")  
            print(f"  - By Subject: {stats['by_type']['subject_pattern']}")
            print(f"Emails Saved from LLM: {stats['total_emails_saved']}")
            
            total_patterns += stats['total_patterns']
            total_emails_saved += stats['total_emails_saved']
            
            # Show top patterns for this account
            patterns = session.query(RepeatOffenderPattern).filter(
                RepeatOffenderPattern.account_name == account_name,
                RepeatOffenderPattern.is_active == True,
                RepeatOffenderPattern.marked_as_repeat_offender.isnot(None)
            ).order_by(
                RepeatOffenderPattern.total_occurrences.desc()
            ).limit(5).all()
            
            if patterns:
                print("\nTop Patterns:")
                for i, pattern in enumerate(patterns, 1):
                    identifier = (pattern.sender_email or 
                                pattern.sender_domain or 
                                pattern.subject_pattern[:50] + "..." if pattern.subject_pattern and len(pattern.subject_pattern) > 50 else pattern.subject_pattern or "Unknown")
                    
                    print(f"  {i}. {identifier}")
                    print(f"     Category: {pattern.category}, Emails: {pattern.total_occurrences}, "
                          f"Confidence: {pattern.confidence_score:.1%}")
        
        print("\n" + "=" * 80)
        print(f"TOTALS: {total_patterns} patterns saving {total_emails_saved} LLM calls")
        print("=" * 80)
        
    finally:
        session.close()


if __name__ == "__main__":
    main()
