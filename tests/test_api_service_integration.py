"""
Tests for API Service Integration with SEND_LOGS Feature Flag.

These tests verify that api_service.py:
1. Reads SEND_LOGS environment variable at startup
2. Creates FeatureFlags with the correct send_logs value
3. Creates LogsCollectorService with the correct send_logs value
4. Propagates the logs_collector instance through the service chain
5. Defaults send_logs to False when env var is missing

Following TDD Red phase - these tests will fail until implementation exists.

Gherkin Scenarios Covered:
  - API service reads SEND_LOGS at startup
  - API service propagates send_logs through service chain
  - API service defaults send_logs to False when env var missing

IMPORTANT: These tests mock database dependencies to avoid requiring
a MySQL connection during test execution.
"""
import unittest
import os
import sys
from unittest.mock import patch, MagicMock, PropertyMock


def _create_mock_repository():
    """Create a mock repository for testing."""
    mock_repo = MagicMock()
    mock_repo.is_connected.return_value = True
    mock_repo.get_connection_status.return_value = {
        "connected": True,
        "status": "Connected",
        "error": None,
        "details": {}
    }
    mock_repo._get_session.return_value = MagicMock()
    return mock_repo


def _create_mock_settings_service():
    """Create a mock settings service for testing."""
    mock_service = MagicMock()
    mock_service.repository = _create_mock_repository()
    mock_service.get_lookback_hours.return_value = 2
    return mock_service


class TestApiServiceReadsSendLogsEnvVar(unittest.TestCase):
    """
    Test cases for API service reading SEND_LOGS environment variable at startup.

    Scenario: API service reads SEND_LOGS at startup
      Given the SEND_LOGS environment variable is set to "true"
      When the FastAPI application starts
      Then the FeatureFlags should be created with send_logs=True
      And the LogsCollectorService should be created with send_logs=True
    """

    @patch('services.settings_service.MySQLRepository')
    def test_should_read_send_logs_true_from_environment(self, mock_mysql_repo_class):
        """
        Test that api_service reads SEND_LOGS=true and creates module-level variable.

        When SEND_LOGS is set to "true", the api_service module should:
        - Have a module-level variable SEND_LOGS_ENABLED set to True
        - This variable should be readable after module import

        The implementation should add near the top of api_service.py:
            SEND_LOGS_ENABLED = os.getenv("SEND_LOGS", "false").lower() in ("true", "1", "yes")
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "true"}

        # Act - mock the environment and import the module
        with patch.dict(os.environ, test_env, clear=False):
            # Remove api_service from sys.modules to force reimport
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Assert
            self.assertTrue(
                hasattr(api_service, 'SEND_LOGS_ENABLED'),
                "api_service should have SEND_LOGS_ENABLED module-level variable"
            )
            self.assertTrue(
                api_service.SEND_LOGS_ENABLED,
                "SEND_LOGS_ENABLED should be True when SEND_LOGS='true'"
            )

    @patch('services.settings_service.MySQLRepository')
    def test_should_read_send_logs_with_numeric_one_value(self, mock_mysql_repo_class):
        """
        Test that api_service reads SEND_LOGS=1 correctly.

        When SEND_LOGS is set to "1", the module-level variable should be True.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "1"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Assert
            self.assertTrue(
                api_service.SEND_LOGS_ENABLED,
                "SEND_LOGS_ENABLED should be True when SEND_LOGS='1'"
            )

    @patch('services.settings_service.MySQLRepository')
    def test_should_read_send_logs_with_yes_value(self, mock_mysql_repo_class):
        """
        Test that api_service reads SEND_LOGS=yes correctly.

        When SEND_LOGS is set to "yes", the module-level variable should be True.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "yes"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Assert
            self.assertTrue(
                api_service.SEND_LOGS_ENABLED,
                "SEND_LOGS_ENABLED should be True when SEND_LOGS='yes'"
            )


class TestApiServiceCreatesLogsCollectorService(unittest.TestCase):
    """
    Test cases for API service creating LogsCollectorService at startup.

    Scenario: API service creates LogsCollectorService with send_logs=True
      Given the SEND_LOGS environment variable is set to "true"
      When the FastAPI application initializes
      Then a global LogsCollectorService should be created with send_logs=True
    """

    @patch('services.settings_service.MySQLRepository')
    def test_should_create_logs_collector_service_with_send_logs_true(self, mock_mysql_repo_class):
        """
        Test that api_service creates a global LogsCollectorService instance.

        The implementation should add after reading SEND_LOGS:
            logs_collector_service = LogsCollectorService(send_logs=SEND_LOGS_ENABLED)
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "true"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Assert - module should have logs_collector_service global
            self.assertTrue(
                hasattr(api_service, 'logs_collector_service'),
                "api_service should have logs_collector_service global variable"
            )
            self.assertIsNotNone(
                api_service.logs_collector_service,
                "logs_collector_service should not be None"
            )

    @patch('services.settings_service.MySQLRepository')
    def test_logs_collector_service_should_have_send_logs_true_when_env_var_true(self, mock_mysql_repo_class):
        """
        Test that LogsCollectorService is created with is_send_enabled=True.

        When SEND_LOGS="true", the logs_collector_service.is_send_enabled should be True.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "true"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Assert
            self.assertTrue(
                api_service.logs_collector_service.is_send_enabled,
                "logs_collector_service.is_send_enabled should be True when SEND_LOGS='true'"
            )

    @patch('services.settings_service.MySQLRepository')
    def test_logs_collector_service_should_have_send_logs_false_when_env_var_false(self, mock_mysql_repo_class):
        """
        Test that LogsCollectorService is created with is_send_enabled=False.

        When SEND_LOGS="false", the logs_collector_service.is_send_enabled should be False.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "false"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Assert
            self.assertFalse(
                api_service.logs_collector_service.is_send_enabled,
                "logs_collector_service.is_send_enabled should be False when SEND_LOGS='false'"
            )


