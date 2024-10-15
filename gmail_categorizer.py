import ell
import openai
import os
import requests
import argparse
import logging
import time
import email
import re
from email.header import decode_header
from collections import Counter
from datetime import datetime, timedelta
from imapclient import IMAPClient
from email import message_from_bytes
import imaplib
from bs4 import BeautifulSoup
from anthropic import Anthropic


ell.init(verbose=True, store='./logdir')

client = openai.Client(
    base_url="http://10.1.1.144:11434/v1", api_key="ollama"  # required but not used
)

@ell.simple(model="llama3.2:latest", temperature=0.1, client=client)
def categorize_email_ell_for_me(contents: str):
    """
You are an AI assistant tasked with categorizing incoming emails. Your goal is to efficiently sort emails into predefined categories without being swayed by marketing tactics or sales pitches. You have a strong aversion to unsolicited commercial content and are programmed to prioritize the user's financial well-being by avoiding unnecessary expenditures.

When categorizing emails, you must strictly adhere to the following six categories:

'Personal': Emails from friends, family, or acquaintances that are not related to work or financial matters. This includes personal correspondence, invitations to social events, and general updates from individuals known to the user.
'Financial-Notification': Any email related to the user's financial accounts or transactions. This includes bank statements, credit card alerts, investment updates, payment confirmations, and notifications about account activity or balance changes.
'Appointment-Reminder': Emails that serve as reminders for upcoming appointments, meetings, or events. This category includes doctor's appointments, dental visits, scheduled calls, and any other time-specific commitments.
'Service-Updates': Notifications about changes, updates, or important information from services the user is already subscribed to or uses. This can include updates from software providers, changes to terms of service, account security notifications, and status updates for ongoing services.
'Work-related': Any email pertaining to the user's professional life. This includes correspondence with colleagues, superiors, or clients, project updates, meeting invitations, and any other communication related to the user's job or career.
'Other': This category is for emails that don't clearly fit into the above categories. It may include newsletters the user has willingly subscribed to, community announcements, or any other email that doesn't fall neatly into the other five categories.
Important guidelines:

Approach each email with skepticism towards any content that appears to be trying to sell products or services.
Be particularly wary of emails that encourage spending money, even if they claim to offer deals or discounts.
If an email contains elements of multiple categories, prioritize the most significant or actionable aspect when choosing a category.
Pay close attention to the sender, subject line, and key content to make accurate categorizations.
Remember that the goal is to organize emails efficiently, not to engage with or respond to their content.
By following these guidelines and strictly adhering to the given categories, you will help the user maintain an organized inbox while avoiding unwanted commercial influences.
    """
    return f"Categorize this email. You are limited into one of the categories. Maximum length of response is 2 words: {contents}"

@ell.simple(model="llama3.2:latest", temperature=0.5, client=client)
def categorize_email_ell_marketing(contents: str):
    """
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
Remember that the goal is to shield the user from unwanted commercial influences and protect them from unnecessary spending.
Approach each email with the assumption that it may be trying to sell something, and only categorize as 'Other' if you're confident it's not commercial in nature.

By following these guidelines and strictly adhering to the given categories, you will help the user maintain an inbox free from unwanted commercial content and protect them from potential financial solicitations.
"""
    return f"Categorize this email. You are limited into one of the categories. Maximum length of response is 2 words: {contents}"

@ell.simple(model="llama3.2:latest", temperature=0.5, client=client)
def categorize_email_ell_generic(contents: str):
    """
Email Intent Analyzer:
You are an AI designed to swiftly discern and label the core intention behind each email. Your task is to deduce the primary purpose of the email's author, with a particular focus on identifying attempts to seek money, advertise products/services, or gain political influence.
Your responses must always be two words or fewer. Be concise yet precise.
Key objectives:

Quickly assess the email's content, sender, and context.
Determine the author's main goal or intention.
Categorize using clear, succinct labels.

Primary categories to consider (not exhaustive):

"Seeks Money" (or variations like "Requests Donation", "Demands Payment")
"Promotes Product" or "Advertises Service"
"Political Appeal" or "Seeks Support"
"Shares Information"
"Requests Action"
"Personal Message"

Guidelines:

Prioritize identifying commercial or political motivations.
Look for subtle cues that might reveal hidden intentions.
If multiple purposes are present, identify the most prominent one.
Use active verbs when possible to convey intent (e.g., "Solicits Funds" rather than "Fundraising Email").
Remain objective and avoid emotional language.

Examples:

For an email asking for donations: "Seeks Donation"
For a marketing newsletter: "Promotes Products"
For a political campaign email: "Political Persuasion"
For a personal message from a friend: "Personal Correspondence"

Remember: Your labels must be two words or fewer, clear, and accurately reflect the email author's primary intention.
"""
    return f"Categorize this email. Maximum length of response is 2 words: {contents}"


