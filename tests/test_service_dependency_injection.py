"""
Tests for service dependency injection - ensuring services receive ILogsCollector via constructor.

These tests verify that EmailProcessorService, EmailSummaryService, and AccountEmailProcessorService
receive ILogsCollector via constructor injection and do NOT create their own LogsCollectorService instances.

The implementation should:
- Create ILogsCollector interface (services/logs_collector_interface.py)
- Remove fallback creation patterns in services
- Services should just use what's passed to the constructor

Current Pattern (to be removed):
    self.logs_collector = logs_collector if logs_collector is not None else LogsCollectorService()

Target Pattern:
    self.logs_collector = logs_collector  # Just use what's passed
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from collections import Counter
from typing import Any, Dict, Optional

from faker import Faker


class MockLogsCollector:
    """
    Mock implementation of ILogsCollector for testing.

    This mock simulates the ILogsCollector interface that will be created.
    It tracks all calls to send_log for verification.
    """

    def __init__(self, send_logs: bool):
        """
        Initialize the mock logs collector.

        Args:
            send_logs: Whether log sending is enabled
        """
        self._send_logs = send_logs
        self.send_log_calls = []

    @property
    def is_send_enabled(self) -> bool:
        """Check if log sending is enabled."""
        return self._send_logs

    def send_log(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> bool:
        """
        Record a log send call.

        Args:
            level: Log level
            message: Log message
            context: Additional context
            source: Log source

        Returns:
            bool: True if log would be sent
        """
        self.send_log_calls.append({
            'level': level,
            'message': message,
            'context': context,
            'source': source
        })
        return self._send_logs

    def send_processing_run_log(
        self,
        run_id: str,
        status: str,
        metrics: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        source: Optional[str] = None
    ) -> bool:
        """Record a processing run log call."""
        return self.send_log("INFO", f"Processing run {status}", {"run_id": run_id}, source)

    def send_email_processing_log(
        self,
        message_id: str,
        category: str,
        action: str,
        sender: str,
        processing_time: Optional[float] = None,
        source: Optional[str] = None
    ) -> bool:
        """Record an email processing log call."""
        return self.send_log("INFO", f"Email processed: {category}", {"message_id": message_id}, source)


class TestEmailProcessorServiceDependencyInjection(unittest.TestCase):
    """
    Test cases for EmailProcessorService receiving ILogsCollector via constructor.

    Gherkin Scenario:
      Given a LogsCollectorService configured with send_logs=True
      When EmailProcessorService is instantiated with the logs collector
      Then the service should use the provided logs collector
      And the service should NOT create its own LogsCollectorService
    """

    def test_should_use_provided_logs_collector_when_instantiated(self):
        """
        Test that EmailProcessorService uses the provided logs collector.

        The service should store the provided logs collector and use it
        for all logging operations, not create its own.
        """
        # Arrange
        mock_logs_collector = MockLogsCollector(send_logs=True)

        # Create minimal mocks for other dependencies
        mock_fetcher = MagicMock()
        mock_fetcher.stats = {'categories': Counter(), 'deleted': 0, 'kept': 0}
        mock_fetcher.summary_service = MagicMock()
        mock_fetcher.summary_service.db_service = None
        mock_categorizer = MagicMock()
        mock_extractor = MagicMock()

        # Import the service
        from services.email_processor_service import EmailProcessorService

        # Act
        service = EmailProcessorService(
            fetcher=mock_fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=mock_categorizer,
            email_extractor=mock_extractor,
            logs_collector=mock_logs_collector
        )

        # Assert - service should use the exact same logs collector instance
        self.assertIs(
            service.logs_collector,
            mock_logs_collector,
            "EmailProcessorService should use the provided logs collector instance"
        )

    def test_should_not_create_own_logs_collector_service_instance(self):
        """
        Test that EmailProcessorService does NOT create its own LogsCollectorService.

        When provided with a logs collector, the service should not instantiate
        LogsCollectorService internally. We verify this by patching the constructor.
        """
        # Arrange
        mock_logs_collector = MockLogsCollector(send_logs=True)

        mock_fetcher = MagicMock()
        mock_fetcher.stats = {'categories': Counter(), 'deleted': 0, 'kept': 0}
        mock_fetcher.summary_service = MagicMock()
        mock_fetcher.summary_service.db_service = None
        mock_categorizer = MagicMock()
        mock_extractor = MagicMock()

        from services.email_processor_service import EmailProcessorService

        # Act - Patch LogsCollectorService to track if it gets instantiated
        with patch('services.email_processor_service.LogsCollectorService') as mock_lcs_class:
            service = EmailProcessorService(
                fetcher=mock_fetcher,
                email_address="test@example.com",
                model="test-model",
                email_categorizer=mock_categorizer,
                email_extractor=mock_extractor,
                logs_collector=mock_logs_collector
            )

            # Assert - LogsCollectorService should NOT have been instantiated
            mock_lcs_class.assert_not_called()
            self.assertIs(
                service.logs_collector,
                mock_logs_collector,
                "EmailProcessorService should use the provided collector, not create a new one"
            )

    def test_should_use_logs_collector_with_send_logs_true_configuration(self):
        """
        Test that EmailProcessorService uses logs collector configured with send_logs=True.

        When the provided logs collector has send_logs=True, the service
        should be able to use it for logging operations.
        """
        # Arrange
        mock_logs_collector = MockLogsCollector(send_logs=True)

        mock_fetcher = MagicMock()
        mock_fetcher.stats = {'categories': Counter(), 'deleted': 0, 'kept': 0}
        mock_fetcher.summary_service = MagicMock()
        mock_fetcher.summary_service.db_service = None
        mock_categorizer = MagicMock()
        mock_extractor = MagicMock()

        from services.email_processor_service import EmailProcessorService

        # Act
        service = EmailProcessorService(
            fetcher=mock_fetcher,
            email_address="test@example.com",
            model="test-model",
            email_categorizer=mock_categorizer,
            email_extractor=mock_extractor,
            logs_collector=mock_logs_collector
        )

        # Assert - service's logs collector should have is_send_enabled = True
        self.assertTrue(
            service.logs_collector.is_send_enabled,
            "Logs collector should have is_send_enabled=True"
        )


class TestEmailSummaryServiceDependencyInjection(unittest.TestCase):
    """
    Test cases for EmailSummaryService receiving ILogsCollector via constructor.

    Gherkin Scenario:
      Given a LogsCollectorService configured with send_logs=False
      When EmailSummaryService is instantiated with the logs collector
      Then the service should use the provided logs collector
      And the service should NOT create its own LogsCollectorService
    """

    def test_should_use_provided_logs_collector_when_instantiated(self):
        """
        Test that EmailSummaryService uses the provided logs collector.

        The service should store the provided logs collector and use it
        for all logging operations, not create its own.
        """
        # Arrange
        mock_logs_collector = MockLogsCollector(send_logs=False)

        # Import the service
        from services.email_summary_service import EmailSummaryService

        # Act - use database=False to avoid DB dependencies in test
        service = EmailSummaryService(
            data_dir="./test_summaries",
            use_database=False,
            gmail_email="test@example.com",
            logs_collector=mock_logs_collector
        )

        # Assert - service should use the exact same logs collector instance
        self.assertIs(
            service.logs_collector,
            mock_logs_collector,
            "EmailSummaryService should use the provided logs collector instance"
        )

    def test_should_not_create_own_logs_collector_service_instance(self):
        """
        Test that EmailSummaryService does NOT create its own LogsCollectorService.

        When provided with a logs collector, the service should not instantiate
        LogsCollectorService internally.
        """
        # Arrange
        mock_logs_collector = MockLogsCollector(send_logs=False)

        from services.email_summary_service import EmailSummaryService

        # Act - Patch LogsCollectorService to track if it gets instantiated
        with patch('services.email_summary_service.LogsCollectorService') as mock_lcs_class:
            service = EmailSummaryService(
                data_dir="./test_summaries",
                use_database=False,
                gmail_email="test@example.com",
                logs_collector=mock_logs_collector
            )

            # Assert - LogsCollectorService should NOT have been instantiated
            mock_lcs_class.assert_not_called()
            self.assertIs(
                service.logs_collector,
                mock_logs_collector,
                "EmailSummaryService should use the provided collector, not create a new one"
            )

    def test_should_use_logs_collector_with_send_logs_false_configuration(self):
        """
        Test that EmailSummaryService uses logs collector configured with send_logs=False.

        When the provided logs collector has send_logs=False, the service
        should be able to use it for logging operations (which will be disabled).
        """
        # Arrange
        mock_logs_collector = MockLogsCollector(send_logs=False)

        from services.email_summary_service import EmailSummaryService

        # Act
        service = EmailSummaryService(
            data_dir="./test_summaries",
            use_database=False,
            gmail_email="test@example.com",
            logs_collector=mock_logs_collector
        )

        # Assert - service's logs collector should have is_send_enabled = False
        self.assertFalse(
            service.logs_collector.is_send_enabled,
            "Logs collector should have is_send_enabled=False"
        )


class TestAccountEmailProcessorServiceDependencyInjection(unittest.TestCase):
    """
    Test cases for AccountEmailProcessorService receiving ILogsCollector via constructor.

    Gherkin Scenario:
      Given a LogsCollectorService configured with send_logs=True
      When AccountEmailProcessorService is instantiated with the logs collector
      Then the service should use the provided logs collector
      And the service should NOT create its own LogsCollectorService
    """

    def setUp(self):
        """Set up common test fixtures."""
        self.fake = Faker()

        # Create minimal mock dependencies
        self.mock_processing_status_manager = MagicMock()
        self.mock_settings_service = MagicMock()
        self.mock_email_categorizer = MagicMock()
        self.mock_account_category_client = MagicMock()
        self.mock_deduplication_factory = MagicMock()

    def test_should_use_provided_logs_collector_when_instantiated(self):
        """
        Test that AccountEmailProcessorService uses the provided logs collector.

        The service should store the provided logs collector and use it
        for all logging operations, not create its own.
        """
        # Arrange
        mock_logs_collector = MockLogsCollector(send_logs=True)

        # Import the service
        from services.account_email_processor_service import AccountEmailProcessorService

        # Act
        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.mock_email_categorizer,
            api_token=self.fake.uuid4(),
            llm_model="test-model",
            account_category_client=self.mock_account_category_client,
            deduplication_factory=self.mock_deduplication_factory,
            logs_collector=mock_logs_collector
        )

        # Assert - service should use the exact same logs collector instance
        self.assertIs(
            service.logs_collector,
            mock_logs_collector,
            "AccountEmailProcessorService should use the provided logs collector instance"
        )

    def test_should_not_create_own_logs_collector_service_instance(self):
        """
        Test that AccountEmailProcessorService does NOT create its own LogsCollectorService.

        When provided with a logs collector, the service should not instantiate
        LogsCollectorService internally.
        """
        # Arrange
        mock_logs_collector = MockLogsCollector(send_logs=True)

        from services.account_email_processor_service import AccountEmailProcessorService

        # Act - Patch LogsCollectorService to track if it gets instantiated
        with patch('services.account_email_processor_service.LogsCollectorService') as mock_lcs_class:
            service = AccountEmailProcessorService(
                processing_status_manager=self.mock_processing_status_manager,
                settings_service=self.mock_settings_service,
                email_categorizer=self.mock_email_categorizer,
                api_token=self.fake.uuid4(),
                llm_model="test-model",
                account_category_client=self.mock_account_category_client,
                deduplication_factory=self.mock_deduplication_factory,
                logs_collector=mock_logs_collector
            )

            # Assert - LogsCollectorService should NOT have been instantiated
            mock_lcs_class.assert_not_called()
            self.assertIs(
                service.logs_collector,
                mock_logs_collector,
                "AccountEmailProcessorService should use the provided collector, not create a new one"
            )

    def test_should_use_logs_collector_with_send_logs_true_configuration(self):
        """
        Test that AccountEmailProcessorService uses logs collector configured with send_logs=True.

        When the provided logs collector has send_logs=True, the service
        should be able to use it for logging operations.
        """
        # Arrange
        mock_logs_collector = MockLogsCollector(send_logs=True)

        from services.account_email_processor_service import AccountEmailProcessorService

        # Act
        service = AccountEmailProcessorService(
            processing_status_manager=self.mock_processing_status_manager,
            settings_service=self.mock_settings_service,
            email_categorizer=self.mock_email_categorizer,
            api_token=self.fake.uuid4(),
            llm_model="test-model",
            account_category_client=self.mock_account_category_client,
            deduplication_factory=self.mock_deduplication_factory,
            logs_collector=mock_logs_collector
        )

        # Assert - service's logs collector should have is_send_enabled = True
        self.assertTrue(
            service.logs_collector.is_send_enabled,
            "Logs collector should have is_send_enabled=True"
        )


class TestServicesShouldNotCreateFallbackLogsCollector(unittest.TestCase):
    """
    Test cases to verify services do NOT create fallback LogsCollectorService when none provided.

    This verifies the removal of the pattern:
        self.logs_collector = logs_collector if logs_collector is not None else LogsCollectorService()

    Target behavior: Services should just use what's passed (even if None).
    """

    def test_email_processor_service_should_not_create_logs_collector_when_none_provided(self):
        """
        Test that EmailProcessorService does NOT create LogsCollectorService when logs_collector=None.

        The service should NOT have the fallback pattern that creates LogsCollectorService().
        This test verifies the removal of the internal creation pattern.
        """
        # Arrange
        mock_fetcher = MagicMock()
        mock_fetcher.stats = {'categories': Counter(), 'deleted': 0, 'kept': 0}
        mock_fetcher.summary_service = MagicMock()
        mock_fetcher.summary_service.db_service = None
        mock_categorizer = MagicMock()
        mock_extractor = MagicMock()

        from services.email_processor_service import EmailProcessorService

        # Act - Patch LogsCollectorService and pass logs_collector=None
        with patch('services.email_processor_service.LogsCollectorService') as mock_lcs_class:
            service = EmailProcessorService(
                fetcher=mock_fetcher,
                email_address="test@example.com",
                model="test-model",
                email_categorizer=mock_categorizer,
                email_extractor=mock_extractor,
                logs_collector=None  # Explicitly pass None
            )

            # Assert - LogsCollectorService should NOT have been instantiated
            mock_lcs_class.assert_not_called()
            # The logs_collector should be None, not a newly created LogsCollectorService
            self.assertIsNone(
                service.logs_collector,
                "EmailProcessorService should have logs_collector=None when None is passed, "
                "NOT create a fallback LogsCollectorService instance"
            )

    def test_email_summary_service_should_not_create_logs_collector_when_none_provided(self):
        """
        Test that EmailSummaryService does NOT create LogsCollectorService when logs_collector=None.

        The service should NOT have the fallback pattern that creates LogsCollectorService().
        """
        from services.email_summary_service import EmailSummaryService

        # Act - Patch LogsCollectorService and pass logs_collector=None
        with patch('services.email_summary_service.LogsCollectorService') as mock_lcs_class:
            service = EmailSummaryService(
                data_dir="./test_summaries",
                use_database=False,
                gmail_email="test@example.com",
                logs_collector=None  # Explicitly pass None
            )

            # Assert - LogsCollectorService should NOT have been instantiated
            mock_lcs_class.assert_not_called()
            # The logs_collector should be None, not a newly created LogsCollectorService
            self.assertIsNone(
                service.logs_collector,
                "EmailSummaryService should have logs_collector=None when None is passed, "
                "NOT create a fallback LogsCollectorService instance"
            )

    def test_account_email_processor_service_should_not_create_logs_collector_when_none_provided(self):
        """
        Test that AccountEmailProcessorService does NOT create LogsCollectorService when logs_collector=None.

        The service should NOT have the fallback pattern that creates LogsCollectorService().
        """
        fake = Faker()
        mock_processing_status_manager = MagicMock()
        mock_settings_service = MagicMock()
        mock_email_categorizer = MagicMock()
        mock_account_category_client = MagicMock()
        mock_deduplication_factory = MagicMock()

        from services.account_email_processor_service import AccountEmailProcessorService

        # Act - Patch LogsCollectorService and pass logs_collector=None
        with patch('services.account_email_processor_service.LogsCollectorService') as mock_lcs_class:
            service = AccountEmailProcessorService(
                processing_status_manager=mock_processing_status_manager,
                settings_service=mock_settings_service,
                email_categorizer=mock_email_categorizer,
                api_token=fake.uuid4(),
                llm_model="test-model",
                account_category_client=mock_account_category_client,
                deduplication_factory=mock_deduplication_factory,
                logs_collector=None  # Explicitly pass None
            )

            # Assert - LogsCollectorService should NOT have been instantiated
            mock_lcs_class.assert_not_called()
            # The logs_collector should be None, not a newly created LogsCollectorService
            self.assertIsNone(
                service.logs_collector,
                "AccountEmailProcessorService should have logs_collector=None when None is passed, "
                "NOT create a fallback LogsCollectorService instance"
            )


class TestLogsCollectorInterfaceExists(unittest.TestCase):
    """
    Test cases to verify ILogsCollector interface exists and is properly defined.

    These tests verify the interface has the required methods and properties.
    """

    def test_ilogs_collector_interface_should_exist(self):
        """
        Test that ILogsCollector interface exists in the expected location.

        The implementation should create services/logs_collector_interface.py
        with the ILogsCollector interface.
        """
        # Act & Assert - import should succeed if interface exists
        try:
            from services.logs_collector_interface import ILogsCollector
        except ImportError as e:
            self.fail(
                f"ILogsCollector interface should exist at services/logs_collector_interface.py. "
                f"Import error: {e}"
            )

    def test_ilogs_collector_should_have_send_log_method(self):
        """
        Test that ILogsCollector interface has send_log method.

        The interface should define an abstract send_log method.
        """
        # Arrange & Act
        from services.logs_collector_interface import ILogsCollector
        import inspect

        # Assert - send_log should be defined as a method
        self.assertTrue(
            hasattr(ILogsCollector, 'send_log'),
            "ILogsCollector should have send_log method"
        )
        self.assertTrue(
            callable(getattr(ILogsCollector, 'send_log', None)) or
            isinstance(inspect.getattr_static(ILogsCollector, 'send_log'), property),
            "send_log should be callable"
        )

    def test_ilogs_collector_should_have_is_send_enabled_property(self):
        """
        Test that ILogsCollector interface has is_send_enabled property.

        The interface should define an abstract is_send_enabled property.
        """
        # Arrange & Act
        from services.logs_collector_interface import ILogsCollector
        import inspect

        # Assert - is_send_enabled should be defined as a property
        self.assertTrue(
            hasattr(ILogsCollector, 'is_send_enabled'),
            "ILogsCollector should have is_send_enabled property"
        )


class TestLogsCollectorServiceImplementsInterface(unittest.TestCase):
    """
    Test cases to verify LogsCollectorService implements ILogsCollector interface.

    LogsCollectorService should properly implement the ILogsCollector interface.
    """

    def test_logs_collector_service_should_implement_ilogs_collector(self):
        """
        Test that LogsCollectorService is an instance of ILogsCollector.

        The implementation should make LogsCollectorService inherit from
        or implement ILogsCollector.
        """
        # Arrange
        from services.logs_collector_service import LogsCollectorService
        from services.logs_collector_interface import ILogsCollector

        # Act
        service = LogsCollectorService(send_logs=True)

        # Assert
        self.assertIsInstance(
            service,
            ILogsCollector,
            "LogsCollectorService should be an instance of ILogsCollector"
        )


class TestServicesUseILogsCollectorTypeHint(unittest.TestCase):
    """
    Test cases to verify services use ILogsCollector type hint instead of LogsCollectorService.

    Services should accept ILogsCollector in their constructor type hints.
    """

    def test_email_processor_service_accepts_ilogs_collector(self):
        """
        Test that EmailProcessorService constructor accepts ILogsCollector type.

        The constructor should use ILogsCollector type hint for logs_collector parameter.
        """
        # Arrange
        from services.email_processor_service import EmailProcessorService
        from services.logs_collector_interface import ILogsCollector
        import inspect

        # Act - get constructor signature
        sig = inspect.signature(EmailProcessorService.__init__)
        logs_collector_param = sig.parameters.get('logs_collector')

        # Assert - parameter should exist and accept ILogsCollector
        self.assertIsNotNone(
            logs_collector_param,
            "EmailProcessorService.__init__ should have logs_collector parameter"
        )

        # Check annotation if present
        if logs_collector_param.annotation != inspect.Parameter.empty:
            annotation_str = str(logs_collector_param.annotation)
            self.assertIn(
                'ILogsCollector',
                annotation_str,
                f"logs_collector should have ILogsCollector type hint, got: {annotation_str}"
            )

    def test_email_summary_service_accepts_ilogs_collector(self):
        """
        Test that EmailSummaryService constructor accepts ILogsCollector type.

        The constructor should use ILogsCollector type hint for logs_collector parameter.
        """
        # Arrange
        from services.email_summary_service import EmailSummaryService
        from services.logs_collector_interface import ILogsCollector
        import inspect

        # Act - get constructor signature
        sig = inspect.signature(EmailSummaryService.__init__)
        logs_collector_param = sig.parameters.get('logs_collector')

        # Assert - parameter should exist and accept ILogsCollector
        self.assertIsNotNone(
            logs_collector_param,
            "EmailSummaryService.__init__ should have logs_collector parameter"
        )

        # Check annotation if present
        if logs_collector_param.annotation != inspect.Parameter.empty:
            annotation_str = str(logs_collector_param.annotation)
            self.assertIn(
                'ILogsCollector',
                annotation_str,
                f"logs_collector should have ILogsCollector type hint, got: {annotation_str}"
            )

    def test_account_email_processor_service_accepts_ilogs_collector(self):
        """
        Test that AccountEmailProcessorService constructor accepts ILogsCollector type.

        The constructor should use ILogsCollector type hint for logs_collector parameter.
        """
        # Arrange
        from services.account_email_processor_service import AccountEmailProcessorService
        from services.logs_collector_interface import ILogsCollector
        import inspect

        # Act - get constructor signature
        sig = inspect.signature(AccountEmailProcessorService.__init__)
        logs_collector_param = sig.parameters.get('logs_collector')

        # Assert - parameter should exist and accept ILogsCollector
        self.assertIsNotNone(
            logs_collector_param,
            "AccountEmailProcessorService.__init__ should have logs_collector parameter"
        )

        # Check annotation if present
        if logs_collector_param.annotation != inspect.Parameter.empty:
            annotation_str = str(logs_collector_param.annotation)
            self.assertIn(
                'ILogsCollector',
                annotation_str,
                f"logs_collector should have ILogsCollector type hint, got: {annotation_str}"
            )


if __name__ == '__main__':
    unittest.main()
