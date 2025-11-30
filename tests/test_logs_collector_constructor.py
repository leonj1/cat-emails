"""
Tests for LogsCollectorService constructor requirements.

These tests verify that LogsCollectorService requires a `send_logs: bool` parameter
and exposes an `is_send_enabled` property.

The implementation should:
- Require send_logs as a mandatory boolean parameter in the constructor
- Expose is_send_enabled property that returns the send_logs value
- Raise TypeError when send_logs parameter is not provided
"""
import unittest

from services.logs_collector_service import LogsCollectorService


class TestLogsCollectorServiceConstructor(unittest.TestCase):
    """Test cases for LogsCollectorService constructor requirements."""

    def test_should_raise_type_error_when_instantiated_without_send_logs_parameter(self):
        """
        Test that LogsCollectorService requires send_logs parameter.

        When I instantiate LogsCollectorService without the send_logs parameter,
        Then a TypeError should be raised.
        And the error message should indicate send_logs is a required argument.

        The implementation should change the constructor to make send_logs required.
        """
        # Arrange - no parameters to pass

        # Act & Assert
        with self.assertRaises(TypeError) as context:
            LogsCollectorService()

        # Verify error message mentions send_logs
        error_message = str(context.exception)
        self.assertIn(
            "send_logs",
            error_message,
            f"Expected error message to mention 'send_logs', got: {error_message}"
        )

    def test_should_create_service_with_send_logs_true_and_expose_is_send_enabled_true(self):
        """
        Test that LogsCollectorService accepts send_logs=True.

        When I instantiate LogsCollectorService with send_logs=True,
        Then the service should be created successfully.
        And the is_send_enabled property should return True.

        The implementation should:
        - Accept send_logs=True as constructor argument
        - Store the value and expose it via is_send_enabled property
        """
        # Arrange
        send_logs = True

        # Act
        service = LogsCollectorService(send_logs=send_logs)

        # Assert
        self.assertIsNotNone(service, "Service should be created successfully")
        self.assertTrue(
            service.is_send_enabled,
            "is_send_enabled should return True when send_logs=True"
        )

    def test_should_create_service_with_send_logs_false_and_expose_is_send_enabled_false(self):
        """
        Test that LogsCollectorService accepts send_logs=False.

        When I instantiate LogsCollectorService with send_logs=False,
        Then the service should be created successfully.
        And the is_send_enabled property should return False.

        The implementation should:
        - Accept send_logs=False as constructor argument
        - Store the value and expose it via is_send_enabled property
        """
        # Arrange
        send_logs = False

        # Act
        service = LogsCollectorService(send_logs=send_logs)

        # Assert
        self.assertIsNotNone(service, "Service should be created successfully")
        self.assertFalse(
            service.is_send_enabled,
            "is_send_enabled should return False when send_logs=False"
        )


class TestLogsCollectorServiceIsSendEnabledProperty(unittest.TestCase):
    """Test cases for is_send_enabled property behavior."""

    def test_is_send_enabled_property_should_exist_on_service(self):
        """
        Test that is_send_enabled property exists on LogsCollectorService.

        The implementation should add an is_send_enabled property to the class.
        """
        # Arrange & Act
        service = LogsCollectorService(send_logs=True)

        # Assert - verify is_send_enabled is accessible as a property
        self.assertTrue(
            hasattr(service, 'is_send_enabled'),
            "LogsCollectorService should have is_send_enabled property"
        )

    def test_is_send_enabled_should_return_boolean_type(self):
        """
        Test that is_send_enabled returns a boolean value.

        The is_send_enabled property should always return a boolean,
        matching the send_logs parameter type.
        """
        # Arrange
        service_enabled = LogsCollectorService(send_logs=True)
        service_disabled = LogsCollectorService(send_logs=False)

        # Act
        result_enabled = service_enabled.is_send_enabled
        result_disabled = service_disabled.is_send_enabled

        # Assert
        self.assertIsInstance(
            result_enabled,
            bool,
            f"is_send_enabled should return bool, got {type(result_enabled)}"
        )
        self.assertIsInstance(
            result_disabled,
            bool,
            f"is_send_enabled should return bool, got {type(result_disabled)}"
        )


if __name__ == '__main__':
    unittest.main()
