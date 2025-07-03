import argparse
import ell
import logging
import openai
import os
import ssl
import imaplib
from email import message_from_bytes
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime, parseaddr
from typing import List, Optional, Set
from bs4 import BeautifulSoup
import re
from collections import Counter
from tabulate import tabulate
from domain_service import DomainService, AllowedDomain, BlockedDomain, BlockedCategory
from services.email_summary_service import EmailSummaryService
from services.ollama_client import create_resilient_client

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

ell.init(verbose=False, store='./logdir')

# Create resilient Ollama client with automatic failover
resilient_client = create_resilient_client(
    primary_host=args.primary_host,
    secondary_host=args.secondary_host
)

# Log initial host status
host_status = resilient_client.get_hosts_status()
logger.info(f"Ollama hosts status: {host_status}")

system_prompt = f"""
You are an AI assistant designed to categorize incoming emails with a focus on protecting the user from unwanted commercial content and unnecessary spending. Your primary goal is to quickly identify and sort emails that may be attempting to solicit money or promote products/services. You should approach each email with a healthy dose of skepticism, always on the lookout for subtle or overt attempts to encourage spending.
When categorizing emails, you must strictly adhere to the following four categories:

'Wants-Money': This category is for any email that directly or indirectly asks the recipient to spend money. This includes:

Invoices or bills
Requests for donations or charitable contributions
Notifications about due payments or subscriptions
Emails about fundraising campaigns
Messages asking for financial support of any kind
Subtle requests disguised as opportunities that require monetary investment


'Advertising': This category is for emails primarily focused on promoting specific products or services. Look for:

Direct product advertisements
Sale announcements
New product launches
Service offerings
Emails showcasing product features or benefits
Messages with prominent calls-to-action to purchase or "learn more" about products


'Marketing': This category is for emails that may not directly advertise products but are part of broader marketing strategies. This includes:

Brand awareness campaigns
Newsletters with soft-sell approaches
Content marketing emails (blogs, articles, videos) that indirectly promote products or services
Customer relationship emails that don't directly sell but keep the brand in the recipient's mind
Surveys or feedback requests that are part of marketing research
Emails about loyalty programs or rewards


'Other': This category is for all emails that don't fit into the above three categories. This may include:

Personal correspondence
Work-related emails
Transactional emails (e.g., order confirmations, shipping notifications)
Account security alerts
Appointment reminders
Service updates or notifications not aimed at selling


Important guidelines:

Be vigilant in identifying even subtle attempts to encourage spending or promote products/services.
Pay close attention to the sender, subject line, and key content to make accurate categorizations.
If an email contains elements of multiple categories, prioritize 'Wants-Money' first, then 'Advertising', then 'Marketing'.
Remember that the goal is to shield the user from unwanted commercial influences and protect them from potential financial solicitations.
Approach each email with the assumption that it may be trying to sell something, and only categorize as 'Other' if you're confident it's not commercial in nature.

By following these guidelines and strictly adhering to the given categories, you will help the user maintain an inbox free from unwanted commercial content and protect them from potential financial solicitations.
"""

