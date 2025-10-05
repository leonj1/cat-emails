"""
Example usage of FakeGmailFetcher for testing.

This demonstrates how to use the fake Gmail fetcher in your tests instead of
requiring a real Gmail connection.
"""
from datetime import datetime, timedelta
from tests.fake_gmail_fetcher import FakeGmailFetcher


def example_usage():
    """Demonstrate using the fake Gmail fetcher."""

    # Create the fake fetcher
    fetcher = FakeGmailFetcher()

    # Connect (simulated)
    fetcher.connect()
    print("✓ Connected to fake Gmail")

    # Add some test emails
    print("\n📧 Adding test emails...")

    # Recent email (30 minutes ago)
    recent_date = datetime.utcnow() - timedelta(minutes=30)
    msg_id_1 = fetcher.add_test_email(
        subject="Important Meeting",
        body="Don't forget about the meeting at 3pm",
        sender="boss@company.com",
        date=recent_date
    )
    print(f"  Added: {msg_id_1}")

    # Another recent email (1 hour ago)
    recent_date_2 = datetime.utcnow() - timedelta(hours=1)
    msg_id_2 = fetcher.add_test_email(
        subject="Marketing Newsletter",
        body="Check out our latest deals!",
        sender="marketing@store.com",
        date=recent_date_2
    )
    print(f"  Added: {msg_id_2}")

    # Old email (3 hours ago) - won't show in recent
    old_date = datetime.utcnow() - timedelta(hours=3)
    msg_id_3 = fetcher.add_test_email(
        subject="Old Email",
        body="This is an old email",
        sender="old@example.com",
        date=old_date
    )
    print(f"  Added: {msg_id_3}")

    # Get recent emails (last 2 hours)
    print("\n📬 Fetching emails from last 2 hours...")
    recent_emails = fetcher.get_recent_emails(hours=2)
    print(f"Found {len(recent_emails)} recent emails:")

    for email in recent_emails:
        print(f"  - {email['Subject']} (from: {email['From']})")
        body = fetcher.get_email_body(email)
        print(f"    Body: {body[:50]}...")

    # Add labels to emails
    print("\n🏷️  Adding labels...")
    fetcher.add_label(msg_id_1, "Important")
    fetcher.add_label(msg_id_1, "Work")
    fetcher.add_label(msg_id_2, "Marketing")

    print(f"  Labels for message 1: {fetcher.get_labels(msg_id_1)}")
    print(f"  Labels for message 2: {fetcher.get_labels(msg_id_2)}")

    # Delete an email
    print("\n🗑️  Deleting marketing email...")
    fetcher.delete_email(msg_id_2)
    print(f"  Message deleted: {fetcher.is_deleted(msg_id_2)}")

    # Get recent emails again (deleted one won't show)
    print("\n📬 Fetching emails again (after deletion)...")
    recent_emails = fetcher.get_recent_emails(hours=2)
    print(f"Found {len(recent_emails)} recent emails:")
    for email in recent_emails:
        print(f"  - {email['Subject']}")

    # Disconnect
    fetcher.disconnect()
    print("\n✓ Disconnected")

    # Clear all data
    print("\n🧹 Clearing all data...")
    fetcher.clear()
    fetcher.connect()
    emails = fetcher.get_recent_emails()
    print(f"Emails after clear: {len(emails)}")


def example_testing_workflow():
    """Example of using fake fetcher in a test."""
    print("\n" + "="*60)
    print("EXAMPLE: Testing Email Processing Workflow")
    print("="*60 + "\n")

    fetcher = FakeGmailFetcher()
    fetcher.connect()

    # Setup: Add emails with different categories
    fetcher.add_test_email(
        subject="Special Offer!",
        body="Buy now and save 50%!",
        sender="deals@shopping.com"
    )

    fetcher.add_test_email(
        subject="Weekly Team Update",
        body="Here's what we accomplished this week...",
        sender="manager@company.com"
    )

    fetcher.add_test_email(
        subject="Your bank statement",
        body="Your monthly statement is ready",
        sender="noreply@bank.com"
    )

    # Simulate email processing
    emails = fetcher.get_recent_emails(hours=24)
    print(f"Processing {len(emails)} emails...\n")

    for email in emails:
        subject = email['Subject']
        body = fetcher.get_email_body(email)
        message_id = email['Message-ID']

        # Categorize (simplified example)
        if "offer" in subject.lower() or "buy" in body.lower():
            category = "Marketing"
            action = "delete"
        elif "team" in subject.lower() or "manager" in email['From']:
            category = "Work"
            action = "label"
        elif "bank" in email['From']:
            category = "Financial"
            action = "label"
        else:
            category = "Other"
            action = "keep"

        print(f"📧 {subject}")
        print(f"   Category: {category}")
        print(f"   Action: {action}")

        # Apply action
        if action == "delete":
            fetcher.delete_email(message_id)
            print(f"   ✓ Deleted")
        elif action == "label":
            fetcher.add_label(message_id, category)
            print(f"   ✓ Labeled as '{category}'")

        print()

    # Verify results
    print("=" * 60)
    print("RESULTS:")
    print("=" * 60)
    remaining = fetcher.get_recent_emails(hours=24)
    print(f"Remaining emails: {len(remaining)}")
    print(f"Deleted emails: {len(fetcher.deleted_message_ids)}")
    print(f"Labeled emails: {len(fetcher.labels)}")


if __name__ == "__main__":
    example_usage()
    example_testing_workflow()