class TestApiServicePropagatesLogsCollectorThroughServiceChain(unittest.TestCase):
    """
    Test cases for API service propagating logs_collector through the service chain.

    Scenario: API service propagates send_logs through service chain
      Given the SEND_LOGS environment variable is set to "true"
      When the FastAPI application starts
      And dependent services are initialized
      Then all services should share the same LogsCollectorService instance
      And that instance should have send_logs=True
    """

    @patch('services.settings_service.MySQLRepository')
    def test_should_inject_logs_collector_into_account_email_processor_service(self, mock_mysql_repo_class):
        """
        Test that _initialize_account_email_processor() injects logs_collector_service.

        The implementation should modify _initialize_account_email_processor():
            account_email_processor_service = AccountEmailProcessorService(
                ...
                logs_collector=logs_collector_service  # <-- ADD THIS
            )
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "true"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Reset the global to force re-initialization
            api_service.account_email_processor_service = None

            # Call the initializer to create the account_email_processor_service
            service = api_service._initialize_account_email_processor()

            # Assert
            self.assertIsNotNone(
                service.logs_collector,
                "AccountEmailProcessorService should have logs_collector injected"
            )

    @patch('services.settings_service.MySQLRepository')
    def test_account_email_processor_should_use_same_logs_collector_instance(self, mock_mysql_repo_class):
        """
        Test that AccountEmailProcessorService receives the same logs_collector instance.

        The service chain should share the same LogsCollectorService instance,
        not create new instances. This ensures consistent configuration.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "true"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Reset the global to force re-initialization
            api_service.account_email_processor_service = None

            # Call the initializer
            service = api_service._initialize_account_email_processor()

            # Assert - the injected logs_collector should be the same instance
            self.assertIs(
                service.logs_collector,
                api_service.logs_collector_service,
                "AccountEmailProcessorService should use the same logs_collector_service instance"
            )

    @patch('services.settings_service.MySQLRepository')
    def test_injected_logs_collector_should_have_correct_send_logs_value(self, mock_mysql_repo_class):
        """
        Test that the injected LogsCollectorService has the correct send_logs value.

        When SEND_LOGS="true", the logs_collector in AccountEmailProcessorService
        should have is_send_enabled=True.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "true"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Reset the global to force re-initialization
            api_service.account_email_processor_service = None

            service = api_service._initialize_account_email_processor()

            # Assert
            self.assertTrue(
                service.logs_collector.is_send_enabled,
                "Injected logs_collector should have is_send_enabled=True when SEND_LOGS='true'"
            )


class TestApiServiceDefaultsSendLogsToFalse(unittest.TestCase):
    """
    Test cases for API service defaulting send_logs to False when env var missing.

    Scenario: API service defaults send_logs to False when env var missing
      Given the SEND_LOGS environment variable is not set
      When the FastAPI application starts
      Then the LogsCollectorService should be created with send_logs=False
    """

    @patch('services.settings_service.MySQLRepository')
    def test_should_default_send_logs_enabled_to_false_when_env_var_missing(self, mock_mysql_repo_class):
        """
        Test that SEND_LOGS_ENABLED defaults to False when SEND_LOGS is not set.

        When the SEND_LOGS environment variable is not set,
        the module-level SEND_LOGS_ENABLED should be False.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()

        # Prepare environment without SEND_LOGS
        current_env = dict(os.environ)
        if 'SEND_LOGS' in current_env:
            del current_env['SEND_LOGS']

        # Act
        with patch.dict(os.environ, current_env, clear=True):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Assert
            self.assertFalse(
                api_service.SEND_LOGS_ENABLED,
                "SEND_LOGS_ENABLED should default to False when SEND_LOGS env var is missing"
            )

    @patch('services.settings_service.MySQLRepository')
    def test_should_create_logs_collector_service_with_send_logs_false_when_env_var_missing(self, mock_mysql_repo_class):
        """
        Test that LogsCollectorService is created with is_send_enabled=False by default.

        When SEND_LOGS is not set, the logs_collector_service.is_send_enabled should be False.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()

        # Prepare environment without SEND_LOGS
        current_env = dict(os.environ)
        if 'SEND_LOGS' in current_env:
            del current_env['SEND_LOGS']

        # Act
        with patch.dict(os.environ, current_env, clear=True):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Assert
            self.assertFalse(
                api_service.logs_collector_service.is_send_enabled,
                "logs_collector_service.is_send_enabled should be False when SEND_LOGS is not set"
            )

    @patch('services.settings_service.MySQLRepository')
    def test_should_default_send_logs_enabled_to_false_when_env_var_empty(self, mock_mysql_repo_class):
        """
        Test that SEND_LOGS_ENABLED defaults to False when SEND_LOGS is empty string.

        When the SEND_LOGS environment variable is set to empty string "",
        the module-level SEND_LOGS_ENABLED should be False.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": ""}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Assert
            self.assertFalse(
                api_service.SEND_LOGS_ENABLED,
                "SEND_LOGS_ENABLED should default to False when SEND_LOGS=''"
            )