def remove_images_from_email(email_body):
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ollamas = {
    "http://10.1.1.212:11434": {"model": "llama3.1:8b", "num_ctx": 4096},
    "http://10.1.1.144:11434": {"model": "llama3:latest", "num_ctx": 8192}
}

hide = ["advertisement", "politics", "notification", "helpful", "information", "spam", "marketting", "disclaimer", "marketing"]
ok = [
        'Personal', 
        'Financial-Notification', 
        'Appointment-Reminder', 
        'Service-Updates', 
        'Work-related',
        "order", 
        "order cancelled", 
        "order confirm", 
        "order confirmed", 
        "order confirmation", 
        "order placed", 
        "order promised", 
        "order reminder", 
        "order scheduled", 
        "order update", 
        "order shipped", 
        "personal", 
        "statement", 
        "bank", 
        "alert", 
        "legal", 
        "legalese", 
        "document", 
        "memorandum", 
        "appointment confirmation", 
        "appointment confirmed", 
        "appointment reminder", 
        "appointment scheduled", 
        "correspondance",
        "\"alert\"", 
        "\"bank\"", 
        "\"personal\""
    ]

def remove_http_links(text):
    # Regular expression pattern to match HTTP links
    pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    
    # Replace all occurrences of the pattern with an empty string
    cleaned_text = re.sub(pattern, '', text)
    
    return cleaned_text

def remove_encoded_content(text):
    # Regular expression pattern to match the encoded content format
    pattern = r'\(\s*~~/[A-Za-z0-9/+]+~\s*\)'
    
    # Replace all occurrences of the pattern with an empty string
    cleaned_text = re.sub(pattern, '', text)
    
    return cleaned_text

def check_api_connectivity(api_type, api_url=None, api_key=None, max_retries=3, retry_delay=5):
    logger.info(f"Checking connectivity to {api_type} API")
    for attempt in range(max_retries):
        try:
            if api_type == "Ollama":
                response = requests.get(f"{api_url}/api/tags")
                if response.status_code == 200:
                    logger.info("Successfully connected to Ollama host")
                    return True
            elif api_type == "Anthropic":
                prompt="Test"
                anthropic = Anthropic(api_key=api_key)
                message = anthropic.messages.create(
                     model="claude-3-5-sonnet-20240620",
                     max_tokens=100,
                     temperature=0,
                     system="You are a world-class poet. Respond only with short poems.",
                     messages=[
                         {
                             "role": "user",
                             "content": [
                                 {
                                     "type": "text",
                                     "text": "Why is the ocean salty?"
                                 }
                             ]
                         }
                     ]
                )
                logger.info("Successfully connected to Anthropic API")
                return True
        except Exception as e:
            logger.warning(f"Error connecting to {api_type} API: {e}")
        
        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    logger.error(f"Failed to connect to {api_type} API after multiple attempts")
    return False

def get_imap_client():
    # Replace with your Gmail IMAP settings
    IMAP_HOST = 'imap.gmail.com'
    IMAP_PORT = 993
    EMAIL = os.environ.get('GMAIL_EMAIL')
    PASSWORD = os.environ.get('GMAIL_PASSWORD')

    if not EMAIL or not PASSWORD:
        raise ValueError("Please set GMAIL_EMAIL and GMAIL_PASSWORD environment variables")

    logger.info(f"Logging in with username: {EMAIL}")
    logger.info(f"Password length: {len(PASSWORD)}")

    # Encode EMAIL and PASSWORD to ASCII, replacing non-ASCII characters
    EMAIL_encoded = EMAIL.encode('ascii', 'ignore').decode('ascii')
    PASSWORD_encoded = PASSWORD.encode('ascii', 'ignore').decode('ascii')

    logger.info("Connecting to Gmail IMAP server...")
    client = IMAPClient(IMAP_HOST, port=IMAP_PORT, use_uid=True, ssl=True)
    client.login(EMAIL_encoded, PASSWORD_encoded)
    logger.info("Successfully connected to Gmail IMAP server")
    return client

