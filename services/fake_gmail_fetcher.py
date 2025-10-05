"""
Fake implementation of GmailFetcherInterface for testing purposes.

This mock class allows testing email processing logic without requiring
actual Gmail IMAP connections or credentials.
"""
from typing import List
from email import message_from_bytes
from email.message import Message
from services.gmail_fetcher_interface import GmailFetcherInterface


class FakeGmailFetcher(GmailFetcherInterface):
    """Fake Gmail fetcher for testing that returns predefined email data."""

    def __init__(self, email_address: str = "test@example.com", app_password: str = "fake"):
        """
        Initialize the fake Gmail fetcher.

        Args:
            email_address: Email address (not used, for compatibility)
            app_password: App password (not used, for compatibility)
        """
        self.email_address = email_address
        self.app_password = app_password
        self.connected = False
        self.fake_emails: List[Message] = []
        self.labels_added: List[tuple] = []  # (message_id, label)
        self.deleted_messages: List[str] = []

    def connect(self) -> None:
        """Establish fake connection to Gmail IMAP server."""
        self.connected = True

    def disconnect(self) -> None:
        """Close the fake IMAP connection."""
        self.connected = False

    def get_recent_emails(self, hours: int = 2) -> List[Message]:
        """
        Fetch fake emails from the last specified hours.

        Args:
            hours: Number of hours to look back (ignored in fake)

        Returns:
            List of fake email messages
        """
        return self.fake_emails

    def get_email_body(self, email_message: Message) -> str:
        """
        Extract and return the plaintext body of an email message.

        Args:
            email_message: Email message to extract body from

        Returns:
            Plaintext body content
        """
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode("utf-8", errors="ignore")
            return ""
        else:
            payload = email_message.get_payload(decode=True)
            if payload:
                return payload.decode("utf-8", errors="ignore")
            return ""

    def add_label(self, message_id: str, label: str) -> bool:
        """
        Add a fake Gmail label to a message.

        Args:
            message_id: Message ID to label
            label: Label name to add

        Returns:
            True if successful
        """
        self.labels_added.append((message_id, label))
        return True

    def delete_email(self, message_id: str) -> bool:
        """
        Move a fake message to Trash.

        Args:
            message_id: Message ID to delete

        Returns:
            True if successful
        """
        self.deleted_messages.append(message_id)
        return True

    def add_fake_email(
        self,
        subject: str,
        sender: str,
        body: str,
        message_id: str = None
    ) -> Message:
        """
        Add a fake email to the fetcher's email list.

        Args:
            subject: Email subject line
            sender: Email sender address
            body: Email body content
            message_id: Optional message ID (auto-generated if not provided)

        Returns:
            The created Message object
        """
        msg = Message()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["Message-ID"] = message_id or f"<fake-{len(self.fake_emails)}@example.com>"
        msg.set_payload(body)

        self.fake_emails.append(msg)
        return msg

    def clear_fake_emails(self) -> None:
        """Clear all fake emails from the fetcher."""
        self.fake_emails.clear()

    def clear_tracking(self) -> None:
        """Clear all tracking data (labels added, deleted messages)."""
        self.labels_added.clear()
        self.deleted_messages.clear()
