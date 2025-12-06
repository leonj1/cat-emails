"""
Tests for API Response Enhancement - emails_categorized and emails_skipped fields.

Based on BDD scenarios from enhance_audit_records.feature:
- Scenario 8: Audit summary endpoint returns categorized count
- Scenario 9: Audit summary endpoint returns skipped count

These tests verify that the /api/processing/history and /api/status endpoints
include the new emails_categorized and emails_skipped fields in their responses.

Target endpoints:
- GET /api/processing/history - Returns recent processing runs
- GET /api/status - Returns unified status with recent runs
"""
import shutil
import tempfile
import unittest
from datetime import datetime
from typing import Protocol
from unittest.mock import Mock, MagicMock

from sqlalchemy.orm import Session

from models.database import ProcessingRun, Base, init_database, get_session


class DatabaseSessionProtocol(Protocol):
    """Protocol for database session dependency injection."""

    def query(self, model): ...
    def add(self, instance): ...
    def commit(self, ): ...
    def rollback(self): ...
    def close(self): ...


class TestApiResponseIncludesEmailsCategorizedField(unittest.TestCase):
    """
    Scenario: Audit summary endpoint returns categorized count

    Given audit records exist with categorized emails
    When the audit summary is requested
    Then the response should include the emails_categorized count
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_api_categorized.db"
        cls.engine = init_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Set up a fresh session for each test."""
        self.session = get_session(self.engine)

    def tearDown(self):
        """Clean up session after each test."""
        self.session.rollback()
        self.session.close()

    def test_api_response_includes_emails_categorized_field(self):
        """
        Test that get_processing_runs response includes emails_categorized field.

        Given a processing run exists with emails_categorized set to 150
        When I retrieve the processing runs via the API
        Then the response should include an "emails_categorized" field
        """
        # Arrange: Create a ProcessingRun with emails_categorized = 150
        run = ProcessingRun(
            email_address="categorized_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=200,
            emails_tagged=180,
            emails_deleted=10,
            emails_categorized=150,
            emails_skipped=20
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Act: Call get_processing_runs through actual DatabaseService
        from services.database_service import DatabaseService

        mock_repo = Mock()
        mock_repo.is_connected.return_value = True

        session_factory = MagicMock()
        session_context = MagicMock()
        session_context.__enter__ = MagicMock(return_value=self.session)
        session_context.__exit__ = MagicMock(return_value=False)
        session_factory.return_value = session_context

        db_service = object.__new__(DatabaseService)
        db_service.repository = mock_repo
        db_service.Session = session_factory
        db_service.engine = self.engine
        db_service.db_path = self.db_path

        result = db_service.get_processing_runs(limit=100)

        # Find our specific run
        our_run = next((r for r in result if r['run_id'] == f"run-{run_id}"), None)

        # Assert: Response includes emails_categorized field
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")
        self.assertIn(
            'emails_categorized',
            our_run,
            "API response should include 'emails_categorized' field"
        )

    def test_api_response_emails_categorized_value_is_correct(self):
        """
        Test that get_processing_runs returns correct emails_categorized value.

        Given a processing run exists with emails_categorized set to 150
        When I retrieve the processing runs via the API
        Then the "emails_categorized" value should be 150
        """
        # Arrange: Create a ProcessingRun with emails_categorized = 150
        expected_categorized = 150
        run = ProcessingRun(
            email_address="categorized_value_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=200,
            emails_tagged=150,
            emails_deleted=0,
            emails_categorized=expected_categorized,
            emails_skipped=50
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Act: Retrieve via DatabaseService.get_processing_runs()
        from services.database_service import DatabaseService

        mock_repo = Mock()
        mock_repo.is_connected.return_value = True

        session_factory = MagicMock()
        session_context = MagicMock()
        session_context.__enter__ = MagicMock(return_value=self.session)
        session_context.__exit__ = MagicMock(return_value=False)
        session_factory.return_value = session_context

        db_service = object.__new__(DatabaseService)
        db_service.repository = mock_repo
        db_service.Session = session_factory
        db_service.engine = self.engine
        db_service.db_path = self.db_path

        result = db_service.get_processing_runs(limit=100)

        # Find our specific run
        our_run = next((r for r in result if r['run_id'] == f"run-{run_id}"), None)

        # Assert: emails_categorized value matches database value
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")
        self.assertEqual(
            our_run.get('emails_categorized'),
            expected_categorized,
            f"emails_categorized should be {expected_categorized}, got {our_run.get('emails_categorized')}"
        )


class TestApiResponseIncludesEmailsSkippedField(unittest.TestCase):
    """
    Scenario: Audit summary endpoint returns skipped count

    Given audit records exist with skipped emails
    When the audit summary is requested
    Then the response should include the emails_skipped count
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_api_skipped.db"
        cls.engine = init_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Set up a fresh session for each test."""
        self.session = get_session(self.engine)

    def tearDown(self):
        """Clean up session after each test."""
        self.session.rollback()
        self.session.close()

    def test_api_response_includes_emails_skipped_field(self):
        """
        Test that get_processing_runs response includes emails_skipped field.

        Given a processing run exists with emails_skipped set to 75
        When I retrieve the processing runs via the API
        Then the response should include an "emails_skipped" field
        """
        # Arrange: Create a ProcessingRun with emails_skipped = 75
        run = ProcessingRun(
            email_address="skipped_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=200,
            emails_tagged=125,
            emails_deleted=0,
            emails_categorized=125,
            emails_skipped=75
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Act: Retrieve via DatabaseService.get_processing_runs()
        from services.database_service import DatabaseService

        mock_repo = Mock()
        mock_repo.is_connected.return_value = True

        session_factory = MagicMock()
        session_context = MagicMock()
        session_context.__enter__ = MagicMock(return_value=self.session)
        session_context.__exit__ = MagicMock(return_value=False)
        session_factory.return_value = session_context

        db_service = object.__new__(DatabaseService)
        db_service.repository = mock_repo
        db_service.Session = session_factory
        db_service.engine = self.engine
        db_service.db_path = self.db_path

        result = db_service.get_processing_runs(limit=100)

        # Find our specific run
        our_run = next((r for r in result if r['run_id'] == f"run-{run_id}"), None)

        # Assert: Response includes emails_skipped field
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")
        self.assertIn(
            'emails_skipped',
            our_run,
            "API response should include 'emails_skipped' field"
        )

    def test_api_response_emails_skipped_value_is_correct(self):
        """
        Test that get_processing_runs returns correct emails_skipped value.

        Given a processing run exists with emails_skipped set to 75
        When I retrieve the processing runs via the API
        Then the "emails_skipped" value should be 75
        """
        # Arrange: Create a ProcessingRun with emails_skipped = 75
        expected_skipped = 75
        run = ProcessingRun(
            email_address="skipped_value_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=150,
            emails_tagged=75,
            emails_deleted=0,
            emails_categorized=75,
            emails_skipped=expected_skipped
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Act: Retrieve via DatabaseService.get_processing_runs()
        from services.database_service import DatabaseService

        mock_repo = Mock()
        mock_repo.is_connected.return_value = True

        session_factory = MagicMock()
        session_context = MagicMock()
        session_context.__enter__ = MagicMock(return_value=self.session)
        session_context.__exit__ = MagicMock(return_value=False)
        session_factory.return_value = session_context

        db_service = object.__new__(DatabaseService)
        db_service.repository = mock_repo
        db_service.Session = session_factory
        db_service.engine = self.engine
        db_service.db_path = self.db_path

        result = db_service.get_processing_runs(limit=100)

        # Find our specific run
        our_run = next((r for r in result if r['run_id'] == f"run-{run_id}"), None)

        # Assert: emails_skipped value matches database value
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")
        self.assertEqual(
            our_run.get('emails_skipped'),
            expected_skipped,
            f"emails_skipped should be {expected_skipped}, got {our_run.get('emails_skipped')}"
        )


class TestApiResponseBothFieldsDefaultToZero(unittest.TestCase):
    """
    Test that null/missing emails_categorized and emails_skipped default to 0.

    Given a processing run exists without categorized/skipped values
    When I retrieve the processing runs via the API
    Then both fields should default to 0
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_api_defaults.db"
        cls.engine = init_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Set up a fresh session for each test."""
        self.session = get_session(self.engine)

    def tearDown(self):
        """Clean up session after each test."""
        self.session.rollback()
        self.session.close()

    def test_null_emails_categorized_defaults_to_zero(self):
        """Test that NULL emails_categorized returns 0 in API response."""
        # Arrange: Create a run without specifying categorized/skipped
        run = ProcessingRun(
            email_address="null_categorized_test@example.com",
            start_time=datetime.utcnow(),
            state="running"
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Act
        from services.database_service import DatabaseService

        mock_repo = Mock()
        mock_repo.is_connected.return_value = True

        session_factory = MagicMock()
        session_context = MagicMock()
        session_context.__enter__ = MagicMock(return_value=self.session)
        session_context.__exit__ = MagicMock(return_value=False)
        session_factory.return_value = session_context

        db_service = object.__new__(DatabaseService)
        db_service.repository = mock_repo
        db_service.Session = session_factory
        db_service.engine = self.engine
        db_service.db_path = self.db_path

        result = db_service.get_processing_runs(limit=100)
        our_run = next((r for r in result if r['run_id'] == f"run-{run_id}"), None)

        # Assert
        self.assertIsNotNone(our_run)
        self.assertIn('emails_categorized', our_run)
        self.assertEqual(
            our_run.get('emails_categorized'),
            0,
            f"emails_categorized should default to 0, got {our_run.get('emails_categorized')}"
        )

    def test_null_emails_skipped_defaults_to_zero(self):
        """Test that NULL emails_skipped returns 0 in API response."""
        # Arrange
        run = ProcessingRun(
            email_address="null_skipped_test@example.com",
            start_time=datetime.utcnow(),
            state="running"
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Act
        from services.database_service import DatabaseService

        mock_repo = Mock()
        mock_repo.is_connected.return_value = True

        session_factory = MagicMock()
        session_context = MagicMock()
        session_context.__enter__ = MagicMock(return_value=self.session)
        session_context.__exit__ = MagicMock(return_value=False)
        session_factory.return_value = session_context

        db_service = object.__new__(DatabaseService)
        db_service.repository = mock_repo
        db_service.Session = session_factory
        db_service.engine = self.engine
        db_service.db_path = self.db_path

        result = db_service.get_processing_runs(limit=100)
        our_run = next((r for r in result if r['run_id'] == f"run-{run_id}"), None)

        # Assert
        self.assertIsNotNone(our_run)
        self.assertIn('emails_skipped', our_run)
        self.assertEqual(
            our_run.get('emails_skipped'),
            0,
            f"emails_skipped should default to 0, got {our_run.get('emails_skipped')}"
        )


class TestApiResponseBothFieldsTogether(unittest.TestCase):
    """
    Test that both emails_categorized and emails_skipped appear together.

    Given a processing run with both categorized and skipped values
    When the audit summary is requested
    Then both fields should be present with correct values
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_api_both_fields.db"
        cls.engine = init_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Set up a fresh session for each test."""
        self.session = get_session(self.engine)

    def tearDown(self):
        """Clean up session after each test."""
        self.session.rollback()
        self.session.close()

    def test_both_fields_present_in_response(self):
        """Test that both new fields are present in API response."""
        # Arrange
        run = ProcessingRun(
            email_address="both_fields_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=300,
            emails_tagged=250,
            emails_deleted=15,
            emails_categorized=220,
            emails_skipped=65
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Act
        from services.database_service import DatabaseService

        mock_repo = Mock()
        mock_repo.is_connected.return_value = True

        session_factory = MagicMock()
        session_context = MagicMock()
        session_context.__enter__ = MagicMock(return_value=self.session)
        session_context.__exit__ = MagicMock(return_value=False)
        session_factory.return_value = session_context

        db_service = object.__new__(DatabaseService)
        db_service.repository = mock_repo
        db_service.Session = session_factory
        db_service.engine = self.engine
        db_service.db_path = self.db_path

        result = db_service.get_processing_runs(limit=100)
        our_run = next((r for r in result if r['run_id'] == f"run-{run_id}"), None)

        # Assert: Both fields present
        self.assertIsNotNone(our_run)
        self.assertIn('emails_categorized', our_run)
        self.assertIn('emails_skipped', our_run)

    def test_both_field_values_are_correct(self):
        """Test that both field values match database values."""
        # Arrange
        expected_categorized = 220
        expected_skipped = 65

        run = ProcessingRun(
            email_address="both_values_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=285,
            emails_tagged=220,
            emails_deleted=0,
            emails_categorized=expected_categorized,
            emails_skipped=expected_skipped
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Act
        from services.database_service import DatabaseService

        mock_repo = Mock()
        mock_repo.is_connected.return_value = True

        session_factory = MagicMock()
        session_context = MagicMock()
        session_context.__enter__ = MagicMock(return_value=self.session)
        session_context.__exit__ = MagicMock(return_value=False)
        session_factory.return_value = session_context

        db_service = object.__new__(DatabaseService)
        db_service.repository = mock_repo
        db_service.Session = session_factory
        db_service.engine = self.engine
        db_service.db_path = self.db_path

        result = db_service.get_processing_runs(limit=100)
        our_run = next((r for r in result if r['run_id'] == f"run-{run_id}"), None)

        # Assert: Values match
        self.assertIsNotNone(our_run)
        self.assertEqual(
            our_run.get('emails_categorized'),
            expected_categorized,
            f"emails_categorized should be {expected_categorized}"
        )
        self.assertEqual(
            our_run.get('emails_skipped'),
            expected_skipped,
            f"emails_skipped should be {expected_skipped}"
        )

    def test_complete_response_structure_with_new_fields(self):
        """Test complete API response structure includes all expected fields."""
        # Arrange
        start_time = datetime.utcnow()
        run = ProcessingRun(
            email_address="complete_structure_test@example.com",
            start_time=start_time,
            state="completed",
            emails_processed=400,
            emails_reviewed=350,
            emails_tagged=300,
            emails_deleted=20,
            emails_categorized=280,
            emails_skipped=70
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Act
        from services.database_service import DatabaseService

        mock_repo = Mock()
        mock_repo.is_connected.return_value = True

        session_factory = MagicMock()
        session_context = MagicMock()
        session_context.__enter__ = MagicMock(return_value=self.session)
        session_context.__exit__ = MagicMock(return_value=False)
        session_factory.return_value = session_context

        db_service = object.__new__(DatabaseService)
        db_service.repository = mock_repo
        db_service.Session = session_factory
        db_service.engine = self.engine
        db_service.db_path = self.db_path

        result = db_service.get_processing_runs(limit=100)
        our_run = next((r for r in result if r['run_id'] == f"run-{run_id}"), None)

        # Assert: Complete response structure
        self.assertIsNotNone(our_run)

        # Verify all required fields exist (including new ones)
        expected_fields = [
            'run_id',
            'started_at',
            'completed_at',
            'duration_seconds',
            'emails_processed',
            'emails_reviewed',
            'emails_tagged',
            'emails_deleted',
            'emails_categorized',  # NEW
            'emails_skipped',      # NEW
            'success',
            'error_message'
        ]

        for field in expected_fields:
            self.assertIn(
                field,
                our_run,
                f"API response should include '{field}' field"
            )

        # Verify specific values
        self.assertEqual(our_run['run_id'], f"run-{run_id}")
        self.assertEqual(our_run['emails_processed'], 400)
        self.assertEqual(our_run['emails_reviewed'], 350)
        self.assertEqual(our_run['emails_tagged'], 300)
        self.assertEqual(our_run['emails_deleted'], 20)
        self.assertEqual(our_run['emails_categorized'], 280)
        self.assertEqual(our_run['emails_skipped'], 70)
        self.assertTrue(our_run['success'])
        self.assertIsNone(our_run['error_message'])


if __name__ == '__main__':
    unittest.main()
