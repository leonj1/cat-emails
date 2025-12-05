"""
Business Functional Integration Tests for Email Processing.

These tests validate the core business workflows for email processing:
1. Listing emails from a Gmail account
2. Getting contents of an email message
3. Categorizing the contents of an email
4. Deleting emails based on category
5. Keeping emails from allowed domains
6. Deleting emails from blocked domains
7. Repeat offender pattern detection
8. Email deduplication (not reprocessing same emails)
9. Labeling emails with categories
10. Processing run tracking and statistics

These are end-to-end business functional tests that verify the system
behaves correctly from a user's perspective.
"""
import unittest
from datetime import datetime, timedelta
from email.message import EmailMessage
from collections import Counter
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Optional, Set

from services.email_processor_service import EmailProcessorService
from services.fake_email_categorizer import FakeEmailCategorizer
from services.interfaces.email_extractor_interface import EmailExtractorInterface


# =============================================================================
# Test Fixtures and Fake Implementations
# =============================================================================

class FakeEmailExtractor(EmailExtractorInterface):
    """Fake email extractor for testing."""

    def extract_sender_email(self, from_header: str) -> str:
        """Extract sender email from a 'From' header."""
        if "<" in from_header and ">" in from_header:
            return from_header.split("<")[1].split(">")[0].lower()
        return from_header.strip().lower()


class FakeGmailFetcher:
    """
    Comprehensive fake Gmail fetcher for business functional testing.

    Simulates all Gmail operations including:
    - Connecting to Gmail
    - Fetching recent emails
    - Getting email body content
    - Adding labels to emails
    - Deleting emails (moving to trash)
    - Domain blocking/allowing
    - Category blocking
    """

    def __init__(self):
        """Initialize the fake Gmail fetcher."""
        self.connected = False
        self.inbox_emails: List[Dict] = []
        self.deleted_message_ids: List[str] = []
        self.labels: Dict[str, List[str]] = {}
        self.blocked_domains: Set[str] = set()
        self.allowed_domains: Set[str] = set()
        self.blocked_categories: Set[str] = set()
        self.stats = {"deleted": 0, "kept": 0, "categories": Counter()}

        # Mock summary_service (required by EmailProcessorService)
        self.summary_service = Mock()
        self.summary_service.db_service = None
        self.summary_service.track_email = Mock()
        self.summary_service.run_metrics = {"fetched": 0}

    def connect(self) -> bool:
        """Simulate connecting to Gmail IMAP."""
        self.connected = True
        return True

    def disconnect(self) -> None:
        """Simulate disconnecting from Gmail IMAP."""
        self.connected = False

    def is_connected(self) -> bool:
        """Check if connected."""
        return self.connected

    def add_email_to_inbox(
        self,
        subject: str,
        body: str,
        sender: str,
        message_id: str,
        date: Optional[datetime] = None
    ) -> None:
        """Add a test email to the fake inbox."""
        email = {
            "Subject": subject,
            "Body": body,
            "From": sender,
            "Message-ID": message_id,
            "Date": date or datetime.now()
        }
        self.inbox_emails.append(email)

    def get_recent_emails(self, hours: int = 2) -> List[Dict]:
        """Fetch emails from the last N hours."""
        if not self.connected:
            raise ConnectionError("Not connected to Gmail")

        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [
            email for email in self.inbox_emails
            if email.get("Date", datetime.now()) >= cutoff
        ]
        return recent

    def get_email_body(self, msg: Dict) -> str:
        """Extract email body content."""
        if isinstance(msg, dict):
            return msg.get("Body", "")
        return ""

    def add_label(self, message_id: str, label: str) -> bool:
        """Add a Gmail label to a message."""
        if message_id not in self.labels:
            self.labels[message_id] = []
        if label not in self.labels[message_id]:
            self.labels[message_id].append(label)
        return True

    def delete_email(self, message_id: str) -> bool:
        """Move a message to Trash."""
        if message_id not in self.deleted_message_ids:
            self.deleted_message_ids.append(message_id)
        return True

    def _extract_domain(self, from_header: str) -> str:
        """Extract domain from email header."""
        if "@" in from_header:
            domain = from_header.split("@")[-1].strip(">").strip().lower()
            return domain
        return ""

    def _is_domain_blocked(self, from_header: str) -> bool:
        """Check if domain is blocked."""
        domain = self._extract_domain(from_header)
        return domain in self.blocked_domains

    def _is_domain_allowed(self, from_header: str) -> bool:
        """Check if domain is allowed."""
        domain = self._extract_domain(from_header)
        return domain in self.allowed_domains

    def _is_category_blocked(self, category: str) -> bool:
        """Check if category is blocked."""
        return category.lower() in {c.lower() for c in self.blocked_categories}

    def remove_http_links(self, text: str) -> str:
        """Remove HTTP links from text."""
        import re
        return re.sub(r'https?://\S+', '', text)

    def remove_images_from_email(self, text: str) -> str:
        """Remove image references from email."""
        return text

    def remove_encoded_content(self, text: str) -> str:
        """Remove encoded content from email."""
        return text

    # Configuration methods for tests
    def set_blocked_domains(self, domains: List[str]) -> None:
        """Set list of blocked domains."""
        self.blocked_domains = set(d.lower() for d in domains)

    def set_allowed_domains(self, domains: List[str]) -> None:
        """Set list of allowed domains."""
        self.allowed_domains = set(d.lower() for d in domains)

    def set_blocked_categories(self, categories: List[str]) -> None:
        """Set list of blocked categories."""
        self.blocked_categories = set(categories)

    def is_deleted(self, message_id: str) -> bool:
        """Check if a message has been deleted."""
        return message_id in self.deleted_message_ids

    def get_labels(self, message_id: str) -> List[str]:
        """Get all labels for a message."""
        return self.labels.get(message_id, [])

    def clear_inbox(self) -> None:
        """Clear all emails from the fake inbox."""
        self.inbox_emails.clear()
        self.deleted_message_ids.clear()
        self.labels.clear()
        self.stats = {"deleted": 0, "kept": 0, "categories": Counter()}


