"""
Service for processing emails for a single Gmail account.

This service extracts the process_account functionality from AccountEmailProcessorService
into a dedicated, testable service with proper dependency injection.
"""

import time
from datetime import datetime, date
from typing import Dict, Callable, List
from utils.logger import get_logger
from services.processing_status_manager import ProcessingState
from services.email_processor_service import EmailProcessorService
from services.extract_sender_email_service import ExtractSenderEmailService
from services.email_categorizer_interface import EmailCategorizerInterface

logger = get_logger(__name__)


class CallbackCategorizerAdapter(EmailCategorizerInterface):
    """Adapter to convert a categorization callback into EmailCategorizerInterface.

    This adapter allows callback-based categorization functions to be used
    wherever the EmailCategorizerInterface is required, enabling dependency
    injection and testability without requiring immediate refactoring of
    existing callback-based code.
    """

    def __init__(self, callback: Callable[[str, str], str]) -> None:
        """Initialize the adapter with a categorization callback.

        Args:
            callback: Function that takes (email_content, model) and returns category name
        """
        self.callback = callback

    def categorize(self, email_content: str, model: str) -> str:
        """Delegate categorization to the wrapped callback.

        Args:
            email_content: The email content to categorize
            model: The model identifier to use for categorization

        Returns:
            str: The category name
        """
        return self.callback(email_content, model)


