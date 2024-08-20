import os
import requests
import argparse
import logging
import time
from collections import Counter
from datetime import datetime, timedelta
from imapclient import IMAPClient
from email import message_from_bytes
import imaplib
from bs4 import BeautifulSoup
from anthropic import Anthropic

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ollamas = {
    "http://10.1.1.212:11434": {"model": "llama3.1:8b", "num_ctx": 4096},
    "http://10.1.1.131:11434": {"model": "llama3:latest", "num_ctx": 8192}
}

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
    messages = client.search(['SINCE', date_criterion, 'NOT', 'KEYWORD', 'SkipInbox'])
    logger.info(f"Found {len(messages)} recent emails without 'SkipInbox' label")
    return messages

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
    purpose = "Categorize email NEW"
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


def categorize_email(subject, body, sender, api_type, model, api_url=None, api_key=None):
    if sender.endswith('@accounts.google.com'):
        logger.info("Email from accounts.google.com, categorizing as Personal")
        return "Personal"
    if sender.endswith('shipment-tracking@amazon.com'):
        logger.info("Email from Amazon shipment, categorizing as Shipment")
        return "Shipment"
    if sender.endswith('alerts@deadmansnitch.com'):
        logger.info("Alert Email from Deadmansnitch, categorizing as Alert")
        return "Alert"
    logger.info("Categorizing email...")
    prompt = f"""You are a laconic assistant that only speaks in single words. You will be given the content of an email. Your task is to categorize this email into one of the following categories:

- Order Receipt
- Advertisement
- Personal Response
- Other

Please analyze the content of the email and determine which category it best fits into. Consider the purpose, tone, and typical characteristics of each category.
Respond with only the category name, using one or two words at most. Do not provide any explanation or additional commentary.
Instead of using the category name "Spam" use "Junk" instead.

Subject: {subject}

Body: {body}

Category: [Single word]"""

    return generate_response("categorize email", prompt, api_type, model, api_url, api_key)

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
    logger.info(f"Setting label '{label}' for email {msg_id}")
    try:
        client.add_gmail_labels(msg_id, [label])
        if label == "SkipInbox":
            client.remove_gmail_labels(msg_id, ["\\Inbox"])
            logger.info(f"Inbox label removed for email {msg_id}")
    except Exception as e:
        logger.error(f"Error setting label or removing Inbox label: {e}")

def extract_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator=' ', strip=True)

def is_human_readable(text, api_type, model, api_url=None, api_key=None):
    logger.info(f"Checking if text is human readable: {text}")
    prompt = f"""
You are an expert in natural language processing and computer science. Your task is to analyze the following text and determine whether it's human-readable or computer-oriented. 

Human-readable text typically has these characteristics:
1. Follows grammatical structures of natural language
2. Uses common words and phrases
3. Has a logical flow of ideas
4. Contains punctuation and proper capitalization
5. May include some technical terms, but in a context understandable to humans

Computer-oriented text typically has these characteristics:
1. Contains programming code, markup, or machine-readable data formats
2. Uses specialized syntax or symbols not common in natural language
3. May have long strings of numbers or seemingly random characters
4. Often lacks natural language sentence structure
5. May include file paths, URLs, or other computer-specific references

Please analyze the following text and respond with either "Human-readable" or "Computer-oriented", followed by a brief explanation of your reasoning.

Text to analyze: {text}
"""
    return generate_response("categorize text", prompt, api_type, model, api_url, api_key)

def has_two_words_or_less(text):
    # Split the string into words
    words = text.split()
    
    # Check if the number of words is 2 or less
    return len(words) <= 2

def word_in_list(word, string_list):
    # Convert the word to lowercase for case-insensitive comparison
    word = word.lower()
    
    # Iterate through each string in the list
    for string in string_list:
        # Split the string into words and convert to lowercase
        words = string.lower().split()
        
        # Check if the word is in the list of words
        if word in words:
            return True
    
    # If we've checked all strings and haven't found the word, return False
    return False

def main():
    logger.info("Starting Gmail Categorizer")
    parser = argparse.ArgumentParser(description="Gmail Categorizer using Ollama or Anthropic API")
    parser.add_argument("--ollama-host", help="Ollama server host (e.g., http://10.1.1.212:11434)")
    parser.add_argument("--ollama-host2", help="Ollama server host (e.g., http://10.1.1.131:11434)")
    parser.add_argument("--anthropic-api-key", help="Anthropic API key")
    parser.add_argument("--hours", type=int, default=1, help="Number of hours to look back for emails (default: 1)")
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

    client = get_imap_client()
    
    # Get total number of emails in the specified time range
    client.select_folder('INBOX')
    time_ago = datetime.now() - timedelta(hours=hours)
    date_criterion = time_ago.strftime("%d-%b-%Y")
    all_messages = client.search(['SINCE', date_criterion])
    total_emails = len(all_messages)
    
    # Get emails without 'SkipInbox' label
    message_ids = get_recent_emails(client, hours)
    skipped_emails = total_emails - len(message_ids)
    
    logger.info(f"Total emails in the last {hours} hour(s): {total_emails}")
    logger.info(f"Emails skipped due to 'SkipInbox' label: {skipped_emails}")
    logger.info(f"Emails to process: {len(message_ids)}")

    category_counter = Counter()

    for i, msg_id in enumerate(message_ids, 1):
        logger.info(f"Processing email {i} of {len(message_ids)}")
        email_data = client.fetch([msg_id], ['RFC822'])[msg_id][b'RFC822']
        email_message = message_from_bytes(email_data)
        
        subject = email_message['Subject']
        sender = get_sender_email(email_message)
        timestamp = email_message['Date']
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

        try:
            hide = ["advertisement", "politics", "notification", "helpful", "information", "spam", "marketting", "disclaimer", "marketing"]
            ok = [
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
            category = categorize_email_new(subject, body, sender, api_type, ollamas[api_url], api_url, api_key)
            logger.info(f"Email {i} - Timestamp: {timestamp}")
            logger.info(f"Email {i} - Sender: {sender}")
            logger.info(f"Email {i} - Subject: {subject}")
            category_counter[category] += 1
            if has_two_words_or_less(category.lower()):
                set_email_label(client, msg_id, category.lower())
            else:
                proposed_category = is_email_summary_advertisement(subject, category, api_type, ollamas[args.ollama_host2], args.ollama_host2, api_key)
                if has_two_words_or_less(proposed_category.lower()):
                    set_email_label(client, msg_id, proposed_category.lower())
                    category = proposed_category
            # checking if the category is in the accepted categories list to keep. If not the set label to skip the inbox
            if not word_in_list(category, ok):
                set_email_label(client, msg_id, "SkipInbox")
            logger.info(f"Email {i} - Category: {category}")
            logger.info("---")
        except Exception as e:
            logger.error(f"Error categorizing email: {e}")
            logger.info("Terminating program due to categorization failure")
            break

    logger.info("Logging out from Gmail IMAP server")
    client.logout()

    logger.info("Category Summary:")
    for category, count in category_counter.most_common():
        logger.info(f"{category}: {count}")

    logger.info("Gmail Categorizer finished")

if __name__ == '__main__':
    main()
