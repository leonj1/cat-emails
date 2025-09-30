"""
Credentials Service Module
Handles storing and retrieving Gmail credentials from SQLite database
Supports both local SQLite and SQLiteCloud
"""
import sqlite3
import os
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class CredentialsService:
    """Service to manage Gmail credentials in SQLite database"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the credentials service

        Args:
            db_path: Path to the SQLite database file or SQLiteCloud URL.
                     If None, checks SQLITE_URL env var, then falls back to './credentials.db'
        """
        # Priority: explicit db_path > SQLITE_URL > CREDENTIALS_DB_PATH > default local path
        self.db_path = db_path or os.getenv('SQLITE_URL') or os.getenv('CREDENTIALS_DB_PATH', './credentials.db')
        self.is_cloud = self.db_path.startswith('sqlitecloud://')

        if self.is_cloud:
            # Import sqlitecloud only if needed
            try:
                import sqlitecloud
                self.sqlitecloud = sqlitecloud
            except ImportError:
                logger.error("sqlitecloud library not found. Install it with: pip install sqlitecloud")
                raise ImportError("sqlitecloud library required for SQLiteCloud connections")

        self._ensure_db_exists()

    def _get_connection(self):
        """Get database connection (local or cloud)"""
        if self.is_cloud:
            return self.sqlitecloud.connect(self.db_path)
        else:
            return sqlite3.connect(self.db_path)

    def _ensure_db_exists(self):
        """Ensure the database and table exist"""
        if not self.is_cloud:
            # Only create directory for local databases
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = self._get_connection()
        cursor = conn.cursor()

        # Create credentials table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gmail_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        logger.info(f"Credentials database initialized at: {self.db_path}")

    def store_credentials(self, email: str, password: str) -> bool:
        """
        Store or update Gmail credentials in the database

        Args:
            email: Gmail email address
            password: Gmail app-specific password

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Use INSERT OR REPLACE to handle both insert and update
            cursor.execute('''
                INSERT OR REPLACE INTO gmail_credentials (email, password, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (email, password))

            conn.commit()
            conn.close()
            logger.info(f"Successfully stored credentials for: {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            return False

    def get_credentials(self, email: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """
        Retrieve Gmail credentials from the database

        Args:
            email: Specific email address to retrieve. If None, returns the first/only credential.

        Returns:
            Tuple[str, str]: (email, password) if found, None otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if email:
                cursor.execute('''
                    SELECT email, password FROM gmail_credentials
                    WHERE email = ?
                    LIMIT 1
                ''', (email,))
            else:
                # Get the first credential (most recently updated)
                cursor.execute('''
                    SELECT email, password FROM gmail_credentials
                    ORDER BY updated_at DESC
                    LIMIT 1
                ''')

            result = cursor.fetchone()
            conn.close()

            if result:
                logger.info(f"Retrieved credentials for: {result[0]}")
                return result
            else:
                logger.warning(f"No credentials found{' for: ' + email if email else ''}")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            return None

    def delete_credentials(self, email: str) -> bool:
        """
        Delete Gmail credentials from the database

        Args:
            email: Gmail email address to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM gmail_credentials
                WHERE email = ?
            ''', (email,))

            conn.commit()
            deleted_count = cursor.rowcount
            conn.close()

            if deleted_count > 0:
                logger.info(f"Successfully deleted credentials for: {email}")
                return True
            else:
                logger.warning(f"No credentials found to delete for: {email}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}")
            return False

    def list_all_emails(self) -> list:
        """
        List all email addresses stored in the database

        Returns:
            list: List of email addresses
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT email FROM gmail_credentials
                ORDER BY updated_at DESC
            ''')

            results = cursor.fetchall()
            conn.close()

            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Failed to list emails: {e}")
            return []