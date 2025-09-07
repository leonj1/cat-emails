import os
import sys
import importlib
from email.message import EmailMessage
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import List

import pytest

# Configure RequestYAI (OpenAI-compatible) endpoint for this test
REQUESTY_API_KEY = os.getenv("REQUESTY_API_KEY")
REQUESTY_API_URL = os.getenv("REQUESTY_API_URL")

# Normalize base URL for OpenAI-compatible client: strip trailing '/v1' if provided,
# since LLMCategorizeEmails appends '/v1' internally.
REQUESTY_BASE_URL = (REQUESTY_API_URL or "").rstrip("/")
if REQUESTY_BASE_URL.endswith("/v1"):
    REQUESTY_BASE_URL = REQUESTY_BASE_URL[:-3]

# Skip the test at collection time if required env vars are not provided
if not REQUESTY_API_KEY or not REQUESTY_BASE_URL:
    pytest.skip("REQUESTY_API_KEY and REQUESTY_API_URL must be set to run this test", allow_module_level=True)


def import_gmail_fetcher_safely():
    """
    Import gmail_fetcher while avoiding argparse conflicts with pytest args.
    gmail_fetcher.py parses args at module import time.
    """
    saved_argv = sys.argv
    try:
        # Neutralize pytest CLI args so argparse in gmail_fetcher doesn't exit
        sys.argv = ["gmail_fetcher.py"]
        module = importlib.import_module("gmail_fetcher")
        return module
    finally:
        sys.argv = saved_argv


# Use the interface with a "fake" concrete class that implements it (no mocks).
from services.gmail_fetcher_interface import GmailFetcherInterface  # noqa: E402


class FakeGmailFetcher(GmailFetcherInterface):
    """
    Fake Gmail fetcher implementing GmailFetcherInterface.
    Returns a single simple advertisement email for testing.
    No network calls to Gmail are made.
    """

    def __init__(self):
        self.connected = False
        self._email = self._make_ad_email()

    def _make_ad_email(self) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = "Promotions & Deals <promo@shop.example>"
        msg["To"] = "user@example.com"
        msg["Subject"] = "Limited Time Offer: 50% Off All Items!"
        msg["Message-ID"] = "<test-ad-1@shop.example>"
        msg["Date"] = format_datetime(datetime.now(timezone.utc))
        # Simple advertisement body (plain text)
        msg.set_content(
            "Huge Sale Today Only! Save 50% on your favorite products. "
            "Shop now and don't miss out on incredible discounts."
        )
        return msg

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def get_recent_emails(self, hours: int = 2) -> List[EmailMessage]:
        if not self.connected:
            raise Exception("Not connected to Gmail")
        return [self._email]

    def get_email_body(self, email_message) -> str:
        # For this fake, content is always plain text
        try:
            return email_message.get_content()
        except Exception:
            return ""

    def add_label(self, message_id: str, label: str) -> bool:
        # Pretend labeling is always successful
        return True

    def delete_email(self, message_id: str) -> bool:
        # Pretend deletion is always successful
        return True


def test_categorize_simple_ad_email_with_fake_gmail_and_real_ollama():
    # Import gmail_fetcher after preparing env and argv
    gf = import_gmail_fetcher_safely()

    # Monkeypatch gmail_fetcher to use RequestYAI via an OpenAI-compatible client
    # This forces the categorizer to call the RequestYAI endpoint with the provided model.
    def _make_requesty_categorizer(model: str):
        return gf.LLMCategorizeEmails(
            provider="openai",
            api_token=REQUESTY_API_KEY,
            model=model,
            base_url=REQUESTY_BASE_URL,
        )

    gf._make_llm_categorizer = _make_requesty_categorizer

    # Prepare the fake Gmail interface and fetch the advertisement email
    fake = FakeGmailFetcher()
    fake.connect()
    try:
        emails = fake.get_recent_emails(hours=2)
        assert len(emails) == 1, "Expected exactly one advertisement email from the fake fetcher"

        msg = emails[0]
        subject = msg.get("Subject", "")
        body = fake.get_email_body(msg)

        # Minimal content prep similar to the main flow
        contents = f"{subject}. {body}"

        # Categorize using RequestYAI (OpenAI-compatible) endpoint and specified model
        category = gf.categorize_email_with_resilient_client(contents, model="google/gemini-2.0-flash-001")

        normalized = (
            category.strip()
            .replace('"', "")
            .replace("'", "")
            .replace("*", "")
            .replace("=", "")
            .replace("+", "")
            .replace("-", "")
            .replace("_", "")
            .strip()
        )

        # Expect the advertisement email to be categorized as commercial content
        # Per categorization rules, 'Wants-Money' has higher priority than 'Advertising',
        # so allow either outcome when using a real model endpoint without mocks.
        expected = {"advertising", "wantsmoney"}
        assert normalized.lower().replace(" ", "") in expected, f"Expected one of {expected}, got: {category!r}"
    finally:
        fake.disconnect()
