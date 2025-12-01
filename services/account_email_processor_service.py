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
from services.gmail_fetcher_interface import GmailFetcherInterface
from services.gmail_fetcher_service import GmailFetcher
from services.email_processor_service import EmailProcessorService
from services.extract_sender_email_service import ExtractSenderEmailService
from services.processing_status_manager import ProcessingState
from services.interfaces.blocking_recommendation_collector_interface import IBlockingRecommendationCollector
from services.interfaces.recommendation_email_notifier_interface import IRecommendationEmailNotifier
from services.domain_extractor import extract_domain

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
        create_gmail_fetcher: Optional[Callable[[str, str, str], GmailFetcherInterface]] = None,
        blocking_recommendation_collector: Optional[IBlockingRecommendationCollector] = None,
        recommendation_email_notifier: Optional[IRecommendationEmailNotifier] = None
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
            create_gmail_fetcher: Optional callable to create GmailFetcherInterface instances (defaults to GmailFetcher constructor)
            blocking_recommendation_collector: Optional IBlockingRecommendationCollector for collecting domain recommendations
            recommendation_email_notifier: Optional IRecommendationEmailNotifier for sending recommendation emails
        """
        self.processing_status_manager = processing_status_manager
        self.settings_service = settings_service
        self.email_categorizer = email_categorizer
        self.api_token = api_token
        self.llm_model = llm_model
        self.account_category_client = account_category_client
        self.deduplication_factory = deduplication_factory
        self.create_gmail_fetcher = create_gmail_fetcher if create_gmail_fetcher is not None else GmailFetcher
        self.blocking_recommendation_collector = blocking_recommendation_collector
        self.recommendation_email_notifier = recommendation_email_notifier

    def process_account(self, email_address: str) -> Dict:
        """
        Process emails for a single Gmail account with real-time status tracking.

        This implementation:
        1. Connects to Gmail via IMAP
        2. Fetches recent emails
        3. Categorizes them using AI
        4. Applies labels and actions
        5. Collects domain blocking recommendations (if collector provided)
        6. Sends recommendation notification email (if notifier provided)

        Args:
            email_address: The Gmail account to process

        Returns:
            Dictionary with processing results including:
            - Standard fields: account, emails_found, emails_processed, etc.
            - Recommendation fields (if collector provided):
              recommended_domains_to_block, total_emails_matched, unique_domains_count
            - Notification fields (if notifier provided):
              notification_sent, notification_error
        """
        logger.info(f"🔍 Processing emails for account: {email_address}")

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

            # Clear the recommendation collector for this processing run
            if self.blocking_recommendation_collector:
                self.blocking_recommendation_collector.clear()

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

            # Create email extractor service
            email_extractor = ExtractSenderEmailService()
            
            processor = EmailProcessorService(
                fetcher,
                email_address,
                self.llm_model,
                self.email_categorizer,
                email_extractor
            )

            # Get blocked domains once outside the loop if collector is present
            blocked_domains_set = (
                fetcher.get_blocked_domains() if self.blocking_recommendation_collector else set()
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
                category = processor.process_email(msg)

                # Collect domain recommendation if collector is present and email was categorized
                if self.blocking_recommendation_collector and category:
                    try:
                        from_header = str(msg.get("From", ""))
                        if from_header and "@" in from_header:
                            # Extract sender email using the email extractor
                            sender_email = email_extractor.extract_sender_email(from_header)
                            if sender_email:
                                sender_domain = extract_domain(sender_email)
                                # Collect the recommendation
                                self.blocking_recommendation_collector.collect(
                                    sender_domain,
                                    category,
                                    blocked_domains_set
                                )
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Failed to collect domain recommendation: {e}")
                    except Exception:
                        logger.exception("Unexpected error collecting domain recommendation")

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

            # Get recommendation summary and send notification
            summary = None
            notification_result = None
            recommendations = []
            total_matched = 0
            unique_domains = 0

            if self.blocking_recommendation_collector:
                try:
                    summary = self.blocking_recommendation_collector.get_summary()
                    recommendations = summary.recommendations
                    total_matched = summary.total_count
                    unique_domains = summary.domain_count

                    # Only send notification if there are recommendations
                    if self.recommendation_email_notifier and unique_domains > 0:
                        try:
                            notification_result = self.recommendation_email_notifier.send_recommendations(
                                email_address,
                                recommendations
                            )
                        except (ConnectionError, TimeoutError, ValueError) as e:
                            logger.warning(f"Failed to send recommendation notification: {e}")
                        except Exception:
                            logger.exception("Unexpected error sending recommendation notification")
                except (AttributeError, ValueError, KeyError) as e:
                    logger.warning(f"Failed to get recommendation summary: {e}")
                except Exception:
                    logger.exception("Unexpected error in recommendation summary")

            result = {
                "account": email_address,
                "emails_found": len(recent_emails),
                "emails_processed": len(new_emails),
                "emails_categorized": len(new_emails),
                "emails_labeled": len(new_emails),
                "category_counts": category_actions,  # Add category counts for aggregator
                "processing_time_seconds": round(processing_time, 2),
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "recommended_domains_to_block": [r.to_dict() for r in recommendations],
                "total_emails_matched": total_matched,
                "unique_domains_count": unique_domains,
                "notification_sent": notification_result.success if notification_result else False,
                "notification_error": notification_result.error_message if notification_result else None
            }

            logger.info(f"✅ Successfully processed {email_address}: {len(new_emails)} emails in {processing_time:.2f}s")

            # Complete the processing session
            self.processing_status_manager.complete_processing()

            # Disconnect from Gmail
            fetcher.disconnect()

            return result

        except Exception as e:
            logger.error(f"❌ Error processing emails for {email_address}: {str(e)}")

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
