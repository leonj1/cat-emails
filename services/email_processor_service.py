from __future__ import annotations

import logging
from utils.logger import get_logger
import ssl
from email.message import Message
from typing import Dict, List, Optional

from services.categorize_emails_interface import SimpleEmailCategory
from services.email_categorizer_interface import EmailCategorizerInterface
from services.gmail_fetcher_service import GmailFetcher as ServiceGmailFetcher
from services.logs_collector_service import LogsCollectorService

logger = get_logger(__name__)


class EmailProcessorService:
    """Encapsulates the logic for processing a single Gmail message.

    This class owns the heavy email processing logic previously in gmail_fetcher.py.
    It mutates the provided fetcher.stats and tracks category actions and processed IDs.
    """

    def __init__(
        self,
        fetcher: ServiceGmailFetcher,
        email_address: str,
        model: str,
        email_categorizer: EmailCategorizerInterface,
        logs_collector: Optional[LogsCollectorService] = None,
    ) -> None:
        self.fetcher = fetcher
        self.email_address = email_address
        self.model = model
        self.email_categorizer = email_categorizer

        # Initialize logs collector service
        self.logs_collector = logs_collector if logs_collector is not None else LogsCollectorService()

        # Aggregated results for the whole batch
        self.category_actions: Dict[str, Dict[str, int]] = {}
        self.processed_message_ids: List[str] = []

    def _extract_sender_email(self, from_header: str) -> str:
        """Extract sender email using fetcher helper if available, otherwise fallback."""
        if hasattr(self.fetcher, "_extract_email_address"):
            try:
                # type: ignore[attr-defined]
                return self.fetcher._extract_email_address(from_header) if from_header else ""
            except Exception:
                pass
        from email.utils import parseaddr
        _, sender_email = parseaddr(from_header) if from_header else ("", "")
        return sender_email.lower() if sender_email else ""

    def process_email(self, msg: Message) -> Optional[str]:
        """Process a single email message. Returns the resolved category or None if skipped."""
        # Access database service through summary service
        db_svc = getattr(self.fetcher.summary_service, "db_service", None)

        # Early extract identifiers and prevent duplicate processing before any LLM calls
        from_header = str(msg.get("From", ""))
        subject = msg.get("Subject", "")
        message_id = msg.get("Message-ID", "")

        # Safeguard duplicate check (pre-filter should have removed these already)
        if db_svc and message_id:
            try:
                if db_svc.is_message_processed(self.email_address, message_id):
                    logger.info(f"Skipping already-processed message (safeguard): {message_id}")
                    return None
            except Exception as e:
                logger.warning(f"Duplicate check failed for message {message_id}: {e}. Proceeding without skip.")

        # Get the email body
        body = self.fetcher.get_email_body(msg)
        pre_categorized = False
        deletion_candidate = False

        # Extract sender details
        sender_email = self._extract_sender_email(from_header)
        sender_domain = self.fetcher._extract_domain(from_header) if from_header else ""

        # Check repeat offender patterns first (skip expensive LLM)
        repeat_offender_category: Optional[str] = None
        if hasattr(self.fetcher, "summary_service") and self.fetcher.summary_service and self.fetcher.summary_service.db_service:
            try:
                from services.repeat_offender_service import RepeatOffenderService
                with self.fetcher.summary_service.db_service.Session() as session:  # type: ignore[attr-defined]
                    repeat_offender_service = RepeatOffenderService(session, self.email_address)
                    repeat_offender_category = repeat_offender_service.check_repeat_offender(
                        sender_email, sender_domain, subject
                    )
            except Exception as e:
                logger.warning(f"Failed to check repeat offender patterns: {e}")
                repeat_offender_category = None

        if repeat_offender_category:
            category = repeat_offender_category
            pre_categorized = True
            deletion_candidate = True
            logger.info(f"Repeat offender detected: {sender_email or sender_domain} -> {category}")
        else:
            # Check domain lists
            if self.fetcher._is_domain_blocked(from_header):
                category = "Blocked_Domain"
                pre_categorized = True
                deletion_candidate = True
                self.logs_collector.send_log(
                    "INFO",
                    f"Email from blocked domain: {sender_domain}",
                    {"sender": sender_email, "domain": sender_domain, "subject": subject[:50]},
                    "email-processor"
                )
            elif self.fetcher._is_domain_allowed(from_header):
                category = "Allowed_Domain"
                pre_categorized = True
                deletion_candidate = False
                self.logs_collector.send_log(
                    "INFO",
                    f"Email from allowed domain: {sender_domain}",
                    {"sender": sender_email, "domain": sender_domain, "subject": subject[:50]},
                    "email-processor"
                )
            else:
                category = "Other"  # placeholder, will be overwritten if not pre_categorized

        # Categorize the email if not pre-categorized
        if not pre_categorized:
            contents_without_links = self.fetcher.remove_http_links(f"{subject}. {body}")
            contents_without_images = self.fetcher.remove_images_from_email(contents_without_links)
            contents_without_encoded = self.fetcher.remove_encoded_content(contents_without_images)
            contents_cleaned = contents_without_encoded

            # Use injected categorizer for categorization
            category = self.email_categorizer.categorize(contents_cleaned, self.model)

            # Clean up the category response
            category = (
                category.replace('"', "")
                .replace("'", "")
                .replace("*", "")
                .replace("=", "")
                .replace("+", "")
                .replace("-", "")
                .replace("_", "")
                .strip()
            )

            # Validate category response
            valid_categories = {c.value for c in SimpleEmailCategory}
            if len(category) > 30 or category not in valid_categories:
                logger.warning(f"Invalid category response: '{category}', defaulting to 'Other'")
                category = "Other"

            # Check if category is blocked
            is_blocked = self.fetcher._is_category_blocked(category)
            if is_blocked:
                deletion_candidate = True
                logger.info(f"🗑️ Category '{category}' is blocked - marking for deletion")
            else:
                deletion_candidate = False
                logger.info(f"📥 Category '{category}' is not blocked - keeping email")

        # Apply label, take action, and track
        try:
            # Re-pull headers in case objects changed (kept for parity with original code)
            from_header = msg.get("From", "")
            subject = msg.get("Subject", "")
            message_id = msg.get("Message-ID", "")

            # Build log message (will complete after action is taken)
            log_msg = f'From: "{from_header}" | Subject: {subject}'
            if len(category) < 20:
                log_msg += f" | Category: {category}"
            log_msg += f" | Deletion Candidate: {deletion_candidate}"

            # Extract sender domain for tracking
            sender_domain = self.fetcher._extract_domain(from_header) if from_header else None

            try:
                self.fetcher.add_label(message_id, category)
                # Track categories
                self.fetcher.stats["categories"][category] += 1
            except ssl.SSLError as ssl_err:
                logger.error(f"SSL Error while adding label: {ssl_err}")
                print("Skipping label addition due to SSL error")
                return None
            except Exception as e:
                logger.error(f"Error adding label: {e}")
                print("Skipping label addition due to error")
                return None

            # Track kept/deleted emails
            action_taken = "kept"  # Default action

            if deletion_candidate:
                try:
                    if self.fetcher.delete_email(message_id):
                        log_msg += " | Email deleted successfully"
                        action_taken = "deleted"
                        self.fetcher.stats["deleted"] += 1
                    else:
                        log_msg += " | Failed to delete email"
                        self.fetcher.stats["kept"] += 1
                except ssl.SSLError as ssl_err:
                    logger.error(f"SSL Error while deleting email: {ssl_err}")
                    log_msg += " | Skipping email deletion due to SSL error"
                    print(log_msg)
                    self.fetcher.stats["kept"] += 1
                    return None
            else:
                log_msg += " | Email left in inbox"
                self.fetcher.stats["kept"] += 1

            # Print the complete log message
            print(log_msg)

            # Track email in summary service
            self.fetcher.summary_service.track_email(
                message_id=message_id,
                sender=from_header,
                subject=subject,
                category=category,
                action=action_taken,
                sender_domain=sender_domain,
                was_pre_categorized=pre_categorized,
            )

            # Record email outcome for repeat offender tracking
            if (
                not category.endswith("-RepeatOffender")  # Don't track repeat offenders to avoid recursion
                and hasattr(self.fetcher, "summary_service")
                and self.fetcher.summary_service
                and self.fetcher.summary_service.db_service
            ):
                try:
                    from services.repeat_offender_service import RepeatOffenderService
                    with self.fetcher.summary_service.db_service.Session() as session:  # type: ignore[attr-defined]
                        repeat_offender_service = RepeatOffenderService(session, self.email_address)
                        repeat_offender_service.record_email_outcome(
                            sender_email=sender_email,
                            sender_domain=sender_domain,
                            subject=subject,
                            category=category,
                            was_deleted=(action_taken == "deleted"),
                        )
                except Exception as e:
                    logger.warning(f"Failed to record repeat offender pattern: {e}")

            # Track category statistics for account service
            if category not in self.category_actions:
                self.category_actions[category] = {"total": 0, "deleted": 0, "kept": 0, "archived": 0}

            self.category_actions[category]["total"] += 1
            if action_taken == "deleted":
                self.category_actions[category]["deleted"] += 1
            elif action_taken == "kept":
                self.category_actions[category]["kept"] += 1
            elif action_taken == "archived":
                self.category_actions[category]["archived"] += 1

            # Collect message ID for bulk processing at the end
            if message_id:
                self.processed_message_ids.append(message_id)
                logger.info(f"📝 Queued email for bulk processing: {message_id}")
            else:
                logger.warning("⚠️ No message_id available - cannot mark as processed")
        except Exception as e:
            logger.error(f"Error processing email: {e}")
            print(f"Skipping email due to error: {e}")

            # Send error log
            self.logs_collector.send_log(
                "ERROR",
                f"Failed to process email: {str(e)}",
                {
                    "message_id": message_id,
                    "sender": from_header,
                    "subject": subject[:50] if subject else "",
                    "error": str(e)
                },
                "email-processor"
            )
            return None

        return category
