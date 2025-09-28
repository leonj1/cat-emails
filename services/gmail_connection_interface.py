from __future__ import annotations
from abc import ABC, abstractmethod
import imaplib


class GmailConnectionInterface(ABC):
    """Interface for establishing a connection to a Gmail IMAP server."""

    @abstractmethod
    def connect(self) -> imaplib.IMAP4:
        """
        Establish and return a connection to the Gmail IMAP server.

        Returns:
            imaplib.IMAP4: An authenticated IMAP4/IMAP4_SSL connection object.
        """
        raise NotImplementedError
