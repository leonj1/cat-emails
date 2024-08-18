import os
import requests
import argparse
from datetime import datetime, timedelta
from imapclient import IMAPClient
from email import message_from_bytes

def get_imap_client():
    # Replace with your Gmail IMAP settings
    IMAP_HOST = 'imap.gmail.com'
    IMAP_PORT = 993
    EMAIL = os.environ.get('GMAIL_EMAIL')
    PASSWORD = os.environ.get('GMAIL_PASSWORD')

    if not EMAIL or not PASSWORD:
        raise ValueError("Please set GMAIL_EMAIL and GMAIL_PASSWORD environment variables")

    print(f"Logging in with username: {EMAIL}")
    print(f"Password length: {len(PASSWORD)}")

    # Encode EMAIL and PASSWORD to ASCII, replacing non-ASCII characters
    EMAIL_encoded = EMAIL.encode('ascii', 'ignore').decode('ascii')
    PASSWORD_encoded = PASSWORD.encode('ascii', 'ignore').decode('ascii')

    client = IMAPClient(IMAP_HOST, port=IMAP_PORT, use_uid=True, ssl=True)
    client.login(EMAIL_encoded, PASSWORD_encoded)
    return client

def get_recent_emails(client):
    client.select_folder('INBOX')
    yesterday = datetime.now() - timedelta(days=1)
    date_criterion = yesterday.strftime("%d-%b-%Y")
    messages = client.search(['SINCE', date_criterion])
    return messages

def categorize_email(subject, body, ollama_url):
    prompt = f"""Categorize the following email into one of these categories: Order Receipt, Advertisement, Personal Response, or Other.

Subject: {subject}

Body: {body}

Category:"""

    response = requests.post(f"{ollama_url}/api/generate", json={
        "model": "llama3.1",
        "prompt": prompt,
        "stream": False
    })

    if response.status_code == 200:
        category = response.json()['response'].strip()
        return category
    else:
        print(f"Error: Unable to categorize email. Status code: {response.status_code}")
        return "Other"

def main():
    parser = argparse.ArgumentParser(description="Gmail Categorizer using Ollama")
    parser.add_argument("--ollama-host", default="http://10.1.1.131:11343", help="Ollama server host (default: http://10.1.1.131:11343)")
    args = parser.parse_args()

    ollama_url = args.ollama_host

    client = get_imap_client()
    message_ids = get_recent_emails(client)

    for msg_id in message_ids:
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
            print(f"Subject: {subject}")
            print(f"Category: {category}")
            print("---")
        except requests.RequestException as e:
            print(f"Error connecting to Ollama server at {ollama_url}: {e}")
            break

    client.logout()

if __name__ == '__main__':
    main()