class TestApiServiceLogsCollectorServiceType(unittest.TestCase):
    """
    Test cases to verify logs_collector_service is the correct type.

    These tests ensure the global logs_collector_service is an instance
    of LogsCollectorService and implements ILogsCollector.
    """

    @patch('services.settings_service.MySQLRepository')
    def test_logs_collector_service_should_be_instance_of_logs_collector_service_class(self, mock_mysql_repo_class):
        """
        Test that logs_collector_service is an instance of LogsCollectorService.

        The global variable should be a LogsCollectorService, not a mock or other type.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "true"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service
            from services.logs_collector_service import LogsCollectorService

            # Assert
            self.assertIsInstance(
                api_service.logs_collector_service,
                LogsCollectorService,
                "logs_collector_service should be an instance of LogsCollectorService"
            )

    @patch('services.settings_service.MySQLRepository')
    def test_logs_collector_service_should_implement_ilogs_collector(self, mock_mysql_repo_class):
        """
        Test that logs_collector_service implements ILogsCollector interface.

        The global variable should be an instance of ILogsCollector protocol.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "true"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service
            from services.logs_collector_interface import ILogsCollector

            # Assert
            self.assertIsInstance(
                api_service.logs_collector_service,
                ILogsCollector,
                "logs_collector_service should implement ILogsCollector"
            )


