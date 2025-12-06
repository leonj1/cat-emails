"""
Tests for ProcessingStatusManager Core Audit Fields (emails_categorized, emails_skipped).

Based on BDD scenarios from tests/bdd/core_fields_audit_records.feature:
- Scenario: AccountStatus dataclass includes emails_categorized field
- Scenario: AccountStatus dataclass includes emails_skipped field

These tests follow TDD approach (Red phase) - tests will FAIL until the
AccountStatus dataclass is updated with the required core audit fields.

The implementation should add to AccountStatus dataclass:
    emails_categorized: int = 0
    emails_skipped: int = 0
"""
import unittest

from services.processing_status_manager import (
    ProcessingStatusManager,
    ProcessingState,
    AccountStatus,
)


class TestAccountStatusEmailsCategorizedField(unittest.TestCase):
    """
    Scenario: AccountStatus dataclass includes emails_categorized field

    Given an account has completed processing runs
    When the account status is retrieved
    Then the status includes the emails_categorized field
    And the field contains the cumulative count of categorized emails
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        # Ensure no active session remains
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_account_status_has_emails_categorized_field(self):
        """
        Test that AccountStatus dataclass has emails_categorized field.

        The implementation should add to AccountStatus:
            emails_categorized: int = 0
        """
        # Assert: AccountStatus has emails_categorized attribute in dataclass fields
        self.assertTrue(
            hasattr(AccountStatus, '__dataclass_fields__'),
            "AccountStatus should be a dataclass"
        )
        self.assertIn(
            'emails_categorized',
            AccountStatus.__dataclass_fields__,
            "AccountStatus should have 'emails_categorized' field"
        )

    def test_emails_categorized_field_default_is_zero(self):
        """
        Test that emails_categorized field defaults to 0.

        The implementation should define:
            emails_categorized: int = 0
        """
        # Arrange: Create AccountStatus with minimal required fields
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.IDLE,
            current_step="None"
        )

        # Assert: emails_categorized defaults to 0
        self.assertEqual(
            status.emails_categorized,
            0,
            f"emails_categorized should default to 0, got {status.emails_categorized}"
        )

    def test_emails_categorized_field_is_integer_type(self):
        """
        Test that emails_categorized field is an integer type.

        The field should be typed as int for proper validation.
        """
        # Arrange: Get field info from dataclass
        field_info = AccountStatus.__dataclass_fields__['emails_categorized']

        # Assert: Field type is int
        self.assertEqual(
            field_info.type,
            int,
            f"emails_categorized field type should be int, got {field_info.type}"
        )

    def test_emails_categorized_field_can_be_set_to_custom_value(self):
        """
        Test that emails_categorized can be set to a custom value.

        The field should accept any non-negative integer value.
        """
        # Arrange: Create AccountStatus with custom emails_categorized
        expected_value = 42
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.COMPLETED,
            current_step="Finished",
            emails_categorized=expected_value
        )

        # Assert: emails_categorized has the custom value
        self.assertEqual(
            status.emails_categorized,
            expected_value,
            f"emails_categorized should be {expected_value}, got {status.emails_categorized}"
        )

    def test_start_processing_initializes_emails_categorized_to_zero(self):
        """
        Test that starting a processing session sets emails_categorized to 0.

        When a processing session starts for "user@example.com"
        Then the current status shows emails categorized as 0
        """
        # Arrange
        test_email = "user@example.com"

        # Act
        self.status_manager.start_processing(test_email)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertIsNotNone(status, "Status should not be None after starting processing")
        self.assertIn(
            'emails_categorized',
            status,
            "Status should include 'emails_categorized' field"
        )
        self.assertEqual(
            status['emails_categorized'],
            0,
            f"emails_categorized should be 0, got {status.get('emails_categorized')}"
        )


class TestAccountStatusEmailsSkippedField(unittest.TestCase):
    """
    Scenario: AccountStatus dataclass includes emails_skipped field

    Given an account has completed processing runs
    When the account status is retrieved
    Then the status includes the emails_skipped field
    And the field contains the cumulative count of skipped emails
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_account_status_has_emails_skipped_field(self):
        """
        Test that AccountStatus dataclass has emails_skipped field.

        The implementation should add to AccountStatus:
            emails_skipped: int = 0
        """
        # Assert: AccountStatus has emails_skipped attribute in dataclass fields
        self.assertIn(
            'emails_skipped',
            AccountStatus.__dataclass_fields__,
            "AccountStatus should have 'emails_skipped' field"
        )

    def test_emails_skipped_field_default_is_zero(self):
        """
        Test that emails_skipped field defaults to 0.

        The implementation should define:
            emails_skipped: int = 0
        """
        # Arrange: Create AccountStatus with minimal required fields
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.IDLE,
            current_step="None"
        )

        # Assert: emails_skipped defaults to 0
        self.assertEqual(
            status.emails_skipped,
            0,
            f"emails_skipped should default to 0, got {status.emails_skipped}"
        )

    def test_emails_skipped_field_is_integer_type(self):
        """
        Test that emails_skipped field is an integer type.

        The field should be typed as int for proper validation.
        """
        # Arrange: Get field info from dataclass
        field_info = AccountStatus.__dataclass_fields__['emails_skipped']

        # Assert: Field type is int
        self.assertEqual(
            field_info.type,
            int,
            f"emails_skipped field type should be int, got {field_info.type}"
        )

    def test_emails_skipped_field_can_be_set_to_custom_value(self):
        """
        Test that emails_skipped can be set to a custom value.

        The field should accept any non-negative integer value.
        """
        # Arrange: Create AccountStatus with custom emails_skipped
        expected_value = 17
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.COMPLETED,
            current_step="Finished",
            emails_skipped=expected_value
        )

        # Assert: emails_skipped has the custom value
        self.assertEqual(
            status.emails_skipped,
            expected_value,
            f"emails_skipped should be {expected_value}, got {status.emails_skipped}"
        )

    def test_start_processing_initializes_emails_skipped_to_zero(self):
        """
        Test that starting a processing session sets emails_skipped to 0.

        When a processing session starts for "user@example.com"
        Then the current status shows emails skipped as 0
        """
        # Arrange
        test_email = "user@example.com"

        # Act
        self.status_manager.start_processing(test_email)
        status = self.status_manager.get_current_status()

        # Assert
        self.assertIsNotNone(status, "Status should not be None after starting processing")
        self.assertIn(
            'emails_skipped',
            status,
            "Status should include 'emails_skipped' field"
        )
        self.assertEqual(
            status['emails_skipped'],
            0,
            f"emails_skipped should be 0, got {status.get('emails_skipped')}"
        )


