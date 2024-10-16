import ell
import openai
import json
import logging
import os
import re
from kafka import KafkaConsumer
from imapclient import IMAPClient
from email import message_from_bytes
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ell.init(verbose=False, store='./logdir')

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

def capitalize_words(text):
    return ' '.join(word.capitalize() for word in text.split())


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

def extract_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator=' ', strip=True)

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

def mark_email_as_unread(client, msg_id):
    logger.info(f"Marking email {msg_id} as unread")
    try:
        client.remove_flags([msg_id], [b'\\Seen'])
        logger.info(f"Email {msg_id} marked as unread successfully")
    except Exception as e:
        logger.error(f"Error marking email {msg_id} as unread: {e}")

def delete_and_expunge_email(client, msg_id):
    logger.info(f"Deleting and expunging email {msg_id}")
    try:
        client.delete_messages([msg_id])
        client.expunge()
        logger.info(f"Email {msg_id} deleted and expunged successfully")
    except Exception as e:
        logger.error(f"Error deleting and expunging email {msg_id}: {e}")

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

    ignore_existing_labels = True
    
    if not ignore_existing_labels:
        if existing_email_labels is not None and len(existing_email_labels) > 0:
            if len(existing_email_labels) == 1 and existing_email_labels[0] == b'\\Important':
                pass
            else:
                logger.info(f"Email - {msg_id} has labels {existing_email_labels}. Skipping...")
                logger.info("---")
                return existing_email_labels
    
    category = categorize_email_ell_for_me(contents_cleaned)
    category = category.replace('"', '').replace("'", "").replace('*', '').replace('=', '').replace('+', '').replace('-', '').replace('_', '')
    category_lower = category.lower()
    
    logger.info("************")
    logger.info(f"Email - Timestamp: {timestamp}")
    logger.info(f"Email - Sender: {sender}")
    logger.info(f"Email - Subject: {subject}")
    if category_lower != "other" and len(category_lower) > 4 and category_lower in ok:
        set_email_label(client, msg_id, category)
        mark_email_as_unread(client, msg_id)
        logger.info("Email - Email is meant for me")
        logger.info("************")
    else:
        category = categorize_email_ell_marketing(contents_cleaned)
        category = category.replace('"', '').replace("'", "")
        category_lower = category.lower()
        if category_lower != "other" and len(category_lower) > 4 and len(category_lower) <= 40:
            set_email_label(client, msg_id, category)
            delete_and_expunge_email(client, msg_id)
            logger.info("Email - Email is an advertisement")
        else:
            category = categorize_email_ell_generic(contents_cleaned)
            category = category.replace('"', '').replace("'", "")
            if len(category) > 4 and len(category) < 40:
                set_email_label(client, msg_id, category)
                delete_and_expunge_email(client, msg_id)
                logger.info("Email - Email is generic")
            else:
                logger.info(f"Email - Could not categorize email {msg_id}. Skipping... ***")
    logger.info("************")

    if category_counter is not None:
        category_counter[category] += 1

    logger.info(f"Email - Category: {category}")
    logger.info("---")
    
    return category

def listen_to_kafka_topic(topic: str = 'gmail_messages', bootstrap_servers: str = 'localhost:9092'):
    """
    Listen to a Kafka topic and print incoming messages.
    
    :param topic: The Kafka topic to listen to (default: 'gmail_messages')
    :param bootstrap_servers: The Kafka server address (default: 'localhost:9111')
    """
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=[bootstrap_servers],
        auto_offset_reset='latest',
        enable_auto_commit=True,
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    client = get_imap_client()    
    client.select_folder('INBOX')
    
    logger.info(f"Starting to listen to Kafka topic: {topic}")
    
    try:
        for message in consumer:
            logger.info(f"Received message from partition {message.partition}, offset {message.offset}:")
            msg_id = message.value['msg_id']
            logger.info(f"Message ID: {msg_id}")
            try:
                process_email(client, msg_id)
            except Exception as e:
                logger.error(f"Error categorizing email: {e}")
                client = get_imap_client()    
                client.select_folder('INBOX')

            logger.info("-" * 50)
    
    except KeyboardInterrupt:
        logger.info("Listener stopped by user.")
    finally:
        consumer.close()
        client.logout()
        logger.info("Kafka consumer closed.")

if __name__ == "__main__":
    listen_to_kafka_topic()