class TestApiServiceFeatureFlagsIntegration(unittest.TestCase):
    """
    Test cases for FeatureFlags integration with api_service.

    These tests verify that FeatureFlags can be used to determine
    the SEND_LOGS configuration (alternative implementation approach).

    NOTE: These tests do NOT require api_service import, so they
    test the FeatureFlags class directly.
    """

    def test_feature_flags_should_parse_send_logs_from_os_environ(self):
        """
        Test that FeatureFlags.from_environment works with os.environ.

        This verifies the integration between FeatureFlags and actual env vars.
        The api_service could use:
            feature_flags = FeatureFlags.from_environment(os.environ)
            logs_collector_service = LogsCollectorService(send_logs=feature_flags.send_logs)
        """
        # Arrange
        test_env = {"SEND_LOGS": "true"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            from models.feature_flags import FeatureFlags
            flags = FeatureFlags.from_environment(os.environ)

            # Assert
            self.assertTrue(
                flags.send_logs,
                "FeatureFlags.from_environment(os.environ) should return send_logs=True"
            )

    def test_feature_flags_should_default_to_false_with_missing_env_var(self):
        """
        Test that FeatureFlags defaults send_logs to False when missing.

        When SEND_LOGS is not in os.environ, FeatureFlags should default to False.
        """
        # Arrange
        current_env = dict(os.environ)
        if 'SEND_LOGS' in current_env:
            del current_env['SEND_LOGS']

        # Act
        with patch.dict(os.environ, current_env, clear=True):
            from models.feature_flags import FeatureFlags
            flags = FeatureFlags.from_environment(os.environ)

            # Assert
            self.assertFalse(
                flags.send_logs,
                "FeatureFlags.from_environment should default send_logs=False when missing"
            )


class TestApiServiceMultipleCallsToInitializeAccountEmailProcessor(unittest.TestCase):
    """
    Test cases for idempotent initialization of account_email_processor_service.

    These tests verify that calling _initialize_account_email_processor() multiple
    times returns the same instance and doesn't create multiple LogsCollectorService
    instances.
    """

    @patch('services.settings_service.MySQLRepository')
    def test_multiple_calls_should_return_same_account_email_processor_instance(self, mock_mysql_repo_class):
        """
        Test that _initialize_account_email_processor() is idempotent.

        Multiple calls should return the same AccountEmailProcessorService instance.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "true"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Reset the global to force re-initialization
            api_service.account_email_processor_service = None

            # Call twice
            service1 = api_service._initialize_account_email_processor()
            service2 = api_service._initialize_account_email_processor()

            # Assert
            self.assertIs(
                service1,
                service2,
                "_initialize_account_email_processor() should return the same instance on multiple calls"
            )

    @patch('services.settings_service.MySQLRepository')
    def test_multiple_calls_should_use_same_logs_collector_instance(self, mock_mysql_repo_class):
        """
        Test that multiple initializations use the same logs_collector_service.

        Even if _initialize_account_email_processor() is called multiple times,
        the logs_collector should always be the same global instance.
        """
        # Arrange
        mock_mysql_repo_class.return_value = _create_mock_repository()
        test_env = {"SEND_LOGS": "true"}

        # Act
        with patch.dict(os.environ, test_env, clear=False):
            if 'api_service' in sys.modules:
                del sys.modules['api_service']

            import api_service

            # Reset the global to force re-initialization
            api_service.account_email_processor_service = None

            service1 = api_service._initialize_account_email_processor()
            service2 = api_service._initialize_account_email_processor()

            # Assert
            self.assertIs(
                service1.logs_collector,
                service2.logs_collector,
                "Both service instances should reference the same logs_collector"
            )
            self.assertIs(
                service1.logs_collector,
                api_service.logs_collector_service,
                "logs_collector should be the global logs_collector_service"
            )


if __name__ == '__main__':
    unittest.main()
