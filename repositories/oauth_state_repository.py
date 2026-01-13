"""Repository for managing OAuth state tokens in the database."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy import Engine, text
import json
import logging

logger = logging.getLogger(__name__)


class OAuthStateRepository:
    """Manages OAuth state tokens in the database for CSRF protection."""

    STATE_TTL_MINUTES = 10  # State tokens expire after 10 minutes

    def __init__(self, engine: Engine):
        """
        Initialize repository with a shared SQLAlchemy engine.

        Args:
            engine: SQLAlchemy Engine instance to use for database connections
        """
        self.engine = engine

    def store_state(
        self,
        state_token: str,
        redirect_uri: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store an OAuth state token with associated metadata.

        Implements atomic upsert behavior using INSERT ... ON DUPLICATE KEY UPDATE
        to avoid race conditions in concurrent scenarios.

        Args:
            state_token: The CSRF state token
            redirect_uri: The redirect URI for the OAuth flow
            metadata: Optional additional metadata to store with the state

        Raises:
            Exception: If database storage fails
        """
        connection = self.engine.connect()
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.STATE_TTL_MINUTES)
            created_at = datetime.now(timezone.utc)
            metadata_json = json.dumps(metadata) if metadata else None

            # Use INSERT ... ON DUPLICATE KEY UPDATE for atomic upsert
            # Note: created_at is intentionally NOT updated on duplicate to preserve original timestamp
            upsert_query = text("""
                INSERT INTO oauth_state (state_token, redirect_uri, created_at, expires_at, metadata)
                VALUES (:state_token, :redirect_uri, :created_at, :expires_at, :metadata) AS new_row
                ON DUPLICATE KEY UPDATE
                    redirect_uri = new_row.redirect_uri,
                    expires_at = new_row.expires_at,
                    metadata = new_row.metadata
            """)

            connection.execute(
                upsert_query,
                {
                    'state_token': state_token,
                    'redirect_uri': redirect_uri,
                    'created_at': created_at,
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
        # Log state token lookup details
        token_len = len(state_token) if state_token else 0
        token_preview = state_token[:10] + '...' if state_token and len(state_token) > 10 else state_token
        logger.debug(
            f"Looking up OAuth state - "
            f"token length: {token_len}, "
            f"token empty: {not bool(state_token)}, "
            f"token repr: {token_preview!r}"
        )

        connection = self.engine.connect()
        try:
            query = text("""
                SELECT redirect_uri, created_at, expires_at, metadata
                FROM oauth_state
                WHERE state_token = :state_token
                AND expires_at > :now
            """)

            now_utc = datetime.now(timezone.utc)
            result = connection.execute(
                query,
                {
                    'state_token': state_token,
                    'now': now_utc
                }
            ).fetchone()

            if not result:
                # Enhanced logging to differentiate between not found vs expired
                if state_token:
                    # Check if token exists but is expired
                    check_query = text("""
                        SELECT expires_at FROM oauth_state WHERE state_token = :state_token
                    """)
                    expired_check = connection.execute(
                        check_query,
                        {'state_token': state_token}
                    ).fetchone()
                    if expired_check:
                        expires_at = expired_check._mapping['expires_at']
                        logger.warning(
                            f"OAuth state token exists but expired - "
                            f"expired_at: {expires_at}, current_utc: {now_utc}"
                        )
                    else:
                        logger.warning(
                            f"OAuth state token not found in database - "
                            f"token_prefix: {state_token[:10] + '...' if len(state_token) > 10 else state_token}"
                        )
                else:
                    logger.warning("OAuth state lookup with empty/None token")
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
            raise
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
        connection = self.engine.connect()
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
                return True
            else:
                return False

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
        connection = self.engine.connect()
        try:
            query = text("""
                DELETE FROM oauth_state
                WHERE expires_at <= :now
            """)

            result = connection.execute(query, {'now': datetime.now(timezone.utc)})
            connection.commit()

            count = result.rowcount
            if count > 0:
                logger.info(f"Cleaned up {count} expired OAuth state tokens")
                return count
            else:
                return 0

        except Exception:
            connection.rollback()
            logger.exception("Failed to cleanup expired OAuth states")
            return 0
        finally:
            connection.close()