def categorize_email_with_resilient_client(contents: str, model: str = "llama3.2:latest") -> str:
    """
    Categorize email using the resilient Ollama client with automatic failover.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Categorize this email. You are limited into one of the categories. Maximum length of response is 2 words: {contents}"}
    ]
    
    try:
        response = resilient_client.chat_completion(
            model=model,
            messages=messages,
            temperature=0.1
        )
        
        # Extract the response text
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        else:
            logger.error("Unexpected response format from Ollama")
            return "Other"
            
    except Exception as e:
        logger.error(f"Failed to categorize email: {str(e)}")
        return "Other"

# Keep the original functions for backward compatibility but have them use the resilient client
@ell.simple(model="llama3.2:latest", temperature=0.1)
def categorize_email_ell_marketing(contents: str):
    """Categorize email using primary model."""
    return categorize_email_with_resilient_client(contents, "llama3.2:latest")

@ell.simple(model="gemma2:latest", temperature=0.1)
def categorize_email_ell_marketing2(contents: str):
    """Categorize email using secondary model."""
    return categorize_email_with_resilient_client(contents, "gemma2:latest")

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
        
        # Initialize summary service for tracking
        self.summary_service = EmailSummaryService()
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

    def _is_domain_allowed(self, from_header: str) -> bool:
        """Check if the email is from an allowed domain."""
        domain = self._extract_domain(from_header)
        return domain in self._allowed_domains

    def _is_domain_blocked(self, from_header: str) -> bool:
        """Check if the email is from a blocked domain."""
        domain = self._extract_domain(from_header)
        return domain in self._blocked_domains

    def _is_category_blocked(self, category: str) -> bool:
        """Check if the category is in the blocked categories list."""
        return category in self._blocked_categories

    def connect(self) -> None:
        """Establish connection to Gmail IMAP server."""
        try:
            # Use original credentials without encoding
            email = self.email_address
            password = self.password
            
            logger.info(f"Attempting to connect to {self.imap_server} for {email}")
            self.conn = imaplib.IMAP4_SSL(self.imap_server)
            self.conn.login(email, password)
            logger.info("Successfully connected to Gmail IMAP server")
        except imaplib.IMAP4_SSL.error as e:
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

def test_api_connection(api_token: str) -> None:
    """Test connection to control API before proceeding"""
    service = DomainService(api_token=api_token)
    try:
        # Try to fetch domains to verify API connection
        service.fetch_allowed_domains()
    except Exception as e:
        raise Exception(f"Failed to connect to control API: {str(e)}")

def main(email_address: str, app_password: str, api_token: str,hours: int = 2):
    logger.info("Starting email processing")
    logger.info(f"Processing emails from the last {hours} hours")
    
    # Test API connection first
    logger.info("Testing API connection")
    test_api_connection(api_token)

    # Initialize and use the fetcher
    fetcher = GmailFetcher(email_address, app_password, api_token)
    
    # Start processing run in database
    fetcher.summary_service.start_processing_run(scan_hours=hours)
    
    try:
        fetcher.connect()
        recent_emails = fetcher.get_recent_emails(hours)
        
        # Update fetched count
        fetcher.summary_service.run_metrics['fetched'] = len(recent_emails)
        
        print(f"Found {len(recent_emails)} emails in the last {hours} hours:")
        for msg in recent_emails:
            # Get the email body
            body = fetcher.get_email_body(msg)
            pre_categorized = False
            deletion_candidate = True
            
            # Check domain lists
            from_header = str(msg.get('From', ''))
            if fetcher._is_domain_blocked(from_header):
                category = "Blocked_Domain"
                pre_categorized = True
                deletion_candidate = True
            elif fetcher._is_domain_allowed(from_header):
                category = "Allowed_Domain"
                pre_categorized = True
                deletion_candidate = False
            
            # Categorize the email if not pre-categorized
            if not pre_categorized:
                contents_without_links = fetcher.remove_http_links(f"{msg.get('Subject')}. {body}")
                contents_without_images = fetcher.remove_images_from_email(contents_without_links)
                contents_without_encoded = fetcher.remove_encoded_content(contents_without_images)
                contents_cleaned = contents_without_encoded
                # Use the resilient client for categorization
                category = categorize_email_with_resilient_client(contents_cleaned)
                
                # Clean up the category response
                category = category.replace('"', '').replace("'", "").replace('*', '').replace('=', '').replace('+', '').replace('-', '').replace('_', '').strip()
                
                # Validate category response
                valid_categories = {'Wants-Money', 'Advertising', 'Marketing', 'Other'}
                if len(category) > 30 or category not in valid_categories:
                    logger.warning(f"Invalid category response: '{category}', defaulting to 'Other'")
                    category = 'Other'
                
                # Check if category is blocked
                if fetcher._is_category_blocked(category):
                    deletion_candidate = True


            try:
                from_header = msg.get('From', '')
                subject = msg.get('Subject', '')
                message_id = msg.get("Message-ID", '')
                
                print(f"From: {from_header}")
                print(f"Subject: {subject}")
                if len(category) < 20:
                    print(f"Category: {category}")
                print(f"Deletion Candidate: {deletion_candidate}")
                
                # Extract sender domain for tracking
                sender_domain = fetcher._extract_domain(from_header) if from_header else None
                
                try:
                    fetcher.add_label(message_id, category)
                    # Track categories
                    fetcher.stats['categories'][category] += 1
                except ssl.SSLError as ssl_err:
                    logger.error(f"SSL Error while adding label: {ssl_err}")
                    print("Skipping label addition due to SSL error")
                    continue
                except Exception as e:
                    logger.error(f"Error adding label: {e}")
                    print("Skipping label addition due to error")
                    continue
                
                # Track kept/deleted emails
                action_taken = "kept"  # Default action
                
                if deletion_candidate:
                    try:
                        if fetcher.delete_email(message_id):
                            print("Email deleted successfully")
                            action_taken = "deleted"
                        else:
                            print("Failed to delete email")
                            fetcher.stats['kept'] += 1
                    except ssl.SSLError as ssl_err:
                        logger.error(f"SSL Error while deleting email: {ssl_err}")
                        print("Skipping email deletion due to SSL error")
                        fetcher.stats['kept'] += 1
                        continue
                else:
                    print("Email left in inbox")
                    fetcher.stats['kept'] += 1
                
                # Track email in summary service
                fetcher.summary_service.track_email(
                    message_id=message_id,
                    sender=from_header,
                    subject=subject,
                    category=category,
                    action=action_taken,
                    sender_domain=sender_domain,
                    was_pre_categorized=pre_categorized
                )
                        
                print("-" * 50)
            except Exception as e:
                logger.error(f"Error processing email: {e}")
                print(f"Skipping email due to error: {e}")
                continue
            
        # Print summary at the end
        print_summary(hours, fetcher.stats)
        
        # Complete processing run in database
        fetcher.summary_service.complete_processing_run(success=True)
            
    except Exception as e:
        logger.error(f"Error during email processing: {str(e)}")
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
