import argparse
import logging
import os
import ssl
import imaplib
from email import message_from_bytes
from datetime import datetime, timedelta, timezone, date
from email.utils import parsedate_to_datetime, parseaddr
from typing import List, Optional, Set
from bs4 import BeautifulSoup
import re
from collections import Counter
from tabulate import tabulate
from domain_service import DomainService, AllowedDomain, BlockedDomain, BlockedCategory
from services.email_summary_service import EmailSummaryService
from clients.account_category_client import AccountCategoryClient

from services.gmail_fetcher_service import GmailFetcher as ServiceGmailFetcher
from services.categorize_emails_interface import SimpleEmailCategory
from services.categorize_emails_llm import LLMCategorizeEmails
from services.email_processor_service import EmailProcessorService
from services.llm_service_interface import LLMServiceInterface
from services.openai_llm_service import OpenAILLMService
from services.logs_collector_service import LogsCollectorService

parser = argparse.ArgumentParser(description="Email Fetcher")
parser.add_argument("--primary-host", default=os.environ.get('OLLAMA_HOST_PRIMARY', '10.1.1.247:11434'),
                   help="Primary Ollama host URL")
parser.add_argument("--secondary-host", default=os.environ.get('OLLAMA_HOST_SECONDARY', '10.1.1.212:11434'),
                   help="Secondary Ollama host URL (for failover)")
parser.add_argument("--base-url", help="Deprecated: Use --primary-host instead")
parser.add_argument("--hours", type=int, default=int(os.environ.get('HOURS', '2')), help="The hours to fetch emails")
args = parser.parse_args()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Handle deprecated --base-url argument
if args.base_url:
    logger.warning("--base-url is deprecated. Use --primary-host instead.")
    args.primary_host = args.base_url


def _make_llm_service(model: str) -> LLMServiceInterface:
    """Construct an LLM service for RequestYAI (OpenAI-compatible) using env for base_url and api key.
    Provide full OpenAI-compatible root (may include version), e.g. https://api.requesty.ai/openai/v1
    """
    base_url = (
        os.environ.get("REQUESTYAI_BASE_URL")
        or os.environ.get("REQUESTY_API_URL")
        or "https://api.requesty.ai/openai/v1"
    )
    api_key = (
        os.environ.get("REQUESTYAI_API_KEY")
        or os.environ.get("REQUESTY_API_KEY")
        or os.environ.get("OPENAI_API_KEY", "")
    )
    return OpenAILLMService(
        model=model,
        api_key=api_key,
        base_url=base_url,
        provider_name="requestyai"
    )

def _make_llm_categorizer(model: str) -> LLMCategorizeEmails:
    """Construct LLMCategorizeEmails using the injected LLM service interface.
    This allows swapping LLM providers without changing the categorization logic.
    """
    llm_service = _make_llm_service(model)
    return LLMCategorizeEmails(llm_service=llm_service)

def categorize_email_with_resilient_client(contents: str, model: str) -> str:
    """
    Categorize email using the LLMCategorizeEmails interface (OpenAI-compatible / Ollama gateway).
    """
    try:
        categorizer = _make_llm_categorizer(model)
        result = categorizer.category(contents)

        if isinstance(result, SimpleEmailCategory):
            return result.value

        logger.warning(f"Categorization returned error or unexpected result: {result}")
        return "Other"
    except Exception as e:
        logger.error(f"Failed to categorize email via LLMCategorizeEmails: {str(e)}")
        return "Other"

# Keep the original function names for backward compatibility but route directly to LLMCategorizeEmails

def categorize_email_ell_marketing(contents: str):
    """Categorize email using LLMCategorizeEmails with the primary model."""
    try:
        # Use a default model for backward compatibility
        model = os.environ.get("PRIMARY_MODEL", "vertex/google/gemini-2.5-flash")
        result = _make_llm_categorizer(model).category(contents)
        return result.value if isinstance(result, SimpleEmailCategory) else "Other"
    except Exception as e:
        logger.error(f"categorize_email_ell_marketing failed: {e}")
        return "Other"


def categorize_email_ell_marketing2(contents: str):
    """Categorize email using LLMCategorizeEmails with the secondary model."""
    try:
        # Use a default model for backward compatibility
        model = os.environ.get("SECONDARY_MODEL", "vertex/google/gemini-2.5-flash")
        result = _make_llm_categorizer(model).category(contents)
        return result.value if isinstance(result, SimpleEmailCategory) else "Other"
    except Exception as e:
        logger.error(f"categorize_email_ell_marketing2 failed: {e}")
        return "Other"

