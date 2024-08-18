import os
import pickle
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

def get_recent_emails(service):
    yesterday = datetime.now() - timedelta(days=1)
    query = f'after:{yesterday.strftime("%Y/%m/%d")}'
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
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
    service = get_gmail_service()
    messages = get_recent_emails(service)

    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        subject = ''
        body = ''
        for header in msg['payload']['headers']:
            if header['name'] == 'Subject':
                subject = header['value']
                break
        
        if 'parts' in msg['payload']:
            body = msg['payload']['parts'][0]['body']['data']
        else:
            body = msg['payload']['body']['data']

        category = categorize_email(subject, body)
        print(f"Subject: {subject}")
        print(f"Category: {category}")
        print("---")

if __name__ == '__main__':
    main()
