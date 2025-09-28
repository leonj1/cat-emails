"""
Concrete Gmail fetcher service implementing the GmailFetcherInterface.
This logic was extracted from gmail_fetcher.py to a dedicated service module.
"""
from __future__ import annotations
import logging
import ssl
import imaplib
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from email.utils import parsedate_to_datetime, parseaddr
from typing import List, Optional, Set

from bs4 import BeautifulSoup

from domain_service import DomainService
from services.email_summary_service import EmailSummaryService
from services.account_category_service import AccountCategoryService
from services.gmail_fetcher_interface import GmailFetcherInterface
from services.gmail_connection_service import GmailConnectionService
from services.http_link_remover_service import HttpLinkRemoverService


logger = logging.getLogger(__name__)


class GmailFetcher(GmailFetcherInterface):
    def __init__(self, email_address: str, app_password: str, api_token: str | None = None):
        """
        Initialize Gmail connection using IMAP.

        Args:
            email_address: Gmail address
            app_password: Gmail App Password (NOT your regular Gmail password)
            api_token: API token for the control API
        """
        self.email_address = email_address
        self.password = app_password
        self.imap_server = "imap.gmail.com"
        self.conn = None
        self.stats = {
            'deleted': 0,
            'kept': 0,
            'categories': Counter()
        }

        # Initialize connection service (delegates IMAP authentication)
        self.connection_service = GmailConnectionService(self.email_address, self.password, self.imap_server)
        # Initialize domain service and load domain data
        self.domain_service = DomainService(api_token=api_token)
        # Initialize link remover service
        self.http_link_remover = HttpLinkRemoverService()

        # Initialize summary service for tracking with account integration
        self.summary_service = EmailSummaryService(gmail_email=self.email_address)

        # Initialize account category service for tracking account-specific statistics
        self.account_service = None
        try:
            self.account_service = AccountCategoryService()
            # Register/activate the account (don't store the returned object to avoid session issues)
            self.account_service.get_or_create_account(self.email_address)
            logger.info(f"Account registered for category tracking: {self.email_address}")
        except Exception as e:
            logger.error(f"Failed to initialize AccountCategoryService for {self.email_address}: {str(e)}")
            logger.warning("Account category tracking will be disabled for this session")
            self.account_service = None

        self._allowed_domains: Set[str] = set()
        self._blocked_domains: Set[str] = set()
        self._blocked_categories: Set[str] = set()
        self._load_domain_data()

    def _load_domain_data(self) -> None:
        """Load all domain and category data during initialization."""
        try:
            # Fetch and cache allowed domains
            allowed = self.domain_service.fetch_allowed_domains()
            self._allowed_domains = {d.domain for d in allowed}

            # Fetch and cache blocked domains
            blocked = self.domain_service.fetch_blocked_domains()
            self._blocked_domains = {d.domain for d in blocked}

            # Fetch and cache blocked categories, converting them to lowercase for case-insensitive matching
            categories = self.domain_service.fetch_blocked_categories()
            self._blocked_categories = {c.category.lower() for c in categories}

        except Exception as e:
            error_msg = str(e)
            print(f"Response: " + error_msg)
            if hasattr(e, 'response'):
                try:
                    print(f"Full API Response:")
                    print(f"Status Code: {e.response.status_code}")
                    print(f"Headers: {dict(e.response.headers)}")
                    print(f"Content: {e.response.text}")
                    error_msg = f"API Error: {e.response.status_code} - {e.response.text}"
                except Exception as parse_err:
                    print(f"Failed to parse response: {str(parse_err)}")
                    error_msg = f"API Error: {str(e)}"
            print(f"Error: Failed to load domain data. Details: {error_msg}")
            # Continue with empty sets rather than exiting
            self._allowed_domains = set()
            self._blocked_domains = set()
            self._blocked_categories = set()

    def _extract_domain(self, from_header: str) -> str:
        """Extract domain from email address in From header."""
        _, email_address = parseaddr(from_header)
        if '@' in email_address:
            return email_address.split('@')[-1].lower()
        return ''

    def _is_domain_allowed(self, from_header: str) -> bool:
        """Check if the email is from an allowed domain."""
        domain = self._extract_domain(from_header)
        return domain in self._allowed_domains

    def _is_domain_blocked(self, from_header: str) -> bool:
        """Check if the email is from a blocked domain."""
        domain = self._extract_domain(from_header)
        return domain in self._blocked_domains

    def _is_category_blocked(self, category: str) -> bool:
        """Check if the category is in the blocked categories list (case-insensitive)."""
        return category.lower() in self._blocked_categories

    def connect(self) -> None:
        """Establish connection to Gmail IMAP server."""
        try:
            self.conn = self.connection_service.connect()
        except Exception as e:
            logger.error(f"Failed to connect to Gmail: {str(e)}")
            raise Exception(f"Failed to connect to Gmail: {str(e)}")

    def disconnect(self) -> None:
        """Close the IMAP connection."""
        if self.conn:
            try:
                self.conn.logout()
            except (ssl.SSLError, imaplib.IMAP4.abort) as e:
                logger.error(f"SSL/Socket error during disconnect: {str(e)}")
            except Exception as e:
                logger.error(f"Error during disconnect: {str(e)}")

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
        return email_date > date_threshold

    def capitalize_words(self, text):
        return ' '.join(word.capitalize() for word in text.split())


    def remove_http_links(self, text: str) -> str:
        return self.http_link_remover.remove(text)

    def remove_encoded_content(self, text):
        # Regular expression pattern to match the encoded content format
        pattern = r'\(\s*~~/[A-Za-z0-9/+]+~\s*\)'

        # Replace all occurrences of the pattern with an empty string
        cleaned_text = re.sub(pattern, '', text)

        return cleaned_text

    def remove_images_from_email(self, email_body):
        """
        Remove images from email contents.

        Args:
            email_body (str): The email body content (can be HTML or plain text).

        Returns:
            str: Email body with images removed.
        """
        # Check if the email body is HTML
        if re.search(r'<[^>]+>', email_body):
            # Parse HTML content
            soup = BeautifulSoup(email_body, 'html.parser')

            # Remove all img tags
            for img in soup.find_all('img'):
                img.decompose()

            # Remove all elements with background images
            for element in soup.find_all(style=re.compile('background-image')):
                del element['style']

            # Convert back to string
            return str(soup)
        else:
            # For plain text, remove any text that looks like an image file or URL
            return re.sub(r'\b(https?:\/\/[^\s]+\.(?:jpg|jpeg|png|gif|bmp))\b', '', email_body, flags=re.IGNORECASE)

    def add_label(self, message_id: str, label: str) -> bool:
        """
        Add a label to a message without marking it as read.

        Args:
            message_id: The message ID to label
            label: The Gmail label to add

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.conn:
            raise Exception("Not connected to Gmail")

        try:
            # Search for the message ID to get the sequence number
            _, data = self.conn.search(None, f'(HEADER Message-ID "{message_id}")')
            if not data[0]:
                print(f"Message ID {message_id} not found")
                return False

            sequence_number = data[0].split()[0]

            # Create the label if it doesn't exist
            self.conn.create(f'"{label}"')

            # Copy the message to the label
            result = self.conn.copy(sequence_number, f'"{label}"')
            return result[0] == 'OK'
        except Exception as e:
            print(f"Error adding label: {str(e)}")
            return False

    def get_email_body(self, email_message) -> str:
        """
        Extract the body content from an email message.
        Handles both plain text and HTML emails.

        Args:
            email_message: Email message object

        Returns:
            str: The email body content
        """
        body = ""

        if email_message.is_multipart():
            # Handle multipart messages
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except:
                        continue
                elif content_type == "text/html":
                    try:
                        html_content = part.get_payload(decode=True).decode()
                        # Convert HTML to plain text
                        soup = BeautifulSoup(html_content, 'html.parser')
                        body = soup.get_text(separator=' ', strip=True)
                        break
                    except:
                        continue
        else:
            # Handle non-multipart messages
            content_type = email_message.get_content_type()
            try:
                if content_type == "text/plain":
                    body = email_message.get_payload(decode=True).decode()
                elif content_type == "text/html":
                    html_content = email_message.get_payload(decode=True).decode()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    body = soup.get_text(separator=' ', strip=True)
            except:
                body = "Could not decode email content"

        # Clean up the body text
        body = re.sub(r'\s+', ' ', body).strip()  # Remove extra whitespace
        return body

    def get_recent_emails(self, hours: int = 2) -> List[message_from_bytes]:
        """
        Fetch emails from the last specified hours.
        """
        logger.info(f"Starting to fetch emails from last {hours} hours")

        if not self.conn:
            logger.error("No active IMAP connection")
            raise Exception("Not connected to Gmail")

        # Select inbox
        logger.debug("Selecting INBOX")
        self.conn.select("INBOX")

        # Calculate the date threshold with timezone information
        date_threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
        date_str = date_threshold.strftime("%d-%b-%Y")
        logger.debug(f"Using date threshold: {date_str}")

        # Search for emails after the threshold
        search_criteria = f'(SINCE "{date_str}")'
        logger.debug(f"Searching with criteria: {search_criteria}")
        _, message_numbers = self.conn.search(None, search_criteria)

        total_messages = len(message_numbers[0].split())
        logger.info(f"Found {total_messages} messages matching date criteria")

        emails = []
        processed = 0
        for num in message_numbers[0].split():
            processed += 1
            logger.debug(f"Processing message {processed}/{total_messages} (ID: {num})")

            try:
                fetch_command = "(BODY.PEEK[])"
                _, msg_data = self.conn.fetch(num, fetch_command)

                email_message = self._create_email_message(msg_data)
                if not email_message:
                    logger.warning(f"Could not create email message for ID {num}")
                    continue

                if self._is_email_within_threshold(email_message, date_threshold):
                    logger.debug(f"Message {num} is within time threshold, adding to results")
                    emails.append(email_message)
                else:
                    logger.debug(f"Message {num} is outside time threshold, skipping")
            except Exception as e:
                logger.error(f"Error processing message {num}: {str(e)}")
                continue

        logger.info(f"Completed fetch: {len(emails)} emails within time threshold")
        return emails

    def delete_email(self, message_id: str) -> bool:
        """
        Delete an email by moving it to the Trash folder.

        Args:
            message_id: The Message-ID of the email to delete

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.conn:
            logger.error("Attempted to delete email without active connection")
            raise Exception("Not connected to Gmail")

        try:
            logger.debug(f"Attempting to delete email with Message-ID: {message_id}")
            # Search for the message ID to get the sequence number
            _, data = self.conn.search(None, f'(HEADER Message-ID "{message_id}")')
            if not data[0]:
                logger.warning(f"Message ID {message_id} not found")
                return False

            sequence_number = data[0].split()[0]
            logger.debug(f"Found email with sequence number: {sequence_number}")

            # Move to Trash (Gmail's trash folder is [Gmail]/Trash)
            logger.debug(f"Setting delete flag for email {message_id}")
            self.conn.store(sequence_number, '+FLAGS', '\\Deleted')

            logger.debug(f"Attempting to copy email {message_id} to Trash folder")
            result = self.conn.copy(sequence_number, '[Gmail]/Trash')

            if result[0] == 'OK':
                logger.debug(f"Successfully copied email {message_id} to Trash, now expunging")
                # Expunge the original message
                self.conn.expunge()
                logger.debug(f"Expunge completed for email {message_id}")
                self.stats['deleted'] += 1  # Increment delete counter
                logger.info(f"Successfully deleted email {message_id}")
                return True

            logger.warning(f"Failed to delete email {message_id}")
            return False

        except Exception as e:
            logger.error(f"Error deleting email {message_id}: {str(e)}")
            return False
