import os
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

    client = IMAPClient(IMAP_HOST, port=IMAP_PORT, use_uid=True, ssl=True)
    client.login(EMAIL, PASSWORD)
    return client

def get_recent_emails(client):
    client.select_folder('INBOX')
    yesterday = datetime.now() - timedelta(days=1)
    date_criterion = yesterday.strftime("%d-%b-%Y")
    messages = client.search(['SINCE', date_criterion])
    return messages

def categorize_email(subject, body):
    subject = subject.lower()
    body = body.lower()
    
    if 'order' in subject or 'receipt' in subject or 'invoice' in subject:
        return 'Order Receipt'
    elif 'advertisement' in subject or 'promo' in subject or 'sale' in body:
        return 'Advertisement'
    elif 're:' in subject or 'fw:' in subject:
        return 'Personal Response'
    else:
        return 'Other'

def main():
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
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = email_message.get_payload(decode=True).decode()

        category = categorize_email(subject, body)
        print(f"Subject: {subject}")
        print(f"Category: {category}")
        print("---")

    client.logout()

if __name__ == '__main__':
    main()