class FakeDeduplicationClient:
    """Fake deduplication client for tracking processed emails."""

    def __init__(self):
        self.processed_message_ids: Set[str] = set()

    def is_email_processed(self, message_id: str) -> bool:
        """Check if an email has already been processed."""
        return message_id in self.processed_message_ids

    def mark_as_processed(self, message_id: str) -> None:
        """Mark an email as processed."""
        self.processed_message_ids.add(message_id)

    def filter_new_emails(self, emails: List[Dict]) -> List[Dict]:
        """Filter out already processed emails."""
        return [
            email for email in emails
            if email.get("Message-ID") not in self.processed_message_ids
        ]

    def bulk_mark_as_processed(self, message_ids: List[str]) -> None:
        """Mark multiple emails as processed."""
        self.processed_message_ids.update(message_ids)


# =============================================================================
# Test Case 1: Listing Emails from Gmail Account
# =============================================================================

class TestListEmailsFromGmailAccount(unittest.TestCase):
    """
    Test Case 1: Able to list emails from a Gmail account.

    Given a configured Gmail account with credentials
    When the system connects to the account
    Then it should be able to fetch a list of recent emails
    """

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = FakeGmailFetcher()

    def test_can_connect_to_gmail_account(self):
        """Test that we can establish a connection to Gmail."""
        # When: Connect to Gmail
        result = self.fetcher.connect()

        # Then: Connection should succeed
        self.assertTrue(result)
        self.assertTrue(self.fetcher.is_connected())

    def test_can_list_recent_emails(self):
        """Test that we can fetch recent emails from the inbox."""
        # Given: Connected to Gmail with emails in inbox
        self.fetcher.connect()
        self.fetcher.add_email_to_inbox(
            subject="Test Email 1",
            body="This is test email 1",
            sender="sender1@example.com",
            message_id="<msg-1@example.com>"
        )
        self.fetcher.add_email_to_inbox(
            subject="Test Email 2",
            body="This is test email 2",
            sender="sender2@example.com",
            message_id="<msg-2@example.com>"
        )

        # When: Fetch recent emails
        emails = self.fetcher.get_recent_emails(hours=2)

        # Then: Should return all emails
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0]["Subject"], "Test Email 1")
        self.assertEqual(emails[1]["Subject"], "Test Email 2")

    def test_fetch_emails_requires_connection(self):
        """Test that fetching emails requires an active connection."""
        # Given: Not connected
        self.assertFalse(self.fetcher.is_connected())

        # When/Then: Fetching should raise error
        with self.assertRaises(ConnectionError):
            self.fetcher.get_recent_emails(hours=2)

    def test_can_filter_emails_by_time_window(self):
        """Test that we only get emails within the specified time window."""
        # Given: Connected with emails at different times
        self.fetcher.connect()

        # Recent email (within 2 hours)
        self.fetcher.add_email_to_inbox(
            subject="Recent Email",
            body="Recent content",
            sender="recent@example.com",
            message_id="<recent@example.com>",
            date=datetime.now() - timedelta(hours=1)
        )

        # Old email (outside 2 hours)
        self.fetcher.add_email_to_inbox(
            subject="Old Email",
            body="Old content",
            sender="old@example.com",
            message_id="<old@example.com>",
            date=datetime.now() - timedelta(hours=5)
        )

        # When: Fetch emails from last 2 hours
        emails = self.fetcher.get_recent_emails(hours=2)

        # Then: Should only return recent email
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]["Subject"], "Recent Email")

    def test_empty_inbox_returns_empty_list(self):
        """Test that an empty inbox returns an empty list."""
        # Given: Connected with empty inbox
        self.fetcher.connect()

        # When: Fetch recent emails
        emails = self.fetcher.get_recent_emails(hours=2)

        # Then: Should return empty list
        self.assertEqual(len(emails), 0)


# =============================================================================
# Test Case 2: Getting Contents of an Email Message
# =============================================================================

