"""
Tests for EmailProcessorService keep/delete decision logic.

This test module validates the critical business logic that determines whether
an email should be kept in the inbox or deleted. The decision is based on:

1. Blocked domains - Domain is on the blocklist
2. Allowed domains - Domain is on the allowlist (prevents deletion)
3. Blocked categories - Category is on the blocklist (after LLM categorization)

Decision Flow (tested in this module):
- Domain is blocked -> DELETE (skips LLM categorization)
- Domain is allowed -> KEEP (skips LLM categorization)
- Category is blocked -> DELETE (after LLM categorization)
- Category is not blocked -> KEEP

Note: Repeat offender patterns (checked before domain/category logic in production)
are not tested in this module as they require database session mocking.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from collections import Counter
from email.message import EmailMessage

from services.email_processor_service import EmailProcessorService
from services.fake_email_categorizer import FakeEmailCategorizer
from services.interfaces.email_extractor_interface import EmailExtractorInterface


class FakeEmailExtractor(EmailExtractorInterface):
    """Fake email extractor for testing."""

    def extract_sender_email(self, from_header: str) -> str:
        """Extract sender email from a 'From' header."""
        if "<" in from_header and ">" in from_header:
            return from_header.split("<")[1].split(">")[0].lower()
        return from_header.strip().lower()


class ConfigurableFakeGmailFetcher:
    """
    Configurable fake Gmail fetcher for testing keep/delete decision logic.

    This implementation allows tests to control:
    - Which domains are blocked/allowed
    - Which categories are blocked
    - Email deletion tracking
    """

    def __init__(self):
        """Initialize the configurable fake Gmail fetcher."""
        self.connected = True
        self.blocked_domains: set = set()
        self.allowed_domains: set = set()
        self.blocked_categories: set = set()
        self.deleted_message_ids: list = []
        self.labels: dict = {}  # message_id -> list of labels
        self.stats = {"deleted": 0, "kept": 0, "categories": Counter()}

        # Mock summary_service (required by EmailProcessorService)
        self.summary_service = Mock()
        self.summary_service.db_service = None  # Disable database checks
        self.summary_service.track_email = Mock()
        self.summary_service.run_metrics = {"fetched": 0}

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

    def get_email_body(self, msg) -> str:
        """Extract email body."""
        if isinstance(msg, dict):
            return msg.get("Body", "")
        return str(msg.get_payload()) if hasattr(msg, "get_payload") else ""

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
        return category in self.blocked_categories

    def remove_http_links(self, text: str) -> str:
        """Remove HTTP links from text."""
        return text

    def remove_images_from_email(self, text: str) -> str:
        """Remove image references from email."""
        return text

    def remove_encoded_content(self, text: str) -> str:
        """Remove encoded content from email."""
        return text

    # Configuration methods for tests

    def set_blocked_domains(self, domains: list) -> None:
        """Set list of blocked domains."""
        self.blocked_domains = set(d.lower() for d in domains)

    def set_allowed_domains(self, domains: list) -> None:
        """Set list of allowed domains."""
        self.allowed_domains = set(d.lower() for d in domains)

    def set_blocked_categories(self, categories: list) -> None:
        """Set list of blocked categories."""
        self.blocked_categories = set(categories)

    def is_deleted(self, message_id: str) -> bool:
        """Check if a message has been deleted."""
        return message_id in self.deleted_message_ids

    def get_labels(self, message_id: str) -> list:
        """Get all labels for a message."""
        return self.labels.get(message_id, [])


def create_test_email(
    subject: str = "Test Subject",
    body: str = "Test body content",
    sender: str = "sender@example.com",
    message_id: str = "<test-123@example.com>",
) -> dict:
    """Create a test email message dictionary."""
    return {
        "Subject": subject,
        "Body": body,
        "From": sender,
        "Message-ID": message_id,
    }


class TestKeepDeleteDecisionBlockedDomain(unittest.TestCase):
    """Test cases for blocked domain deletion logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = ConfigurableFakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_blocked_domain_triggers_deletion(self):
        """Test that email from blocked domain is deleted."""
        # Setup: Block the domain
        self.fetcher.set_blocked_domains(["spam-company.com"])

        # Create email from blocked domain
        email = create_test_email(
            sender="promo@spam-company.com",
            message_id="<blocked-domain-test@example.com>",
        )

        # Process email
        category = self.processor.process_email(email)

        # Verify: Email should be deleted
        self.assertEqual(category, "Blocked_Domain")
        self.assertTrue(self.fetcher.is_deleted("<blocked-domain-test@example.com>"))
        self.assertEqual(self.fetcher.stats["deleted"], 1)
        self.assertEqual(self.fetcher.stats["kept"], 0)

    def test_blocked_domain_skips_llm_categorization(self):
        """Test that blocked domain emails skip expensive LLM calls."""
        # Setup: Block the domain
        self.fetcher.set_blocked_domains(["blocked.com"])

        email = create_test_email(
            sender="anyone@blocked.com",
            message_id="<skip-llm-test@example.com>",
        )

        # Process email
        self.processor.process_email(email)

        # Verify: LLM categorizer should NOT have been called
        self.assertEqual(self.categorizer.get_categorization_count(), 0)

    def test_multiple_blocked_domains(self):
        """Test that multiple blocked domains all trigger deletion."""
        # Setup: Block multiple domains
        self.fetcher.set_blocked_domains(["spam1.com", "spam2.com", "spam3.com"])

        emails = [
            create_test_email(sender="a@spam1.com", message_id="<msg-1@test>"),
            create_test_email(sender="b@spam2.com", message_id="<msg-2@test>"),
            create_test_email(sender="c@spam3.com", message_id="<msg-3@test>"),
        ]

        # Process all emails
        for email in emails:
            self.processor.process_email(email)

        # Verify: All 3 emails should be deleted
        self.assertEqual(self.fetcher.stats["deleted"], 3)
        self.assertEqual(self.fetcher.stats["kept"], 0)
        self.assertTrue(self.fetcher.is_deleted("<msg-1@test>"))
        self.assertTrue(self.fetcher.is_deleted("<msg-2@test>"))
        self.assertTrue(self.fetcher.is_deleted("<msg-3@test>"))


