from __future__ import annotations
import imaplib
import logging
from utils.logger import get_logger

from services.gmail_connection_interface import GmailConnectionInterface

logger = get_logger(__name__)


class GmailConnectionService(GmailConnectionInterface):
    def __init__(self, email_address: str, password: str, imap_server: str = "imap.gmail.com"):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server

    def connect(self) -> imaplib.IMAP4:
        """Establish connection to Gmail IMAP server and return the authenticated connection."""
        try:
            # Prepare credentials (normalize email display; keep raw password, but we may try a sanitized retry)
            email = (self.email_address or "").replace("\u00a0", " ").strip()
            password_raw = self.password or ""

            if not email or not password_raw:
                raise Exception("Missing GMAIL_EMAIL or GMAIL_PASSWORD environment variables")

            logger.info(f"Attempting to connect to {self.imap_server} for {email}")
            conn = imaplib.IMAP4_SSL(self.imap_server)

            # Use SASL AUTHENTICATE PLAIN with explicit UTF-8 bytes to avoid ASCII encoding issues
            def _auth_plain(_challenge: bytes) -> bytes:
                return b"\0" + email.encode("utf-8") + b"\0" + password_raw.encode("utf-8")

            try:
                typ, data = conn.authenticate("PLAIN", _auth_plain)
                if typ != "OK":
                    raise imaplib.IMAP4.error(f"AUTHENTICATE PLAIN failed: {data!r}")
                logger.info("Successfully connected to Gmail IMAP server")
                return conn
            except imaplib.IMAP4.error as auth_err:
                err_msg = str(auth_err)

                # Retry with sanitized password (remove spaces and NBSP) if different
                password_sanitized = password_raw.replace("\u00a0", "").replace(" ", "").strip()
                if password_sanitized != password_raw:
                    try:
                        logger.warning("Initial authentication failed; retrying with sanitized App Password (whitespace removed)")
                        try:
                            conn.logout()
                        except Exception:
                            pass
                        conn = imaplib.IMAP4_SSL(self.imap_server)

                        def _auth_plain2(_challenge: bytes) -> bytes:
                            return b"\0" + email.encode("utf-8") + b"\0" + password_sanitized.encode("utf-8")

                        typ2, data2 = conn.authenticate("PLAIN", _auth_plain2)
                        if typ2 == "OK":
                            logger.info("Successfully connected to Gmail IMAP server after sanitizing password whitespace")
                            return conn
                        else:
                            err_msg = f"{err_msg}; sanitized retry failed: {data2!r}"
                    except imaplib.IMAP4.error as auth_err2:
                        err_msg = f"{err_msg}; sanitized retry error: {str(auth_err2)}"

                # Optional fallback to IMAP LOGIN
                try:
                    logger.warning("Falling back to IMAP LOGIN mechanism")
                    try:
                        conn.logout()
                    except Exception:
                        pass
                    conn = imaplib.IMAP4_SSL(self.imap_server)
                    typ3, data3 = conn.login(email, password_sanitized if 'password_sanitized' in locals() else password_raw)
                    if typ3 == "OK":
                        logger.info("Successfully connected to Gmail IMAP server using LOGIN")
                        return conn
                    else:
                        err_msg = f"{err_msg}; LOGIN failed: {data3!r}"
                except imaplib.IMAP4.error as login_err:
                    err_msg = f"{err_msg}; LOGIN error: {str(login_err)}"

                guidance = (
                    "Gmail authentication failed. Ensure GMAIL_PASSWORD is a Gmail App Password "
                    "(not your regular password), 16 characters, no spaces, and that 2-Step Verification is enabled. "
                    "If you pasted the password from Google, remove all spaces."
                )
                logger.error(f"Gmail authentication failed for account '{email}': {err_msg}. {guidance}")
                raise Exception(f"Failed to connect to Gmail: {err_msg}. {guidance}")
        except (imaplib.IMAP4.error, UnicodeEncodeError) as e:
            logger.error(f"Gmail connection error for account '{self.email_address}': {str(e)}")
            raise Exception(f"Failed to connect to Gmail: {str(e)}")
