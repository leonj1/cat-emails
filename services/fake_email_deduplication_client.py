"""
Fake email deduplication client for testing.
"""
from typing import List, Dict, Tuple, Optional
from clients.email_deduplication_client_interface import EmailDeduplicationClientInterface
from models.processed_email_log_model import ProcessedEmailLogModel
from datetime import datetime


class FakeEmailDeduplicationClient(EmailDeduplicationClientInterface):
    """
    Fake implementation of email deduplication client for testing.

    This implementation stores processed emails in memory and doesn't persist
    to any database.
    """

    def __init__(self, account_email: str):
        """
        Initialize the fake deduplication client.

        Args:
            account_email: Email account being processed
        """
        self.account_email = account_email
        self.processed_emails = set()
        self.stats = {
            'checked': 0,
            'duplicates_found': 0,
            'new_emails': 0,
            'logged': 0,
            'errors': 0
        }

    def is_email_processed(self, message_id: str) -> bool:
        """Check if an email has already been processed."""
        if not message_id or not message_id.strip():
            self.stats['errors'] += 1
            return False

        self.stats['checked'] += 1

        is_processed = message_id in self.processed_emails

        if is_processed:
            self.stats['duplicates_found'] += 1
        else:
            self.stats['new_emails'] += 1

        return is_processed

    def mark_email_as_processed(self, message_id: str) -> ProcessedEmailLogModel:
        """Mark an email as processed."""
        if not message_id or not message_id.strip():
            self.stats['errors'] += 1
            raise ValueError("message_id must be a non-empty string")

        self.processed_emails.add(message_id.strip())
        self.stats['logged'] += 1

        # Return a fake ProcessedEmailLogModel
        return ProcessedEmailLogModel(
            id=len(self.processed_emails),
            account_email=self.account_email,
            message_id=message_id.strip(),
            processed_at=datetime.utcnow()
        )

    def filter_new_emails(self, emails: List[Dict]) -> List[Dict]:
        """Filter a list of emails to only include those not yet processed."""
        if not emails:
            return []

        new_emails = []

        for email in emails:
            message_id = email.get('Message-ID', '')

            if not message_id:
                new_emails.append(email)
                continue

            if not self.is_email_processed(message_id):
                new_emails.append(email)

        return new_emails

    def bulk_mark_as_processed(self, message_ids: List[str]) -> Tuple[int, int]:
        """Mark multiple emails as processed."""
        if not message_ids:
            return 0, 0

        successful = 0
        errors = 0

        for message_id in message_ids:
            try:
                if message_id and message_id.strip():
                    self.mark_email_as_processed(message_id)
                    successful += 1
            except Exception:
                errors += 1

        return successful, errors

    def get_processed_count(self, days_back: Optional[int] = None) -> int:
        """Get count of processed emails."""
        # In the fake implementation, we don't track timestamps, so we return total count
        return len(self.processed_emails)

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about deduplication operations."""
        return self.stats.copy()

    def cleanup_old_records(self, days_to_keep: int = 90) -> int:
        """Clean up old processed email records (no-op for fake)."""
        return 0

    def reset_account_history(self) -> bool:
        """Reset all processed email history."""
        self.processed_emails.clear()
        return True
