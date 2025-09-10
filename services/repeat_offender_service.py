"""Service for managing repeat offender patterns to skip expensive LLM categorization."""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.database import RepeatOffenderPattern
from services.categorize_emails_interface import SimpleEmailCategory


class RepeatOffenderService:
    """
    Manages repeat offender patterns to identify emails that consistently get deleted
    and can skip expensive LLM categorization.
    """
    
    def __init__(self, session: Session, account_name: str):
        self.session = session
        self.account_name = account_name
        
        # Thresholds for marking as repeat offender
        self.min_occurrences = 3  # Minimum emails needed to establish pattern
        self.confidence_threshold = 0.8  # 80% deletion rate needed
        self.lookback_days = 30  # Consider patterns from last 30 days
    
    def check_repeat_offender(self, sender_email: str, sender_domain: str, subject: str) -> Optional[str]:
        """
        Check if this email matches a known repeat offender pattern.
        
        Returns:
            Category with -RepeatOffender suffix if match found, None otherwise
        """
        cutoff_date = datetime.now() - timedelta(days=self.lookback_days)
        
        patterns = self.session.query(RepeatOffenderPattern).filter(
            and_(
                RepeatOffenderPattern.account_name == self.account_name,
                RepeatOffenderPattern.is_active == True,
                RepeatOffenderPattern.marked_as_repeat_offender.isnot(None),
                RepeatOffenderPattern.last_seen >= cutoff_date
            )
        ).order_by(
            # Prioritize specific patterns over general ones
            RepeatOffenderPattern.sender_email.desc(),  # email patterns first
            RepeatOffenderPattern.sender_domain.desc(),  # then domain patterns
            RepeatOffenderPattern.confidence_score.desc()  # then by confidence
        ).all()
        
        for pattern in patterns:
            if self._matches_pattern(pattern, sender_email, sender_domain, subject):
                return f"{pattern.category}-RepeatOffender"
        
        return None
    
    def record_email_outcome(self, sender_email: str, sender_domain: str, subject: str, 
                           category: str, was_deleted: bool) -> None:
        """
        Record the outcome of an email to track patterns and potentially mark as repeat offender.
        """
        # Skip if already a repeat offender category
        if category.endswith("-RepeatOffender"):
            return
        
        # Only track categories that could be deletion candidates
        deletion_categories = {"Advertising", "Marketing", "Wants-Money", "WantsMoney", "Blocked_Domain"}
        if category not in deletion_categories:
            return
            
        now = datetime.now()
        
        # Find existing patterns or create new ones
        patterns_to_update = []
        
        # Check for sender email pattern
        if sender_email:
            pattern = self._get_or_create_pattern(
                sender_email=sender_email, 
                category=category
            )
            patterns_to_update.append(pattern)
        
        # Check for sender domain pattern
        if sender_domain and sender_domain != sender_email:
            pattern = self._get_or_create_pattern(
                sender_domain=sender_domain,
                category=category
            )
            patterns_to_update.append(pattern)
        
        # Check for subject pattern (extract common patterns)
        subject_pattern = self._extract_subject_pattern(subject)
        if subject_pattern:
            pattern = self._get_or_create_pattern(
                subject_pattern=subject_pattern,
                category=category
            )
            patterns_to_update.append(pattern)
        
        # Update patterns
        for pattern in patterns_to_update:
            pattern.total_occurrences += 1
            if was_deleted:
                pattern.deletion_count += 1
            
            pattern.confidence_score = pattern.deletion_count / pattern.total_occurrences
            pattern.last_seen = now
            
            # Check if this pattern should be marked as repeat offender
            if (pattern.total_occurrences >= self.min_occurrences and 
                pattern.confidence_score >= self.confidence_threshold and
                pattern.marked_as_repeat_offender is None):
                
                pattern.marked_as_repeat_offender = now
        
        self.session.commit()
    
    def _get_or_create_pattern(self, sender_email: Optional[str] = None, 
                              sender_domain: Optional[str] = None,
                              subject_pattern: Optional[str] = None,
                              category: str = "") -> RepeatOffenderPattern:
        """Get existing pattern or create new one."""
        
        # Build query conditions
        conditions = [RepeatOffenderPattern.account_name == self.account_name]
        
        if sender_email:
            conditions.append(RepeatOffenderPattern.sender_email == sender_email)
            conditions.append(RepeatOffenderPattern.sender_domain.is_(None))
            conditions.append(RepeatOffenderPattern.subject_pattern.is_(None))
        elif sender_domain:
            conditions.append(RepeatOffenderPattern.sender_domain == sender_domain)
            conditions.append(RepeatOffenderPattern.sender_email.is_(None))
            conditions.append(RepeatOffenderPattern.subject_pattern.is_(None))
        elif subject_pattern:
            conditions.append(RepeatOffenderPattern.subject_pattern == subject_pattern)
            conditions.append(RepeatOffenderPattern.sender_email.is_(None))
            conditions.append(RepeatOffenderPattern.sender_domain.is_(None))
        
        conditions.append(RepeatOffenderPattern.category == category)
        
        # Try to find existing pattern
        pattern = self.session.query(RepeatOffenderPattern).filter(and_(*conditions)).first()
        
        if not pattern:
            now = datetime.now()
            pattern = RepeatOffenderPattern(
                account_name=self.account_name,
                sender_email=sender_email,
                sender_domain=sender_domain,
                subject_pattern=subject_pattern,
                category=category,
                total_occurrences=0,
                deletion_count=0,
                confidence_score=0.0,
                first_seen=now,
                last_seen=now,
                is_active=True
            )
            self.session.add(pattern)
        
        return pattern
    
    def _matches_pattern(self, pattern: RepeatOffenderPattern, sender_email: str, 
                        sender_domain: str, subject: str) -> bool:
        """Check if email matches the given pattern."""
        
        if pattern.sender_email:
            return pattern.sender_email == sender_email
        
        if pattern.sender_domain:
            return pattern.sender_domain == sender_domain
        
        if pattern.subject_pattern:
            return bool(re.search(pattern.subject_pattern, subject, re.IGNORECASE))
        
        return False
    
    def _extract_subject_pattern(self, subject: str) -> Optional[str]:
        """
        Extract common patterns from email subjects that might indicate spam.
        Returns a regex pattern or None if no clear pattern.
        """
        if not subject or len(subject.strip()) < 5:
            return None
        
        subject = subject.strip()
        
        # Look for common spam patterns
        spam_indicators = [
            r'(?i)\b(free|save|discount|offer|deal|limited time|urgent|act now|click here)\b',
            r'(?i)\b(congratulations|winner|selected|prize|lottery|sweepstakes)\b',
            r'(?i)\b(earn money|make money|work from home|business opportunity)\b',
            r'(?i)\b(weight loss|lose weight|diet|pills|medication)\b',
            r'(?i)\b(credit|loan|mortgage|debt|refinance|insurance)\b',
        ]
        
        # Check if subject contains spam indicators
        for indicator in spam_indicators:
            if re.search(indicator, subject):
                return indicator
        
        # For very repetitive subjects, create a pattern
        # Simple approach: if subject has repeated patterns of promotional language
        words = subject.lower().split()
        if len(words) >= 3:
            # Look for subjects that are very promotional
            promo_words = {'free', 'save', 'discount', 'offer', 'deal', 'sale', 'buy', 'get', 'win'}
            promo_count = sum(1 for word in words if word in promo_words)
            
            if promo_count >= 2:  # High promotional content
                # Create a loose pattern based on first few words
                pattern_words = words[:min(3, len(words))]
                return r'\b' + r'\s+'.join(re.escape(word) for word in pattern_words) + r'\b'
        
        return None
    
    def get_repeat_offender_stats(self) -> dict:
        """Get statistics about repeat offender patterns."""
        
        patterns = self.session.query(RepeatOffenderPattern).filter(
            and_(
                RepeatOffenderPattern.account_name == self.account_name,
                RepeatOffenderPattern.is_active == True,
                RepeatOffenderPattern.marked_as_repeat_offender.isnot(None)
            )
        ).all()
        
        stats = {
            'total_patterns': len(patterns),
            'by_type': {
                'sender_email': 0,
                'sender_domain': 0,
                'subject_pattern': 0
            },
            'total_emails_saved': 0,  # Total emails that would have been sent to LLM
        }
        
        for pattern in patterns:
            if pattern.sender_email:
                stats['by_type']['sender_email'] += 1
            elif pattern.sender_domain:
                stats['by_type']['sender_domain'] += 1
            elif pattern.subject_pattern:
                stats['by_type']['subject_pattern'] += 1
            
            stats['total_emails_saved'] += pattern.total_occurrences
        
        return stats