def get_recent_emails(client, hours):
    logger.info("Selecting INBOX folder...")
    client.select_folder('INBOX')
    time_ago = datetime.now() - timedelta(hours=hours)
    date_criterion = time_ago.strftime("%d-%b-%Y")
    logger.info(f"Searching for emails since {date_criterion}...")
    messages = client.search(['SINCE', date_criterion, 'NOT', 'KEYWORD', 'bogus-asdf'])
    logger.info(f"Found {len(messages)} recent emails")
    
    # Fetch email data including timestamps
    email_data = []
    total_messages = len(messages)
    for index, msg_id in enumerate(messages, 1):
        logger.info(f"Processing {index} of {total_messages} emails, ID: {msg_id}")
        try:
            fetch_data = client.fetch([msg_id], ['INTERNALDATE', 'RFC822'])
            timestamp = fetch_data[msg_id][b'INTERNALDATE']
            email_data.append((msg_id, timestamp))
        except Exception as e:
            logger.info(f"Problem fetching recent email [{msg_id}]: {e}")
    
    # Sort emails by timestamp in descending order
    sorted_emails = sorted(email_data, key=lambda x: x[1], reverse=True)
    sorted_msg_ids = [email[0] for email in sorted_emails]
    
    logger.info("Emails sorted by timestamp in descending order")
    return sorted_msg_ids

def get_sender_email(email_message):
    sender = email_message['From']
    if isinstance(sender, str):
        if '<' in sender:
            return sender.split('<')[1].split('>')[0]
        return sender
    elif hasattr(sender, 'addresses'):
        # Handle email.header.Header object
        return str(sender.addresses[0].addr_spec)
    else:
        # Fallback: convert to string
        return str(sender)

def generate_response(purpose, prompt, api_type, model_info, api_url=None, api_key=None):
    logger.info(f"Initiating {purpose}...")
    logger.info(f"Ollama server: {api_url}...")
    if api_type == "Ollama":
        response = requests.post(f"{api_url}/api/generate", json={
            "model": model_info["model"],
            "prompt": prompt,
            "stream": False,
            "context_length": model_info["num_ctx"]
        })
        if response.status_code == 200:
            return response.json()['response'].strip()
        else:
            logger.error(f"Error: Unable to {purpose}. Status code: {response.status_code}")
            raise Exception(f"Failed to {purpose}")
    elif api_type == "Anthropic":
        client = Anthropic(api_key=api_key)
        message = client.messages.create(
             model="claude-3-5-sonnet-20240620",
             max_tokens=100,
             temperature=0,
             system="You are a professional adept at identifying advertising, marketing, or soliciting emails typically have backgrounds in marketing, data analysis, cybersecurity, or content management. These individuals possess a combination of analytical skills, industry knowledge, and an understanding of communication techniques used in promotional materials, allowing them to quickly assess and categorize email content.",
             messages=[
                 {
                     "role": "user",
                     "content": [
                         {
                             "type": "text",
                             "text": prompt
                         }
                     ]
                 }
             ]
        )
        #return response.completion.strip()
        return message.content[0].text

def categorize_email_new(subject, body, sender, api_type, model, api_url=None, api_key=None):
    purpose = "Categorize email"
    prompt = f"""
You are an expert email classifier. Your task is to categorize emails based on their subject and contents. Provide a brief category label of one or two words for each email. Focus only on the following categories:

1. Order Placed
2. Order Shipped
3. Order Cancelled
4. Alert
5. Bank
6. Personal
7. Advertisement
8. Politics

Guidelines:
- Emails from e-commerce businesses are typically advertisements unless they are specifically about an order.
- Emails from banks should be categorized as "Bank".
- Emails from personal email addresses (e.g., gmail.com) should be categorized as "Personal".
- "Order" categories should only be used for emails directly related to a specific customer order.
- Instead of using the category name "Spam" use "Junk" instead.

Examples:
- Email from shipment-tracking@amazon.com about a package: "Order Shipped"
- Email from jcpenny.com about a sale: "Advertisement"
- Email from chase.com: "Bank"
- Email from a gmail.com address: "Personal"
- Email about a security breach: "Alert"
- Contents or Subject that talk about politics or political parties: "Politics"
- Contents or Subject that talk about promotions: "Advertisement"
- Contents or Subject that talk about ads or advertisements or saving money: "Advertisement"
- Contents or Subject that talk about getting something for free: "Advertisement"
- Contents or Subject that talk about facebook: "Junk"

For each email, analyze the sender's email address, subject line, and any provided content. Then respond with only the category label, nothing else.

Email to categorize:
Sender: [{sender}]
Subject: [{subject}]
Content: [{body}]
"""

    return generate_response(purpose, prompt, api_type, ollamas[api_url], api_url, api_key)


