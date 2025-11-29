"""
Tests for FakeGmailFetcher to ensure it properly implements GmailFetcherInterface.
"""
import unittest
from datetime import datetime, timedelta
from tests.fake_gmail_fetcher import FakeGmailFetcher


class TestFakeGmailFetcher(unittest.TestCase):
    """Test cases for FakeGmailFetcher."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = FakeGmailFetcher()

    def test_connect(self):
        """Test connecting to Gmail."""
        self.assertFalse(self.fetcher.connected)
        self.fetcher.connect()
        self.assertTrue(self.fetcher.connected)

    def test_disconnect(self):
        """Test disconnecting from Gmail."""
        self.fetcher.connect()
        self.assertTrue(self.fetcher.connected)
        self.fetcher.disconnect()
        self.assertFalse(self.fetcher.connected)

    def test_get_recent_emails_requires_connection(self):
        """Test that get_recent_emails requires a connection."""
        with self.assertRaises(RuntimeError):
            self.fetcher.get_recent_emails()

    def test_get_recent_emails_empty(self):
        """Test getting recent emails when none exist."""
        self.fetcher.connect()
        emails = self.fetcher.get_recent_emails()
        self.assertEqual(len(emails), 0)

    def test_add_test_email(self):
        """Test adding a test email."""
        message_id = self.fetcher.add_test_email(
            subject="Test Subject",
            body="Test Body",
            sender="sender@example.com"
        )

        self.assertIsNotNone(message_id)
        self.assertTrue(message_id.startswith("<test-"))

    def test_get_recent_emails_with_data(self):
        """Test getting recent emails with test data."""
        self.fetcher.connect()

        # Add some test emails
        self.fetcher.add_test_email(
            subject="Email 1",
            body="Body 1",
            sender="sender1@example.com"
        )
        self.fetcher.add_test_email(
            subject="Email 2",
            body="Body 2",
            sender="sender2@example.com"
        )

        emails = self.fetcher.get_recent_emails(hours=2)
        self.assertEqual(len(emails), 2)

    def test_get_recent_emails_time_filter(self):
        """Test that get_recent_emails filters by time."""
        self.fetcher.connect()

        # Add old email (3 hours ago)
        old_date = datetime.utcnow() - timedelta(hours=3)
        self.fetcher.add_test_email(
            subject="Old Email",
            body="Old Body",
            date=old_date
        )

        # Add recent email (1 hour ago)
        recent_date = datetime.utcnow() - timedelta(hours=1)
        self.fetcher.add_test_email(
            subject="Recent Email",
            body="Recent Body",
            date=recent_date
        )

        # Get emails from last 2 hours
        emails = self.fetcher.get_recent_emails(hours=2)
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]['Subject'], "Recent Email")

    def test_get_email_body(self):
        """Test extracting email body."""
        email = {
            'Subject': 'Test',
            'Body': 'This is the email body'
        }

        body = self.fetcher.get_email_body(email)
        self.assertEqual(body, 'This is the email body')

    def test_get_email_body_missing(self):
        """Test extracting email body when Body field is missing."""
        email = {'Subject': 'Test'}
        body = self.fetcher.get_email_body(email)
        self.assertEqual(body, '')

    def test_add_label(self):
        """Test adding a label to a message."""
        self.fetcher.connect()

        message_id = self.fetcher.add_test_email(
            subject="Test",
            body="Test Body"
        )

        result = self.fetcher.add_label(message_id, "Important")
        self.assertTrue(result)

        labels = self.fetcher.get_labels(message_id)
        self.assertIn("Important", labels)

    def test_add_label_requires_connection(self):
        """Test that add_label requires a connection."""
        result = self.fetcher.add_label("test-id", "Label")
        self.assertFalse(result)

    def test_add_multiple_labels(self):
        """Test adding multiple labels to the same message."""
        self.fetcher.connect()

        message_id = self.fetcher.add_test_email(
            subject="Test",
            body="Test Body"
        )

        self.fetcher.add_label(message_id, "Important")
        self.fetcher.add_label(message_id, "Work")
        self.fetcher.add_label(message_id, "Urgent")

        labels = self.fetcher.get_labels(message_id)
        self.assertEqual(len(labels), 3)
        self.assertIn("Important", labels)
        self.assertIn("Work", labels)
        self.assertIn("Urgent", labels)

    def test_add_duplicate_label(self):
        """Test that adding the same label twice doesn't duplicate it."""
        self.fetcher.connect()

        message_id = self.fetcher.add_test_email(
            subject="Test",
            body="Test Body"
        )

        self.fetcher.add_label(message_id, "Important")
        self.fetcher.add_label(message_id, "Important")

        labels = self.fetcher.get_labels(message_id)
        self.assertEqual(len(labels), 1)

    def test_delete_email(self):
        """Test deleting an email."""
        self.fetcher.connect()

        message_id = self.fetcher.add_test_email(
            subject="Test",
            body="Test Body"
        )

        result = self.fetcher.delete_email(message_id)
        self.assertTrue(result)
        self.assertTrue(self.fetcher.is_deleted(message_id))

    def test_delete_email_requires_connection(self):
        """Test that delete_email requires a connection."""
        result = self.fetcher.delete_email("test-id")
        self.assertFalse(result)

    def test_deleted_emails_not_in_recent(self):
        """Test that deleted emails are not returned in get_recent_emails."""
        self.fetcher.connect()

        message_id = self.fetcher.add_test_email(
            subject="Test",
            body="Test Body"
        )

        # Verify it's returned before deletion
        emails = self.fetcher.get_recent_emails()
        self.assertEqual(len(emails), 1)

        # Delete it
        self.fetcher.delete_email(message_id)

        # Verify it's not returned after deletion
        emails = self.fetcher.get_recent_emails()
        self.assertEqual(len(emails), 0)

    def test_get_labels_nonexistent_message(self):
        """Test getting labels for a nonexistent message."""
        labels = self.fetcher.get_labels("nonexistent-id")
        self.assertEqual(labels, [])

    def test_is_deleted_nonexistent_message(self):
        """Test checking if a nonexistent message is deleted."""
        result = self.fetcher.is_deleted("nonexistent-id")
        self.assertFalse(result)

    def test_clear(self):
        """Test clearing all data."""
        self.fetcher.connect()

        # Add some data
        message_id = self.fetcher.add_test_email(
            subject="Test",
            body="Test Body"
        )
        self.fetcher.add_label(message_id, "Important")
        self.fetcher.delete_email(message_id)

        # Clear
        self.fetcher.clear()

        # Verify everything is cleared
        emails = self.fetcher.get_recent_emails()
        self.assertEqual(len(emails), 0)
        self.assertEqual(len(self.fetcher.labels), 0)
        self.assertEqual(len(self.fetcher.deleted_message_ids), 0)

    def test_custom_message_id(self):
        """Test adding email with custom message ID."""
        custom_id = "<custom-123@example.com>"
        message_id = self.fetcher.add_test_email(
            subject="Test",
            body="Test Body",
            message_id=custom_id
        )

        self.assertEqual(message_id, custom_id)

    def test_email_fields(self):
        """Test that added emails have all expected fields."""
        self.fetcher.connect()

        message_id = self.fetcher.add_test_email(
            subject="Test Subject",
            body="Test Body",
            sender="sender@example.com"
        )

        emails = self.fetcher.get_recent_emails()
        self.assertEqual(len(emails), 1)

        email = emails[0]
        self.assertEqual(email['Subject'], "Test Subject")
        self.assertEqual(email['Body'], "Test Body")
        self.assertEqual(email['From'], "sender@example.com")
        self.assertIn('Message-ID', email)
        self.assertIn('Date', email)
        self.assertIn('To', email)

    def test_auto_incrementing_message_ids(self):
        """Test that auto-generated message IDs increment."""
        id1 = self.fetcher.add_test_email(subject="Test 1", body="Body 1")
        id2 = self.fetcher.add_test_email(subject="Test 2", body="Body 2")
        id3 = self.fetcher.add_test_email(subject="Test 3", body="Body 3")

        self.assertNotEqual(id1, id2)
        self.assertNotEqual(id2, id3)
        self.assertNotEqual(id1, id3)

    def test_clear_resets_message_id_counter(self):
        """Test that clear resets the message ID counter."""
        id1 = self.fetcher.add_test_email(subject="Test 1", body="Body 1")
        self.fetcher.clear()
        id2 = self.fetcher.add_test_email(subject="Test 2", body="Body 2")

        # After clear, counter should reset
        self.assertEqual(id1, id2)

    def test_get_blocked_domains(self):
        """Test that get_blocked_domains returns the internal _blocked_domains set."""
        blocked_domains = self.fetcher.get_blocked_domains()
        self.assertIsInstance(blocked_domains, set)
        self.assertEqual(blocked_domains, set())


if __name__ == '__main__':
    unittest.main()
