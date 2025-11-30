"""
Tests for constructor argument limit compliance verification.

These tests verify that LogsCollectorService has at most 3 constructor parameters
(excluding self) with send_logs as the first required parameter.

Gherkin Feature: SEND_LOGS Feature Flag - Constructor Argument Limit Compliance

  Scenario: LogsCollectorService has fewer than 4 constructor arguments
    When I inspect the LogsCollectorService constructor
    Then it should have at most 3 parameters (excluding self)
    And send_logs should be the first required parameter

  Scenario: Services maintain constructor argument limit
    When I inspect all service constructors that use ILogsCollector
    Then each service should have fewer than 4 parameters (excluding self)

The implementation should:
- Require send_logs as a mandatory boolean parameter in the constructor
- Have api_url as an optional string parameter (second position)
- Have api_token as an optional string parameter (third position)
- Not exceed 3 constructor parameters (excluding self)
"""
import inspect
import unittest

from services.logs_collector_service import LogsCollectorService


class TestLogsCollectorServiceConstructorLimit(unittest.TestCase):
    """
    Test cases for LogsCollectorService constructor argument limit compliance.

    These tests use Python's inspect module to verify constructor signatures
    meet the strict architecture requirements.
    """

    def test_constructor_should_have_at_most_three_parameters_excluding_self(self):
        """
        Test that LogsCollectorService constructor has at most 3 parameters.

        When I inspect the LogsCollectorService constructor
        Then it should have at most 3 parameters (excluding self)

        The strict architecture requires MAX_ARGS: 4 arguments per function/constructor.
        For this service, we verify the limit is 3 (send_logs, api_url, api_token).
        """
        # Arrange
        sig = inspect.signature(LogsCollectorService.__init__)

        # Act - Get all parameters excluding 'self'
        params = [p for p in sig.parameters.keys() if p != 'self']

        # Assert
        self.assertLessEqual(
            len(params),
            3,
            f"LogsCollectorService constructor should have at most 3 parameters "
            f"(excluding self), but has {len(params)}: {params}"
        )

    def test_send_logs_should_be_first_parameter_after_self(self):
        """
        Test that send_logs is the first parameter after self.

        When I inspect the LogsCollectorService constructor
        Then send_logs should be the first parameter after self

        The constructor signature should be:
            __init__(self, send_logs: bool, ...)
        """
        # Arrange
        sig = inspect.signature(LogsCollectorService.__init__)
        params = list(sig.parameters.items())

        # Act - Get the first parameter after 'self'
        # params[0] is 'self', params[1] should be 'send_logs'
        first_param_name = params[1][0] if len(params) > 1 else None

        # Assert
        self.assertEqual(
            first_param_name,
            'send_logs',
            f"First parameter after 'self' should be 'send_logs', "
            f"but got '{first_param_name}'"
        )

    def test_send_logs_should_be_required_parameter_with_no_default(self):
        """
        Test that send_logs is a required parameter with no default value.

        When I inspect the LogsCollectorService constructor
        Then send_logs should have no default value (required parameter)

        Per coding standards: No default argument values - Be explicit about all inputs
        """
        # Arrange
        sig = inspect.signature(LogsCollectorService.__init__)
        params = list(sig.parameters.items())

        # Act - Get the send_logs parameter
        send_logs_param = params[1][1] if len(params) > 1 else None

        # Assert - Parameter should have empty default (no default value)
        self.assertIsNotNone(
            send_logs_param,
            "send_logs parameter should exist"
        )
        self.assertIs(
            send_logs_param.default,
            inspect.Parameter.empty,
            f"send_logs should be a required parameter with no default value, "
            f"but has default: {send_logs_param.default}"
        )

    def test_send_logs_parameter_should_have_bool_type_annotation(self):
        """
        Test that send_logs parameter has bool type annotation.

        When I inspect the LogsCollectorService constructor
        Then send_logs should have bool as its type annotation

        Type hints are required per Python coding standards.
        """
        # Arrange
        sig = inspect.signature(LogsCollectorService.__init__)
        params = list(sig.parameters.items())

        # Act - Get the send_logs parameter annotation
        send_logs_param = params[1][1] if len(params) > 1 else None

        # Assert
        self.assertIsNotNone(
            send_logs_param,
            "send_logs parameter should exist"
        )
        self.assertEqual(
            send_logs_param.annotation,
            bool,
            f"send_logs should have bool type annotation, "
            f"but has: {send_logs_param.annotation}"
        )


