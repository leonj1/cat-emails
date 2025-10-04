from abc import ABC, abstractmethod
from typing import Dict


class AccountEmailProcessorInterface(ABC):
    """Interface for processing emails for Gmail accounts."""

    @abstractmethod
    def process_account(self, email_address: str) -> Dict:
        """
        Process emails for a single Gmail account.

        Args:
            email_address: The Gmail account to process

        Returns:
            Dictionary with processing results including:
            - account: Email address processed
            - success: Boolean indicating success/failure
            - emails_found: Number of emails found (if successful)
            - emails_processed: Number of emails processed (if successful)
            - processing_time_seconds: Time taken (if successful)
            - error: Error message (if failed)
            - timestamp: ISO timestamp of completion
        """
        pass
