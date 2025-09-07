from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
from email import message_from_bytes


class GmailFetcherInterface(ABC):
    """Interface for fetching and manipulating Gmail messages via IMAP."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to Gmail IMAP server."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Close the IMAP connection."""
        raise NotImplementedError

    @abstractmethod
    def get_recent_emails(self, hours: int = 2) -> List[message_from_bytes]:
        """Fetch emails from the last specified hours."""
        raise NotImplementedError

    @abstractmethod
    def get_email_body(self, email_message) -> str:
        """Extract and return the plaintext body of an email message."""
        raise NotImplementedError

    @abstractmethod
    def add_label(self, message_id: str, label: str) -> bool:
        """Add a Gmail label to a message without marking it as read."""
        raise NotImplementedError

    @abstractmethod
    def delete_email(self, message_id: str) -> bool:
        """Move a message to Trash and expunge the original."""
        raise NotImplementedError

