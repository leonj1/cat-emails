from abc import ABC, abstractmethod

class EmailAddressExtractorInterface(ABC):
    """Interface for extracting email addresses from message headers."""

    @abstractmethod
    def extract_sender_email(self, from_header: str) -> str:
        """Extract sender email address from a 'From' header.

        Args:
            from_header (str): The 'From' header string from an email message

        Returns:
            str: The extracted email address in lowercase, or empty string if not found
        """
        pass