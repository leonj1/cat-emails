import os
import time
import logging
from utils.logger import get_logger
from datetime import datetime, date
from typing import Dict, Callable, Optional
from services.account_email_processor_interface import AccountEmailProcessorInterface
from clients.account_category_client_interface import AccountCategoryClientInterface
from services.email_deduplication_factory_interface import EmailDeduplicationFactoryInterface
from services.email_categorizer_interface import EmailCategorizerInterface
from services.logs_collector_service import LogsCollectorService
from services.gmail_fetcher_interface import GmailFetcherInterface
from services.gmail_fetcher_service import GmailFetcher
from services.email_processor_service import EmailProcessorService
from services.processing_status_manager import ProcessingState

logger = get_logger(__name__)


class AccountEmailProcessorService(AccountEmailProcessorInterface):
    """Service for processing emails for Gmail accounts with real-time status tracking."""

    def __init__(
        self,
        processing_status_manager,
        settings_service,
        email_categorizer: EmailCategorizerInterface,
        api_token: str,
        llm_model: str,
        account_category_client: AccountCategoryClientInterface,
        deduplication_factory: EmailDeduplicationFactoryInterface,
        logs_collector: Optional[LogsCollectorService] = None,
        create_gmail_fetcher: Optional[Callable[[str, str, str], GmailFetcherInterface]] = None
    ):
        """
        Initialize the account email processor service.

        Args:
            processing_status_manager: Manager for tracking processing status
            settings_service: Service for getting settings like lookback hours
            email_categorizer: Email categorizer implementation
            api_token: Control API token for domain service authentication
            llm_model: LLM model identifier (e.g., "vertex/google/gemini-2.5-flash")
            account_category_client: AccountCategoryClientInterface implementation (required)
            deduplication_factory: EmailDeduplicationFactoryInterface implementation (required)
            logs_collector: LogsCollectorService instance (optional, creates new if not provided)
            create_gmail_fetcher: Optional callable to create GmailFetcherInterface instances (defaults to GmailFetcher constructor)
        """
        self.processing_status_manager = processing_status_manager
        self.settings_service = settings_service
        self.email_categorizer = email_categorizer
        self.api_token = api_token
        self.llm_model = llm_model
        self.account_category_client = account_category_client
        self.deduplication_factory = deduplication_factory
        self.logs_collector = logs_collector if logs_collector is not None else LogsCollectorService()
        self.create_gmail_fetcher = create_gmail_fetcher if create_gmail_fetcher is not None else GmailFetcher

    def process_account(self, email_address: str) -> Dict:
        """
        Process emails for a single Gmail account with real-time status tracking.

        This implementation:
        1. Connects to Gmail via IMAP
        2. Fetches recent emails
        3. Categorizes them using AI
        4. Applies labels and actions
        5. Sends logs to remote collector

        Args:
            email_address: The Gmail account to process

        Returns:
            Dictionary with processing results
        """
        logger.info(f"🔍 Processing emails for account: {email_address}")

        self.logs_collector.send_log(
            "INFO",
            f"Email processing started for {email_address}",
            {"email": email_address},
            "api-service"
        )

        try:
            # Start processing session
            try:
                self.processing_status_manager.start_processing(email_address)
            except ValueError as e:
                logger.warning(f"Could not start processing for {email_address}: {str(e)}")
                return {
                    "account": email_address,
                    "error": f"Processing already in progress: {str(e)}",
                    "success": False,
                    "timestamp": datetime.now().isoformat()
                }

            # Get account service to check if account exists in database
            account = self.account_category_client.get_account_by_email(email_address)

            if not account:
                error_msg = f"Account {email_address} not found in database"
                logger.error(f"❌ {error_msg}")
                self.logs_collector.send_log("ERROR", error_msg, {"email": email_address}, "api-service")
                self.processing_status_manager.update_status(
                    ProcessingState.ERROR,
                    error_msg,
                    error_message=error_msg
                )
                self.processing_status_manager.complete_processing()
                return {
                    "account": email_address,
                    "error": error_msg,
                    "success": False,
                    "timestamp": datetime.now().isoformat()
                }

            # Get credentials
            app_password = account.app_password
            api_token = self.api_token

            if not app_password:
                error_msg = f"No app password configured for {email_address}"
                logger.error(f"❌ {error_msg}")
                self.logs_collector.send_log("ERROR", error_msg, {"email": email_address}, "api-service")
                self.processing_status_manager.update_status(
                    ProcessingState.ERROR,
                    error_msg,
                    error_message=error_msg
                )
                self.processing_status_manager.complete_processing()
                return {
                    "account": email_address,
                    "error": error_msg,
                    "success": False,
                    "timestamp": datetime.now().isoformat()
                }

            start_time = time.time()

            # Get the current lookback hours from settings
            current_lookback_hours = self.settings_service.get_lookback_hours()

            # Initialize the fetcher using the create function
            fetcher = self.create_gmail_fetcher(email_address, app_password, api_token)

            # Clear any existing tracked data to start fresh
            fetcher.summary_service.clear_tracked_data()

            # Start processing run in database
            fetcher.summary_service.start_processing_run(scan_hours=current_lookback_hours)

            # Step 1: Connect to Gmail IMAP
            self.processing_status_manager.update_status(
                ProcessingState.CONNECTING,
                f"Connecting to Gmail IMAP for {email_address}"
            )
            logger.info(f"  📬 Connecting to Gmail IMAP for {email_address}...")

            fetcher.connect()

            # Step 2: Fetch emails
            self.processing_status_manager.update_status(
                ProcessingState.FETCHING,
                f"Fetching emails from last {current_lookback_hours} hours"
            )
            logger.info(f"  🔎 Fetching emails from last {current_lookback_hours} hours...")

            recent_emails = fetcher.get_recent_emails(current_lookback_hours)
            logger.info(f"Fetched {len(recent_emails)} records from the last {current_lookback_hours} hours.")

            # Identify which emails are new using deduplication client
            deduplication_client = self.deduplication_factory.create_deduplication_client(email_address)
            new_emails = deduplication_client.filter_new_emails(recent_emails)

            # Log deduplication stats
            stats = deduplication_client.get_stats()
            logger.info(f"📊 Email deduplication stats: {stats}")

            # Update fetched count
            fetcher.summary_service.run_metrics['fetched'] = len(recent_emails)

            logger.info(f"  📧 Found {len(new_emails)} emails to process")

            # Step 3: Process emails
            self.processing_status_manager.update_status(
                ProcessingState.PROCESSING,
                f"Processing {len(new_emails)} emails",
                {"current": 0, "total": len(new_emails)}
            )

            processor = EmailProcessorService(
                fetcher,
                email_address,
                self.llm_model,
                self.email_categorizer,
                self.logs_collector
            )

            for i, msg in enumerate(new_emails, 1):
                logger.info(f"    ⚡ Processing email {i}/{len(new_emails)}")
                self.processing_status_manager.update_status(
                    ProcessingState.PROCESSING,
                    f"Processing email {i} of {len(new_emails)}",
                    {"current": i, "total": len(new_emails)}
                )

                # Update status for categorization periodically
                if i % 3 == 1:
                    self.processing_status_manager.update_status(
                        ProcessingState.CATEGORIZING,
                        f"Categorizing email {i} with AI",
                        {"current": i, "total": len(new_emails)}
                    )

                # Process the email
                processor.process_email(msg)

                # Update status for labeling periodically
                if i % 3 == 2:
                    self.processing_status_manager.update_status(
                        ProcessingState.LABELING,
                        f"Applying Gmail labels for email {i}",
                        {"current": i, "total": len(new_emails)}
                    )

                # Log progress every 5 emails
                if i % 5 == 0:
                    logger.info(f"    📊 Progress: {i}/{len(new_emails)} emails processed")
                    self.processing_status_manager.update_status(
                        ProcessingState.PROCESSING,
                        f"Processed {i} of {len(new_emails)} emails",
                        {"current": i, "total": len(new_emails)}
                    )

            # Bulk mark emails as processed
            processed_message_ids = processor.processed_message_ids
            if processed_message_ids:
                logger.info(f"🔄 Bulk marking {len(processed_message_ids)} emails as processed...")
                try:
                    successful, errors = deduplication_client.bulk_mark_as_processed(processed_message_ids)
                    logger.info(f"✅ Bulk processing completed: {successful} successful, {errors} errors")
                except Exception as e:
                    logger.error(f"❌ Bulk deduplication failed: {e}")

            # Record category statistics
            category_actions = processor.category_actions
            if fetcher.account_service and category_actions:
                try:
                    today = date.today()
                    fetcher.account_service.record_category_stats(
                        email_address=email_address,
                        stats_date=today,
                        category_stats=category_actions
                    )
                    fetcher.account_service.update_account_last_scan(email_address)
                    logger.info(f"Recorded category statistics for {email_address}: {len(category_actions)} categories")
                except Exception as e:
                    logger.error(f"Failed to record category statistics for {email_address}: {str(e)}")
            elif fetcher.account_service:
                try:
                    fetcher.account_service.update_account_last_scan(email_address)
                    logger.info(f"Updated last scan timestamp for {email_address}")
                except Exception as e:
                    logger.error(f"Failed to update last scan timestamp for {email_address}: {str(e)}")

            processing_time = time.time() - start_time

            # Complete processing run in database
            fetcher.summary_service.complete_processing_run(success=True)

            # Mark processing as completed
            self.processing_status_manager.update_status(
                ProcessingState.COMPLETED,
                f"Successfully processed {len(new_emails)} emails",
                {"current": len(new_emails), "total": len(new_emails)}
            )

            result = {
                "account": email_address,
                "emails_found": len(recent_emails),
                "emails_processed": len(new_emails),
                "emails_categorized": len(new_emails),
                "emails_labeled": len(new_emails),
                "processing_time_seconds": round(processing_time, 2),
                "timestamp": datetime.now().isoformat(),
                "success": True
            }

            logger.info(f"✅ Successfully processed {email_address}: {len(new_emails)} emails in {processing_time:.2f}s")

            # Send completion log
            self.logs_collector.send_log(
                "INFO",
                f"Email processing completed successfully for {email_address}",
                {
                    "processed": fetcher.stats['deleted'] + fetcher.stats['kept'],
                    "deleted": fetcher.stats['deleted'],
                    "kept": fetcher.stats['kept']
                },
                "api-service"
            )

            # Complete the processing session
            self.processing_status_manager.complete_processing()

            # Disconnect from Gmail
            fetcher.disconnect()

            return result

        except Exception as e:
            logger.error(f"❌ Error processing emails for {email_address}: {str(e)}")

            # Send error log to remote collector
            self.logs_collector.send_log(
                "ERROR",
                f"Email processing failed for {email_address}: {str(e)}",
                {"error": str(e), "email": email_address},
                "api-service"
            )

            # Update status to error and complete processing
            try:
                self.processing_status_manager.update_status(
                    ProcessingState.ERROR,
                    f"Processing failed: {str(e)}",
                    error_message=str(e)
                )
            except RuntimeError:
                # If no processing session is active, log the error but don't fail
                logger.warning(f"Could not update status to ERROR - no active session for {email_address}")
            finally:
                # Always try to complete processing to clean up state
                self.processing_status_manager.complete_processing()

            return {
                "account": email_address,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
