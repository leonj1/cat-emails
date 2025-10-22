from email.utils import parseaddr
from typing import Optional

from utils.logger import get_logger
from services.interfaces.email_address_extractor_interface import EmailAddressExtractorInterface

logger = get_logger(__name__)

class ExtractSenderEmailService(EmailAddressExtractorInterface):
    """Service for extracting sender email addresses from email headers.

    This service provides email address extraction with optional fallback capabilities.
    It first attempts to use a provided extractor (if available), then falls back to
    the standard email.utils.parseaddr implementation.
    """

    def __init__(self, fallback_extractor: Optional[EmailAddressExtractorInterface] = None) -> None:
        """Initialize the service.

        Args:
            fallback_extractor: Optional alternative extractor to try first before falling
                              back to the default parseaddr implementation.
        """
        self.fallback_extractor = fallback_extractor

    def extract_sender_email(self, from_header: str) -> str:
        """Extract sender email using fallback extractor if available, otherwise use parseaddr.

        The service first tries the fallback extractor if provided. If that fails or returns
        an empty result, it falls back to using email.utils.parseaddr.

        Args:
            from_header: The 'From' header string from an email message

        Returns:
            str: The extracted email address in lowercase, or empty string if not found
        """
        if not from_header:
            return ""

        # Try fallback extractor first if available
        if self.fallback_extractor is not None:
            try:
                result = self.fallback_extractor.extract_sender_email(from_header)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Fallback extractor failed: {e}")

        # Default implementation using parseaddr
        _, sender_email = parseaddr(from_header)
        return sender_email.lower() if sender_email else ""