class TestKeepDeleteDecisionAllowedDomain(unittest.TestCase):
    """Test cases for allowed domain keep logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = ConfigurableFakeGmailFetcher()
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
        """Test that email from allowed domain is kept."""
        # Setup: Allow the domain
        self.fetcher.set_allowed_domains(["trusted-company.com"])

        email = create_test_email(
            sender="updates@trusted-company.com",
            message_id="<allowed-domain-test@example.com>",
        )

        # Process email
        category = self.processor.process_email(email)

        # Verify: Email should NOT be deleted
        self.assertEqual(category, "Allowed_Domain")
        self.assertFalse(self.fetcher.is_deleted("<allowed-domain-test@example.com>"))
        self.assertEqual(self.fetcher.stats["deleted"], 0)
        self.assertEqual(self.fetcher.stats["kept"], 1)

    def test_allowed_domain_skips_llm_categorization(self):
        """Test that allowed domain emails skip expensive LLM calls."""
        # Setup: Allow the domain
        self.fetcher.set_allowed_domains(["mybank.com"])

        email = create_test_email(
            sender="alerts@mybank.com",
            message_id="<skip-llm-allowed@example.com>",
        )

        # Process email
        self.processor.process_email(email)

        # Verify: LLM categorizer should NOT have been called
        self.assertEqual(self.categorizer.get_categorization_count(), 0)

    def test_allowed_domain_overrides_blocked_category(self):
        """Test that allowed domain takes precedence - email is kept even if it would be blocked by category."""
        # Setup: Allow domain but also block Marketing category
        self.fetcher.set_allowed_domains(["trusted.com"])
        self.fetcher.set_blocked_categories(["Marketing"])

        # Set categorizer to return Marketing (but this shouldn't be called)
        self.categorizer.set_category_mapping("promo", "Marketing")

        email = create_test_email(
            sender="newsletter@trusted.com",
            body="Check out our promo deals!",
            message_id="<override-test@example.com>",
        )

        # Process email
        category = self.processor.process_email(email)

        # Verify: Email should be kept because domain is allowed
        self.assertEqual(category, "Allowed_Domain")
        self.assertFalse(self.fetcher.is_deleted("<override-test@example.com>"))
        self.assertEqual(self.categorizer.get_categorization_count(), 0)


class TestKeepDeleteDecisionBlockedCategory(unittest.TestCase):
    """Test cases for blocked category deletion logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = ConfigurableFakeGmailFetcher()
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
        """Test that email in blocked category is deleted."""
        # Setup: Block the Marketing category
        self.fetcher.set_blocked_categories(["Marketing"])
        self.categorizer.set_category_mapping("buy now", "Marketing")

        email = create_test_email(
            sender="newsletter@unknown-company.com",
            body="Buy now and save 50%!",
            message_id="<blocked-category-test@example.com>",
        )

        # Process email
        category = self.processor.process_email(email)

        # Verify: Email should be deleted
        self.assertEqual(category, "Marketing")
        self.assertTrue(self.fetcher.is_deleted("<blocked-category-test@example.com>"))
        self.assertEqual(self.fetcher.stats["deleted"], 1)
        self.assertEqual(self.fetcher.stats["kept"], 0)

    def test_multiple_blocked_categories(self):
        """Test that multiple blocked categories all trigger deletion."""
        # Setup: Block multiple categories
        self.fetcher.set_blocked_categories(["Marketing", "Advertising", "WantsMoney"])
        self.categorizer.set_category_mapping("buy", "Marketing")
        self.categorizer.set_category_mapping("ad", "Advertising")
        self.categorizer.set_category_mapping("donate", "WantsMoney")

        emails = [
            create_test_email(body="Buy this product!", message_id="<marketing@test>"),
            create_test_email(body="Check out this ad!", message_id="<advertising@test>"),
            create_test_email(body="Please donate today", message_id="<wantsmoney@test>"),
        ]

        # Process all emails
        for email in emails:
            self.processor.process_email(email)

        # Verify: All 3 emails should be deleted
        self.assertEqual(self.fetcher.stats["deleted"], 3)
        self.assertEqual(self.fetcher.stats["kept"], 0)

    def test_non_blocked_category_keeps_email(self):
        """Test that email in non-blocked category is kept."""
        # Setup: Only block Marketing category
        # Use a categorizer that returns Advertising by default (valid but not blocked)
        self.fetcher.set_blocked_categories(["Marketing"])

        # Create a new categorizer with Advertising as default (valid category, not blocked)
        ad_categorizer = FakeEmailCategorizer(default_category="Advertising")
        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=ad_categorizer,
            email_extractor=self.email_extractor,
        )

        email = create_test_email(
            sender="friend@example.com",
            body="Let's have a meeting next week",
            message_id="<keep-personal@example.com>",
        )

        # Process email
        category = self.processor.process_email(email)

        # Verify: Email should NOT be deleted (Advertising is not blocked, only Marketing is)
        self.assertEqual(category, "Advertising")
        self.assertFalse(self.fetcher.is_deleted("<keep-personal@example.com>"))
        self.assertEqual(self.fetcher.stats["deleted"], 0)
        self.assertEqual(self.fetcher.stats["kept"], 1)