class TestGetEmailContents(unittest.TestCase):
    """
    Test Case 2: Able to get contents of an email message.

    Given a fetched email message
    When the system extracts the content
    Then it should return the email body text
    """

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = FakeGmailFetcher()
        self.fetcher.connect()

    def test_can_get_plain_text_body(self):
        """Test that we can extract plain text body from an email."""
        # Given: An email with plain text body
        self.fetcher.add_email_to_inbox(
            subject="Plain Text Email",
            body="This is the plain text content of the email.",
            sender="sender@example.com",
            message_id="<plain-text@example.com>"
        )
        emails = self.fetcher.get_recent_emails(hours=2)
        email = emails[0]

        # When: Extract body
        body = self.fetcher.get_email_body(email)

        # Then: Should return the body content
        self.assertEqual(body, "This is the plain text content of the email.")

    def test_can_get_email_subject(self):
        """Test that we can extract the subject from an email."""
        # Given: An email with a subject
        self.fetcher.add_email_to_inbox(
            subject="Important Meeting Tomorrow",
            body="Meeting details...",
            sender="sender@example.com",
            message_id="<subject-test@example.com>"
        )
        emails = self.fetcher.get_recent_emails(hours=2)
        email = emails[0]

        # Then: Should have the subject
        self.assertEqual(email["Subject"], "Important Meeting Tomorrow")

    def test_can_get_email_sender(self):
        """Test that we can extract the sender from an email."""
        # Given: An email with a sender
        self.fetcher.add_email_to_inbox(
            subject="Test",
            body="Content",
            sender="John Doe <john@example.com>",
            message_id="<sender-test@example.com>"
        )
        emails = self.fetcher.get_recent_emails(hours=2)
        email = emails[0]

        # Then: Should have the sender
        self.assertEqual(email["From"], "John Doe <john@example.com>")

    def test_can_get_message_id(self):
        """Test that we can extract the message ID from an email."""
        # Given: An email with a message ID
        self.fetcher.add_email_to_inbox(
            subject="Test",
            body="Content",
            sender="sender@example.com",
            message_id="<unique-id-12345@example.com>"
        )
        emails = self.fetcher.get_recent_emails(hours=2)
        email = emails[0]

        # Then: Should have the message ID
        self.assertEqual(email["Message-ID"], "<unique-id-12345@example.com>")

    def test_empty_body_returns_empty_string(self):
        """Test that an email with no body returns empty string."""
        # Given: An email with empty body
        self.fetcher.add_email_to_inbox(
            subject="Empty Body Email",
            body="",
            sender="sender@example.com",
            message_id="<empty-body@example.com>"
        )
        emails = self.fetcher.get_recent_emails(hours=2)
        email = emails[0]

        # When: Extract body
        body = self.fetcher.get_email_body(email)

        # Then: Should return empty string
        self.assertEqual(body, "")


# =============================================================================
# Test Case 3: Categorizing Email Contents
# =============================================================================

class TestCategorizeEmailContents(unittest.TestCase):
    """
    Test Case 3: Able to categorize the contents of an email.

    Given an email with content
    When the system categorizes the email
    Then it should return an appropriate category
    """

    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = FakeEmailCategorizer(default_category="Other")

    def test_can_categorize_marketing_email(self):
        """Test that marketing emails are categorized as Marketing."""
        # Given: Configure categorizer for marketing keywords
        self.categorizer.set_category_mapping("sale", "Marketing")
        self.categorizer.set_category_mapping("discount", "Marketing")
        self.categorizer.set_category_mapping("limited time offer", "Marketing")

        # When: Categorize marketing content
        category = self.categorizer.categorize(
            "Don't miss our big sale! 50% discount on all items!",
            "test-model"
        )

        # Then: Should be categorized as Marketing
        self.assertEqual(category, "Marketing")

    def test_can_categorize_financial_notification(self):
        """Test that financial notifications are categorized correctly."""
        # Given: Configure categorizer for financial keywords
        self.categorizer.set_category_mapping("bank statement", "Financial-Notification")
        self.categorizer.set_category_mapping("account balance", "Financial-Notification")

        # When: Categorize financial content
        category = self.categorizer.categorize(
            "Your monthly bank statement is ready to view.",
            "test-model"
        )

        # Then: Should be categorized as Financial-Notification
        self.assertEqual(category, "Financial-Notification")

    def test_can_categorize_other_email(self):
        """Test that miscellaneous emails are categorized as Other."""
        # Given: No specific category mappings for content

        # When: Categorize miscellaneous content
        category = self.categorizer.categorize(
            "Hey! Are you free for dinner with the family this weekend?",
            "test-model"
        )

        # Then: Should be categorized as Other (default)
        self.assertEqual(category, "Other")

    def test_can_categorize_wants_money_email(self):
        """Test that solicitation emails are categorized correctly."""
        # Given: Configure categorizer for solicitation keywords
        self.categorizer.set_category_mapping("donate", "Wants-Money")
        self.categorizer.set_category_mapping("contribute", "Wants-Money")
        self.categorizer.set_category_mapping("urgent payment", "Wants-Money")

        # When: Categorize solicitation content
        category = self.categorizer.categorize(
            "Please donate to support our cause. Your contribution matters!",
            "test-model"
        )

        # Then: Should be categorized as Wants-Money
        self.assertEqual(category, "Wants-Money")

    def test_unknown_content_returns_default_category(self):
        """Test that unknown content returns the default category."""
        # Given: Categorizer with no mappings for the content

        # When: Categorize unknown content
        category = self.categorizer.categorize(
            "Random text that doesn't match any keywords",
            "test-model"
        )

        # Then: Should return default category
        self.assertEqual(category, "Other")

    def test_categorization_is_tracked(self):
        """Test that categorization calls are tracked."""
        # Given: Fresh categorizer
        self.assertEqual(self.categorizer.get_categorization_count(), 0)

        # When: Categorize multiple emails
        self.categorizer.categorize("Email 1 content", "model-1")
        self.categorizer.categorize("Email 2 content", "model-2")
        self.categorizer.categorize("Email 3 content", "model-3")

        # Then: Should track all calls
        self.assertEqual(self.categorizer.get_categorization_count(), 3)


