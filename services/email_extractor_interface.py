from abc import ABC, abstractmethod

class EmailExtractorInterface(ABC):
    """Interface for email address extraction services."""

    @abstractmethod
    def extract_sender_email(self, from_header: str) -> str:
        """Extract sender email from a 'From' header.

        Args:
            from_header: The 'From' header string from an email message.

        Returns:
            The extracted email address as a lowercase string, or empty string if none found.
        """
        pass