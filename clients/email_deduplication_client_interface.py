"""
Interface for email deduplication clients.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional

from models.processed_email_log_model import ProcessedEmailLogModel


class EmailDeduplicationClientInterface(ABC):
    """Interface for managing email deduplication across application restarts."""

    @abstractmethod
    def is_email_processed(self, message_id: str) -> bool:
        """
        Check if an email has already been processed.

        Args:
            message_id: The Message-ID header from the email

        Returns:
            True if email has been processed, False otherwise
        """
        pass

    @abstractmethod
    def mark_email_as_processed(self, message_id: str) -> ProcessedEmailLogModel:
        """
        Mark an email as processed to prevent future reprocessing.

        Args:
            message_id: The Message-ID header from the email

        Returns:
            ProcessedEmailLogModel representing the persisted record

        Raises:
            ValueError: If message_id is empty or whitespace
            IntegrityError: If a duplicate record violates the unique constraint
            Exception: Any other database error encountered will be propagated
        """
        pass

    @abstractmethod
    def filter_new_emails(self, emails: List[Dict]) -> List[Dict]:
        """
        Filter a list of emails to only include those not yet processed.

        Args:
            emails: List of email dictionaries with Message-ID keys

        Returns:
            List of emails that haven't been processed yet
        """
        pass

    @abstractmethod
    def bulk_mark_as_processed(self, message_ids: List[str]) -> Tuple[int, int]:
        """
        Mark multiple emails as processed in a single transaction.

        Args:
            message_ids: List of Message-ID values to mark as processed

        Returns:
            Tuple of (successful_count, error_count)
        """
        pass

    @abstractmethod
    def get_processed_count(self, days_back: Optional[int] = None) -> int:
        """
        Get count of processed emails for this account.

        Args:
            days_back: If specified, only count emails from last N days

        Returns:
            Number of processed emails
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about deduplication operations in this session.

        Returns:
            Dictionary with operation counts
        """
        pass

    @abstractmethod
    def cleanup_old_records(self, days_to_keep: int = 90) -> int:
        """
        Clean up old processed email records to prevent database bloat.

        Args:
            days_to_keep: Number of days of records to keep

        Returns:
            Number of records deleted
        """
        pass

    @abstractmethod
    def reset_account_history(self) -> bool:
        """
        Reset all processed email history for this account.
        WARNING: This will cause all emails to be reprocessed!

        Returns:
            True if successful, False otherwise
        """
        pass