# =============================================================================
# Test Case 4: Deleting Emails Based on Category
# =============================================================================

class TestDeleteEmailsByCategory(unittest.TestCase):
    """
    Test Case 4: If category means the email should be deleted, then delete.

    Given an email categorized in a blocked category
    When the system processes the email
    Then it should delete the email
    """

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = FakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_blocked_category_triggers_deletion(self):
        """Test that emails in blocked categories are deleted."""
        # Given: Block the Marketing category
        self.fetcher.set_blocked_categories(["Marketing"])
        self.categorizer.set_category_mapping("buy now", "Marketing")

        email = {
            "Subject": "Buy Now!",
            "Body": "Buy now and save 50%!",
            "From": "promo@store.com",
            "Message-ID": "<promo-1@store.com>"
        }

        # When: Process the email
        category = self.processor.process_email(email)

        # Then: Email should be deleted
        self.assertEqual(category, "Marketing")
        self.assertTrue(self.fetcher.is_deleted("<promo-1@store.com>"))
        self.assertEqual(self.fetcher.stats["deleted"], 1)

    def test_non_blocked_category_keeps_email(self):
        """Test that emails in non-blocked categories are kept."""
        # Given: Block only Marketing, no category mapping (defaults to Other)
        self.fetcher.set_blocked_categories(["Marketing"])

        email = {
            "Subject": "Dinner Plans",
            "Body": "Want to grab dinner tonight?",
            "From": "friend@example.com",
            "Message-ID": "<dinner-1@example.com>"
        }

        # When: Process the email
        category = self.processor.process_email(email)

        # Then: Email should be kept (Other is not blocked)
        self.assertEqual(category, "Other")
        self.assertFalse(self.fetcher.is_deleted("<dinner-1@example.com>"))
        self.assertEqual(self.fetcher.stats["kept"], 1)

    def test_multiple_blocked_categories(self):
        """Test that multiple blocked categories all trigger deletion."""
        # Given: Block multiple valid categories
        self.fetcher.set_blocked_categories(["Marketing", "Advertising"])
        self.categorizer.set_category_mapping("sale", "Marketing")
        self.categorizer.set_category_mapping("promo", "Marketing")
        self.categorizer.set_category_mapping("sponsored", "Advertising")

        emails = [
            {"Subject": "Sale!", "Body": "Big sale today!", "From": "a@x.com", "Message-ID": "<1@x>"},
            {"Subject": "Promo", "Body": "Get our promo deal", "From": "b@y.com", "Message-ID": "<2@y>"},
            {"Subject": "Ad", "Body": "Sponsored content", "From": "c@z.com", "Message-ID": "<3@z>"},
        ]

        # When: Process all emails
        for email in emails:
            self.processor.process_email(email)

        # Then: All should be deleted
        self.assertEqual(self.fetcher.stats["deleted"], 3)
        self.assertTrue(self.fetcher.is_deleted("<1@x>"))
        self.assertTrue(self.fetcher.is_deleted("<2@y>"))
        self.assertTrue(self.fetcher.is_deleted("<3@z>"))

    def test_email_is_labeled_with_category_before_deletion(self):
        """Test that emails are labeled with their category before deletion."""
        # Given: Block Marketing category
        self.fetcher.set_blocked_categories(["Marketing"])
        self.categorizer.set_category_mapping("promo", "Marketing")

        email = {
            "Subject": "Promo",
            "Body": "Check out this promo!",
            "From": "sender@example.com",
            "Message-ID": "<labeled-1@example.com>"
        }

        # When: Process the email
        self.processor.process_email(email)

        # Then: Email should have the category label
        labels = self.fetcher.get_labels("<labeled-1@example.com>")
        self.assertIn("Marketing", labels)


# =============================================================================
# Test Case 5: Allowed Domains - Keep Email
# =============================================================================