class TestAccountStatusToDictIncludesCoreAuditFields(unittest.TestCase):
    """
    Test that AccountStatus.to_dict() includes core audit fields.

    This ensures the core audit fields are serializable for API responses
    and included when the account status is retrieved.
    """

    def test_to_dict_includes_emails_categorized(self):
        """
        Test that AccountStatus.to_dict() includes emails_categorized field.

        When the account status is retrieved,
        Then the status includes the emails_categorized field.
        """
        # Arrange
        expected_value = 50
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.PROCESSING,
            current_step="Testing",
            emails_categorized=expected_value
        )

        # Act
        result = status.to_dict()

        # Assert
        self.assertIn(
            'emails_categorized',
            result,
            "to_dict() should include 'emails_categorized' field"
        )
        self.assertEqual(
            result['emails_categorized'],
            expected_value,
            f"to_dict() emails_categorized should be {expected_value}, got {result.get('emails_categorized')}"
        )

    def test_to_dict_includes_emails_skipped(self):
        """
        Test that AccountStatus.to_dict() includes emails_skipped field.

        When the account status is retrieved,
        Then the status includes the emails_skipped field.
        """
        # Arrange
        expected_value = 25
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.PROCESSING,
            current_step="Testing",
            emails_skipped=expected_value
        )

        # Act
        result = status.to_dict()

        # Assert
        self.assertIn(
            'emails_skipped',
            result,
            "to_dict() should include 'emails_skipped' field"
        )
        self.assertEqual(
            result['emails_skipped'],
            expected_value,
            f"to_dict() emails_skipped should be {expected_value}, got {result.get('emails_skipped')}"
        )

    def test_to_dict_includes_both_core_audit_fields(self):
        """
        Test that AccountStatus.to_dict() includes both core audit fields together.

        Validates complete serialization of core audit fields.
        """
        # Arrange
        expected_categorized = 100
        expected_skipped = 30
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.COMPLETED,
            current_step="Done",
            emails_categorized=expected_categorized,
            emails_skipped=expected_skipped
        )

        # Act
        result = status.to_dict()

        # Assert: Both fields present with correct values
        self.assertEqual(
            result.get('emails_categorized'),
            expected_categorized,
            f"emails_categorized should be {expected_categorized}, got {result.get('emails_categorized')}"
        )
        self.assertEqual(
            result.get('emails_skipped'),
            expected_skipped,
            f"emails_skipped should be {expected_skipped}, got {result.get('emails_skipped')}"
        )