class AccountEmailProcessorServiceProcessAccountService:
    """
    Dedicated service for processing emails for a single Gmail account.

    This service handles the complete email processing workflow:
    1. Validates account exists and has credentials
    2. Connects to Gmail via IMAP
    3. Fetches and deduplicates emails
    4. Categorizes and processes emails
    5. Records statistics and updates status
    """

    def __init__(
        self,
        processing_status_manager,
        settings_service,
        email_categorizer_callback: Callable[[str, str], str],
        api_token: str,
        llm_model: str,
        account_category_client,
        deduplication_factory,
        create_gmail_fetcher: Callable[[str, str, str], object]
    ):
        """Initialize the process account service with all dependencies."""
        self.processing_status_manager = processing_status_manager
        self.settings_service = settings_service
        self.email_categorizer_callback = email_categorizer_callback
        self.api_token = api_token
        self.llm_model = llm_model
        self.account_category_client = account_category_client
        self.deduplication_factory = deduplication_factory
        self.create_gmail_fetcher = create_gmail_fetcher

    def process_account(self, email_address: str) -> Dict:
        """
        Process emails for a single Gmail account with real-time status tracking.

        Args:
            email_address: The Gmail account to process

        Returns:
            Dictionary with processing results
        """
        logger.info(f"Email processing started for {email_address}")

        try:
            return self._process_account_workflow(email_address)
        except Exception as e:
            return self._handle_processing_error(email_address, e)

    def _process_account_workflow(self, email_address: str) -> Dict:
        """Execute the account processing workflow with validation."""
        if not self._start_processing_session(email_address):
            return self._create_error_response(
                email_address,
                "Processing already in progress"
            )

        account = self._validate_account(email_address)
        if not account:
            return self._handle_account_not_found(email_address)

        if not account.app_password:
            return self._handle_no_password(email_address)

        return self._execute_processing(email_address, account.app_password)

    def _start_processing_session(self, email_address: str) -> bool:
        """
        Start a processing session.

        Returns:
            True if session started successfully, False otherwise
        """
        try:
            self.processing_status_manager.start_processing(email_address)
            return True
        except ValueError as e:
            logger.warning(f"Could not start processing for {email_address}: {str(e)}")
            return False

    def _validate_account(self, email_address: str):
        """Validate that account exists in database."""
        return self.account_category_client.get_account_by_email(email_address)

    def _handle_account_not_found(self, email_address: str) -> Dict:
        """Handle case when account is not found."""
        error_msg = f"Account {email_address} not found in database"
        logger.error(f"Error: {error_msg}")
        self._update_error_status(error_msg)
        self.processing_status_manager.complete_processing()
        return self._create_error_response(email_address, error_msg)

    def _handle_no_password(self, email_address: str) -> Dict:
        """Handle case when account has no app password."""
        error_msg = f"No app password configured for {email_address}"
        logger.error(f"Error: {error_msg}")
        self._update_error_status(error_msg)
        self.processing_status_manager.complete_processing()
        return self._create_error_response(email_address, error_msg)

    def _execute_processing(self, email_address: str, app_password: str) -> Dict:
        """Execute the main email processing workflow."""
        start_time = time.time()
        lookback_hours = self.settings_service.get_lookback_hours()

        fetcher = self._initialize_fetcher(email_address, app_password, lookback_hours)
        self._connect_to_gmail(email_address)
        fetcher.connect()

        recent_emails, new_emails = self._fetch_and_deduplicate(
            fetcher, email_address, lookback_hours
        )
        self._process_emails(fetcher, email_address, new_emails)
        self._record_statistics(fetcher, email_address)

        return self._finalize_processing(
            fetcher, email_address, len(recent_emails), len(new_emails), start_time
        )

    def _finalize_processing(
        self, fetcher, email_address: str, found: int, processed: int, start_time: float
    ) -> Dict:
        """Finalize processing and create result."""
        processing_time = time.time() - start_time
        fetcher.summary_service.complete_processing_run(success=True)
        self._complete_processing_successfully(processed)

        result = self._create_success_response(
            email_address, found, processed, processing_time
        )
        logger.info(f"Email processing completed successfully for {email_address}")
        self.processing_status_manager.complete_processing()
        fetcher.disconnect()
        return result

    def _initialize_fetcher(self, email_address: str, app_password: str, lookback_hours: int):
        """Initialize and configure the Gmail fetcher."""
        fetcher = self.create_gmail_fetcher(email_address, app_password, self.api_token)
        fetcher.summary_service.clear_tracked_data()
        fetcher.summary_service.start_processing_run(scan_hours=lookback_hours)
        return fetcher

    def _connect_to_gmail(self, email_address: str) -> None:
        """Update status for Gmail connection."""
        self.processing_status_manager.update_status(
            ProcessingState.CONNECTING,
            f"Connecting to Gmail IMAP for {email_address}"
        )
        logger.info(f"Connecting to Gmail IMAP for {email_address}...")

    def _fetch_and_deduplicate(self, fetcher, email_address: str, lookback_hours: int) -> tuple:
        """
        Fetch emails and remove duplicates.

        Returns:
            Tuple of (recent_emails, new_emails)
        """
        self.processing_status_manager.update_status(
            ProcessingState.FETCHING,
            f"Fetching emails from last {lookback_hours} hours"
        )
        logger.info(f"Fetching emails from last {lookback_hours} hours...")

        recent_emails = fetcher.get_recent_emails(lookback_hours)
        logger.info(f"Fetched {len(recent_emails)} records from last {lookback_hours} hours.")

        deduplication_client = self.deduplication_factory.create_deduplication_client(email_address)
        new_emails = deduplication_client.filter_new_emails(recent_emails)

        stats = deduplication_client.get_stats()
        logger.info(f"Email deduplication stats: {stats}")

        fetcher.summary_service.run_metrics['fetched'] = len(recent_emails)
        logger.info(f"Found {len(new_emails)} emails to process")

        return recent_emails, new_emails

    def _process_emails(self, fetcher, email_address: str, new_emails: List) -> None:
        """Process all new emails through categorization and labeling."""
        total = len(new_emails)
        self.processing_status_manager.update_status(
            ProcessingState.PROCESSING,
            f"Processing {total} emails",
            {"current": 0, "total": total}
        )

        email_categorizer = CallbackCategorizerAdapter(self.email_categorizer_callback)
        email_extractor = ExtractSenderEmailService()

        processor = EmailProcessorService(
            fetcher, email_address, self.llm_model,
            email_categorizer, email_extractor
        )

        for i, msg in enumerate(new_emails, 1):
            self._process_single_email(processor, msg, i, total)

        self._bulk_mark_processed(processor, email_address)
        self._update_category_stats(fetcher, processor, email_address)

    def _process_single_email(self, processor, msg, index: int, total: int) -> None:
        """Process a single email with status updates."""
        logger.info(f"Processing email {index}/{total}")
        self._update_processing_status(index, total)

        if index % 3 == 1:
            self._update_categorizing_status(index, total)

        processor.process_email(msg)

        if index % 3 == 2:
            self._update_labeling_status(index, total)

        if index % 5 == 0:
            self._log_progress(index, total)

    def _update_processing_status(self, index: int, total: int) -> None:
        """Update status for processing step."""
        self.processing_status_manager.update_status(
            ProcessingState.PROCESSING,
            f"Processing email {index} of {total}",
            {"current": index, "total": total}
        )

    def _update_categorizing_status(self, index: int, total: int) -> None:
        """Update status for categorization step."""
        self.processing_status_manager.update_status(
            ProcessingState.CATEGORIZING,
            f"Categorizing email {index} with AI",
            {"current": index, "total": total}
        )

    def _update_labeling_status(self, index: int, total: int) -> None:
        """Update status for labeling step."""
        self.processing_status_manager.update_status(
            ProcessingState.LABELING,
            f"Applying Gmail labels for email {index}",
            {"current": index, "total": total}
        )

    def _log_progress(self, index: int, total: int) -> None:
        """Log processing progress."""
        logger.info(f"Progress: {index}/{total} emails processed")
        self.processing_status_manager.update_status(
            ProcessingState.PROCESSING,
            f"Processed {index} of {total} emails",
            {"current": index, "total": total}
        )

    def _bulk_mark_processed(self, processor, email_address: str) -> None:
        """Bulk mark emails as processed in deduplication system."""
        message_ids = processor.processed_message_ids
        if not message_ids:
            return

        logger.info(f"Bulk marking {len(message_ids)} emails as processed...")
        try:
            dedup_client = self.deduplication_factory.create_deduplication_client(email_address)
            successful, errors = dedup_client.bulk_mark_as_processed(message_ids)
            logger.info(f"Bulk processing completed: {successful} successful, {errors} errors")
        except Exception as e:
            logger.error(f"Bulk deduplication failed: {e}")

    def _update_category_stats(self, fetcher, processor, email_address: str) -> None:
        """Update category statistics in database."""
        category_actions = processor.category_actions
        if not fetcher.account_service:
            return

        if category_actions:
            try:
                today = date.today()
                fetcher.account_service.record_category_stats(
                    email_address=email_address,
                    stats_date=today,
                    category_stats=category_actions
                )
                fetcher.account_service.update_account_last_scan(email_address)
                logger.info(f"Recorded category statistics for {email_address}")
            except Exception as e:
                logger.error(f"Failed to record category statistics: {str(e)}")
        else:
            try:
                fetcher.account_service.update_account_last_scan(email_address)
                logger.info(f"Updated last scan timestamp for {email_address}")
            except Exception as e:
                logger.error(f"Failed to update last scan timestamp: {str(e)}")

    def _record_statistics(self, fetcher, email_address: str) -> None:
        """Record processing statistics."""
        pass  # Statistics recording happens in _update_category_stats

    def _complete_processing_successfully(self, email_count: int) -> None:
        """Update status to completed."""
        self.processing_status_manager.update_status(
            ProcessingState.COMPLETED,
            f"Successfully processed {email_count} emails",
            {"current": email_count, "total": email_count}
        )

    def _create_success_response(
        self, email_address: str, found: int, processed: int, processing_time: float
    ) -> Dict:
        """Create successful processing response."""
        logger.info(
            f"Successfully processed {email_address}: {processed} emails in {processing_time:.2f}s"
        )
        return {
            "account": email_address,
            "emails_found": found,
            "emails_processed": processed,
            "emails_categorized": processed,
            "emails_labeled": processed,
            "processing_time_seconds": round(processing_time, 2),
            "timestamp": datetime.now().isoformat(),
            "success": True
        }

    def _handle_processing_error(self, email_address: str, error: Exception) -> Dict:
        """Handle processing errors."""
        logger.error(f"Email processing failed for {email_address}: {error!s}")

        try:
            self.processing_status_manager.update_status(
                ProcessingState.ERROR,
                f"Processing failed: {str(error)}",
                error_message=str(error)
            )
        except RuntimeError:
            logger.warning(f"Could not update status to ERROR - no active session")
        finally:
            self.processing_status_manager.complete_processing()

        return self._create_error_response(email_address, str(error))

    def _update_error_status(self, error_msg: str) -> None:
        """Update processing status to error."""
        self.processing_status_manager.update_status(
            ProcessingState.ERROR,
            error_msg,
            error_message=error_msg
        )

    def _create_error_response(self, email_address: str, error_msg: str) -> Dict:
        """Create error response dictionary."""
        return {
            "account": email_address,
            "error": error_msg,
            "success": False,
            "timestamp": datetime.now().isoformat()
        }
