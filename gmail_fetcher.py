import imaplib
from email import message_from_bytes  # Changed import
from datetime import datetime, timedelta, timezone
import os
from email.utils import parsedate_to_datetime
from typing import List, Optional

class GmailFetcher:
    def __init__(self, email_address: str, app_password: str):
        """
        Initialize Gmail connection using IMAP.
        
        Args:
            email_address: Gmail address
            app_password: Gmail App Password (NOT your regular Gmail password)
        """
        self.email_address = email_address
        self.password = app_password
        self.imap_server = "imap.gmail.com"
        self.conn = None

    def connect(self) -> None:
        """Establish connection to Gmail IMAP server."""
        try:
            self.conn = imaplib.IMAP4_SSL(self.imap_server)
            self.conn.login(self.email_address, self.password)
        except Exception as e:
            raise Exception(f"Failed to connect to Gmail: {str(e)}")

    def disconnect(self) -> None:
        """Close the IMAP connection."""
        if self.conn:
            self.conn.logout()

    def _create_email_message(self, msg_data) -> Optional[message_from_bytes]:
        """Convert raw message data into an email message object."""
        if not msg_data or not msg_data[0]:
            return None
        email_body = msg_data[0][1]
        return message_from_bytes(email_body)

    def _is_email_within_threshold(self, email_message, date_threshold) -> bool:
        """Check if email falls within the specified time threshold."""
        date_tuple = email_message.get("Date")
        if not date_tuple:
            return False
        email_date = parsedate_to_datetime(date_tuple)
        if date_threshold.tzinfo is None:
            date_threshold = date_threshold.replace(tzinfo=timezone.utc)
        if email_date.tzinfo is None:
            email_date = email_date.replace(tzinfo=timezone.utc)
        print(f"email_date: {email_date}, tzinfo: {email_date.tzinfo}")
        print(f"threshold: {date_threshold}, tzinfo: {date_threshold.tzinfo}")
        return email_date > date_threshold

    def get_recent_emails(self, hours: int = 2, mark_as_read: bool = False) -> List[message_from_bytes]:
        """
        Fetch emails from the last specified hours.
        """
        if not self.conn:
            raise Exception("Not connected to Gmail")

        # Select inbox
        self.conn.select("INBOX")

        # Calculate the date threshold with timezone information
        date_threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
        date_str = date_threshold.strftime("%d-%b-%Y")

        # Search for emails after the threshold
        search_criteria = f'(SINCE "{date_str}")'
        _, message_numbers = self.conn.search(None, search_criteria)

        emails = []
        for num in message_numbers[0].split():
            fetch_command = "(BODY.PEEK[])"
            # RFC822 always marks the email as read            
            # fetch_command = "(RFC822)" if mark_as_read else "(BODY.PEEK[])"
            _, msg_data = self.conn.fetch(num, fetch_command)
            
            email_message = self._create_email_message(msg_data)
            if not email_message:
                continue
                
            if self._is_email_within_threshold(email_message, date_threshold):
                emails.append(email_message)

        return emails

def main(email_address: str, app_password: str):
    # Initialize and use the fetcher
    fetcher = GmailFetcher(email_address, app_password)
    try:
        fetcher.connect()
        # Pass mark_as_read=False explicitly for clarity
        recent_emails = fetcher.get_recent_emails(mark_as_read=False)
        
        print(f"Found {len(recent_emails)} emails in the last 2 hours:")
        for msg in recent_emails:
            print(f"Subject: {msg.get('Subject')}")
            print(f"From: {msg.get('From')}")
            print("-" * 50)
            
    finally:
        fetcher.disconnect()

if __name__ == "__main__":
    # Get credentials from environment variables
    email_address = os.getenv("GMAIL_EMAIL")
    app_password = os.getenv("GMAIL_PASSWORD")

    if not email_address or not app_password:
        raise ValueError("Please set GMAIL_EMAIL and GMAIL_PASSWORD environment variables")

    main(email_address, app_password)

    