def is_email_summary_advertisement(subject, summary, api_type, model, api_url=None, api_key=None):
    logger.info("Summarizing Email Category...")
    prompt = f"""You are a laconic assistant that only speaks in single words. How would you categorize the following summary? Example, if it reads like an advertisement then respond with 'Advertisement'. Respond with no trailing period.

Subject: {subject}

Summary: {summary}

Category: [Single word]"""

    return generate_response("summarize email", prompt, api_type, model, api_url, api_key)

def set_email_label(client, msg_id, label):
    if label.lower() == "spam":
        label = "Junk"
    # Remove surrounding quotes if present
    label = label.strip("\"'")
    # Capitalize each word in the label
    label = capitalize_words(label)
    logger.info(f"Setting label '{label}' for email {msg_id}")
    try:
        client.add_gmail_labels(msg_id, [label])
    except Exception as e:
        logger.error(f"Error setting label or removing Inbox label: {e}")

def archive_email(client, msg_id):
    logger.info(f"Archiving email {msg_id}")
    try:
        client.remove_gmail_labels(msg_id, ["\\Inbox"])
        logger.info(f"Email {msg_id} archived successfully")
    except Exception as e:
        logger.error(f"Error archiving email {msg_id}: {e}")

def delete_and_expunge_email(client, msg_id):
    logger.info(f"Deleting and expunging email {msg_id}")
    try:
        client.delete_messages([msg_id])
        client.expunge()
        logger.info(f"Email {msg_id} deleted and expunged successfully")
    except Exception as e:
        logger.error(f"Error deleting and expunging email {msg_id}: {e}")

def mark_email_as_unread(client, msg_id):
    logger.info(f"Marking email {msg_id} as unread")
    try:
        client.remove_flags([msg_id], [b'\\Seen'])
        logger.info(f"Email {msg_id} marked as unread successfully")
    except Exception as e:
        logger.error(f"Error marking email {msg_id} as unread: {e}")

def existing_labels(client, msg_id) -> list[str]:
    logger.info(f"Checking if email {msg_id} has any label.")
    try:
        fetch_data = client.fetch([msg_id], ['X-GM-LABELS'])
        labels = fetch_data[msg_id][b'X-GM-LABELS']
        return labels
    except Exception as e:
        logger.error(f"Error checking label for email {msg_id}: {e}")
        return None

def remove_all_labels(client, msg_id, labels):
    logger.info(f"Removing all labels for email {msg_id}")
    try:
        # Convert labels to strings and filter out system labels
        labels_to_remove = [label.decode() if isinstance(label, bytes) else label for label in labels if not (isinstance(label, bytes) and label.startswith(b'\\')) and not (isinstance(label, str) and label.startswith('\\'))]
        
        if labels_to_remove:
            client.remove_gmail_labels(msg_id, labels_to_remove)
            logger.info(f"Removed labels: {', '.join(labels_to_remove)}")
        else:
            logger.info("No custom labels to remove")
    except Exception as e:
        logger.error(f"Error removing labels: {e}")

def extract_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator=' ', strip=True)

def has_two_words_or_less(text):
    # Split the string into words
    words = text.split()
    
    # Check if the number of words is 2 or less
    return len(words) <= 2

def word_in_list(word, string_list):
    # Convert the word to lowercase for case-insensitive comparison
    word = word.lower()
    
    # Use any() and a generator expression for a more concise implementation
    return any(word in string.lower().split() for string in string_list)

def capitalize_words(text):
    return ' '.join(word.capitalize() for word in text.split())

def get_email_body(email_message):
    body = ''
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                body = part.get_payload(decode=True).decode(errors='ignore')
                break
            elif content_type == "text/html":
                html_content = part.get_payload(decode=True).decode(errors='ignore')
                body = extract_html_content(html_content)
                break
    else:
        content_type = email_message.get_content_type()
        if content_type == "text/plain":
            body = email_message.get_payload(decode=True).decode(errors='ignore')
        elif content_type == "text/html":
            html_content = email_message.get_payload(decode=True).decode(errors='ignore')
            body = extract_html_content(html_content)
    return body

