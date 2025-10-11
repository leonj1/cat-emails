import os
import argparse
import logging
from utils.logger import get_logger
from email.header import decode_header
from collections import Counter
from datetime import datetime, timedelta
from imapclient import IMAPClient
from email import message_from_bytes
from bs4 import BeautifulSoup
from anthropic import Anthropic
from send_email_to_kafka import send_email_to_kafka

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = get_logger(__name__)

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

def get_recent_emails(client, hours):
    logger.info("Selecting INBOX folder...")
    client.select_folder('INBOX')
    time_ago = datetime.now() - timedelta(hours=hours)
    date_criterion = time_ago.strftime("%d-%b-%Y")
    logger.info(f"Searching for emails since {date_criterion}...")
    messages = client.search(['SINCE', date_criterion, 'NOT', 'KEYWORD', 'bogus-asdf'])
    logger.info(f"Found {len(messages)} recent emails")
    
    total_messages = len(messages)
    for index, msg_id in enumerate(messages, 1):
        logger.info(f"Processing {index} of {total_messages} emails, ID: {msg_id}")
        try:
            send_email_to_kafka(msg_id)
        except Exception as e:
            logger.info(f"Problem fetching recent email [{msg_id}]: {e}")
    
    logger.info("Emails sorted by timestamp in descending order")
    return None

from datetime import datetime

# The expected format for the date? dd-MMM-yyyy
def get_emails_by_date_range(start_date_str, end_date_str):
    """
    Fetch email message IDs within a specified date range.

    :param start_date_str: Start date (inclusive) as a string in format "dd-MMM-yyyy"
    :param end_date_str: End date (inclusive) as a string in format "dd-MMM-yyyy"
    :return: List of message IDs
    """
    client = get_imap_client()    
    logger.info("Selecting INBOX folder...")
    client.select_folder('INBOX')

    start_date = datetime.strptime(start_date_str, "%d-%b-%Y")
    end_date = datetime.strptime(end_date_str, "%d-%b-%Y")

    start_criterion = start_date.strftime("%d-%b-%Y")
    end_criterion = end_date.strftime("%d-%b-%Y")
    
    logger.info(f"Searching for emails between {start_criterion} and {end_criterion}...")
    messages = client.search(['SINCE', start_criterion, 'BEFORE', end_criterion, 'NOT', 'KEYWORD', 'bogus-asdf'])
    
    total_messages = len(messages)
    logger.info(f"Found {total_messages} emails within the specified date range")
    for index, msg_id in enumerate(messages, 1):
        logger.info(f"Processing {index} of {total_messages} emails, ID: {msg_id}")
        try:
            send_email_to_kafka(msg_id)
        except Exception as e:
            logger.info(f"Problem fetching recent email [{msg_id}]: {e}")

    return messages


def send_recent_emails_to_kafka(hours):
    client = get_imap_client()    
    client.select_folder('INBOX')
    time_ago = datetime.now() - timedelta(hours=hours)
    get_recent_emails(client, hours)


def main():
    logger.info("Starting Gmail Categorizer")
    parser = argparse.ArgumentParser(description="Gmail Categorizer using Ollama or Anthropic API")
    parser.add_argument("--hours", type=int, default=1, help="Number of hours to look back for emails")
    parser.add_argument("--start", help="Start date")
    parser.add_argument("--end", help="End date")
    args = parser.parse_args()

    hours = args.hours
    start = args.start
    end = args.end
    
    # validate start and end are in format dd-MMM-yyyy
    if start:
        try:
            datetime.strptime(start, "%d-%b-%Y")
        except ValueError:
            logger.error("Invalid start date format. Expected format: dd-MMM-yyyy. Example: 01-Jan-2021")
            return
    if end:
        try:
            datetime.strptime(end, "%d-%b-%Y")
        except ValueError:
            logger.error("Invalid end date format. Expected format: dd-MMM-yyyy. Example: 01-Jan-2021")
            return

    if hours > 0:
        logger.info(f"Fetching emails from the last {hours} hour(s)")
        send_recent_emails_to_kafka(hours)

    if start != "" and end != "":
        logger.info(f"Fetching emails from {start} to {end}")
        get_emails_by_date_range(start, end)

    logger.info("Gmail Categorizer finished")

if __name__ == '__main__':
    main()
