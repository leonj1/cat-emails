"""Integration tests for OAuthStateRepository."""

import pytest
import os
import sys
import time
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from repositories.oauth_state_repository import OAuthStateRepository, get_db_connection
from sqlalchemy import text


def check_database_available():
    """Check if database is available for integration tests."""
    from sqlalchemy.exc import SQLAlchemyError
    try:
        connection = get_db_connection()
        connection.close()
    except (SQLAlchemyError, OSError):
        return False
    else:
        return True


# Skip all tests in this module if database is not available
pytestmark = pytest.mark.skipif(
    not check_database_available(),
    reason="Database not available for integration tests"
)


@pytest.fixture
def state_repo():
    """Create OAuthStateRepository instance for testing."""
    return OAuthStateRepository()


@pytest.fixture(autouse=True)
def cleanup_oauth_state():
    """Clean up oauth_state table before and after each test."""
    connection = get_db_connection()
    try:
        connection.execute(text("DELETE FROM oauth_state"))
        connection.commit()
    finally:
        connection.close()

    yield

    connection = get_db_connection()
    try:
        connection.execute(text("DELETE FROM oauth_state"))
        connection.commit()
    finally:
        connection.close()


class TestOAuthStateRepository:
    """Test suite for OAuthStateRepository."""

    def test_store_and_retrieve_state(self, state_repo):
        """Test storing and retrieving a state token."""
        state_token = "test_state_12345"
        redirect_uri = "https://example.com/oauth/callback"

        # Store state
        state_repo.store_state(state_token, redirect_uri)

        # Retrieve state
        state_data = state_repo.get_state(state_token)

        assert state_data is not None
        assert state_data['redirect_uri'] == redirect_uri
        assert 'created_at' in state_data
        assert 'expires_at' in state_data

    def test_store_state_with_metadata(self, state_repo):
        """Test storing state with additional metadata."""
        state_token = "test_state_metadata"
        redirect_uri = "https://example.com/oauth/callback"
        metadata = {
            'user_id': '123',
            'session_id': 'abc-xyz'
        }

        # Store state with metadata
        state_repo.store_state(state_token, redirect_uri, metadata)

        # Retrieve and verify metadata
        state_data = state_repo.get_state(state_token)

        assert state_data is not None
        assert state_data['redirect_uri'] == redirect_uri
        assert state_data.get('user_id') == '123'
        assert state_data.get('session_id') == 'abc-xyz'

    def test_get_nonexistent_state(self, state_repo):
        """Test retrieving a state token that doesn't exist."""
        state_data = state_repo.get_state("nonexistent_state")
        assert state_data is None

    def test_get_expired_state(self, state_repo):
        """Test that expired state tokens are not retrieved."""
        state_token = "test_expired_state"
        redirect_uri = "https://example.com/oauth/callback"

        # Store state with very short TTL for testing
        # We'll manually update the database to set an expired time
        state_repo.store_state(state_token, redirect_uri)

        # Manually expire the state
        connection = get_db_connection()
        try:
            query = text("""
                UPDATE oauth_state
                SET expires_at = :past_time
                WHERE state_token = :state_token
            """)
            connection.execute(
                query,
                {
                    'state_token': state_token,
                    'past_time': datetime.utcnow() - timedelta(minutes=1)
                }
            )
            connection.commit()
        finally:
            connection.close()

        # Try to retrieve expired state
        state_data = state_repo.get_state(state_token)
        assert state_data is None

    def test_delete_state(self, state_repo):
        """Test deleting a state token."""
        state_token = "test_delete_state"
        redirect_uri = "https://example.com/oauth/callback"

        # Store state
        state_repo.store_state(state_token, redirect_uri)

        # Verify it exists
        state_data = state_repo.get_state(state_token)
        assert state_data is not None

        # Delete state
        deleted = state_repo.delete_state(state_token)
        assert deleted is True

        # Verify it's gone
        state_data = state_repo.get_state(state_token)
        assert state_data is None

    def test_delete_nonexistent_state(self, state_repo):
        """Test deleting a state token that doesn't exist."""
        deleted = state_repo.delete_state("nonexistent_state")
        assert deleted is False

    def test_cleanup_expired_states(self, state_repo):
        """Test cleanup of expired state tokens."""
        # Create multiple states
        state_repo.store_state("state1", "https://example.com/1")
        state_repo.store_state("state2", "https://example.com/2")
        state_repo.store_state("state3", "https://example.com/3")

        # Manually expire state1 and state2
        connection = get_db_connection()
        try:
            query = text("""
                UPDATE oauth_state
                SET expires_at = :past_time
                WHERE state_token IN ('state1', 'state2')
            """)
            connection.execute(
                query,
                {'past_time': datetime.utcnow() - timedelta(minutes=1)}
            )
            connection.commit()
        finally:
            connection.close()

        # Run cleanup
        count = state_repo.cleanup_expired_states()
        assert count == 2

        # Verify state3 still exists
        state_data = state_repo.get_state("state3")
        assert state_data is not None

        # Verify state1 and state2 are gone
        assert state_repo.get_state("state1") is None
        assert state_repo.get_state("state2") is None

    def test_state_isolation(self, state_repo):
        """Test that multiple states don't interfere with each other."""
        states = [
            ("state_a", "https://example.com/a"),
            ("state_b", "https://example.com/b"),
            ("state_c", "https://example.com/c"),
        ]

        # Store all states
        for state_token, redirect_uri in states:
            state_repo.store_state(state_token, redirect_uri)

        # Verify each state independently
        for state_token, expected_uri in states:
            state_data = state_repo.get_state(state_token)
            assert state_data is not None
            assert state_data['redirect_uri'] == expected_uri

        # Delete one state
        state_repo.delete_state("state_b")

        # Verify state_b is gone but others remain
        assert state_repo.get_state("state_a") is not None
        assert state_repo.get_state("state_b") is None
        assert state_repo.get_state("state_c") is not None

    def test_concurrent_state_storage(self, state_repo):
        """Test that concurrent state storage doesn't cause conflicts."""
        # This simulates multiple authorization requests happening concurrently
        states = [f"concurrent_state_{i}" for i in range(10)]

        # Store all states
        for state_token in states:
            state_repo.store_state(state_token, f"https://example.com/{state_token}")

        # Verify all states exist
        for state_token in states:
            state_data = state_repo.get_state(state_token)
            assert state_data is not None
            assert state_token in state_data['redirect_uri']

    def test_state_ttl_default(self, state_repo):
        """Test that state tokens have the correct default TTL."""
        state_token = "test_ttl_state"
        redirect_uri = "https://example.com/oauth/callback"

        # Store state
        state_repo.store_state(state_token, redirect_uri)

        # Retrieve and check expiry
        state_data = state_repo.get_state(state_token)
        assert state_data is not None

        # Parse expires_at
        expires_at = datetime.fromisoformat(state_data['expires_at'].replace('Z', '+00:00'))
        created_at = datetime.fromisoformat(state_data['created_at'].replace('Z', '+00:00'))

        # Calculate actual TTL (should be approximately STATE_TTL_MINUTES)
        ttl_seconds = (expires_at - created_at).total_seconds()
        expected_ttl_seconds = state_repo.STATE_TTL_MINUTES * 60

        # Allow 5 second tolerance for test execution time
        assert abs(ttl_seconds - expected_ttl_seconds) < 5