class TestAccountStatusCoreAuditFieldsCumulativeCount(unittest.TestCase):
    """
    Tests that core audit fields contain cumulative counts.

    Scenario requirements:
    - And the field contains the cumulative count of categorized emails
    - And the field contains the cumulative count of skipped emails
    """

    def setUp(self):
        """Set up test fixtures."""
        self.status_manager = ProcessingStatusManager(max_history=10)

    def tearDown(self):
        """Clean up after each test."""
        if self.status_manager.is_processing():
            self.status_manager.complete_processing()

    def test_emails_categorized_stores_cumulative_count(self):
        """
        Test that emails_categorized can store cumulative counts across a session.

        The field should be capable of storing accumulated values.
        """
        # Arrange: Create status with a cumulative count
        cumulative_count = 150
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.COMPLETED,
            current_step="Processing complete",
            emails_categorized=cumulative_count
        )

        # Assert: Cumulative count is stored correctly
        self.assertEqual(
            status.emails_categorized,
            cumulative_count,
            f"emails_categorized should store cumulative count of {cumulative_count}, "
            f"got {status.emails_categorized}"
        )

    def test_emails_skipped_stores_cumulative_count(self):
        """
        Test that emails_skipped can store cumulative counts across a session.

        The field should be capable of storing accumulated values.
        """
        # Arrange: Create status with a cumulative count
        cumulative_count = 75
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.COMPLETED,
            current_step="Processing complete",
            emails_skipped=cumulative_count
        )

        # Assert: Cumulative count is stored correctly
        self.assertEqual(
            status.emails_skipped,
            cumulative_count,
            f"emails_skipped should store cumulative count of {cumulative_count}, "
            f"got {status.emails_skipped}"
        )

    def test_core_audit_fields_can_store_large_cumulative_values(self):
        """
        Test that core audit fields can store large cumulative counts.

        Validates the fields can handle realistic processing volumes.
        """
        # Arrange: Large cumulative counts from extensive processing
        large_categorized = 50000
        large_skipped = 25000
        status = AccountStatus(
            email_address="bulk@example.com",
            state=ProcessingState.COMPLETED,
            current_step="Bulk processing complete",
            emails_categorized=large_categorized,
            emails_skipped=large_skipped
        )

        # Assert: Large values are stored correctly
        self.assertEqual(
            status.emails_categorized,
            large_categorized,
            f"emails_categorized should store large value {large_categorized}, "
            f"got {status.emails_categorized}"
        )
        self.assertEqual(
            status.emails_skipped,
            large_skipped,
            f"emails_skipped should store large value {large_skipped}, "
            f"got {status.emails_skipped}"
        )