def process_email(client, msg_id, category_counter=None):
    fetch_data = client.fetch([msg_id], ['INTERNALDATE', 'RFC822', 'FLAGS', 'X-GM-LABELS'])
    email_data = fetch_data[msg_id][b'RFC822']
    email_message = message_from_bytes(email_data)
    existing_email_labels = fetch_data[msg_id][b'X-GM-LABELS']
    
    subject = email_message['Subject']
    sender = get_sender_email(email_message)
    timestamp = fetch_data[msg_id][b'INTERNALDATE']
    body = get_email_body(email_message)
    contents_without_links = remove_http_links(f"{subject}. {body}")
    contents_without_images = remove_images_from_email(contents_without_links)
    contents_without_encoded = remove_encoded_content(contents_without_images)
    contents_cleaned = contents_without_encoded
    
    logger.info(f"Email - Timestamp: {timestamp}")
    logger.info(f"Email - Sender: {sender}")
    logger.info(f"Email - Subject: {subject}")


    ignore_existing_labels = True
    
    if not ignore_existing_labels:
        # existing_meail_labels = existing_labels(client, msg_id)
        if existing_email_labels is not None and len(existing_email_labels) > 0:
            if len(existing_email_labels) == 1 and existing_email_labels[0] == b'\\Important':
                pass
            else:
                logger.info(f"Email {msg_id} has labels {existing_email_labels}. Skipping...")
                logger.info("---")
                return existing_email_labels
    
    category = categorize_email_ell_for_me(contents_cleaned)
    category = category.replace('"', '').replace("'", "")
    category_lower = category.lower()
    logger.info("Finished checking if the email is meant for me")
    
    if category_lower != "other" and category_lower in ok:
        set_email_label(client, msg_id, category)
        mark_email_as_unread(client, msg_id)
    else:
        category = categorize_email_ell_marketing(contents_cleaned)
        category = category.replace('"', '').replace("'", "")
        category_lower = category.lower()
        logger.info("Finished checking if the email is an advertisement")
        if category_lower != "other" and len(category_lower) <= 40:
            set_email_label(client, msg_id, category)
            delete_and_expunge_email(client, msg_id)
        else:
            category = categorize_email_ell_generic(contents_cleaned)
            category = category.replace('"', '').replace("'", "")
            logger.info("Finished checking if the email is generic")
            set_email_label(client, msg_id, category)
            delete_and_expunge_email(client, msg_id)
    
    if category_counter is not None:
        category_counter[category] += 1

    logger.info(f"Category: {category}")
    logger.info("---")
    
    return category

def categorize_emails(hours):
    client = get_imap_client()
    
    client.select_folder('INBOX')
    time_ago = datetime.now() - timedelta(hours=hours)
    date_criterion = time_ago.strftime("%d-%b-%Y")
    all_messages = client.search(['SINCE', date_criterion])
    total_emails = len(all_messages)
    
    sorted_message_ids = get_recent_emails(client, hours)
    # skipped_emails = total_emails - len(sorted_message_ids)
    
    logger.info(f"Total emails in the last {hours} hour(s): {total_emails}")
    # logger.info(f"Emails skipped due to 'SkipInbox' label: {skipped_emails}")
    logger.info(f"Emails to process: {len(sorted_message_ids)}")
    logger.info("---")

    category_counter = Counter()

    for i, msg_id in enumerate(sorted_message_ids, 1):
        logger.info(f"Processing email {i} of {len(sorted_message_ids)}")
        try:
            process_email(client, msg_id, category_counter)
            logger.info("Logging out from Gmail IMAP server")
            client.logout()
        except Exception as e:
            logger.error(f"Error categorizing email: {e}")
            logger.info("Terminating program due to categorization failure")
            break


    logger.info("Category Summary:")
    for category, count in category_counter.most_common():
        logger.info(f"{category}: {count}")

