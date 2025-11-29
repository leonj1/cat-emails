"""
Fake implementation of GmailFetcherInterface for testing.

This fake fetcher provides an in-memory implementation that doesn't connect to
a real Gmail account. It's useful for testing email processing logic without
needing actual IMAP credentials or network access.

Usage:
    from tests.fake_gmail_fetcher import FakeGmailFetcher

    fetcher = FakeGmailFetcher()
    fetcher.add_test_email(subject="Test", body="Test email body", sender="test@example.com")
    emails = fetcher.get_recent_emails(hours=2)
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from email.message import EmailMessage

from services.gmail_fetcher_interface import GmailFetcherInterface


class FakeGmailFetcher(GmailFetcherInterface):
    """
    Fake implementation of Gmail fetcher for testing.

    This implementation stores emails in memory and simulates IMAP operations
    without requiring a real Gmail connection.
    """

    def __init__(self):
        """Initialize the fake Gmail fetcher."""
        self.connected = False
        self.emails: List[Dict] = []
        self.labels: Dict[str, List[str]] = {}  # message_id -> list of labels
        self.deleted_message_ids: List[str] = []
        self._next_message_id = 1
        self._blocked_domains = set()  # Set of blocked domain strings

    def connect(self) -> None:
        """Simulate establishing connection to Gmail IMAP server."""
        self.connected = True

    def disconnect(self) -> None:
        """Simulate closing the IMAP connection."""
        self.connected = False

    def get_recent_emails(self, hours: int = 2) -> List[Dict]:
        """
        Return emails from the last specified hours.

        Args:
            hours: Number of hours to look back

        Returns:
            List of email dictionaries with standard email fields
        """
        if not self.connected:
            raise RuntimeError("Not connected. Call connect() first.")

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        recent_emails = [
            email for email in self.emails
            if email.get('Date', datetime.utcnow()) >= cutoff_time
            and email.get('Message-ID') not in self.deleted_message_ids
        ]

        return recent_emails

    def get_email_body(self, email_message) -> str:
        """
        Extract and return the plaintext body of an email message.

        Args:
            email_message: Email dictionary with 'Body' field

        Returns:
            Plain text body content
        """
        if isinstance(email_message, dict):
            return email_message.get('Body', '')
        return ''

    def add_label(self, message_id: str, label: str) -> bool:
        """
        Add a Gmail label to a message.

        Args:
            message_id: The message ID to label
            label: The label name to add

        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            return False

        if message_id not in self.labels:
            self.labels[message_id] = []

        if label not in self.labels[message_id]:
            self.labels[message_id].append(label)

        return True

    def delete_email(self, message_id: str) -> bool:
        """
        Move a message to Trash (simulated by marking as deleted).

        Args:
            message_id: The message ID to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            return False

        if message_id not in self.deleted_message_ids:
            self.deleted_message_ids.append(message_id)

        return True

    # Helper methods for testing

    def add_test_email(
        self,
        subject: str,
        body: str,
        sender: str = "test@example.com",
        date: Optional[datetime] = None,
        message_id: Optional[str] = None
    ) -> str:
        """
        Add a test email to the fake fetcher.

        Args:
            subject: Email subject line
            body: Email body content
            sender: Sender email address
            date: Email date (defaults to now)
            message_id: Optional message ID (auto-generated if not provided)

        Returns:
            The message ID of the created email
        """
        if message_id is None:
            message_id = f"<test-{self._next_message_id}@example.com>"
            self._next_message_id += 1

        if date is None:
            date = datetime.utcnow()

        email = {
            'Message-ID': message_id,
            'Subject': subject,
            'Body': body,
            'From': sender,
            'Date': date,
            'To': 'recipient@example.com'
        }

        self.emails.append(email)
        return message_id

    def get_labels(self, message_id: str) -> List[str]:
        """
        Get all labels for a message.

        Args:
            message_id: The message ID

        Returns:
            List of label names
        """
        return self.labels.get(message_id, [])

    def is_deleted(self, message_id: str) -> bool:
        """
        Check if a message has been deleted.

        Args:
            message_id: The message ID

        Returns:
            True if deleted, False otherwise
        """
        return message_id in self.deleted_message_ids

    def clear(self) -> None:
        """Clear all emails, labels, and deleted messages."""
        self.emails.clear()
        self.labels.clear()
        self.deleted_message_ids.clear()
        self._next_message_id = 1
        self._blocked_domains.clear()

    def add_blocked_domain(self, domain: str) -> None:
        """
        Add a domain to the blocked list for testing.

        Args:
            domain: Domain name to block (e.g., 'spam.com')
        """
        self._blocked_domains.add(domain.lower())

    # Methods required by EmailProcessorService (stub implementations for testing)

    def remove_http_links(self, text: str) -> str:
        """Remove HTTP links from text (stub for testing)."""
        return text

    def remove_images_from_email(self, text: str) -> str:
        """Remove image references from email (stub for testing)."""
        return text

    def remove_encoded_content(self, text: str) -> str:
        """Remove encoded content from email (stub for testing)."""
        return text

    def _extract_domain(self, from_header: str) -> str:
        """Extract domain from email header (stub for testing)."""
        if "@" in from_header:
            return from_header.split("@")[-1].strip(">").strip()
        return ""

    def _extract_email_address(self, from_header: str) -> str:
        """Extract email address from header (stub for testing)."""
        if "<" in from_header and ">" in from_header:
            return from_header.split("<")[1].split(">")[0]
        return from_header.strip()

    def _is_domain_blocked(self, from_header: str) -> bool:
        """
        Check if domain is blocked.

        Args:
            from_header: Email From header

        Returns:
            True if domain is in the blocked list, False otherwise
        """
        domain = self._extract_domain(from_header)
        return domain.lower() in self._blocked_domains

    def _is_domain_allowed(self, from_header: str) -> bool:
        """Check if domain is allowed (stub for testing - always False)."""
        return False

    def _is_category_blocked(self, category: str) -> bool:
        """Check if category is blocked (stub for testing - always False)."""
        return False

    def get_blocked_domains(self) -> Set[str]:
        """Return the set of blocked domains."""
        return self._blocked_domains.copy()