class TestAccountStatusBothCoreAuditFieldsTogether(unittest.TestCase):
    """
    Integration tests for both core audit fields together.

    Validates that emails_categorized and emails_skipped work together
    correctly in the AccountStatus dataclass.
    """

    def test_both_core_audit_fields_initialize_to_zero_by_default(self):
        """
        Test that both core audit fields default to 0 when not specified.
        """
        # Arrange: Create AccountStatus without specifying core audit fields
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.IDLE,
            current_step="None"
        )

        # Assert: Both fields default to 0
        self.assertEqual(
            status.emails_categorized,
            0,
            f"emails_categorized should default to 0, got {status.emails_categorized}"
        )
        self.assertEqual(
            status.emails_skipped,
            0,
            f"emails_skipped should default to 0, got {status.emails_skipped}"
        )

    def test_both_core_audit_fields_can_be_set_independently(self):
        """
        Test that both core audit fields can be set to different values.
        """
        # Arrange: Create AccountStatus with different values for each field
        expected_categorized = 100
        expected_skipped = 25
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.COMPLETED,
            current_step="Done",
            emails_categorized=expected_categorized,
            emails_skipped=expected_skipped
        )

        # Assert: Both fields have their expected values
        self.assertEqual(
            status.emails_categorized,
            expected_categorized,
            f"emails_categorized should be {expected_categorized}, got {status.emails_categorized}"
        )
        self.assertEqual(
            status.emails_skipped,
            expected_skipped,
            f"emails_skipped should be {expected_skipped}, got {status.emails_skipped}"
        )

    def test_core_audit_fields_coexist_with_existing_audit_fields(self):
        """
        Test that new core audit fields work alongside existing audit fields.

        The AccountStatus should support all audit fields:
        - emails_reviewed, emails_tagged, emails_deleted (existing)
        - emails_categorized, emails_skipped (new core fields)
        """
        # Arrange: Create AccountStatus with all audit fields
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.COMPLETED,
            current_step="Done",
            # Existing audit fields
            emails_reviewed=100,
            emails_tagged=50,
            emails_deleted=10,
            # New core audit fields
            emails_categorized=75,
            emails_skipped=15
        )

        # Assert: All fields are set correctly
        self.assertEqual(status.emails_reviewed, 100)
        self.assertEqual(status.emails_tagged, 50)
        self.assertEqual(status.emails_deleted, 10)
        self.assertEqual(status.emails_categorized, 75)
        self.assertEqual(status.emails_skipped, 15)

    def test_to_dict_includes_all_core_audit_fields_with_existing_fields(self):
        """
        Test that to_dict() includes all audit fields together.

        The serialized output should contain both existing and new audit fields.
        """
        # Arrange: Create AccountStatus with all audit fields
        status = AccountStatus(
            email_address="test@example.com",
            state=ProcessingState.COMPLETED,
            current_step="Done",
            emails_reviewed=100,
            emails_tagged=50,
            emails_deleted=10,
            emails_categorized=75,
            emails_skipped=15
        )

        # Act
        result = status.to_dict()

        # Assert: All audit fields are present in serialized output
        self.assertIn('emails_reviewed', result)
        self.assertIn('emails_tagged', result)
        self.assertIn('emails_deleted', result)
        self.assertIn('emails_categorized', result)
        self.assertIn('emails_skipped', result)

        # Verify values
        self.assertEqual(result['emails_reviewed'], 100)
        self.assertEqual(result['emails_tagged'], 50)
        self.assertEqual(result['emails_deleted'], 10)
        self.assertEqual(result['emails_categorized'], 75)
        self.assertEqual(result['emails_skipped'], 15)


if __name__ == '__main__':
    unittest.main()
