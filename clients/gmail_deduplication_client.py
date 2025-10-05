"""
Gmail Deduplication Client

Handles tracking and detection of previously processed emails to prevent
duplicate processing across application restarts and container rebuilds.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Set, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from clients.email_deduplication_client_interface import EmailDeduplicationClientInterface
from models.database import ProcessedEmailLog
from models.processed_email_log_model import ProcessedEmailLogModel

logger = logging.getLogger(__name__)


class GmailDeduplicationClient(EmailDeduplicationClientInterface):
    """
    Client for managing Gmail email deduplication across application restarts.

    This client tracks which emails have been processed to prevent duplicate
    processing when the application restarts or containers are rebuilt.
    """
    
    def __init__(self, session: Session, account_email: str):
        """
        Initialize the deduplication service.
        
        Args:
            session: SQLAlchemy database session
            account_email: Email account being processed (for scoping)
        """
        self.session = session
        self.account_email = account_email
        self.stats = {
            'checked': 0,
            'duplicates_found': 0,
            'new_emails': 0,
            'logged': 0,
            'errors': 0
        }
        # Log which database file/name is in use
        try:
            bind = self.session.get_bind() if hasattr(self.session, "get_bind") else getattr(self.session, "bind", None)
            if bind is not None:
                url = getattr(bind, "url", None)
                backend = getattr(url, "get_backend_name", lambda: None)() if url is not None else None
                # For SQLite, url.database is the absolute file path. For others, show database name if available.
                if url is not None:
                    db_desc = url.database or str(url)
                    logger.info(f"🗄️ Using database: {db_desc} (backend={backend}) for account {self.account_email}")
                else:
                    logger.info(f"🗄️ Using database: <unknown url> for account {self.account_email}")
        except Exception as e:
            logger.debug(f"Could not determine database in GmailDeduplicationClient: {e}")
    
    def is_email_processed(self, message_id: str) -> bool:
        """
        Check if an email has already been processed.
        
        Args:
            message_id: The Message-ID header from the email
            
        Returns:
            True if email has been processed, False otherwise
        """
        if not message_id or not message_id.strip():
            logger.warning(f"Empty message_id provided for account {self.account_email}")
            self.stats['errors'] += 1
            return False
        
        self.stats['checked'] += 1
        
        try:
            exists = self.session.query(ProcessedEmailLog).filter_by(
                account_email=self.account_email,
                message_id=message_id.strip()
            ).first()
            
            is_processed = exists is not None
            
            if is_processed:
                self.stats['duplicates_found'] += 1
                logger.debug(f"📧 Email already processed: {message_id} for {self.account_email}")
            else:
                self.stats['new_emails'] += 1
                logger.debug(f"🆕 New email detected: {message_id} for {self.account_email}")
            
            return is_processed
            
        except Exception as e:
            logger.error(f"❌ Error checking if email processed: {e}")
            self.stats['errors'] += 1
            return False  # Assume not processed on error to avoid missing emails
    
    def mark_email_as_processed(self, message_id: str) -> ProcessedEmailLogModel:
        """
        Mark an email as processed to prevent future reprocessing.
        
        Args:
            message_id: The Message-ID header from the email
            
        Returns:
            ProcessedEmailLogModel representing the persisted record.
        
        Raises:
            ValueError: If message_id is empty or whitespace.
            IntegrityError: If a duplicate record violates the unique constraint.
            Exception: Any other database error encountered will be propagated.
        """
        if not message_id or not message_id.strip():
            logger.warning(f"Empty message_id provided for logging: account={self.account_email}")
            self.stats['errors'] += 1
            raise ValueError("message_id must be a non-empty string")
        
        try:
            record = ProcessedEmailLog(
                account_email=self.account_email,
                message_id=message_id.strip(),
                processed_at=datetime.utcnow()
            )
            
            self.session.add(record)
            self.session.commit()
            
            self.stats['logged'] += 1
            logger.info(f"✅ Marked email as processed: {self.account_email} -> {message_id}")
            # Return Pydantic model built from ORM record (requires from_attributes)
            return ProcessedEmailLogModel.model_validate(record)
            
        except IntegrityError as e:
            # Roll back and let caller decide how to handle duplicates
            self.session.rollback()
            logger.debug(f"ℹ️ Email already marked as processed (duplicate): {self.account_email} -> {message_id}")
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Failed to mark email as processed {self.account_email} -> {message_id}: {e}")
            self.stats['errors'] += 1
            raise
    
    def filter_new_emails(self, emails: List[Dict]) -> List[Dict]:
        """
        Filter a list of emails to only include those not yet processed.
        
        Args:
            emails: List of email dictionaries with Message-ID keys
            
        Returns:
            List of emails that haven't been processed yet
        """
        if not emails:
            return []
        
        new_emails = []
        
        for email in emails:
            message_id = email.get('Message-ID', '')
            
            if not message_id:
                logger.warning(f"Email without Message-ID found, processing as new: {email.get('Subject', 'Unknown')}")
                new_emails.append(email)
                continue
            
            if not self.is_email_processed(message_id):
                new_emails.append(email)
        
        logger.info(f"📊 Deduplication results for {self.account_email}:")
        logger.info(f"   Total emails checked: {len(emails)}")
        logger.info(f"   Already processed: {len(emails) - len(new_emails)}")
        logger.info(f"   New emails to process: {len(new_emails)}")
        
        return new_emails
    
    def bulk_mark_as_processed(self, message_ids: List[str]) -> Tuple[int, int]:
        """
        Mark multiple emails as processed in a single transaction.
        
        Args:
            message_ids: List of Message-ID values to mark as processed
            
        Returns:
            Tuple of (successful_count, error_count)
        """
        if not message_ids:
            return 0, 0
        
        successful = 0
        errors = 0
        
        try:
            records = []
            for message_id in message_ids:
                if message_id and message_id.strip():
                    records.append(ProcessedEmailLog(
                        account_email=self.account_email,
                        message_id=message_id.strip(),
                        processed_at=datetime.utcnow()
                    ))
            
            if records:
                self.session.add_all(records)
                self.session.commit()
                successful = len(records)
                self.stats['logged'] += successful
                
                logger.info(f"✅ Bulk marked {successful} emails as processed for {self.account_email}")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Bulk marking failed for {self.account_email}: {e}")
            
            # Fallback to individual processing
            for message_id in message_ids:
                try:
                    # Will raise on error (including duplicates); count successes/errors accordingly
                    self.mark_email_as_processed(message_id)
                    successful += 1
                except Exception:
                    errors += 1
        
        return successful, errors
    
    def get_processed_count(self, days_back: Optional[int] = None) -> int:
        """
        Get count of processed emails for this account.
        
        Args:
            days_back: If specified, only count emails from last N days
            
        Returns:
            Number of processed emails
        """
        try:
            query = self.session.query(ProcessedEmailLog).filter_by(
                account_email=self.account_email
            )
            
            if days_back:
                cutoff_date = datetime.utcnow() - timedelta(days=days_back)
                query = query.filter(ProcessedEmailLog.processed_at >= cutoff_date)
            
            count = query.count()
            logger.debug(f"📊 Processed email count for {self.account_email}: {count}")
            return count
            
        except Exception as e:
            logger.error(f"❌ Error getting processed count: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about deduplication operations in this session.
        
        Returns:
            Dictionary with operation counts
        """
        return self.stats.copy()
    
    def cleanup_old_records(self, days_to_keep: int = 90) -> int:
        """
        Clean up old processed email records to prevent database bloat.
        
        Args:
            days_to_keep: Number of days of records to keep
            
        Returns:
            Number of records deleted
        """
        if days_to_keep <= 0:
            logger.warning("Invalid days_to_keep value, skipping cleanup")
            return 0
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            deleted_count = self.session.query(ProcessedEmailLog).filter(
                ProcessedEmailLog.account_email == self.account_email,
                ProcessedEmailLog.processed_at < cutoff_date
            ).delete()
            
            self.session.commit()
            
            if deleted_count > 0:
                logger.info(f"🧹 Cleaned up {deleted_count} old processed email records for {self.account_email}")
            
            return deleted_count
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error during cleanup: {e}")
            return 0
    
    def reset_account_history(self) -> bool:
        """
        Reset all processed email history for this account.
        WARNING: This will cause all emails to be reprocessed!
        
        Returns:
            True if successful, False otherwise
        """
        try:
            deleted_count = self.session.query(ProcessedEmailLog).filter_by(
                account_email=self.account_email
            ).delete()
            
            self.session.commit()
            
            logger.warning(f"🗑️  RESET: Deleted {deleted_count} processed email records for {self.account_email}")
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Error resetting account history: {e}")
            return False