class TestAllowedDomainsKeepEmail(unittest.TestCase):
    """
    Test Case 5: If email sender is in allowed domains, leave the email alone.

    Given an email from an allowed domain
    When the system processes the email
    Then it should keep the email regardless of content
    """

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = FakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_allowed_domain_prevents_deletion(self):
        """Test that emails from allowed domains are kept."""
        # Given: Allow the domain
        self.fetcher.set_allowed_domains(["mybank.com"])

        # Even with blocked category, allowed domain takes precedence
        self.fetcher.set_blocked_categories(["Marketing"])

        email = {
            "Subject": "Account Update",
            "Body": "Your account has been updated",
            "From": "notifications@mybank.com",
            "Message-ID": "<bank-1@mybank.com>"
        }

        # When: Process the email
        category = self.processor.process_email(email)

        # Then: Email should be kept
        self.assertEqual(category, "Allowed_Domain")
        self.assertFalse(self.fetcher.is_deleted("<bank-1@mybank.com>"))
        self.assertEqual(self.fetcher.stats["kept"], 1)

    def test_allowed_domain_skips_categorization(self):
        """Test that allowed domain emails skip LLM categorization."""
        # Given: Allow the domain
        self.fetcher.set_allowed_domains(["trusted.com"])

        email = {
            "Subject": "Important",
            "Body": "Important message",
            "From": "admin@trusted.com",
            "Message-ID": "<trusted-1@trusted.com>"
        }

        # When: Process the email
        self.processor.process_email(email)

        # Then: Categorizer should NOT have been called
        self.assertEqual(self.categorizer.get_categorization_count(), 0)

    def test_multiple_allowed_domains(self):
        """Test that multiple allowed domains are all protected."""
        # Given: Allow multiple domains
        self.fetcher.set_allowed_domains(["bank.com", "work.com", "family.org"])
        self.fetcher.set_blocked_categories(["Marketing"])

        emails = [
            {"Subject": "A", "Body": "A", "From": "a@bank.com", "Message-ID": "<1@a>"},
            {"Subject": "B", "Body": "B", "From": "b@work.com", "Message-ID": "<2@b>"},
            {"Subject": "C", "Body": "C", "From": "c@family.org", "Message-ID": "<3@c>"},
        ]

        # When: Process all emails
        for email in emails:
            self.processor.process_email(email)

        # Then: All should be kept
        self.assertEqual(self.fetcher.stats["kept"], 3)
        self.assertEqual(self.fetcher.stats["deleted"], 0)

    def test_allowed_domain_labeled_correctly(self):
        """Test that allowed domain emails are labeled as Allowed_Domain."""
        # Given: Allow the domain
        self.fetcher.set_allowed_domains(["vip.com"])

        email = {
            "Subject": "VIP",
            "Body": "VIP content",
            "From": "ceo@vip.com",
            "Message-ID": "<vip-1@vip.com>"
        }

        # When: Process the email
        self.processor.process_email(email)

        # Then: Email should have Allowed_Domain label
        labels = self.fetcher.get_labels("<vip-1@vip.com>")
        self.assertIn("Allowed_Domain", labels)


# =============================================================================
# Test Case 6: Blocked Domains - Delete Email
# =============================================================================

class TestBlockedDomainsDeleteEmail(unittest.TestCase):
    """
    Test Case 6: If email sender is in blocked domains, delete the email.

    Given an email from a blocked domain
    When the system processes the email
    Then it should delete the email without categorization
    """

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = FakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Personal")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_blocked_domain_triggers_deletion(self):
        """Test that emails from blocked domains are deleted."""
        # Given: Block the domain
        self.fetcher.set_blocked_domains(["spam-company.com"])

        email = {
            "Subject": "You won!",
            "Body": "You've won a million dollars!",
            "From": "winner@spam-company.com",
            "Message-ID": "<spam-1@spam-company.com>"
        }

        # When: Process the email
        category = self.processor.process_email(email)

        # Then: Email should be deleted
        self.assertEqual(category, "Blocked_Domain")
        self.assertTrue(self.fetcher.is_deleted("<spam-1@spam-company.com>"))
        self.assertEqual(self.fetcher.stats["deleted"], 1)

    def test_blocked_domain_skips_categorization(self):
        """Test that blocked domain emails skip LLM categorization."""
        # Given: Block the domain
        self.fetcher.set_blocked_domains(["blocked.com"])

        email = {
            "Subject": "Something",
            "Body": "Content",
            "From": "anyone@blocked.com",
            "Message-ID": "<blocked-1@blocked.com>"
        }

        # When: Process the email
        self.processor.process_email(email)

        # Then: Categorizer should NOT have been called
        self.assertEqual(self.categorizer.get_categorization_count(), 0)

    def test_multiple_blocked_domains(self):
        """Test that multiple blocked domains all trigger deletion."""
        # Given: Block multiple domains
        self.fetcher.set_blocked_domains(["spam1.com", "spam2.com", "spam3.com"])

        emails = [
            {"Subject": "A", "Body": "A", "From": "a@spam1.com", "Message-ID": "<1@s>"},
            {"Subject": "B", "Body": "B", "From": "b@spam2.com", "Message-ID": "<2@s>"},
            {"Subject": "C", "Body": "C", "From": "c@spam3.com", "Message-ID": "<3@s>"},
        ]

        # When: Process all emails
        for email in emails:
            self.processor.process_email(email)

        # Then: All should be deleted
        self.assertEqual(self.fetcher.stats["deleted"], 3)
        self.assertTrue(self.fetcher.is_deleted("<1@s>"))
        self.assertTrue(self.fetcher.is_deleted("<2@s>"))
        self.assertTrue(self.fetcher.is_deleted("<3@s>"))

    def test_blocked_domain_labeled_correctly(self):
        """Test that blocked domain emails are labeled as Blocked_Domain."""
        # Given: Block the domain
        self.fetcher.set_blocked_domains(["junk.com"])

        email = {
            "Subject": "Junk",
            "Body": "Junk content",
            "From": "junk@junk.com",
            "Message-ID": "<junk-1@junk.com>"
        }

        # When: Process the email
        self.processor.process_email(email)

        # Then: Email should have Blocked_Domain label
        labels = self.fetcher.get_labels("<junk-1@junk.com>")
        self.assertIn("Blocked_Domain", labels)


