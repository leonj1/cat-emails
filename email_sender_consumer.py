import json
import logging
import os
from bs4 import BeautifulSoup
from imapclient import IMAPClient
from kafka import KafkaProducer

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



def send_email_to_kafka(msg_id: str, kafka_topic: str = 'gmail_messages', kafka_server: str = 'localhost:9092'):
    """
    Fetch a Gmail message by its ID and send it to a Kafka topic.
    
    :param msg_id: The Gmail message ID
    :param kafka_topic: The Kafka topic to send the message to (default: 'gmail_messages')
    :param kafka_server: The Kafka server address (default: 'localhost:9111')
    """
    # Initialize Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=[kafka_server],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    has_message_published = False
    
    try:
        # Prepare the message for Kafka
        kafka_message = {
            'msg_id': msg_id,
        }
        
        # Send the message to Kafkagmail
        logger.info("Publishing to Kafka")
        future = producer.send(kafka_topic, value=kafka_message)
        record_metadata = future.get(timeout=10)
        
        logger.info(f"Message sent to Kafka topic {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
        has_message_published = True
    except Exception as e:
        logger.info(f"Error sending message to Kafka: {str(e)}")
    
    finally:
        producer.close()
        
    if not has_message_published:
        raise Exception(f"Failed to publish message {msg_id} to Kafka")