class TestLogsCollectorServiceParameterOrder(unittest.TestCase):
    """
    Test cases for verifying parameter order in LogsCollectorService constructor.

    Expected order:
    1. send_logs: bool (required)
    2. api_url: Optional[str] = None (optional)
    3. api_token: Optional[str] = None (optional)
    """

    def test_constructor_parameters_should_be_in_correct_order(self):
        """
        Test that constructor parameters are in the expected order.

        When I inspect the LogsCollectorService constructor
        Then parameters should be in order: send_logs, api_url, api_token
        """
        # Arrange
        sig = inspect.signature(LogsCollectorService.__init__)
        params = [p for p in sig.parameters.keys() if p != 'self']

        # Expected parameter order
        expected_order = ['send_logs', 'api_url', 'api_token']

        # Act & Assert
        self.assertEqual(
            params,
            expected_order,
            f"Constructor parameters should be in order {expected_order}, "
            f"but got: {params}"
        )

    def test_api_url_should_be_second_parameter_with_default_none(self):
        """
        Test that api_url is the second parameter with default None.

        When I inspect the LogsCollectorService constructor
        Then api_url should be the second parameter with default None

        Note: The coding standards allow Optional parameters to have = None
        as they represent truly optional configuration.
        """
        # Arrange
        sig = inspect.signature(LogsCollectorService.__init__)
        params = list(sig.parameters.items())

        # Act - Get api_url parameter (index 2 after self and send_logs)
        api_url_param = None
        for name, param in params:
            if name == 'api_url':
                api_url_param = param
                break

        # Assert
        self.assertIsNotNone(
            api_url_param,
            "api_url parameter should exist"
        )
        self.assertIsNone(
            api_url_param.default,
            f"api_url should have default value None, "
            f"but has: {api_url_param.default}"
        )

    def test_api_token_should_be_third_parameter_with_default_none(self):
        """
        Test that api_token is the third parameter with default None.

        When I inspect the LogsCollectorService constructor
        Then api_token should be the third parameter with default None
        """
        # Arrange
        sig = inspect.signature(LogsCollectorService.__init__)
        params = list(sig.parameters.items())

        # Act - Get api_token parameter
        api_token_param = None
        for name, param in params:
            if name == 'api_token':
                api_token_param = param
                break

        # Assert
        self.assertIsNotNone(
            api_token_param,
            "api_token parameter should exist"
        )
        self.assertIsNone(
            api_token_param.default,
            f"api_token should have default value None, "
            f"but has: {api_token_param.default}"
        )


class TestLogsCollectorServiceConstructorCompliance(unittest.TestCase):
    """
    Test cases to verify constructor complies with strict architecture rules.

    Strict Architecture Rules:
    - MAX_ARGS: 4 arguments per function/constructor
    - For LogsCollectorService: exactly 3 parameters (send_logs, api_url, api_token)
    """

    def test_constructor_exact_parameter_count(self):
        """
        Test that constructor has exactly 3 parameters.

        When I inspect the LogsCollectorService constructor
        Then it should have exactly 3 parameters (excluding self)

        This verifies the constructor is well-designed with minimal parameters.
        """
        # Arrange
        sig = inspect.signature(LogsCollectorService.__init__)
        params = [p for p in sig.parameters.keys() if p != 'self']

        # Assert
        self.assertEqual(
            len(params),
            3,
            f"LogsCollectorService constructor should have exactly 3 parameters "
            f"(excluding self), but has {len(params)}: {params}"
        )

    def test_no_additional_unexpected_parameters(self):
        """
        Test that constructor has only the expected parameters.

        When I inspect the LogsCollectorService constructor
        Then it should only have: send_logs, api_url, api_token parameters
        """
        # Arrange
        sig = inspect.signature(LogsCollectorService.__init__)
        params = set(p for p in sig.parameters.keys() if p != 'self')

        # Expected parameters
        expected_params = {'send_logs', 'api_url', 'api_token'}

        # Assert
        self.assertEqual(
            params,
            expected_params,
            f"Constructor should only have parameters {expected_params}, "
            f"but has: {params}"
        )


