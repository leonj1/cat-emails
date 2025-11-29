#!/usr/bin/env python3
"""
Debug script to investigate Gmail IMAP fetch issues.
"""
import imaplib
import ssl
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from email.utils import parsedate_to_datetime

# Gmail credentials
EMAIL_ADDRESS = "leonj1@gmail.com"
APP_PASSWORD = "ians rrxl nfpq yzsw"
IMAP_SERVER = "imap.gmail.com"
LOOKBACK_HOURS = 1

def main():
    print("=" * 60)
    print("Gmail IMAP Debug Script")
    print("=" * 60)
    print(f"Email: {EMAIL_ADDRESS}")
    print(f"Lookback hours: {LOOKBACK_HOURS}")
    print("=" * 60)

    # Create SSL context
    context = ssl.create_default_context()

    # Connect to Gmail
    print("\n1. Connecting to Gmail IMAP...")
    conn = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)

    print("2. Logging in...")
    conn.login(EMAIL_ADDRESS, APP_PASSWORD)
    print("   Login successful!")

    # List all folders
    print("\n3. Listing all folders:")
    status, folders = conn.list()
    for folder in folders[:10]:  # Show first 10 folders
        print(f"   {folder.decode()}")
    if len(folders) > 10:
        print(f"   ... and {len(folders) - 10} more folders")

    # Select INBOX
    print("\n4. Selecting INBOX...")
    status, data = conn.select("INBOX")
    total_in_inbox = int(data[0].decode())
    print(f"   Total messages in INBOX: {total_in_inbox}")

    # Calculate date threshold
    date_threshold = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    date_str = date_threshold.strftime("%d-%b-%Y")
    print(f"\n5. Date threshold: {date_threshold}")
    print(f"   IMAP date string: {date_str}")

    # Search for recent emails
    search_criteria = f'(SINCE "{date_str}")'
    print(f"\n6. Searching with criteria: {search_criteria}")
    status, message_numbers = conn.search(None, search_criteria)

    msg_nums = message_numbers[0].split()
    print(f"   Found {len(msg_nums)} messages matching SINCE criteria")

    # Now check each message's actual date
    print(f"\n7. Checking actual dates of messages:")
    within_threshold = 0
    outside_threshold = 0

    for num in msg_nums[:20]:  # Check first 20 messages
        try:
            _, msg_data = conn.fetch(num, "(BODY.PEEK[HEADER.FIELDS (DATE SUBJECT FROM)])")
            if msg_data and msg_data[0]:
                header = msg_data[0][1].decode('utf-8', errors='replace')

                # Parse date from header
                for line in header.split('\n'):
                    if line.lower().startswith('date:'):
                        date_str_email = line[5:].strip()
                        try:
                            email_date = parsedate_to_datetime(date_str_email)
                            if email_date.tzinfo is None:
                                email_date = email_date.replace(tzinfo=timezone.utc)

                            is_within = email_date > date_threshold
                            status_emoji = "✅" if is_within else "❌"

                            if is_within:
                                within_threshold += 1
                            else:
                                outside_threshold += 1

                            # Get subject
                            subject = "Unknown"
                            for sline in header.split('\n'):
                                if sline.lower().startswith('subject:'):
                                    subject = sline[8:].strip()[:50]
                                    break

                            print(f"   {status_emoji} {num.decode()}: {email_date.strftime('%Y-%m-%d %H:%M:%S')} - {subject}")
                        except Exception as e:
                            print(f"   ⚠️  {num.decode()}: Could not parse date: {date_str_email[:30]}... - {e}")
                        break
        except Exception as e:
            print(f"   ❌ Error fetching message {num}: {e}")

    if len(msg_nums) > 20:
        print(f"   ... (showing first 20 of {len(msg_nums)} messages)")

    print(f"\n8. Summary:")
    print(f"   Messages within last {LOOKBACK_HOURS} hour(s): {within_threshold}")
    print(f"   Messages outside threshold: {outside_threshold}")

    # Try alternative search - UNSEEN messages
    print(f"\n9. Alternative search - UNSEEN messages:")
    status, unseen_nums = conn.search(None, 'UNSEEN')
    print(f"   Unseen messages: {len(unseen_nums[0].split())}")

    # Try ALL messages in the last day
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%d-%b-%Y")
    print(f"\n10. Messages since yesterday ({yesterday}):")
    status, yesterday_nums = conn.search(None, f'(SINCE "{yesterday}")')
    yesterday_msg_nums = yesterday_nums[0].split()
    print(f"    Found: {len(yesterday_msg_nums)} messages")

    # Check the most recent messages from yesterday's search
    print(f"\n11. Checking most recent emails (last 10 from yesterday's search):")
    for num in yesterday_msg_nums[-10:]:
        try:
            _, msg_data = conn.fetch(num, "(BODY.PEEK[HEADER.FIELDS (DATE SUBJECT)])")
            if msg_data and msg_data[0]:
                header = msg_data[0][1].decode('utf-8', errors='replace')
                date_line = ""
                subject_line = ""
                for line in header.split('\n'):
                    if line.lower().startswith('date:'):
                        date_line = line[5:].strip()
                    if line.lower().startswith('subject:'):
                        subject_line = line[8:].strip()[:60]

                try:
                    email_date = parsedate_to_datetime(date_line)
                    is_recent = email_date > date_threshold
                    emoji = "✅" if is_recent else "❌"
                    print(f"    {emoji} {email_date.strftime('%Y-%m-%d %H:%M:%S %Z')} - {subject_line}")
                except:
                    print(f"    ⚠️  Could not parse: {date_line[:40]}")
        except Exception as e:
            print(f"    Error: {e}")

    # Logout
    print("\n11. Disconnecting...")
    conn.logout()
    print("    Done!")

if __name__ == "__main__":
    main()
