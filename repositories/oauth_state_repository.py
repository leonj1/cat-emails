"""Repository for managing OAuth state tokens in the database."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import json
import logging

logger = logging.getLogger(__name__)

# Module-level engine singleton for connection pooling
_engine = None


def _get_engine():
    """Get or create the SQLAlchemy engine singleton."""
    global _engine
    if _engine is None:
        db_url = os.getenv(
            'DATABASE_URL',
            f"mysql+pymysql://{os.getenv('MYSQL_USER', 'cat_emails')}:"
            f"{os.getenv('MYSQL_PASSWORD', 'password')}@"
            f"{os.getenv('MYSQL_HOST', 'localhost')}:"
            f"{os.getenv('MYSQL_PORT', '3306')}/"
            f"{os.getenv('MYSQL_DATABASE', 'cat_emails')}"
        )
        _engine = create_engine(db_url, pool_pre_ping=True)
    return _engine


def get_db_connection():
    """Get a database connection for OAuth state repository."""
    return _get_engine().connect()


class OAuthStateRepository:
    """Manages OAuth state tokens in the database for CSRF protection."""

    STATE_TTL_MINUTES = 10  # State tokens expire after 10 minutes

    def store_state(
        self,
        state_token: str,
        redirect_uri: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store an OAuth state token with associated metadata.

        Args:
            state_token: The CSRF state token
            redirect_uri: The redirect URI for the OAuth flow
            metadata: Optional additional metadata to store with the state

        Raises:
            Exception: If database storage fails
        """
        connection = get_db_connection()
        try:
            expires_at = datetime.utcnow() + timedelta(minutes=self.STATE_TTL_MINUTES)
            metadata_json = json.dumps(metadata) if metadata else None

            query = text("""
                INSERT INTO oauth_state (state_token, redirect_uri, created_at, expires_at, metadata)
                VALUES (:state_token, :redirect_uri, :created_at, :expires_at, :metadata)
            """)

            connection.execute(
                query,
                {
                    'state_token': state_token,
                    'redirect_uri': redirect_uri,
                    'created_at': datetime.utcnow(),
                    'expires_at': expires_at,
                    'metadata': metadata_json
                }
            )
            connection.commit()

            logger.debug(f"Stored OAuth state token (expires in {self.STATE_TTL_MINUTES} minutes)")

        except Exception:
            connection.rollback()
            logger.exception("Failed to store OAuth state")
            raise
        finally:
            connection.close()

    def get_state(self, state_token: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and validate an OAuth state token.

        Args:
            state_token: The state token to retrieve

        Returns:
            Dict with state data if valid and not expired, None otherwise
        """
        connection = get_db_connection()
        try:
            query = text("""
                SELECT redirect_uri, created_at, expires_at, metadata
                FROM oauth_state
                WHERE state_token = :state_token
                AND expires_at > :now
            """)

            result = connection.execute(
                query,
                {
                    'state_token': state_token,
                    'now': datetime.utcnow()
                }
            ).fetchone()

            if not result:
                logger.warning("OAuth state not found or expired")
                return None

            # Use named access via _mapping for clarity
            row = result._mapping
            metadata = json.loads(row['metadata']) if row['metadata'] else {}

            return {
                'redirect_uri': row['redirect_uri'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'expires_at': row['expires_at'].isoformat() if row['expires_at'] else None,
                **metadata
            }

        except Exception:
            logger.exception("Failed to retrieve OAuth state")
            return None
        finally:
            connection.close()

    def delete_state(self, state_token: str) -> bool:
        """
        Delete an OAuth state token after it has been used.

        Args:
            state_token: The state token to delete

        Returns:
            True if deleted, False otherwise
        """
        connection = get_db_connection()
        try:
            query = text("""
                DELETE FROM oauth_state
                WHERE state_token = :state_token
            """)

            result = connection.execute(query, {'state_token': state_token})
            connection.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.debug("Deleted used OAuth state token")

            return deleted

        except Exception:
            connection.rollback()
            logger.exception("Failed to delete OAuth state")
            return False
        finally:
            connection.close()

    def cleanup_expired_states(self) -> int:
        """
        Clean up expired state tokens from the database.

        Returns:
            Number of expired tokens deleted
        """
        connection = get_db_connection()
        try:
            query = text("""
                DELETE FROM oauth_state
                WHERE expires_at <= :now
            """)

            result = connection.execute(query, {'now': datetime.utcnow()})
            connection.commit()

            count = result.rowcount
            if count > 0:
                logger.info(f"Cleaned up {count} expired OAuth state tokens")

            return count

        except Exception:
            connection.rollback()
            logger.exception("Failed to cleanup expired OAuth states")
            return 0
        finally:
            connection.close()