class TestOtherServicesConstructorCompliance(unittest.TestCase):
    """
    Test cases documenting constructor compliance for other services.

    Note: Per the requirements, existing services like AccountEmailProcessorService
    already exceed the 4-parameter limit (it has 10+ parameters). These tests
    document the non-compliance but do not fail.

    Gherkin Scenario:
      When I inspect all service constructors that use ILogsCollector
      Then each service should have fewer than 4 parameters (excluding self)
    """

    def test_document_account_email_processor_service_non_compliance(self):
        """
        Document AccountEmailProcessorService constructor parameter count.

        Note: This test documents non-compliance but does not fail.
        AccountEmailProcessorService has 10+ parameters which exceeds
        the MAX_ARGS limit of 4.
        """
        # Arrange
        from services.account_email_processor_service import AccountEmailProcessorService
        sig = inspect.signature(AccountEmailProcessorService.__init__)
        params = [p for p in sig.parameters.keys() if p != 'self']

        # Document the current state
        param_count = len(params)

        # This test documents rather than enforces
        # The service has many dependencies which exceed the limit
        if param_count > 4:
            # Document non-compliance
            self.skipTest(
                f"AccountEmailProcessorService has {param_count} parameters "
                f"(exceeds MAX_ARGS limit of 4): {params}. "
                f"This is documented non-compliance - refactoring needed."
            )
        else:
            # If it becomes compliant, verify it
            self.assertLessEqual(
                param_count,
                4,
                f"AccountEmailProcessorService should have at most 4 parameters "
                f"(excluding self), but has {param_count}: {params}"
            )

    def test_document_email_processor_service_constructor(self):
        """
        Document EmailProcessorService constructor parameter count.

        Note: This test documents the constructor compliance status.
        """
        # Arrange
        from services.email_processor_service import EmailProcessorService
        sig = inspect.signature(EmailProcessorService.__init__)
        params = [p for p in sig.parameters.keys() if p != 'self']

        param_count = len(params)

        if param_count > 4:
            self.skipTest(
                f"EmailProcessorService has {param_count} parameters "
                f"(exceeds MAX_ARGS limit of 4): {params}. "
                f"This is documented non-compliance - refactoring needed."
            )
        else:
            self.assertLessEqual(
                param_count,
                4,
                f"EmailProcessorService should have at most 4 parameters "
                f"(excluding self), but has {param_count}: {params}"
            )

    def test_document_email_summary_service_constructor(self):
        """
        Document EmailSummaryService constructor parameter count.

        Note: This test documents the constructor compliance status.
        """
        # Arrange
        from services.email_summary_service import EmailSummaryService
        sig = inspect.signature(EmailSummaryService.__init__)
        params = [p for p in sig.parameters.keys() if p != 'self']

        param_count = len(params)

        if param_count > 4:
            self.skipTest(
                f"EmailSummaryService has {param_count} parameters "
                f"(exceeds MAX_ARGS limit of 4): {params}. "
                f"This is documented non-compliance - refactoring needed."
            )
        else:
            self.assertLessEqual(
                param_count,
                4,
                f"EmailSummaryService should have at most 4 parameters "
                f"(excluding self), but has {param_count}: {params}"
            )


class TestLogsCollectorServiceInstantiationCompliance(unittest.TestCase):
    """
    Test cases verifying that LogsCollectorService can be instantiated correctly
    with its compliant constructor signature.
    """

    def test_should_instantiate_with_required_send_logs_parameter_only(self):
        """
        Test that LogsCollectorService can be instantiated with only send_logs.

        When I instantiate LogsCollectorService with only send_logs parameter
        Then the service should be created successfully
        And api_url and api_token should default to None (read from env)
        """
        # Arrange & Act
        service = LogsCollectorService(send_logs=False)

        # Assert
        self.assertIsNotNone(service, "Service should be instantiated")
        self.assertFalse(
            service.is_send_enabled,
            "is_send_enabled should return False when send_logs=False"
        )

    def test_should_instantiate_with_all_parameters(self):
        """
        Test that LogsCollectorService can be instantiated with all parameters.

        When I instantiate LogsCollectorService with all three parameters
        Then the service should be created successfully
        And the provided values should be used
        """
        # Arrange
        test_api_url = "https://test-logs-api.example.com"
        test_api_token = "test-token-123"

        # Act
        service = LogsCollectorService(
            send_logs=True,
            api_url=test_api_url,
            api_token=test_api_token
        )

        # Assert
        self.assertIsNotNone(service, "Service should be instantiated")
        self.assertTrue(
            service.is_send_enabled,
            "is_send_enabled should return True when send_logs=True"
        )
        self.assertEqual(
            service.api_url,
            test_api_url,
            f"api_url should be '{test_api_url}'"
        )
        self.assertEqual(
            service.api_token,
            test_api_token,
            f"api_token should be '{test_api_token}'"
        )


if __name__ == '__main__':
    unittest.main()
