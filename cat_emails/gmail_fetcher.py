from typing import Tuple
import os
import re
import sys
import imaplib
import openai
import argparse
import ell
from email import message_from_bytes
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime, parseaddr
from typing import List, Optional, Set
from bs4 import BeautifulSoup
from collections import Counter
from tabulate import tabulate
from .domain_service import DomainService, AllowedDomain, BlockedDomain, BlockedCategory
from .email_processors.email_processor import process_single_email

# Global variables for clients and args
client = None
client2 = None
_args = None

def get_args():
    """Get command line arguments lazily."""
    global _args
    if _args is None:
        parser = argparse.ArgumentParser(description="Email Fetcher")
        parser.add_argument("--base-url", default="10.1.1.144:11434", help="Base URL for the OpenAI API")
        parser.add_argument("--consumer-group", default="default", help="Consumer group name")
        parser.add_argument("--delay-on-error-seconds", type=int, default=60, help="Delay in seconds when an error occurs")
        parser.add_argument("--hours", type=int, default=2, help="Number of hours to look back for emails")
        try:
            _args = parser.parse_args()
        except SystemExit:
            # If running under test, use default values
            _args = parser.parse_args([])
    return _args

def init_clients(base_url=None):
    """Initialize ELL and OpenAI clients."""
    global client, client2
    if base_url is None:
        base_url = get_args().base_url
    ell.init(verbose=False, store='./logdir')
    client = openai.Client(base_url=f"http://{base_url}/v1", api_key="ollama")
    client2 = openai.Client(base_url="http://10.1.1.212:11434/v1", api_key="ollama")

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

@ell.simple(model="llama3.2:latest", temperature=0.1)
def categorize_email_ell_marketing(contents: str):
    """Categorize email using llama model."""
    global client
    if client is None:
        raise RuntimeError("OpenAI client not initialized. Call init_clients() first.")
    return client.chat.completions.create(
        model="llama3.2:latest",
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Categorize this email. You are limited into one of the categories. Maximum length of response is 2 words: {contents}"}
        ]
    ).choices[0].message.content

@ell.simple(model="gemma2:latest", temperature=0.1)
def categorize_email_ell_marketing2(contents: str):
    """Categorize email using gemma model."""
    global client2
    if client2 is None:
        raise RuntimeError("OpenAI client not initialized. Call init_clients() first.")
    return client2.chat.completions.create(
        model="gemma2:latest",
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Categorize this email. You are limited into one of the categories. Maximum length of response is 2 words: {contents}"}
        ]
    ).choices[0].message.content

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
            
            self.conn = imaplib.IMAP4_SSL(self.imap_server)
            self.conn.login(email, password)
        except imaplib.IMAP4_SSL.error as e:
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
            _, msg_data = self.conn.fetch(num, fetch_command)
            
            email_message = self._create_email_message(msg_data)
            if not email_message:
                continue
                
            if self._is_email_within_threshold(email_message, date_threshold):
                emails.append(email_message)

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
            raise Exception("Not connected to Gmail")

        try:
            # Search for the message ID to get the sequence number
            _, data = self.conn.search(None, f'(HEADER Message-ID "{message_id}")')
            if not data[0]:
                print(f"Message ID {message_id} not found")
                return False

            sequence_number = data[0].split()[0]
            
            # Move to Trash (Gmail's trash folder is [Gmail]/Trash)
            self.conn.store(sequence_number, '+FLAGS', '\\Deleted')
            result = self.conn.copy(sequence_number, '[Gmail]/Trash')
            
            if result[0] == 'OK':
                # Expunge the original message
                self.conn.expunge()
                self.stats['deleted'] += 1  # Increment delete counter
                return True
            return False
            
        except Exception as e:
            print(f"Error deleting email: {str(e)}")
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

def main(email_address: str, app_password: str, api_token: str, hours: Optional[int] = None):
    """
    Main function to process emails.
    
    Args:
        email_address: Gmail address
        app_password: Gmail App Password
        api_token: API token for control API
        hours: Number of hours to look back for emails. If None, uses value from command line args.
    """
    # Test API connection first
    test_api_connection(api_token)

    # Initialize and use the fetcher
    init_clients()
    fetcher = GmailFetcher(email_address, app_password, api_token)
    try:
        fetcher.connect()
        hours = hours if hours is not None else get_args().hours
        recent_emails = fetcher.get_recent_emails(hours)
        
        if not recent_emails:
            print(f"No emails found in the last {hours} hours.")
            return

        print(f"\nProcessing {len(recent_emails)} emails from the last {hours} hours...")
        
        for email in recent_emails:
            should_delete = process_single_email(fetcher, email)
            
            if should_delete:
                message_id = email.get("Message-ID")
                if message_id:
                    if fetcher.delete_email(message_id):
                        fetcher.stats['deleted'] += 1
                    else:
                        fetcher.stats['kept'] += 1
            else:
                fetcher.stats['kept'] += 1

        print_summary(hours, fetcher.stats)
            
    finally:
        fetcher.disconnect()

if __name__ == "__main__":
    # Get credentials from environment variables
    email_address = os.getenv("GMAIL_EMAIL")
    app_password = os.getenv("GMAIL_PASSWORD")
    api_token = os.getenv("CONTROL_API_TOKEN")

    if not all([email_address, app_password, api_token]):
        print("Error: Required environment variables are missing.")
        print("Please set GMAIL_EMAIL, GMAIL_PASSWORD, and CONTROL_API_TOKEN")
        sys.exit(1)

    # Run the main function
    main(email_address, app_password, api_token)
