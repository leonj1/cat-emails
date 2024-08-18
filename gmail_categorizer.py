import os
import requests
import argparse
import logging
from datetime import datetime, timedelta
from imapclient import IMAPClient
from email import message_from_bytes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def categorize_email(subject, body, ollama_url):
    logger.info("Categorizing email...")
    prompt = f"""Categorize the following email into one of these categories: Order Receipt, Advertisement, Personal Response, or Other.

Subject: {subject}

Body: {body}

Category:"""

    logger.info("Sending request to Ollama server...")
    response = requests.post(f"{ollama_url}/api/generate", json={
        "model": "llama3.1",
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

def main():
    logger.info("Starting Gmail Categorizer")
    parser = argparse.ArgumentParser(description="Gmail Categorizer using Ollama")
    parser.add_argument("--ollama-host", default="http://10.1.1.131:11343", help="Ollama server host (default: http://10.1.1.131:11343)")
    args = parser.parse_args()

    ollama_url = args.ollama_host
    logger.info(f"Using Ollama server at: {ollama_url}")

    client = get_imap_client()
    message_ids = get_recent_emails(client)

    for i, msg_id in enumerate(message_ids, 1):
        logger.info(f"Processing email {i} of {len(message_ids)}")
        email_data = client.fetch([msg_id], ['RFC822'])[msg_id][b'RFC822']
        email_message = message_from_bytes(email_data)
        
        subject = email_message['Subject']
        body = ''

        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors='ignore')
                    break
        else:
            body = email_message.get_payload(decode=True).decode(errors='ignore')

        try:
            category = categorize_email(subject, body, ollama_url)
            logger.info(f"Email {i} - Subject: {subject}")
            logger.info(f"Email {i} - Category: {category}")
            logger.info("---")
        except Exception as e:
            logger.error(f"Error categorizing email: {e}")
            logger.info("Terminating program due to categorization failure")
            break

    logger.info("Logging out from Gmail IMAP server")
    client.logout()
    logger.info("Gmail Categorizer finished")

if __name__ == '__main__':
    main()
