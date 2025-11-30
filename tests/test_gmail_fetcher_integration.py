"""
Tests for gmail_fetcher.py integration with SEND_LOGS feature flag.

These tests verify that gmail_fetcher.py:
1. Reads SEND_LOGS environment variable at startup in main() function
2. Parses truthy values correctly: "true", "1", "yes" (case-insensitive)
3. Defaults to False when SEND_LOGS is not set or empty
4. Creates LogsCollectorService with the explicit send_logs parameter value

The implementation should:
- Read SEND_LOGS env var at the beginning of main() function
- Parse truthy values (true, 1, yes) case-insensitively
- Default to False when not set or empty
- Pass the parsed value explicitly to LogsCollectorService constructor

Gherkin Scenarios:
  Scenario: gmail_fetcher reads SEND_LOGS at startup
    Given the SEND_LOGS environment variable is set to "true"
    When gmail_fetcher.py main() function is executed
    Then the LogsCollectorService should be created with send_logs=True

  Scenario: gmail_fetcher defaults send_logs to False when env var missing
    Given the SEND_LOGS environment variable is not set
    When gmail_fetcher.py main() function is executed
    Then the LogsCollectorService should be created with send_logs=False

  Scenario: gmail_fetcher creates LogsCollectorService with explicit flag
    Given the SEND_LOGS environment variable is set to "1"
    When gmail_fetcher.py initializes the LogsCollectorService
    Then the constructor receives send_logs=True as a required parameter
    And no default value is used
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import sys


def _setup_gmail_fetcher_import():
    """
    Setup imports for gmail_fetcher by mocking argparse to avoid module-level execution.

    Returns the mock objects needed for testing.
    """
    # Create mock args object
    mock_args = MagicMock()
    mock_args.primary_host = '10.1.1.247:11434'
    mock_args.secondary_host = '10.1.1.212:11434'
    mock_args.base_url = None
    mock_args.hours = 2

    # Mock argparse
    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = mock_args

    return mock_parser, mock_args


class TestGmailFetcherSendLogsEnvVarReading(unittest.TestCase):
    """Test cases for SEND_LOGS environment variable reading in gmail_fetcher.py main()."""

    def setUp(self):
        """Clear gmail_fetcher from sys.modules before each test."""
        # Remove gmail_fetcher and related modules from cache
        modules_to_remove = [m for m in sys.modules if 'gmail_fetcher' in m]
        for mod in modules_to_remove:
            del sys.modules[mod]

    @patch('argparse.ArgumentParser')
    def test_should_create_logs_collector_with_send_logs_true_when_env_var_is_true(
        self,
        mock_argparse_class
    ):
        """
        Scenario: gmail_fetcher reads SEND_LOGS at startup

        Given the SEND_LOGS environment variable is set to "true"
        When gmail_fetcher.py main() function is executed
        Then the LogsCollectorService should be created with send_logs=True

        The implementation should:
        - Read SEND_LOGS env var at the beginning of main()
        - Parse "true" as True (case-insensitive)
        - Pass send_logs=True to LogsCollectorService constructor
        """
        # Arrange - setup argparse mock
        mock_parser, mock_args = _setup_gmail_fetcher_import()
        mock_argparse_class.return_value = mock_parser

        # Set environment variable
        with patch.dict(os.environ, {'SEND_LOGS': 'true'}, clear=False):
            # Import after mocking
            import gmail_fetcher

            # Mock LogsCollectorService and other dependencies
            with patch.object(gmail_fetcher, 'LogsCollectorService') as mock_logs_collector_class, \
                 patch.object(gmail_fetcher, 'test_api_connection') as mock_test_api_connection, \
                 patch.object(gmail_fetcher, 'ServiceGmailFetcher'):

                mock_test_api_connection.return_value = False  # Make test exit early
                mock_logs_collector = MagicMock()
                mock_logs_collector_class.return_value = mock_logs_collector

                # Act
                try:
                    gmail_fetcher.main(
                        email_address="test@example.com",
                        app_password="test-password",
                        api_token="test-token",
                        hours=2
                    )
                except SystemExit:
                    pass  # Expected due to mock_test_api_connection returning False

                # Assert
                mock_logs_collector_class.assert_called_once()
                call_kwargs = mock_logs_collector_class.call_args

                # Verify send_logs=True was passed
                if call_kwargs.kwargs:
                    self.assertTrue(
                        call_kwargs.kwargs.get('send_logs'),
                        f"LogsCollectorService should be created with send_logs=True, got: {call_kwargs}"
                    )
                else:
                    # If called with positional args, first arg should be True
                    self.assertTrue(
                        call_kwargs.args[0] if call_kwargs.args else False,
                        f"LogsCollectorService should be created with send_logs=True, got: {call_kwargs}"
                    )

    @patch('argparse.ArgumentParser')
    def test_should_handle_uppercase_true_value(self, mock_argparse_class):
        """
        Test that SEND_LOGS=TRUE (uppercase) is parsed as True.

        The implementation should handle case-insensitive parsing.
        """
        # Arrange
        mock_parser, mock_args = _setup_gmail_fetcher_import()
        mock_argparse_class.return_value = mock_parser

        with patch.dict(os.environ, {'SEND_LOGS': 'TRUE'}, clear=False):
            import gmail_fetcher

            with patch.object(gmail_fetcher, 'LogsCollectorService') as mock_logs_collector_class, \
                 patch.object(gmail_fetcher, 'test_api_connection') as mock_test_api_connection, \
                 patch.object(gmail_fetcher, 'ServiceGmailFetcher'):

                mock_test_api_connection.return_value = False
                mock_logs_collector = MagicMock()
                mock_logs_collector_class.return_value = mock_logs_collector

                # Act
                try:
                    gmail_fetcher.main(
                        email_address="test@example.com",
                        app_password="test-password",
                        api_token="test-token",
                        hours=2
                    )
                except SystemExit:
                    pass

                # Assert
                mock_logs_collector_class.assert_called_once()
                call_kwargs = mock_logs_collector_class.call_args

                if call_kwargs.kwargs:
                    self.assertTrue(
                        call_kwargs.kwargs.get('send_logs'),
                        f"LogsCollectorService should be created with send_logs=True for 'TRUE', got: {call_kwargs}"
                    )
                else:
                    self.assertTrue(
                        call_kwargs.args[0] if call_kwargs.args else False,
                        f"LogsCollectorService should be created with send_logs=True for 'TRUE', got: {call_kwargs}"
                    )

    @patch('argparse.ArgumentParser')
    def test_should_parse_1_as_true(self, mock_argparse_class):
        """
        Scenario: gmail_fetcher creates LogsCollectorService with explicit flag

        Given the SEND_LOGS environment variable is set to "1"
        When gmail_fetcher.py initializes the LogsCollectorService
        Then the constructor receives send_logs=True as a required parameter
        And no default value is used

        The implementation should:
        - Parse "1" as True
        - Pass send_logs=True explicitly to constructor
        """
        # Arrange
        mock_parser, mock_args = _setup_gmail_fetcher_import()
        mock_argparse_class.return_value = mock_parser

        with patch.dict(os.environ, {'SEND_LOGS': '1'}, clear=False):
            import gmail_fetcher

            with patch.object(gmail_fetcher, 'LogsCollectorService') as mock_logs_collector_class, \
                 patch.object(gmail_fetcher, 'test_api_connection') as mock_test_api_connection, \
                 patch.object(gmail_fetcher, 'ServiceGmailFetcher'):

                mock_test_api_connection.return_value = False
                mock_logs_collector = MagicMock()
                mock_logs_collector_class.return_value = mock_logs_collector

                # Act
                try:
                    gmail_fetcher.main(
                        email_address="test@example.com",
                        app_password="test-password",
                        api_token="test-token",
                        hours=2
                    )
                except SystemExit:
                    pass

                # Assert
                mock_logs_collector_class.assert_called_once()
                call_kwargs = mock_logs_collector_class.call_args

                if call_kwargs.kwargs:
                    self.assertTrue(
                        call_kwargs.kwargs.get('send_logs'),
                        f"LogsCollectorService should be created with send_logs=True for '1', got: {call_kwargs}"
                    )
                else:
                    self.assertTrue(
                        call_kwargs.args[0] if call_kwargs.args else False,
                        f"LogsCollectorService should be created with send_logs=True for '1', got: {call_kwargs}"
                    )

    @patch('argparse.ArgumentParser')
    def test_should_parse_yes_as_true(self, mock_argparse_class):
        """
        Test that SEND_LOGS=yes is parsed as True.

        The implementation should:
        - Parse "yes" as True (case-insensitive)
        """
        # Arrange
        mock_parser, mock_args = _setup_gmail_fetcher_import()
        mock_argparse_class.return_value = mock_parser

        with patch.dict(os.environ, {'SEND_LOGS': 'yes'}, clear=False):
            import gmail_fetcher

            with patch.object(gmail_fetcher, 'LogsCollectorService') as mock_logs_collector_class, \
                 patch.object(gmail_fetcher, 'test_api_connection') as mock_test_api_connection, \
                 patch.object(gmail_fetcher, 'ServiceGmailFetcher'):

                mock_test_api_connection.return_value = False
                mock_logs_collector = MagicMock()
                mock_logs_collector_class.return_value = mock_logs_collector

                # Act
                try:
                    gmail_fetcher.main(
                        email_address="test@example.com",
                        app_password="test-password",
                        api_token="test-token",
                        hours=2
                    )
                except SystemExit:
                    pass

                # Assert
                mock_logs_collector_class.assert_called_once()
                call_kwargs = mock_logs_collector_class.call_args

                if call_kwargs.kwargs:
                    self.assertTrue(
                        call_kwargs.kwargs.get('send_logs'),
                        f"LogsCollectorService should be created with send_logs=True for 'yes', got: {call_kwargs}"
                    )
                else:
                    self.assertTrue(
                        call_kwargs.args[0] if call_kwargs.args else False,
                        f"LogsCollectorService should be created with send_logs=True for 'yes', got: {call_kwargs}"
                    )


class TestGmailFetcherSendLogsDefaultBehavior(unittest.TestCase):
    """Test cases for SEND_LOGS default behavior when env var is missing or empty."""

    def setUp(self):
        """Clear gmail_fetcher from sys.modules before each test."""
        modules_to_remove = [m for m in sys.modules if 'gmail_fetcher' in m]
        for mod in modules_to_remove:
            del sys.modules[mod]

    @patch('argparse.ArgumentParser')
    def test_should_default_to_false_when_send_logs_not_set(self, mock_argparse_class):
        """
        Scenario: gmail_fetcher defaults send_logs to False when env var missing

        Given the SEND_LOGS environment variable is not set
        When gmail_fetcher.py main() function is executed
        Then the LogsCollectorService should be created with send_logs=False

        The implementation should:
        - Default to "false" when SEND_LOGS is not set
        - Pass send_logs=False to LogsCollectorService constructor
        """
        # Arrange
        mock_parser, mock_args = _setup_gmail_fetcher_import()
        mock_argparse_class.return_value = mock_parser

        # Remove SEND_LOGS from environment
        env_without_send_logs = {k: v for k, v in os.environ.items() if k != 'SEND_LOGS'}

        with patch.dict(os.environ, env_without_send_logs, clear=True):
            import gmail_fetcher

            with patch.object(gmail_fetcher, 'LogsCollectorService') as mock_logs_collector_class, \
                 patch.object(gmail_fetcher, 'test_api_connection') as mock_test_api_connection, \
                 patch.object(gmail_fetcher, 'ServiceGmailFetcher'):

                mock_test_api_connection.return_value = False
                mock_logs_collector = MagicMock()
                mock_logs_collector_class.return_value = mock_logs_collector

                # Act
                try:
                    gmail_fetcher.main(
                        email_address="test@example.com",
                        app_password="test-password",
                        api_token="test-token",
                        hours=2
                    )
                except SystemExit:
                    pass

                # Assert
                mock_logs_collector_class.assert_called_once()
                call_kwargs = mock_logs_collector_class.call_args

                if call_kwargs.kwargs:
                    self.assertFalse(
                        call_kwargs.kwargs.get('send_logs', True),
                        f"LogsCollectorService should be created with send_logs=False when not set, got: {call_kwargs}"
                    )
                else:
                    self.assertFalse(
                        call_kwargs.args[0] if call_kwargs.args else True,
                        f"LogsCollectorService should be created with send_logs=False when not set, got: {call_kwargs}"
                    )

    @patch('argparse.ArgumentParser')
    def test_should_default_to_false_when_send_logs_is_empty_string(self, mock_argparse_class):
        """
        Test that empty SEND_LOGS defaults to False.

        The implementation should:
        - Treat empty string as False
        - Pass send_logs=False to LogsCollectorService constructor
        """
        # Arrange
        mock_parser, mock_args = _setup_gmail_fetcher_import()
        mock_argparse_class.return_value = mock_parser

        with patch.dict(os.environ, {'SEND_LOGS': ''}, clear=False):
            import gmail_fetcher

            with patch.object(gmail_fetcher, 'LogsCollectorService') as mock_logs_collector_class, \
                 patch.object(gmail_fetcher, 'test_api_connection') as mock_test_api_connection, \
                 patch.object(gmail_fetcher, 'ServiceGmailFetcher'):

                mock_test_api_connection.return_value = False
                mock_logs_collector = MagicMock()
                mock_logs_collector_class.return_value = mock_logs_collector

                # Act
                try:
                    gmail_fetcher.main(
                        email_address="test@example.com",
                        app_password="test-password",
                        api_token="test-token",
                        hours=2
                    )
                except SystemExit:
                    pass

                # Assert
                mock_logs_collector_class.assert_called_once()
                call_kwargs = mock_logs_collector_class.call_args

                if call_kwargs.kwargs:
                    self.assertFalse(
                        call_kwargs.kwargs.get('send_logs', True),
                        f"LogsCollectorService should be created with send_logs=False for empty string, got: {call_kwargs}"
                    )
                else:
                    self.assertFalse(
                        call_kwargs.args[0] if call_kwargs.args else True,
                        f"LogsCollectorService should be created with send_logs=False for empty string, got: {call_kwargs}"
                    )

    @patch('argparse.ArgumentParser')
    def test_should_parse_false_as_false(self, mock_argparse_class):
        """
        Test that SEND_LOGS=false is parsed as False.

        The implementation should:
        - Parse "false" as False
        - Pass send_logs=False to LogsCollectorService constructor
        """
        # Arrange
        mock_parser, mock_args = _setup_gmail_fetcher_import()
        mock_argparse_class.return_value = mock_parser

        with patch.dict(os.environ, {'SEND_LOGS': 'false'}, clear=False):
            import gmail_fetcher

            with patch.object(gmail_fetcher, 'LogsCollectorService') as mock_logs_collector_class, \
                 patch.object(gmail_fetcher, 'test_api_connection') as mock_test_api_connection, \
                 patch.object(gmail_fetcher, 'ServiceGmailFetcher'):

                mock_test_api_connection.return_value = False
                mock_logs_collector = MagicMock()
                mock_logs_collector_class.return_value = mock_logs_collector

                # Act
                try:
                    gmail_fetcher.main(
                        email_address="test@example.com",
                        app_password="test-password",
                        api_token="test-token",
                        hours=2
                    )
                except SystemExit:
                    pass

                # Assert
                mock_logs_collector_class.assert_called_once()
                call_kwargs = mock_logs_collector_class.call_args

                if call_kwargs.kwargs:
                    self.assertFalse(
                        call_kwargs.kwargs.get('send_logs', True),
                        f"LogsCollectorService should be created with send_logs=False for 'false', got: {call_kwargs}"
                    )
                else:
                    self.assertFalse(
                        call_kwargs.args[0] if call_kwargs.args else True,
                        f"LogsCollectorService should be created with send_logs=False for 'false', got: {call_kwargs}"
                    )

    @patch('argparse.ArgumentParser')
    def test_should_parse_0_as_false(self, mock_argparse_class):
        """
        Test that SEND_LOGS=0 is parsed as False.

        The implementation should:
        - Parse "0" as False (not in truthy list)
        - Pass send_logs=False to LogsCollectorService constructor
        """
        # Arrange
        mock_parser, mock_args = _setup_gmail_fetcher_import()
        mock_argparse_class.return_value = mock_parser

        with patch.dict(os.environ, {'SEND_LOGS': '0'}, clear=False):
            import gmail_fetcher

            with patch.object(gmail_fetcher, 'LogsCollectorService') as mock_logs_collector_class, \
                 patch.object(gmail_fetcher, 'test_api_connection') as mock_test_api_connection, \
                 patch.object(gmail_fetcher, 'ServiceGmailFetcher'):

                mock_test_api_connection.return_value = False
                mock_logs_collector = MagicMock()
                mock_logs_collector_class.return_value = mock_logs_collector

                # Act
                try:
                    gmail_fetcher.main(
                        email_address="test@example.com",
                        app_password="test-password",
                        api_token="test-token",
                        hours=2
                    )
                except SystemExit:
                    pass

                # Assert
                mock_logs_collector_class.assert_called_once()
                call_kwargs = mock_logs_collector_class.call_args

                if call_kwargs.kwargs:
                    self.assertFalse(
                        call_kwargs.kwargs.get('send_logs', True),
                        f"LogsCollectorService should be created with send_logs=False for '0', got: {call_kwargs}"
                    )
                else:
                    self.assertFalse(
                        call_kwargs.args[0] if call_kwargs.args else True,
                        f"LogsCollectorService should be created with send_logs=False for '0', got: {call_kwargs}"
                    )


class TestGmailFetcherExplicitFlagPassing(unittest.TestCase):
    """Test cases to verify send_logs is passed explicitly (no default value used)."""

    def setUp(self):
        """Clear gmail_fetcher from sys.modules before each test."""
        modules_to_remove = [m for m in sys.modules if 'gmail_fetcher' in m]
        for mod in modules_to_remove:
            del sys.modules[mod]

    @patch('argparse.ArgumentParser')
    def test_should_pass_send_logs_as_keyword_argument(self, mock_argparse_class):
        """
        Test that send_logs is passed as an explicit argument to LogsCollectorService.

        The implementation should:
        - NOT rely on any default value in LogsCollectorService
        - Explicitly pass send_logs=<value> to the constructor
        - The call should include send_logs in either kwargs or as first positional arg
        """
        # Arrange
        mock_parser, mock_args = _setup_gmail_fetcher_import()
        mock_argparse_class.return_value = mock_parser

        with patch.dict(os.environ, {'SEND_LOGS': 'true'}, clear=False):
            import gmail_fetcher

            with patch.object(gmail_fetcher, 'LogsCollectorService') as mock_logs_collector_class, \
                 patch.object(gmail_fetcher, 'test_api_connection') as mock_test_api_connection, \
                 patch.object(gmail_fetcher, 'ServiceGmailFetcher'):

                mock_test_api_connection.return_value = False
                mock_logs_collector = MagicMock()
                mock_logs_collector_class.return_value = mock_logs_collector

                # Act
                try:
                    gmail_fetcher.main(
                        email_address="test@example.com",
                        app_password="test-password",
                        api_token="test-token",
                        hours=2
                    )
                except SystemExit:
                    pass

                # Assert
                mock_logs_collector_class.assert_called_once()
                call_kwargs = mock_logs_collector_class.call_args

                # Verify send_logs was passed explicitly (either as kwarg or positional)
                has_send_logs_kwarg = 'send_logs' in (call_kwargs.kwargs or {})
                has_positional_arg = len(call_kwargs.args) > 0

                self.assertTrue(
                    has_send_logs_kwarg or has_positional_arg,
                    f"LogsCollectorService should be called with explicit send_logs argument, got: {call_kwargs}"
                )

    @patch('argparse.ArgumentParser')
    def test_should_strip_whitespace_from_send_logs_value(self, mock_argparse_class):
        """
        Test that whitespace is stripped from SEND_LOGS value.

        The implementation should:
        - Strip leading/trailing whitespace from env var value
        - Parse "  true  " as True after stripping
        """
        # Arrange
        mock_parser, mock_args = _setup_gmail_fetcher_import()
        mock_argparse_class.return_value = mock_parser

        with patch.dict(os.environ, {'SEND_LOGS': '  true  '}, clear=False):
            import gmail_fetcher

            with patch.object(gmail_fetcher, 'LogsCollectorService') as mock_logs_collector_class, \
                 patch.object(gmail_fetcher, 'test_api_connection') as mock_test_api_connection, \
                 patch.object(gmail_fetcher, 'ServiceGmailFetcher'):

                mock_test_api_connection.return_value = False
                mock_logs_collector = MagicMock()
                mock_logs_collector_class.return_value = mock_logs_collector

                # Act
                try:
                    gmail_fetcher.main(
                        email_address="test@example.com",
                        app_password="test-password",
                        api_token="test-token",
                        hours=2
                    )
                except SystemExit:
                    pass

                # Assert
                mock_logs_collector_class.assert_called_once()
                call_kwargs = mock_logs_collector_class.call_args

                if call_kwargs.kwargs:
                    self.assertTrue(
                        call_kwargs.kwargs.get('send_logs'),
                        f"LogsCollectorService should be created with send_logs=True after stripping whitespace, got: {call_kwargs}"
                    )
                else:
                    self.assertTrue(
                        call_kwargs.args[0] if call_kwargs.args else False,
                        f"LogsCollectorService should be created with send_logs=True after stripping whitespace, got: {call_kwargs}"
                    )


class TestGmailFetcherLogsCollectorUsage(unittest.TestCase):
    """Test cases to verify LogsCollectorService is used correctly after instantiation."""

    def setUp(self):
        """Clear gmail_fetcher from sys.modules before each test."""
        modules_to_remove = [m for m in sys.modules if 'gmail_fetcher' in m]
        for mod in modules_to_remove:
            del sys.modules[mod]

    @patch('argparse.ArgumentParser')
    def test_logs_collector_send_log_called_on_startup(self, mock_argparse_class):
        """
        Test that LogsCollectorService.send_log is called after instantiation.

        The implementation should:
        - Create LogsCollectorService with send_logs parameter
        - Call send_log() to log the startup message
        """
        # Arrange
        mock_parser, mock_args = _setup_gmail_fetcher_import()
        mock_argparse_class.return_value = mock_parser

        with patch.dict(os.environ, {'SEND_LOGS': 'true'}, clear=False):
            import gmail_fetcher

            with patch.object(gmail_fetcher, 'LogsCollectorService') as mock_logs_collector_class, \
                 patch.object(gmail_fetcher, 'test_api_connection') as mock_test_api_connection, \
                 patch.object(gmail_fetcher, 'ServiceGmailFetcher'):

                mock_test_api_connection.return_value = False
                mock_logs_collector = MagicMock()
                mock_logs_collector_class.return_value = mock_logs_collector

                # Act
                try:
                    gmail_fetcher.main(
                        email_address="test@example.com",
                        app_password="test-password",
                        api_token="test-token",
                        hours=2
                    )
                except SystemExit:
                    pass

                # Assert
                mock_logs_collector.send_log.assert_called()

                # Verify at least one call was for startup
                calls = mock_logs_collector.send_log.call_args_list
                startup_calls = [
                    call for call in calls
                    if 'started' in str(call).lower() or 'processing' in str(call).lower()
                ]
                self.assertGreater(
                    len(startup_calls),
                    0,
                    f"LogsCollectorService.send_log should be called with startup message, calls: {calls}"
                )

    @patch('argparse.ArgumentParser')
    def test_logs_collector_send_log_called_on_api_failure(self, mock_argparse_class):
        """
        Test that LogsCollectorService.send_log is called when API connection fails.

        The implementation should:
        - Call send_log with ERROR level when API connection fails
        """
        # Arrange
        mock_parser, mock_args = _setup_gmail_fetcher_import()
        mock_argparse_class.return_value = mock_parser

        with patch.dict(os.environ, {'SEND_LOGS': 'true'}, clear=False):
            import gmail_fetcher

            with patch.object(gmail_fetcher, 'LogsCollectorService') as mock_logs_collector_class, \
                 patch.object(gmail_fetcher, 'test_api_connection') as mock_test_api_connection, \
                 patch.object(gmail_fetcher, 'ServiceGmailFetcher'):

                mock_test_api_connection.return_value = False
                mock_logs_collector = MagicMock()
                mock_logs_collector_class.return_value = mock_logs_collector

                # Act
                try:
                    gmail_fetcher.main(
                        email_address="test@example.com",
                        app_password="test-password",
                        api_token="test-token",
                        hours=2
                    )
                except SystemExit:
                    pass

                # Assert
                calls = mock_logs_collector.send_log.call_args_list
                error_calls = [
                    call for call in calls
                    if 'ERROR' in str(call)
                ]
                self.assertGreater(
                    len(error_calls),
                    0,
                    f"LogsCollectorService.send_log should be called with ERROR level on API failure, calls: {calls}"
                )


if __name__ == '__main__':
    unittest.main()
