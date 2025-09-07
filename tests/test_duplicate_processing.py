import os
import tempfile
from services.database_service import DatabaseService


def test_processed_email_log_per_account_scoping():
    # Use a temporary database file for isolation
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "summaries.db")
        db = DatabaseService(db_path=db_path)

        account_a = "account_a@example.com"
        account_b = "account_b@example.com"
        message_id = "<unique-message-id@example.com>"

        # Initially not processed
        assert db.is_message_processed(account_a, message_id) is False
        assert db.is_message_processed(account_b, message_id) is False

        # Log for account A
        db.log_processed_email(account_a, message_id)

        # Now processed for account A, but not for account B
        assert db.is_message_processed(account_a, message_id) is True
        assert db.is_message_processed(account_b, message_id) is False

        # Logging same pair again should not raise due to unique constraint (idempotent)
        db.log_processed_email(account_a, message_id)
        assert db.is_message_processed(account_a, message_id) is True

        # Log for account B should be independent
        db.log_processed_email(account_b, message_id)
        assert db.is_message_processed(account_b, message_id) is True


def test_missing_inputs_are_safe_noop():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "summaries.db")
        db = DatabaseService(db_path=db_path)

        # Missing inputs should simply return False / no exception
        assert db.is_message_processed("", "") is False
        assert db.is_message_processed("acc@example.com", "") is False
        assert db.is_message_processed("", "<mid>") is False

        # Logging with missing inputs should not raise
        db.log_processed_email("", "")
        db.log_processed_email("acc@example.com", "")
        db.log_processed_email("", "<mid>")