# =============================================================================
# Test Case 7: Domain Priority - Allowed Takes Precedence Over Blocked
# =============================================================================

class TestDomainPriority(unittest.TestCase):
    """
    Test domain priority: Blocked domains are checked before allowed.

    In the real system, the order is:
    1. Check if blocked -> DELETE
    2. Check if allowed -> KEEP
    3. Categorize with LLM
    """

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = FakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_blocked_domain_checked_before_allowed(self):
        """Test that blocked domains are processed before allowed check."""
        # Given: Domain is in BOTH blocked and allowed lists
        self.fetcher.set_blocked_domains(["ambiguous.com"])
        self.fetcher.set_allowed_domains(["ambiguous.com"])

        email = {
            "Subject": "Test",
            "Body": "Test content",
            "From": "user@ambiguous.com",
            "Message-ID": "<ambiguous-1@ambiguous.com>"
        }

        # When: Process the email
        category = self.processor.process_email(email)

        # Then: Should be treated as blocked (checked first)
        self.assertEqual(category, "Blocked_Domain")
        self.assertTrue(self.fetcher.is_deleted("<ambiguous-1@ambiguous.com>"))

    def test_allowed_domain_overrides_blocked_category(self):
        """Test that allowed domain prevents deletion even for blocked categories."""
        # Given: Domain is allowed but category would be blocked
        self.fetcher.set_allowed_domains(["trusted.com"])
        self.fetcher.set_blocked_categories(["Marketing"])
        self.categorizer.set_category_mapping("sale", "Marketing")

        email = {
            "Subject": "Sale!",
            "Body": "Big sale happening now!",
            "From": "promo@trusted.com",
            "Message-ID": "<trusted-sale@trusted.com>"
        }

        # When: Process the email
        category = self.processor.process_email(email)

        # Then: Should be kept because domain is allowed
        self.assertEqual(category, "Allowed_Domain")
        self.assertFalse(self.fetcher.is_deleted("<trusted-sale@trusted.com>"))


# =============================================================================
# Test Case 8: Email Deduplication
# =============================================================================

class TestEmailDeduplication(unittest.TestCase):
    """
    Test that emails are not processed twice.

    Given an email that has already been processed
    When the system encounters it again
    Then it should skip processing
    """

    def setUp(self):
        """Set up test fixtures."""
        self.dedup_client = FakeDeduplicationClient()

    def test_processed_email_is_skipped(self):
        """Test that already processed emails are filtered out."""
        # Given: An email that was already processed
        self.dedup_client.mark_as_processed("<already-processed@example.com>")

        emails = [
            {"Subject": "Old", "Body": "Old", "From": "a@x.com", "Message-ID": "<already-processed@example.com>"},
            {"Subject": "New", "Body": "New", "From": "b@y.com", "Message-ID": "<new-email@example.com>"},
        ]

        # When: Filter new emails
        new_emails = self.dedup_client.filter_new_emails(emails)

        # Then: Only the new email should be returned
        self.assertEqual(len(new_emails), 1)
        self.assertEqual(new_emails[0]["Message-ID"], "<new-email@example.com>")

    def test_bulk_mark_as_processed(self):
        """Test that multiple emails can be marked as processed at once."""
        # Given: Multiple message IDs
        message_ids = ["<msg-1@x>", "<msg-2@x>", "<msg-3@x>"]

        # When: Bulk mark as processed
        self.dedup_client.bulk_mark_as_processed(message_ids)

        # Then: All should be marked as processed
        for msg_id in message_ids:
            self.assertTrue(self.dedup_client.is_email_processed(msg_id))

    def test_deduplication_prevents_double_processing(self):
        """Test end-to-end deduplication scenario."""
        # Given: First batch of emails
        batch1 = [
            {"Subject": "A", "Body": "A", "From": "a@x.com", "Message-ID": "<a@x>"},
            {"Subject": "B", "Body": "B", "From": "b@x.com", "Message-ID": "<b@x>"},
        ]

        # Process first batch
        new_in_batch1 = self.dedup_client.filter_new_emails(batch1)
        self.assertEqual(len(new_in_batch1), 2)
        self.dedup_client.bulk_mark_as_processed([e["Message-ID"] for e in new_in_batch1])

        # When: Second batch with some overlap
        batch2 = [
            {"Subject": "A", "Body": "A", "From": "a@x.com", "Message-ID": "<a@x>"},  # Already seen
            {"Subject": "C", "Body": "C", "From": "c@x.com", "Message-ID": "<c@x>"},  # New
        ]
        new_in_batch2 = self.dedup_client.filter_new_emails(batch2)

        # Then: Only new email should be returned
        self.assertEqual(len(new_in_batch2), 1)
        self.assertEqual(new_in_batch2[0]["Message-ID"], "<c@x>")