class TestKeepDeleteDecisionPriority(unittest.TestCase):
    """Test cases for decision priority logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = ConfigurableFakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_blocked_domain_takes_priority_over_allowed_domain(self):
        """Test that blocked domain check happens before allowed domain check.

        The system checks blocked first, so if a domain is somehow in both lists,
        blocked should take priority.
        """
        # Setup: Domain in both blocked and allowed (shouldn't happen, but test priority)
        self.fetcher.set_blocked_domains(["confusing.com"])
        self.fetcher.set_allowed_domains(["confusing.com"])

        email = create_test_email(
            sender="test@confusing.com",
            message_id="<priority-test@example.com>",
        )

        # Process email
        category = self.processor.process_email(email)

        # Verify: Blocked domain should win, email deleted
        self.assertEqual(category, "Blocked_Domain")
        self.assertTrue(self.fetcher.is_deleted("<priority-test@example.com>"))

    def test_domain_checks_happen_before_category_check(self):
        """Test that domain checks skip category checks entirely."""
        # Setup: Allow domain, block category
        self.fetcher.set_allowed_domains(["trusted.com"])
        self.fetcher.set_blocked_categories(["Marketing"])

        # This email would be Marketing if categorized
        self.categorizer.set_category_mapping("sale", "Marketing")

        email = create_test_email(
            sender="sales@trusted.com",
            body="Big sale happening now!",
            message_id="<domain-priority@example.com>",
        )

        # Process email
        category = self.processor.process_email(email)

        # Verify: Domain check happened first, no LLM call
        self.assertEqual(category, "Allowed_Domain")
        self.assertFalse(self.fetcher.is_deleted("<domain-priority@example.com>"))
        self.assertEqual(self.categorizer.get_categorization_count(), 0)

    def test_neither_blocked_nor_allowed_domain_triggers_categorization(self):
        """Test that emails from unknown domains get categorized."""
        # Setup: No domain rules
        self.categorizer.set_category_mapping("newsletter", "Marketing")

        email = create_test_email(
            sender="news@random-site.com",
            body="Weekly newsletter update",
            message_id="<categorization-needed@example.com>",
        )

        # Process email
        category = self.processor.process_email(email)

        # Verify: LLM categorizer was called
        self.assertEqual(category, "Marketing")
        self.assertEqual(self.categorizer.get_categorization_count(), 1)


class TestKeepDeleteDecisionStats(unittest.TestCase):
    """Test cases for statistics tracking."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = ConfigurableFakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_deleted_stats_tracked_correctly(self):
        """Test that deleted email count is tracked."""
        self.fetcher.set_blocked_domains(["spam.com"])

        for i in range(5):
            email = create_test_email(
                sender=f"spammer{i}@spam.com", message_id=f"<spam-{i}@test>"
            )
            self.processor.process_email(email)

        self.assertEqual(self.fetcher.stats["deleted"], 5)
        self.assertEqual(self.fetcher.stats["kept"], 0)

    def test_kept_stats_tracked_correctly(self):
        """Test that kept email count is tracked."""
        self.fetcher.set_allowed_domains(["trusted.com"])

        for i in range(3):
            email = create_test_email(
                sender=f"user{i}@trusted.com", message_id=f"<trusted-{i}@test>"
            )
            self.processor.process_email(email)

        self.assertEqual(self.fetcher.stats["deleted"], 0)
        self.assertEqual(self.fetcher.stats["kept"], 3)

    def test_category_stats_tracked_correctly(self):
        """Test that category counts are tracked."""
        # Use valid categories from SimpleEmailCategory enum
        # Marketing and Advertising are both valid categories
        marketing_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=marketing_categorizer,
            email_extractor=self.email_extractor,
        )

        # Process 2 marketing emails
        for i in range(2):
            email = create_test_email(body=f"promo update {i}", message_id=f"<marketing-{i}@test>")
            self.processor.process_email(email)

        # Now switch to Advertising categorizer
        ad_categorizer = FakeEmailCategorizer(default_category="Advertising")
        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=ad_categorizer,
            email_extractor=self.email_extractor,
        )

        email = create_test_email(body="ad content", message_id="<ad-1@test>")
        self.processor.process_email(email)

        self.assertEqual(self.fetcher.stats["categories"]["Marketing"], 2)
        self.assertEqual(self.fetcher.stats["categories"]["Advertising"], 1)

    def test_mixed_deleted_and_kept_stats(self):
        """Test stats with mix of deleted and kept emails."""
        self.fetcher.set_blocked_domains(["spam.com"])
        self.fetcher.set_allowed_domains(["trusted.com"])

        emails = [
            create_test_email(sender="a@spam.com", message_id="<spam-1@test>"),
            create_test_email(sender="b@trusted.com", message_id="<trusted-1@test>"),
            create_test_email(sender="c@spam.com", message_id="<spam-2@test>"),
            create_test_email(sender="d@trusted.com", message_id="<trusted-2@test>"),
        ]

        for email in emails:
            self.processor.process_email(email)

        self.assertEqual(self.fetcher.stats["deleted"], 2)
        self.assertEqual(self.fetcher.stats["kept"], 2)