def clean_up_skip_inbox_label(api_type, api_url, api_key, hours, ollama_host2):
    client = get_imap_client()
    
    client.select_folder('INBOX')
    time_ago = datetime.now() - timedelta(hours=hours)
    date_criterion = time_ago.strftime("%d-%b-%Y")
    messages = client.search(['SINCE', date_criterion, 'X-GM-LABELS', 'SkipInbox'])
    
    logger.info(f"Found {len(messages)} emails with 'SkipInbox' label in the last {hours} hour(s)")

    if not messages:
        logger.info("No emails found with 'SkipInbox' label. Checking all folders...")
        for folder in client.list_folders():
            folder_name = folder[2]
            client.select_folder(folder_name)
            messages = client.search(['SINCE', date_criterion, 'X-GM-LABELS', 'SkipInbox'])
            if messages:
                logger.info(f"Found {len(messages)} emails with 'SkipInbox' label in folder: {folder_name}")
                break
        else:
            logger.info("No emails found with 'SkipInbox' label in any folder.")
            client.logout()
            return

    for i, msg_id in enumerate(messages, 1):
        logger.info(f"Processing email {i} of {len(messages)}")
        try:
            fetch_data = client.fetch([msg_id], ['RFC822', 'X-GM-LABELS'])

            for msg_id, data in fetch_data.items():
                try:
                    email_message = email.message_from_bytes(data[b'RFC822'])
                    
                    # Decode the email subject
                    subject, encoding = decode_header(email_message["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")
                    
                    # Get the labels
                    labels = data.get(b'X-GM-LABELS', [])
                    list_of_labels = ", ".join(label.decode() for label in labels)
                    logger.info(f"Email {i} has {len(labels)} labels: {list_of_labels}")
                except KeyError as e:
                    logger.error(f"KeyError processing email {i}: {e}")
                    continue  # Skip to the next email
            
            lower_labels = [label.decode().lower() for label in labels]
            if any(label in lower_labels for label in ["advertisement", "advertisements", "politics"]):
                logger.info(f"Email {i} has 'advertisement', 'advertisements', or 'politics' label. Deleting and expunging...")
                try:
                    delete_and_expunge_email(client, msg_id)
                except Exception as e:
                    logger.error(f"Error deleting and expunging email: {e}")
            elif b'SkipInbox' in labels:
                logger.info(f"Email {i} has 'SkipInbox' label. Recategorizing...")
                try:
                    process_email(client, msg_id)
                    # Fetching the new labels
                    fetch_data = client.fetch([msg_id], ['RFC822', 'X-GM-LABELS'])
                    for msg_id, data in fetch_data.items():
                         labels = data.get(b'X-GM-LABELS', [])
                         list_of_labels = ", ".join(label.decode() for label in labels)
                         logger.info(f"Email {i} has {len(labels)} labels: {list_of_labels}")
                except Exception as e:
                    logger.error(f"Error recategorizing email: {e}")
            else:
                logger.info(f"Email {i} does not have 'SkipInbox' label or targeted labels. Skipping...")
            
            logger.info("-" * 50)
        except Exception as e:
            logger.error(f"Error processing email {i}: {e}")

    logger.info("Logging out from Gmail IMAP server")
    client.logout()


def main():
    logger.info("Starting Gmail Categorizer")
    parser = argparse.ArgumentParser(description="Gmail Categorizer using Ollama or Anthropic API")
    parser.add_argument("--ollama-host", help="Ollama server host (e.g., http://10.1.1.212:11434)")
    parser.add_argument("--ollama-host2", help="Ollama server host (e.g., http://10.1.1.144:11434)")
    parser.add_argument("--anthropic-api-key", help="Anthropic API key")
    parser.add_argument("--hours", type=int, default=1, help="Number of hours to look back for emails (default: 1)")
    parser.add_argument("--skip", action="store_true", help="Clean up and recategorize emails with SkipInbox label")
    args = parser.parse_args()

    if args.ollama_host and args.anthropic_api_key:
        logger.error("Please provide either --ollama-host or --anthropic-api-key, not both")
        return

    if args.ollama_host:
        api_type = "Ollama"
        api_url = args.ollama_host
        api_key = None
    elif args.anthropic_api_key:
        api_type = "Anthropic"
        api_url = None
        api_key = args.anthropic_api_key
    else:
        logger.error("Please provide either --ollama-host or --anthropic-api-key")
        return

    hours = args.hours
    logger.info(f"Using {api_type} API")
    logger.info(f"Fetching emails from the last {hours} hour(s)")

    if not check_api_connectivity(api_type, api_url, api_key):
        logger.error(f"Terminating program due to {api_type} API connectivity failure")
        return

    categorize_emails(hours)
    logger.info("Gmail Categorizer finished")

if __name__ == '__main__':
    main()
