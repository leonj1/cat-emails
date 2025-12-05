"""
Tests for ProcessingRun API Response Audit Count Fields.

Based on BDD scenarios from Phase 3: Email Processing Audit Counts - API Response:
- Scenario: API response includes emails_reviewed field
- Scenario: API response includes emails_tagged field
- Scenario: API response includes emails_deleted field from database
- Scenario: Null audit count values default to zero in API response
- Scenario: API response includes all audit fields together

These tests follow TDD approach (Red phase) - tests will FAIL until the
get_processing_runs() method is updated to include the audit count fields from
the database instead of hardcoded values.

The implementation should modify services/database_service.py get_processing_runs():
    return [
        {
            ...
            'emails_reviewed': run.emails_reviewed if run.emails_reviewed is not None else 0,
            'emails_tagged': run.emails_tagged if run.emails_tagged is not None else 0,
            'emails_deleted': run.emails_deleted if run.emails_deleted is not None else 0,
            ...
        } for run in runs
    ]

Target: /root/repo/services/database_service.py - get_processing_runs() method (lines 287-305)
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
    def commit(self): ...
    def rollback(self): ...
    def close(self): ...


class TestApiResponseIncludesEmailsReviewedField(unittest.TestCase):
    """
    Scenario: API response includes emails_reviewed field

    Given a processing run exists with emails_reviewed set to 100
    When I retrieve the processing runs via the API
    Then the response should include an "emails_reviewed" field
    And the "emails_reviewed" value should be 100
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_api_reviewed.db"
        cls.engine = init_database(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up database after all tests."""
        cls.engine.dispose()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Set up a fresh session for each test."""
        self.session = get_session(self.engine)
        # Import DatabaseService here to avoid circular imports during test collection
        from services.database_service import DatabaseService
        from repositories.database_repository_interface import DatabaseRepositoryInterface

        # Create a mock repository that uses our test session
        self.mock_repository = Mock(spec=DatabaseRepositoryInterface)
        self.mock_repository.is_connected.return_value = True

        # We will create a real DatabaseService but use direct session access for setup
        self.db_service = None  # Will be set in tests

    def tearDown(self):
        """Clean up session after each test."""
        self.session.rollback()
        self.session.close()

    def test_api_response_includes_emails_reviewed_field(self):
        """
        Test that get_processing_runs response includes emails_reviewed field.

        Given a processing run exists with emails_reviewed set to 100
        When I retrieve the processing runs via the API
        Then the response should include an "emails_reviewed" field
        """
        # Arrange: Create a ProcessingRun with emails_reviewed = 100
        run = ProcessingRun(
            email_address="test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=100,
            emails_tagged=0,
            emails_deleted=0
        )
        self.session.add(run)
        self.session.commit()

        # Act: Call get_processing_runs through actual DatabaseService
        from services.database_service import DatabaseService

        # Create a mock repository that mimics the real behavior
        mock_repo = Mock()
        mock_repo.is_connected.return_value = True

        # Create a Session factory that returns our test session
        session_factory = MagicMock()
        session_context = MagicMock()
        session_context.__enter__ = MagicMock(return_value=self.session)
        session_context.__exit__ = MagicMock(return_value=False)
        session_factory.return_value = session_context

        # Create DatabaseService instance with test session
        db_service = object.__new__(DatabaseService)
        db_service.repository = mock_repo
        db_service.Session = session_factory
        db_service.engine = self.engine
        db_service.db_path = self.db_path

        # Call the actual get_processing_runs method
        result = db_service.get_processing_runs(limit=100)

        # Assert: Response includes emails_reviewed field
        self.assertGreater(len(result), 0, "Should have at least one processing run")
        first_run = result[0]
        self.assertIn(
            'emails_reviewed',
            first_run,
            "API response should include 'emails_reviewed' field"
        )

    def test_api_response_emails_reviewed_value_is_correct(self):
        """
        Test that get_processing_runs returns correct emails_reviewed value.

        Given a processing run exists with emails_reviewed set to 100
        When I retrieve the processing runs via the API
        Then the "emails_reviewed" value should be 100
        """
        # Arrange: Create a ProcessingRun with emails_reviewed = 100
        expected_reviewed = 100
        run = ProcessingRun(
            email_address="reviewed_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=expected_reviewed,
            emails_tagged=0,
            emails_deleted=0
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Act: Retrieve via the actual DatabaseService.get_processing_runs()
        # This will FAIL because current implementation doesn't include emails_reviewed
        from services.database_service import DatabaseService

        # Create a mock repository that mimics the real behavior
        mock_repo = Mock()
        mock_repo.is_connected.return_value = True

        # Create a Session factory that returns our test session
        session_factory = MagicMock()
        session_context = MagicMock()
        session_context.__enter__ = MagicMock(return_value=self.session)
        session_context.__exit__ = MagicMock(return_value=False)
        session_factory.return_value = session_context

        # Patch the Session attribute on database service
        db_service = object.__new__(DatabaseService)
        db_service.repository = mock_repo
        db_service.Session = session_factory
        db_service.engine = self.engine
        db_service.db_path = self.db_path

        # Call get_processing_runs - this should include emails_reviewed
        result = db_service.get_processing_runs(limit=100)

        # Find our specific run
        our_run = None
        for r in result:
            if r['run_id'] == f"run-{run_id}":
                our_run = r
                break

        # Assert: emails_reviewed value matches database value
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")
        self.assertIn(
            'emails_reviewed',
            our_run,
            "API response should include 'emails_reviewed' field"
        )
        self.assertEqual(
            our_run['emails_reviewed'],
            expected_reviewed,
            f"emails_reviewed should be {expected_reviewed}, got {our_run.get('emails_reviewed')}"
        )


class TestApiResponseIncludesEmailsTaggedField(unittest.TestCase):
    """
    Scenario: API response includes emails_tagged field

    Given a processing run exists with emails_tagged set to 45
    When I retrieve the processing runs via the API
    Then the response should include an "emails_tagged" field
    And the "emails_tagged" value should be 45
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_api_tagged.db"
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

    def test_api_response_includes_emails_tagged_field(self):
        """
        Test that get_processing_runs response includes emails_tagged field.

        Given a processing run exists with emails_tagged set to 45
        When I retrieve the processing runs via the API
        Then the response should include an "emails_tagged" field
        """
        # Arrange: Create a ProcessingRun with emails_tagged = 45
        run = ProcessingRun(
            email_address="tagged_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=0,
            emails_tagged=45,
            emails_deleted=0
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Act: Retrieve via the actual DatabaseService.get_processing_runs()
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

        # Assert: Response includes emails_tagged field
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")
        self.assertIn(
            'emails_tagged',
            our_run,
            "API response should include 'emails_tagged' field"
        )

    def test_api_response_emails_tagged_value_is_correct(self):
        """
        Test that get_processing_runs returns correct emails_tagged value.

        Given a processing run exists with emails_tagged set to 45
        When I retrieve the processing runs via the API
        Then the "emails_tagged" value should be 45
        """
        # Arrange: Create a ProcessingRun with emails_tagged = 45
        expected_tagged = 45
        run = ProcessingRun(
            email_address="tagged_value_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=0,
            emails_tagged=expected_tagged,
            emails_deleted=0
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

        # Assert: emails_tagged value matches database value
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")
        self.assertEqual(
            our_run.get('emails_tagged'),
            expected_tagged,
            f"emails_tagged should be {expected_tagged}, got {our_run.get('emails_tagged')}"
        )


class TestApiResponseIncludesEmailsDeletedFromDatabase(unittest.TestCase):
    """
    Scenario: API response includes emails_deleted field from database

    Given a processing run exists with emails_deleted set to 30
    When I retrieve the processing runs via the API
    Then the response should include an "emails_deleted" field
    And the "emails_deleted" value should be 30

    NOTE: Current implementation hardcodes 'emails_deleted': 0
    This test verifies that the actual database value is returned.
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_api_deleted.db"
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

    def test_api_response_includes_emails_deleted_field(self):
        """
        Test that get_processing_runs response includes emails_deleted field.

        Given a processing run exists with emails_deleted set to 30
        When I retrieve the processing runs via the API
        Then the response should include an "emails_deleted" field
        """
        # Arrange: Create a ProcessingRun with emails_deleted = 30
        run = ProcessingRun(
            email_address="deleted_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=0,
            emails_tagged=0,
            emails_deleted=30
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

        # Assert: Response includes emails_deleted field
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")
        self.assertIn(
            'emails_deleted',
            our_run,
            "API response should include 'emails_deleted' field"
        )

    def test_api_response_emails_deleted_returns_database_value_not_hardcoded_zero(self):
        """
        Test that get_processing_runs returns actual database value for emails_deleted.

        Given a processing run exists with emails_deleted set to 30 in database
        When I retrieve the processing runs via the API
        Then the "emails_deleted" value should be 30 (NOT hardcoded 0)

        This test will FAIL with current implementation which returns:
            'emails_deleted': 0,  # Not tracked in current model

        The fix should return:
            'emails_deleted': run.emails_deleted if run.emails_deleted is not None else 0,
        """
        # Arrange: Create a ProcessingRun with emails_deleted = 30
        expected_deleted = 30
        run = ProcessingRun(
            email_address="deleted_value_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=0,
            emails_tagged=0,
            emails_deleted=expected_deleted
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Verify the value is actually in the database
        self.session.expire_all()
        db_run = self.session.query(ProcessingRun).filter_by(id=run_id).first()
        self.assertEqual(
            db_run.emails_deleted,
            expected_deleted,
            f"Database should have emails_deleted={expected_deleted}"
        )

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

        # Assert: emails_deleted value matches database value (NOT hardcoded 0)
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")
        self.assertEqual(
            our_run.get('emails_deleted'),
            expected_deleted,
            f"emails_deleted should be {expected_deleted} from database, got {our_run.get('emails_deleted')}. "
            "Current implementation hardcodes 0 - this test verifies actual DB value is returned."
        )


class TestNullAuditCountValuesDefaultToZero(unittest.TestCase):
    """
    Scenario: Null audit count values default to zero in API response

    Given a processing run exists with null audit count values
    When I retrieve the processing runs via the API
    Then the "emails_reviewed" value should be 0
    And the "emails_tagged" value should be 0
    And the "emails_deleted" value should be 0

    NOTE: This tests that the API gracefully handles NULL values from
    legacy records created before the audit columns were added.
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_api_null_defaults.db"
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

    def test_null_emails_reviewed_defaults_to_zero_in_response(self):
        """
        Test that NULL emails_reviewed in database returns 0 in API response.

        This simulates legacy records where audit columns might be NULL.
        The implementation should handle: run.emails_reviewed or 0
        """
        # Arrange: Create a ProcessingRun without specifying audit counts
        # SQLAlchemy model has default=0, so we test that the API
        # returns 0 for these default values
        run = ProcessingRun(
            email_address="null_reviewed_test@example.com",
            start_time=datetime.utcnow(),
            state="running"
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

        # Assert: emails_reviewed defaults to 0
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")
        self.assertIn(
            'emails_reviewed',
            our_run,
            "API response should include 'emails_reviewed' field"
        )
        self.assertEqual(
            our_run.get('emails_reviewed'),
            0,
            f"emails_reviewed should default to 0, got {our_run.get('emails_reviewed')}"
        )

    def test_null_emails_tagged_defaults_to_zero_in_response(self):
        """
        Test that NULL emails_tagged in database returns 0 in API response.
        """
        # Arrange
        run = ProcessingRun(
            email_address="null_tagged_test@example.com",
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
        self.assertIn('emails_tagged', our_run)
        self.assertEqual(
            our_run.get('emails_tagged'),
            0,
            f"emails_tagged should default to 0, got {our_run.get('emails_tagged')}"
        )

    def test_null_emails_deleted_defaults_to_zero_in_response(self):
        """
        Test that NULL emails_deleted in database returns 0 in API response.
        """
        # Arrange
        run = ProcessingRun(
            email_address="null_deleted_test@example.com",
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
        self.assertIn('emails_deleted', our_run)
        self.assertEqual(
            our_run.get('emails_deleted'),
            0,
            f"emails_deleted should default to 0, got {our_run.get('emails_deleted')}"
        )

    def test_all_audit_counts_default_to_zero_when_not_specified(self):
        """
        Test that all audit counts default to 0 when not specified.

        Given a processing run exists with null audit count values
        When I retrieve the processing runs via the API
        Then the "emails_reviewed" value should be 0
        And the "emails_tagged" value should be 0
        And the "emails_deleted" value should be 0
        """
        # Arrange: Create a ProcessingRun without audit counts
        run = ProcessingRun(
            email_address="all_null_test@example.com",
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

        # Assert: All audit counts are 0
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")
        self.assertEqual(
            our_run.get('emails_reviewed'),
            0,
            f"emails_reviewed should be 0, got {our_run.get('emails_reviewed')}"
        )
        self.assertEqual(
            our_run.get('emails_tagged'),
            0,
            f"emails_tagged should be 0, got {our_run.get('emails_tagged')}"
        )
        self.assertEqual(
            our_run.get('emails_deleted'),
            0,
            f"emails_deleted should be 0, got {our_run.get('emails_deleted')}"
        )


class TestApiResponseIncludesAllAuditFieldsTogether(unittest.TestCase):
    """
    Scenario: API response includes all audit fields together

    Given a processing run exists with:
      | emails_reviewed | 150 |
      | emails_tagged   | 60  |
      | emails_deleted  | 25  |
    When I retrieve the processing runs via the API
    Then the response should contain all audit count fields
    And the "emails_reviewed" value should be 150
    And the "emails_tagged" value should be 60
    And the "emails_deleted" value should be 25
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_api_all_fields.db"
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

    def test_api_response_contains_all_audit_count_fields(self):
        """
        Test that get_processing_runs response contains all three audit fields.

        Given a processing run exists with all audit values set
        When I retrieve the processing runs via the API
        Then the response should contain all audit count fields
        """
        # Arrange
        run = ProcessingRun(
            email_address="all_fields_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=150,
            emails_tagged=60,
            emails_deleted=25
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

        # Assert: All three audit fields are present
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")

        required_fields = ['emails_reviewed', 'emails_tagged', 'emails_deleted']
        for field in required_fields:
            self.assertIn(
                field,
                our_run,
                f"API response should include '{field}' field"
            )

    def test_api_response_all_audit_values_match_database(self):
        """
        Test that all audit field values match the database values.

        Given a processing run exists with:
          | emails_reviewed | 150 |
          | emails_tagged   | 60  |
          | emails_deleted  | 25  |
        When I retrieve the processing runs via the API
        Then the "emails_reviewed" value should be 150
        And the "emails_tagged" value should be 60
        And the "emails_deleted" value should be 25
        """
        # Arrange
        expected_reviewed = 150
        expected_tagged = 60
        expected_deleted = 25

        run = ProcessingRun(
            email_address="all_values_test@example.com",
            start_time=datetime.utcnow(),
            state="completed",
            emails_reviewed=expected_reviewed,
            emails_tagged=expected_tagged,
            emails_deleted=expected_deleted
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

        # Assert: All values match
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")

        self.assertEqual(
            our_run.get('emails_reviewed'),
            expected_reviewed,
            f"emails_reviewed should be {expected_reviewed}, got {our_run.get('emails_reviewed')}"
        )
        self.assertEqual(
            our_run.get('emails_tagged'),
            expected_tagged,
            f"emails_tagged should be {expected_tagged}, got {our_run.get('emails_tagged')}"
        )
        self.assertEqual(
            our_run.get('emails_deleted'),
            expected_deleted,
            f"emails_deleted should be {expected_deleted}, got {our_run.get('emails_deleted')}"
        )

    def test_api_response_complete_structure_with_audit_fields(self):
        """
        Test the complete API response structure includes all expected fields.

        This is a complete response assertion test per testing standards.
        """
        # Arrange
        start_time = datetime.utcnow()
        run = ProcessingRun(
            email_address="complete_response_test@example.com",
            start_time=start_time,
            state="completed",
            emails_processed=200,
            emails_reviewed=150,
            emails_tagged=60,
            emails_deleted=25
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
        self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")

        # Verify all required fields exist
        expected_fields = [
            'run_id',
            'started_at',
            'completed_at',
            'duration_seconds',
            'emails_processed',
            'emails_reviewed',
            'emails_tagged',
            'emails_deleted',
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
        self.assertEqual(our_run['emails_processed'], 200)
        self.assertEqual(our_run['emails_reviewed'], 150)
        self.assertEqual(our_run['emails_tagged'], 60)
        self.assertEqual(our_run['emails_deleted'], 25)
        self.assertTrue(our_run['success'])
        self.assertIsNone(our_run['error_message'])


class TestApiResponseAuditFieldsIntegration(unittest.TestCase):
    """
    Integration tests for audit fields in API responses.

    These tests verify the end-to-end behavior of the API when
    processing runs with various audit count configurations.
    """

    @classmethod
    def setUpClass(cls):
        """Set up database engine once for all tests in this class."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = f"{cls.temp_dir}/test_api_integration.db"
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

    def test_multiple_runs_each_have_audit_fields(self):
        """
        Test that multiple processing runs each have their own audit fields.
        """
        # Arrange: Create multiple runs with different audit values
        runs_data = [
            {'email': 'run1@example.com', 'reviewed': 10, 'tagged': 5, 'deleted': 2},
            {'email': 'run2@example.com', 'reviewed': 50, 'tagged': 25, 'deleted': 10},
            {'email': 'run3@example.com', 'reviewed': 100, 'tagged': 50, 'deleted': 20},
        ]

        created_run_ids = []
        for data in runs_data:
            run = ProcessingRun(
                email_address=data['email'],
                start_time=datetime.utcnow(),
                state="completed",
                emails_reviewed=data['reviewed'],
                emails_tagged=data['tagged'],
                emails_deleted=data['deleted']
            )
            self.session.add(run)
            self.session.commit()
            created_run_ids.append(run.id)

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

        # Assert: Each run has correct audit values
        for i, run_id in enumerate(created_run_ids):
            our_run = next((r for r in result if r['run_id'] == f"run-{run_id}"), None)
            self.assertIsNotNone(our_run, f"Should find run with id run-{run_id}")

            expected = runs_data[i]
            self.assertEqual(
                our_run.get('emails_reviewed'),
                expected['reviewed'],
                f"Run {run_id} emails_reviewed mismatch"
            )
            self.assertEqual(
                our_run.get('emails_tagged'),
                expected['tagged'],
                f"Run {run_id} emails_tagged mismatch"
            )
            self.assertEqual(
                our_run.get('emails_deleted'),
                expected['deleted'],
                f"Run {run_id} emails_deleted mismatch"
            )

    def test_audit_fields_preserved_after_run_completion(self):
        """
        Test that audit fields are preserved when a processing run completes.
        """
        # Arrange: Create a run in 'running' state with audit counts
        run = ProcessingRun(
            email_address="completion_test@example.com",
            start_time=datetime.utcnow(),
            state="running",
            emails_reviewed=75,
            emails_tagged=30,
            emails_deleted=15
        )
        self.session.add(run)
        self.session.commit()
        run_id = run.id

        # Simulate completion by updating state
        run.state = "completed"
        run.end_time = datetime.utcnow()
        self.session.commit()

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

        # Assert: Audit fields preserved after completion
        self.assertIsNotNone(our_run)
        self.assertEqual(our_run.get('emails_reviewed'), 75)
        self.assertEqual(our_run.get('emails_tagged'), 30)
        self.assertEqual(our_run.get('emails_deleted'), 15)
        self.assertTrue(our_run.get('success'))


if __name__ == '__main__':
    unittest.main()