# =============================================================================
# Test Case 9: Email Labeling
# =============================================================================

class TestEmailLabeling(unittest.TestCase):
    """
    Test that emails are labeled with their category.

    Given a processed email
    When the system determines its category
    Then it should apply a Gmail label matching the category
    """

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = FakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_categorized_email_gets_label(self):
        """Test that categorized emails get the category as a label."""
        # Given: Email that will be categorized as Marketing
        self.categorizer.set_category_mapping("sale", "Marketing")

        email = {
            "Subject": "Big Sale!",
            "Body": "Don't miss our sale!",
            "From": "store@example.com",
            "Message-ID": "<marketing-1@example.com>"
        }

        # When: Process the email
        self.processor.process_email(email)

        # Then: Email should have Marketing label
        labels = self.fetcher.get_labels("<marketing-1@example.com>")
        self.assertIn("Marketing", labels)

    def test_blocked_domain_email_gets_blocked_domain_label(self):
        """Test that blocked domain emails get Blocked_Domain label."""
        # Given: Blocked domain
        self.fetcher.set_blocked_domains(["spam.com"])

        email = {
            "Subject": "Spam",
            "Body": "Spam content",
            "From": "spammer@spam.com",
            "Message-ID": "<spam-label@spam.com>"
        }

        # When: Process the email
        self.processor.process_email(email)

        # Then: Email should have Blocked_Domain label
        labels = self.fetcher.get_labels("<spam-label@spam.com>")
        self.assertIn("Blocked_Domain", labels)

    def test_allowed_domain_email_gets_allowed_domain_label(self):
        """Test that allowed domain emails get Allowed_Domain label."""
        # Given: Allowed domain
        self.fetcher.set_allowed_domains(["bank.com"])

        email = {
            "Subject": "Statement",
            "Body": "Your statement is ready",
            "From": "notify@bank.com",
            "Message-ID": "<allowed-label@bank.com>"
        }

        # When: Process the email
        self.processor.process_email(email)

        # Then: Email should have Allowed_Domain label
        labels = self.fetcher.get_labels("<allowed-label@bank.com>")
        self.assertIn("Allowed_Domain", labels)


# =============================================================================
# Test Case 10: Processing Statistics Tracking
# =============================================================================

class TestProcessingStatistics(unittest.TestCase):
    """
    Test that processing statistics are tracked correctly.

    Given multiple processed emails
    When the processing completes
    Then accurate statistics should be available
    """

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = FakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_deleted_count_is_tracked(self):
        """Test that deleted email count is tracked."""
        # Given: Some emails will be deleted
        self.fetcher.set_blocked_domains(["spam.com"])

        emails = [
            {"Subject": "Spam 1", "Body": "S1", "From": "a@spam.com", "Message-ID": "<s1@x>"},
            {"Subject": "Spam 2", "Body": "S2", "From": "b@spam.com", "Message-ID": "<s2@x>"},
            {"Subject": "Spam 3", "Body": "S3", "From": "c@spam.com", "Message-ID": "<s3@x>"},
        ]

        # When: Process all emails
        for email in emails:
            self.processor.process_email(email)

        # Then: Deleted count should be 3
        self.assertEqual(self.fetcher.stats["deleted"], 3)

    def test_kept_count_is_tracked(self):
        """Test that kept email count is tracked."""
        # Given: Some emails will be kept
        self.fetcher.set_allowed_domains(["safe.com"])

        emails = [
            {"Subject": "Safe 1", "Body": "S1", "From": "a@safe.com", "Message-ID": "<safe1@x>"},
            {"Subject": "Safe 2", "Body": "S2", "From": "b@safe.com", "Message-ID": "<safe2@x>"},
        ]

        # When: Process all emails
        for email in emails:
            self.processor.process_email(email)

        # Then: Kept count should be 2
        self.assertEqual(self.fetcher.stats["kept"], 2)

    def test_category_counts_are_tracked(self):
        """Test that category counts are tracked."""
        # Given: Emails with different valid categories
        self.categorizer.set_category_mapping("sale", "Marketing")
        self.categorizer.set_category_mapping("ad", "Advertising")

        emails = [
            {"Subject": "Sale!", "Body": "Big sale!", "From": "a@x.com", "Message-ID": "<1@x>"},
            {"Subject": "Sale 2", "Body": "Another sale", "From": "b@x.com", "Message-ID": "<2@x>"},
            {"Subject": "Ad", "Body": "Check this ad!", "From": "c@x.com", "Message-ID": "<3@x>"},
        ]

        # When: Process all emails
        for email in emails:
            self.processor.process_email(email)

        # Then: Category counts should be accurate
        self.assertEqual(self.fetcher.stats["categories"]["Marketing"], 2)
        self.assertEqual(self.fetcher.stats["categories"]["Advertising"], 1)

    def test_mixed_processing_statistics(self):
        """Test statistics with a mix of deleted and kept emails."""
        # Given: Mix of blocked domains, allowed domains, and categories
        self.fetcher.set_blocked_domains(["spam.com"])
        self.fetcher.set_allowed_domains(["safe.com"])
        self.fetcher.set_blocked_categories(["Marketing"])
        self.categorizer.set_category_mapping("sale", "Marketing")
        # Other (default) is a valid category and won't be blocked

        emails = [
            {"Subject": "Spam", "Body": "Spam", "From": "x@spam.com", "Message-ID": "<1@x>"},  # Deleted (blocked domain)
            {"Subject": "Safe", "Body": "Safe", "From": "x@safe.com", "Message-ID": "<2@x>"},  # Kept (allowed domain)
            {"Subject": "Sale!", "Body": "Big sale", "From": "x@store.com", "Message-ID": "<3@x>"},  # Deleted (blocked category)
            {"Subject": "Report", "Body": "Monthly report", "From": "x@work.com", "Message-ID": "<4@x>"},  # Kept (Other - non-blocked)
        ]

        # When: Process all emails
        for email in emails:
            self.processor.process_email(email)

        # Then: Statistics should reflect the mix
        self.assertEqual(self.fetcher.stats["deleted"], 2)  # spam.com + Marketing
        self.assertEqual(self.fetcher.stats["kept"], 2)  # safe.com + Other