class TestKeepDeleteDecisionCategoryActions(unittest.TestCase):
    """Test cases for category_actions tracking in processor."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = ConfigurableFakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_category_actions_tracks_deleted(self):
        """Test that category_actions tracks deleted count per category."""
        self.fetcher.set_blocked_categories(["Marketing"])
        self.categorizer.set_category_mapping("promo", "Marketing")

        email = create_test_email(body="promo offer", message_id="<promo@test>")
        self.processor.process_email(email)

        self.assertIn("Marketing", self.processor.category_actions)
        self.assertEqual(self.processor.category_actions["Marketing"]["deleted"], 1)
        self.assertEqual(self.processor.category_actions["Marketing"]["kept"], 0)
        self.assertEqual(self.processor.category_actions["Marketing"]["total"], 1)

    def test_category_actions_tracks_kept(self):
        """Test that category_actions tracks kept count per category."""
        # Use a categorizer that returns Advertising by default (valid category)
        ad_categorizer = FakeEmailCategorizer(default_category="Advertising")
        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=ad_categorizer,
            email_extractor=self.email_extractor,
        )

        email = create_test_email(body="ad message", message_id="<ad@test>")
        self.processor.process_email(email)

        self.assertIn("Advertising", self.processor.category_actions)
        self.assertEqual(self.processor.category_actions["Advertising"]["deleted"], 0)
        self.assertEqual(self.processor.category_actions["Advertising"]["kept"], 1)
        self.assertEqual(self.processor.category_actions["Advertising"]["total"], 1)

    def test_category_actions_accumulates_across_emails(self):
        """Test that category_actions accumulates counts across multiple emails."""
        self.fetcher.set_blocked_categories(["Marketing"])

        # Use Marketing categorizer for first 2 emails (which will be deleted)
        marketing_categorizer = FakeEmailCategorizer(default_category="Marketing")
        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=marketing_categorizer,
            email_extractor=self.email_extractor,
        )

        for i in range(2):
            email = create_test_email(body=f"ad offer {i}", message_id=f"<ad-{i}@test>")
            self.processor.process_email(email)

        self.assertEqual(self.processor.category_actions["Marketing"]["deleted"], 2)
        self.assertEqual(self.processor.category_actions["Marketing"]["total"], 2)

        # Now use Advertising categorizer for 1 email (which will be kept, since only Marketing is blocked)
        ad_categorizer = FakeEmailCategorizer(default_category="Advertising")
        processor2 = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=ad_categorizer,
            email_extractor=self.email_extractor,
        )

        email = create_test_email(body="advertising content", message_id="<ad-kept@test>")
        processor2.process_email(email)

        self.assertEqual(processor2.category_actions["Advertising"]["kept"], 1)
        self.assertEqual(processor2.category_actions["Advertising"]["total"], 1)


class TestKeepDeleteDecisionLabeling(unittest.TestCase):
    """Test cases for email labeling during processing."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = ConfigurableFakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_blocked_domain_label_applied(self):
        """Test that blocked domain emails get Blocked_Domain label."""
        self.fetcher.set_blocked_domains(["spam.com"])

        email = create_test_email(
            sender="a@spam.com", message_id="<labeled-blocked@test>"
        )
        self.processor.process_email(email)

        labels = self.fetcher.get_labels("<labeled-blocked@test>")
        self.assertIn("Blocked_Domain", labels)

    def test_allowed_domain_label_applied(self):
        """Test that allowed domain emails get Allowed_Domain label."""
        self.fetcher.set_allowed_domains(["trusted.com"])

        email = create_test_email(
            sender="a@trusted.com", message_id="<labeled-allowed@test>"
        )
        self.processor.process_email(email)

        labels = self.fetcher.get_labels("<labeled-allowed@test>")
        self.assertIn("Allowed_Domain", labels)

    def test_category_label_applied(self):
        """Test that categorized emails get category label."""
        # Use a categorizer that returns Advertising by default (valid category)
        ad_categorizer = FakeEmailCategorizer(default_category="Advertising")
        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=ad_categorizer,
            email_extractor=self.email_extractor,
        )

        email = create_test_email(body="ad update", message_id="<labeled-ad@test>")
        self.processor.process_email(email)

        labels = self.fetcher.get_labels("<labeled-ad@test>")
        self.assertIn("Advertising", labels)