class GmailFetcher:
    def __init__(self, email_address: str, app_password: str, api_token: str = None):
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

        # Initialize domain service and load domain data
        self.domain_service = DomainService(api_token=api_token)

        # Initialize summary service for tracking with account integration
        self.summary_service = EmailSummaryService(gmail_email=self.email_address)

        # Initialize account category service for tracking account-specific statistics
        self.account_service = None
        try:
            self.account_service = AccountCategoryClient()
            # Register/activate the account (don't store the returned object to avoid session issues)
            self.account_service.get_or_create_account(self.email_address)
            logger.info(f"Account registered for category tracking: {self.email_address}")
        except Exception as e:
            logger.error(f"Failed to initialize AccountCategoryClient for {self.email_address}: {str(e)}")
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

            # Fetch and cache blocked categories
            categories = self.domain_service.fetch_blocked_categories()
            self._blocked_categories = {c.category for c in categories}
            logger.info(f"📋 Loaded blocked categories: {sorted(self._blocked_categories)}")

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
        """Extract domain from email address in From header.

        Args:
            from_header: Raw From header string

        Returns:
            str: Domain part of the email address
        """
        _, email_address = parseaddr(from_header)
        if '@' in email_address:
            return email_address.split('@')[-1].lower()
        return ''
    
    def _extract_email_address(self, from_header: str) -> str:
        """Extract email address from From header.

        Args:
            from_header: Raw From header string

        Returns:
            str: Email address part
        """
        _, email_address = parseaddr(from_header)
        return email_address.lower() if email_address else ''

    def _is_domain_allowed(self, from_header: str) -> bool:
        """Check if the email is from an allowed domain."""
        domain = self._extract_domain(from_header)
        return domain in self._allowed_domains

    def _is_domain_blocked(self, from_header: str) -> bool:
        """Check if the email is from a blocked domain."""
        domain = self._extract_domain(from_header)
        return domain in self._blocked_domains

    def _is_category_blocked(self, category: str) -> bool:
        """
        Check if the category is in the blocked categories list.
        
        Handles category name variations:
        - "Wants-Money" (from API/domain service)
        - "WantsMoney" (from LLM responses)
        """
        if category in self._blocked_categories:
            return True
        
        # Handle category name variations for money-related categories
        category_variations = {
            "WantsMoney": ["Wants-Money", "WantsMoney"],
            "Wants-Money": ["Wants-Money", "WantsMoney"],
        }
        
        if category in category_variations:
            for variant in category_variations[category]:
                if variant in self._blocked_categories:
                    return True
        
        return False

    def connect(self) -> None:
        """Establish connection to Gmail IMAP server."""
        try:
            # Prepare credentials (do not mutate password; only normalize email display)
            email = (self.email_address or "").replace("\u00a0", " ").strip()
            password = self.password or ""

            logger.info(f"Attempting to connect to {self.imap_server} for {email}")
            self.conn = imaplib.IMAP4_SSL(self.imap_server)

            # Use SASL AUTHENTICATE PLAIN with explicit UTF-8 bytes to avoid ASCII encoding issues
            def _auth_plain(_challenge: bytes) -> bytes:
                return b"\0" + email.encode("utf-8") + b"\0" + password.encode("utf-8")

            typ, data = self.conn.authenticate("PLAIN", _auth_plain)
            if typ != "OK":
                raise imaplib.IMAP4.error(f"AUTHENTICATE PLAIN failed: {data!r}")

            logger.info("Successfully connected to Gmail IMAP server")
        except (imaplib.IMAP4.error, UnicodeEncodeError) as e:
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

    def remove_http_links(self, text):
        # Regular expression pattern to match HTTP links
        pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

        # Replace all occurrences of the pattern with an empty string
        cleaned_text = re.sub(pattern, '', text)

        return cleaned_text

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

def print_summary(hours: int, stats: dict):
    """Print a summary of email processing results."""
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Time window: Last {hours} hours")
    print(f"Emails processed: {stats['deleted'] + stats['kept']}")
    print(f"Emails deleted: {stats['deleted']}")
    print(f"Emails kept: {stats['kept']}")

    # Create category table
    if stats['categories']:
        print("\nCategories:")
        table = [[category, count] for category, count in stats['categories'].most_common()]
        print(tabulate(table, headers=['Category', 'Count'], tablefmt='grid'))
    print("="*50 + "\n")

def test_api_connection(api_token: str) -> bool:
    """Test connection to control API before proceeding"""
    service = DomainService(api_token=api_token)
    try:
        # Try to fetch domains to verify API connection
        service.fetch_allowed_domains()
        logger.info("Successfully connected to control API")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to control API: {str(e)}")
        return False

