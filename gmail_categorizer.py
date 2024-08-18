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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_ollama_connectivity(ollama_url, max_retries=3, retry_delay=5):
    logger.info(f"Checking connectivity to Ollama host: {ollama_url}")
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{ollama_url}/api/tags")
            if response.status_code == 200:
                logger.info("Successfully connected to Ollama host")
                return True
            else:
                logger.warning(f"Failed to connect to Ollama host. Status code: {response.status_code}")
        except requests.RequestException as e:
            logger.warning(f"Error connecting to Ollama host: {e}")
        
        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    logger.error("Failed to connect to Ollama host after multiple attempts")
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

def get_recent_emails(client):
    logger.info("Selecting INBOX folder...")
    client.select_folder('INBOX')
    yesterday = datetime.now() - timedelta(days=1)
    date_criterion = yesterday.strftime("%d-%b-%Y")
    logger.info(f"Searching for emails since {date_criterion}...")
    messages = client.search(['SINCE', date_criterion])
    logger.info(f"Found {len(messages)} recent emails")
    return messages

def get_sender_email(email_message):
    sender = email_message['From']
    if '<' in sender:
        return sender.split('<')[1].split('>')[0]
    return sender

def ollama_generic(purpose, prompt, subject, body, sender, ollama_url):
    logger.info(f"Initiating {purpose}...")
    logger.info("Sending request to Ollama server...")
    response = requests.post(f"{ollama_url}/api/generate", json={
        "model": "llama3.1:8b",
        "prompt": prompt,
        "stream": False
    })

    if response.status_code == 200:
        resp = response.json()['response'].strip()
        logger.info(f"LLM response completed: {resp}")
        return resp
    else:
        logger.error(f"Error: Unable to {purpose}. Status code: {response.status_code}")
        raise Exception(f"Failed to {purpose}")

def foo(subject, body, sender, ollama_url):
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

Examples:
- Email from shipment-tracking@amazon.com about a package: "Order Shipped"
- Email from jcpenny.com about a sale: "Advertisement"
- Email from chase.com: "Bank"
- Email from a gmail.com address: "Personal"
- Email about a security breach: "Alert"
- Contents or Subject that talk about politics or political parties: "Politics"

For each email, analyze the sender's email address, subject line, and any provided content. Then respond with only the category label, nothing else.

Email to categorize:
Sender: [{sender}]
Subject: [{subject}]
Content: [{body}]
"""

    return ollama_generic(purpose, prompt, subject, body, sender, ollama_url)


def categorize_email(subject, body, sender, ollama_url):
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

Subject: {subject}

Body: {body}

Category: [Single word]"""

    logger.info("Sending request to Ollama server...")
    response = requests.post(f"{ollama_url}/api/generate", json={
        "model": "llama3.1:8b",
        "prompt": prompt,
        "stream": False
    })

    if response.status_code == 200:
        category = response.json()['response'].strip()
        logger.info(f"Email categorized as: {category}")
        return category
    else:
        logger.error(f"Error: Unable to categorize email. Status code: {response.status_code}")
        raise Exception("Failed to categorize email")

def is_email_summary_advertisement(subject, summary, ollama_url):
    logger.info("Summarizing Email Category...")
    prompt = f"""You are a laconic assistant that only speaks in single words. Could the following email summary be considered Advertisement? Respond with Yes or No and no trailing period.

Subject: {subject}

Summary: {summary}

Category: [Single word]"""

    logger.info("Sending request to Ollama server...")
    response = requests.post(f"{ollama_url}/api/generate", json={
        "model": "llama3.1:8b",
        "prompt": prompt,
        "stream": False
    })

    if response.status_code == 200:
        category = response.json()['response'].strip()
        logger.info(f"Email categorized as: {category}")
        return category
    else:
        logger.error(f"Error: Unable to summarize email. Status code: {response.status_code}")
        raise Exception("Failed to summarize email")

def set_email_label(client, msg_id, label):
    logger.info(f"Setting label '{label}' for email {msg_id}")
    try:
        client.add_gmail_labels(msg_id, [label])
        logger.info(f"Label '{label}' set successfully")
    except Exception as e:
        logger.error(f"Error setting label: {e}")

def is_human_readable(text, ollama_url):
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
    response = requests.post(f"{ollama_url}/api/generate", json={
        "model": "llama3.1:8b",
        "prompt": prompt,
        "stream": False
    })

    if response.status_code == 200:
        category = response.json()['response'].strip()
        logger.info(f"Text categorized as: {category}")
        return category
    else:
        logger.error(f"Error: Unable to categorize text. Status code: {response.status_code}")
        raise Exception("Failed to categorize text")

def check_string(text):
    # Convert to lowercase for case-insensitive comparison
    text_lower = text.lower()

    # Check for 'email' or 'html'
    if 'email' in text_lower or 'html' in text_lower:
        return True

    # Check if more than 2 words
    if len(text.split()) > 2:
        return True

    return False

def main():
    logger.info("Starting Gmail Categorizer")
    parser = argparse.ArgumentParser(description="Gmail Categorizer using Ollama")
    parser.add_argument("--ollama-host", default="http://10.1.1.131:11343", help="Ollama server host (default: http://10.1.1.131:11343)")
    args = parser.parse_args()

    ollama_url = args.ollama_host
    logger.info(f"Using Ollama server at: {ollama_url}")

    if not check_ollama_connectivity(ollama_url):
        logger.error("Terminating program due to Ollama connectivity failure")
        return

    client = get_imap_client()
    message_ids = get_recent_emails(client)

    category_counter = Counter()

    for i, msg_id in enumerate(message_ids, 1):
        logger.info(f"Processing email {i} of {len(message_ids)}")
        email_data = client.fetch([msg_id], ['RFC822'])[msg_id][b'RFC822']
        email_message = message_from_bytes(email_data)
        
        subject = email_message['Subject']
        sender = get_sender_email(email_message)
        body = ''

        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors='ignore')
                    break
        else:
            body = email_message.get_payload(decode=True).decode(errors='ignore')

        try:
            category = foo(subject, body, sender, ollama_url)
            logger.info(f"Email {i} - Subject: {subject}")
            logger.info(f"Email {i} - Sender: {sender}")
            logger.info(f"Email {i} - Category: {category}")
            logger.info("---")
            category_counter[category] += 1
            
            if category.lower() == "advertisement":
                set_email_label(client, msg_id, "Advertisement")
            if category.lower() == "politics":
                set_email_label(client, msg_id, "Politics")
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