class TestKeepDeleteDecisionEdgeCases(unittest.TestCase):
    """Test cases for edge cases in keep/delete decision logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = ConfigurableFakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_empty_from_header(self):
        """Test handling of email with empty From header."""
        email = create_test_email(sender="", message_id="<empty-from@test>")

        # Should not crash - defaults to categorization
        category = self.processor.process_email(email)

        self.assertEqual(category, "Other")
        self.assertEqual(self.fetcher.stats["kept"], 1)

    def test_case_insensitive_domain_matching(self):
        """Test that domain matching is case insensitive."""
        self.fetcher.set_blocked_domains(["SPAM.COM"])

        email = create_test_email(
            sender="test@spam.com", message_id="<case-test@test>"
        )
        self.processor.process_email(email)

        self.assertTrue(self.fetcher.is_deleted("<case-test@test>"))

    def test_domain_with_name_in_from_header(self):
        """Test extraction of domain from 'Name <email>' format."""
        self.fetcher.set_blocked_domains(["spam.com"])

        email = create_test_email(
            sender="Spammer Name <spammer@spam.com>",
            message_id="<name-format@test>",
        )
        self.processor.process_email(email)

        self.assertTrue(self.fetcher.is_deleted("<name-format@test>"))

    def test_subdomain_not_matched_as_parent(self):
        """Test that subdomain is NOT matched when parent domain is blocked."""
        # Only block parent domain
        self.fetcher.set_blocked_domains(["spam.com"])

        email = create_test_email(
            sender="test@mail.spam.com",  # subdomain
            message_id="<subdomain-test@test>",
        )
        self.processor.process_email(email)

        # Subdomain mail.spam.com is different from spam.com
        # So it should NOT be deleted (unless your implementation does subdomain matching)
        # Based on current implementation, this would NOT match
        self.assertFalse(self.fetcher.is_deleted("<subdomain-test@test>"))

    def test_delete_failure_keeps_email(self):
        """Test that if delete fails, email is counted as kept."""
        self.fetcher.set_blocked_domains(["spam.com"])

        # Override delete_email to return False (failure)
        self.fetcher.delete_email = Mock(return_value=False)

        email = create_test_email(
            sender="a@spam.com", message_id="<delete-fail@test>"
        )
        self.processor.process_email(email)

        # Even though it was marked for deletion, since delete failed,
        # it should be counted as kept
        self.assertEqual(self.fetcher.stats["kept"], 1)
        self.assertEqual(self.fetcher.stats["deleted"], 0)


class TestKeepDeleteDecisionSummaryServiceTracking(unittest.TestCase):
    """Test cases for summary service tracking integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = ConfigurableFakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_summary_service_tracks_deleted_email(self):
        """Test that summary service tracks deleted email with correct action."""
        self.fetcher.set_blocked_domains(["spam.com"])

        email = create_test_email(
            sender="a@spam.com",
            subject="Spam Subject",
            message_id="<track-deleted@test>",
        )
        self.processor.process_email(email)

        # Verify track_email was called with action='deleted'
        self.fetcher.summary_service.track_email.assert_called_once()
        call_kwargs = self.fetcher.summary_service.track_email.call_args[1]
        self.assertEqual(call_kwargs["action"], "deleted")
        self.assertEqual(call_kwargs["category"], "Blocked_Domain")
        self.assertTrue(call_kwargs["was_pre_categorized"])

    def test_summary_service_tracks_kept_email(self):
        """Test that summary service tracks kept email with correct action."""
        self.fetcher.set_allowed_domains(["trusted.com"])

        email = create_test_email(
            sender="a@trusted.com",
            subject="Trusted Subject",
            message_id="<track-kept@test>",
        )
        self.processor.process_email(email)

        # Verify track_email was called with action='kept'
        self.fetcher.summary_service.track_email.assert_called_once()
        call_kwargs = self.fetcher.summary_service.track_email.call_args[1]
        self.assertEqual(call_kwargs["action"], "kept")
        self.assertEqual(call_kwargs["category"], "Allowed_Domain")
        self.assertTrue(call_kwargs["was_pre_categorized"])

    def test_summary_service_tracks_categorized_email(self):
        """Test that summary service tracks categorized email correctly."""
        # Use a categorizer that returns Advertising by default (valid category)
        ad_categorizer = FakeEmailCategorizer(default_category="Advertising")
        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=ad_categorizer,
            email_extractor=self.email_extractor,
        )

        email = create_test_email(
            sender="colleague@company.com",
            body="ad report",
            message_id="<track-categorized@test>",
        )
        self.processor.process_email(email)

        # Verify track_email was called with correct category
        self.fetcher.summary_service.track_email.assert_called_once()
        call_kwargs = self.fetcher.summary_service.track_email.call_args[1]
        self.assertEqual(call_kwargs["category"], "Advertising")
        self.assertFalse(call_kwargs["was_pre_categorized"])


class TestKeepDeleteDecisionProcessedMessageIds(unittest.TestCase):
    """Test cases for processed message ID tracking."""

    def setUp(self):
        """Set up test fixtures."""
        self.fetcher = ConfigurableFakeGmailFetcher()
        self.categorizer = FakeEmailCategorizer(default_category="Other")
        self.email_extractor = FakeEmailExtractor()

        self.processor = EmailProcessorService(
            fetcher=self.fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=self.categorizer,
            email_extractor=self.email_extractor,
        )

    def test_processed_message_ids_collected(self):
        """Test that processed message IDs are collected."""
        emails = [
            create_test_email(message_id="<msg-1@test>"),
            create_test_email(message_id="<msg-2@test>"),
            create_test_email(message_id="<msg-3@test>"),
        ]

        for email in emails:
            self.processor.process_email(email)

        self.assertEqual(len(self.processor.processed_message_ids), 3)
        self.assertIn("<msg-1@test>", self.processor.processed_message_ids)
        self.assertIn("<msg-2@test>", self.processor.processed_message_ids)
        self.assertIn("<msg-3@test>", self.processor.processed_message_ids)


if __name__ == "__main__":
    unittest.main()