def main(email_address: str, app_password: str, api_token: str,hours: int = 2):
    logger.info("Starting email processing")
    logger.info(f"Processing emails from the last {hours} hours")

    # Initialize logs collector service
    logs_collector = LogsCollectorService()
    logs_collector.send_log(
        "INFO",
        f"Email processing started for {email_address}",
        {"hours": hours},
        "gmail-fetcher"
    )

    # Test API connection first
    logger.info("Testing API connection")
    api_connected = test_api_connection(api_token)

    # Terminate if API connection failed
    if not api_connected:
        logger.error("Cannot connect to control API. Terminating service.")
        logs_collector.send_log(
            "ERROR",
            "Failed to connect to control API - terminating",
            {"email": email_address},
            "gmail-fetcher"
        )
        raise SystemExit(1)

    # Initialize and use the fetcher
    fetcher = ServiceGmailFetcher(email_address, app_password, api_token)

    # Clear any existing tracked data to start fresh
    fetcher.summary_service.clear_tracked_data()

    # Start processing run in database
    fetcher.summary_service.start_processing_run(scan_hours=hours)

    # Initialize category tracking for this session
    category_actions = {}  # Track actions per category: {category: {"total": N, "deleted": N, "kept": N, "archived": N}}

    model = "vertex/google/gemini-2.5-flash"

    try:
        fetcher.connect()
        recent_emails = fetcher.get_recent_emails(hours)
        logger.info(f"Fetched {len(recent_emails)} records from the last {hours} hours.")

        # Identify which emails are new using GmailDeduplicationClient
        new_emails = []
        deduplication_service = None
        processed_message_ids = []  # Track which emails we process successfully
        
        db_svc = getattr(fetcher.summary_service, "db_service", None)
        # Fail fast if database service is unavailable
        if not db_svc:
            logger.error("Database service not available. Terminating service.")
            raise Exception("Database service not available")

        try:
            from clients.gmail_deduplication_client import GmailDeduplicationClient
            with db_svc.Session() as session:
                deduplication_service = GmailDeduplicationClient(session, email_address)
                new_emails = deduplication_service.filter_new_emails(recent_emails)
                
                # Log deduplication stats
                stats = deduplication_service.get_stats()
                logger.info(f"📊 Email deduplication stats: {stats}")
                
        except Exception as e:
            logger.error(f"Failed to use GmailDeduplicationClient: {e}")
            raise

        # Update fetched count
        fetcher.summary_service.run_metrics['fetched'] = len(recent_emails)

        print(f"Found {len(new_emails)} new emails to process:")
        processor = EmailProcessorService(fetcher, email_address, model, categorize_email_with_resilient_client)
        for msg in new_emails:
            # Delegate processing to EmailProcessorService
            processor.process_email(msg)

        # Print summary at the end
        print_summary(hours, fetcher.stats)

        # Bulk mark emails as processed to prevent reprocessing
        processed_message_ids = processor.processed_message_ids
        if processed_message_ids and db_svc:
            logger.info(f"🔄 Bulk marking {len(processed_message_ids)} emails as processed...")
            try:
                from clients.gmail_deduplication_client import GmailDeduplicationClient
                with db_svc.Session() as session:
                    dedup_service = GmailDeduplicationClient(session, email_address)
                    successful, errors = dedup_service.bulk_mark_as_processed(processed_message_ids)
                    logger.info(f"✅ Bulk processing completed: {successful} successful, {errors} errors")
            except Exception as e:
                logger.error(f"❌ Bulk GmailDeduplicationClient failed: {e}")
                raise
        elif processed_message_ids:
            logger.warning(f"⚠️ {len(processed_message_ids)} emails processed but no database service to record them")

        # Record category statistics and update account last scan timestamp
        category_actions = processor.category_actions
        if fetcher.account_service and category_actions:
            try:
                today = date.today()
                fetcher.account_service.record_category_stats(
                    email_address=email_address,
                    stats_date=today,
                    category_stats=category_actions
                )

                # Update account last scan timestamp
                fetcher.account_service.update_account_last_scan(email_address)
                logger.info(f"Recorded category statistics for {email_address}: {len(category_actions)} categories")
            except Exception as e:
                logger.error(f"Failed to record category statistics for {email_address}: {str(e)}")
                logger.warning("Email processing completed but account statistics were not recorded")
        elif fetcher.account_service:
            try:
                # Still update last scan timestamp even if no emails processed
                fetcher.account_service.update_account_last_scan(email_address)
                logger.info(f"Updated last scan timestamp for {email_address} (no emails processed)")
            except Exception as e:
                logger.error(f"Failed to update last scan timestamp for {email_address}: {str(e)}")

        # Complete processing run in database
        fetcher.summary_service.complete_processing_run(success=True)

        # Send completion log
        logs_collector.send_log(
            "INFO",
            f"Email processing completed successfully for {email_address}",
            {
                "processed": fetcher.stats['deleted'] + fetcher.stats['kept'],
                "deleted": fetcher.stats['deleted'],
                "kept": fetcher.stats['kept']
            },
            "gmail-fetcher"
        )

    except Exception as e:
        logger.error(f"Error during email processing: {str(e)}")

        # Send error log
        logs_collector.send_log(
            "ERROR",
            f"Email processing failed for {email_address}: {str(e)}",
            {"error": str(e), "email": email_address},
            "gmail-fetcher"
        )

        # Complete processing run with error
        fetcher.summary_service.complete_processing_run(success=False, error_message=str(e))
        raise
    finally:
        fetcher.disconnect()

if __name__ == "__main__":
    # Get credentials from environment variables
    email_address = os.getenv("GMAIL_EMAIL")
    app_password = os.getenv("GMAIL_PASSWORD")
    api_token = os.getenv("CONTROL_API_TOKEN")

    if not email_address or not app_password:
        raise ValueError("Please set GMAIL_EMAIL and GMAIL_PASSWORD environment variables")

    if not api_token:
        raise ValueError("Please set CONTROL_API_TOKEN environment variable")

    main(email_address, app_password, api_token, args.hours)