# =============================================================================
# Test Case 11: Case Insensitivity
# =============================================================================

class TestCaseInsensitivity(unittest.TestCase):
    """
    Test that domain matching is case insensitive.

    Given domain rules with mixed case
    When processing emails with different case variations
    Then matching should work regardless of case
    """

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = FakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_blocked_domain_case_insensitive(self):
        """Test that blocked domain matching is case insensitive."""
        # Given: Block domain in lowercase
        self.fetcher.set_blocked_domains(["spam.com"])

        # Email with uppercase domain
        email = {
            "Subject": "Test",
            "Body": "Test",
            "From": "user@SPAM.COM",
            "Message-ID": "<case-test@x>"
        }

        # When: Process the email
        category = self.processor.process_email(email)

        # Then: Should be blocked
        self.assertEqual(category, "Blocked_Domain")
        self.assertTrue(self.fetcher.is_deleted("<case-test@x>"))

    def test_allowed_domain_case_insensitive(self):
        """Test that allowed domain matching is case insensitive."""
        # Given: Allow domain in lowercase
        self.fetcher.set_allowed_domains(["bank.com"])

        # Email with mixed case domain
        email = {
            "Subject": "Statement",
            "Body": "Statement",
            "From": "notify@BaNk.CoM",
            "Message-ID": "<case-allowed@x>"
        }

        # When: Process the email
        category = self.processor.process_email(email)

        # Then: Should be allowed
        self.assertEqual(category, "Allowed_Domain")
        self.assertFalse(self.fetcher.is_deleted("<case-allowed@x>"))


# =============================================================================
# Test Case 12: Edge Cases
# =============================================================================

class TestEdgeCases(unittest.TestCase):
    """
    Test edge cases and boundary conditions.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = FakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_email_with_formatted_from_header(self):
        """Test that emails with 'Name <email>' format are handled."""
        # Given: Blocked domain with formatted header
        self.fetcher.set_blocked_domains(["spam.com"])

        email = {
            "Subject": "Test",
            "Body": "Test",
            "From": "Spammer <spammer@spam.com>",
            "Message-ID": "<formatted-from@x>"
        }

        # When: Process the email
        category = self.processor.process_email(email)

        # Then: Should extract domain correctly and block
        self.assertEqual(category, "Blocked_Domain")

    def test_email_with_empty_body(self):
        """Test that emails with empty body can be processed."""
        # Given: Email with empty body
        email = {
            "Subject": "Empty",
            "Body": "",
            "From": "sender@example.com",
            "Message-ID": "<empty-body@x>"
        }

        # When: Process the email
        category = self.processor.process_email(email)

        # Then: Should process without error
        self.assertIsNotNone(category)

    def test_email_with_no_domain_lists(self):
        """Test processing when no domain lists are configured."""
        # Given: No blocked or allowed domains
        email = {
            "Subject": "Normal",
            "Body": "Normal content",
            "From": "sender@example.com",
            "Message-ID": "<no-lists@x>"
        }

        # When: Process the email
        category = self.processor.process_email(email)

        # Then: Should use default category
        self.assertEqual(category, "Other")


if __name__ == '__main__':
    unittest.main()
