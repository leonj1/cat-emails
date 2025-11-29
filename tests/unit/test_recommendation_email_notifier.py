"""
Tests for RecommendationEmailNotifier Service (TDD Red Phase).

This module tests the email notification functionality for domain blocking recommendations.
The service is responsible for:
1. Formatting recommendations into HTML and plain text emails
2. Sending notification emails via the existing MailtrapProvider
3. Gracefully handling send failures without breaking main processing

Based on Gherkin scenarios from the Blocking Recommendations Email Notification feature.
These tests follow TDD Red phase - they will fail until implementation is complete.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Tuple, Optional, Protocol
from dataclasses import dataclass


# ============================================================================
# SECTION 1: NotificationResult Data Model Tests
# ============================================================================

class TestNotificationResultModelExists(unittest.TestCase):
    """
    Tests to verify the NotificationResult data model exists with required fields.

    The NotificationResult model should be defined in:
    models/domain_recommendation_models.py

    Fields required:
    - success (bool): Whether the notification was sent successfully
    - recipient (str): The email address that received the notification
    - recommendations_count (int): Number of recommendations in the notification
    - error_message (Optional[str]): Error details if sending failed
    """

    def test_notification_result_model_exists(self):
        """
        Test that NotificationResult model exists.

        The implementation should define NotificationResult in:
        models/domain_recommendation_models.py
        """
        # Act & Assert
        from models.domain_recommendation_models import NotificationResult

        self.assertTrue(
            hasattr(NotificationResult, '__dataclass_fields__'),
            "NotificationResult should be a dataclass"
        )

    def test_notification_result_has_success_field(self):
        """
        Test that NotificationResult has success field of type bool.
        """
        from models.domain_recommendation_models import NotificationResult

        self.assertIn(
            'success',
            NotificationResult.__dataclass_fields__,
            "NotificationResult should have 'success' field"
        )

        field = NotificationResult.__dataclass_fields__['success']
        self.assertEqual(
            field.type,
            bool,
            "success field should be of type bool"
        )

    def test_notification_result_has_recipient_field(self):
        """
        Test that NotificationResult has recipient field of type str.
        """
        from models.domain_recommendation_models import NotificationResult

        self.assertIn(
            'recipient',
            NotificationResult.__dataclass_fields__,
            "NotificationResult should have 'recipient' field"
        )

        field = NotificationResult.__dataclass_fields__['recipient']
        self.assertEqual(
            field.type,
            str,
            "recipient field should be of type str"
        )

    def test_notification_result_has_recommendations_count_field(self):
        """
        Test that NotificationResult has recommendations_count field of type int.
        """
        from models.domain_recommendation_models import NotificationResult

        self.assertIn(
            'recommendations_count',
            NotificationResult.__dataclass_fields__,
            "NotificationResult should have 'recommendations_count' field"
        )

        field = NotificationResult.__dataclass_fields__['recommendations_count']
        self.assertEqual(
            field.type,
            int,
            "recommendations_count field should be of type int"
        )

    def test_notification_result_has_error_message_field(self):
        """
        Test that NotificationResult has error_message field of type Optional[str].
        """
        from models.domain_recommendation_models import NotificationResult

        self.assertIn(
            'error_message',
            NotificationResult.__dataclass_fields__,
            "NotificationResult should have 'error_message' field"
        )

        field = NotificationResult.__dataclass_fields__['error_message']
        # Optional[str] is represented as Union[str, None] or Optional[str]
        field_type_str = str(field.type)
        self.assertTrue(
            'str' in field_type_str and ('None' in field_type_str or 'Optional' in field_type_str),
            f"error_message field should be of type Optional[str], got {field.type}"
        )


class TestNotificationResultCreation(unittest.TestCase):
    """
    Tests for creating NotificationResult instances with valid data.
    """

    def test_create_successful_notification_result(self):
        """
        Test creating a successful NotificationResult.

        When notification is sent successfully:
        - success should be True
        - recipient should be the email address
        - recommendations_count should be the count
        - error_message should be None
        """
        from models.domain_recommendation_models import NotificationResult

        # Arrange
        recipient = "user@gmail.com"
        recommendations_count = 5

        # Act
        result = NotificationResult(
            success=True,
            recipient=recipient,
            recommendations_count=recommendations_count,
            error_message=None
        )

        # Assert
        expected = {
            "success": True,
            "recipient": "user@gmail.com",
            "recommendations_count": 5,
            "error_message": None
        }
        actual = {
            "success": result.success,
            "recipient": result.recipient,
            "recommendations_count": result.recommendations_count,
            "error_message": result.error_message
        }
        self.assertEqual(
            actual,
            expected,
            f"Expected {expected}, got {actual}"
        )

    def test_create_failed_notification_result(self):
        """
        Test creating a failed NotificationResult.

        When notification fails to send:
        - success should be False
        - error_message should contain the failure reason
        """
        from models.domain_recommendation_models import NotificationResult

        # Arrange
        recipient = "user@gmail.com"
        recommendations_count = 5
        error_message = "Connection refused"

        # Act
        result = NotificationResult(
            success=False,
            recipient=recipient,
            recommendations_count=recommendations_count,
            error_message=error_message
        )

        # Assert
        expected = {
            "success": False,
            "recipient": "user@gmail.com",
            "recommendations_count": 5,
            "error_message": "Connection refused"
        }
        actual = {
            "success": result.success,
            "recipient": result.recipient,
            "recommendations_count": result.recommendations_count,
            "error_message": result.error_message
        }
        self.assertEqual(
            actual,
            expected,
            f"Expected {expected}, got {actual}"
        )

    def test_notification_result_is_immutable(self):
        """
        Test that NotificationResult is immutable (frozen dataclass).

        Once created, the fields should not be modifiable.
        """
        from models.domain_recommendation_models import NotificationResult

        result = NotificationResult(
            success=True,
            recipient="user@gmail.com",
            recommendations_count=5,
            error_message=None
        )

        # Act & Assert - trying to modify should raise an error
        with self.assertRaises(AttributeError):
            result.success = False

        with self.assertRaises(AttributeError):
            result.recipient = "other@gmail.com"


# ============================================================================
# SECTION 2: IRecommendationEmailFormatter Interface Tests
# ============================================================================

class TestIRecommendationEmailFormatterInterface(unittest.TestCase):
    """
    Tests to verify the IRecommendationEmailFormatter interface exists
    and has the correct methods.

    The interface should define:
    - format(recommendations) -> Tuple[str, str] (html_body, text_body)
    """

    def test_interface_exists(self):
        """
        Test that IRecommendationEmailFormatter interface exists.

        The implementation should define an interface in:
        services/interfaces/recommendation_email_formatter_interface.py
        """
        # Act & Assert
        from services.interfaces.recommendation_email_formatter_interface import (
            IRecommendationEmailFormatter
        )

        # Verify it's an abstract class or protocol
        import inspect
        self.assertTrue(
            inspect.isabstract(IRecommendationEmailFormatter) or
            hasattr(IRecommendationEmailFormatter, '__protocol_attrs__'),
            "IRecommendationEmailFormatter should be an abstract class or Protocol"
        )

    def test_interface_has_format_method(self):
        """
        Test that interface defines format method.

        The format method should:
        - Accept recommendations (List[DomainRecommendation])
        - Return Tuple[str, str] containing (html_body, text_body)
        """
        from services.interfaces.recommendation_email_formatter_interface import (
            IRecommendationEmailFormatter
        )
        import inspect

        # Get all methods including those from Protocol
        methods = []
        for name, _ in inspect.getmembers(
            IRecommendationEmailFormatter,
            predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x)
        ):
            methods.append(name)

        self.assertIn(
            "format",
            methods,
            "IRecommendationEmailFormatter should have format method"
        )


# ============================================================================
# SECTION 3: IRecommendationEmailNotifier Interface Tests
# ============================================================================

class TestIRecommendationEmailNotifierInterface(unittest.TestCase):
    """
    Tests to verify the IRecommendationEmailNotifier interface exists
    and has the correct methods.

    The interface should define:
    - send_recommendations(recipient_email, recommendations) -> NotificationResult
    """

    def test_interface_exists(self):
        """
        Test that IRecommendationEmailNotifier interface exists.

        The implementation should define an interface in:
        services/interfaces/recommendation_email_notifier_interface.py
        """
        # Act & Assert
        from services.interfaces.recommendation_email_notifier_interface import (
            IRecommendationEmailNotifier
        )

        # Verify it's an abstract class or protocol
        import inspect
        self.assertTrue(
            inspect.isabstract(IRecommendationEmailNotifier) or
            hasattr(IRecommendationEmailNotifier, '__protocol_attrs__'),
            "IRecommendationEmailNotifier should be an abstract class or Protocol"
        )

    def test_interface_has_send_recommendations_method(self):
        """
        Test that interface defines send_recommendations method.

        The send_recommendations method should:
        - Accept recipient_email (str) and recommendations (List[DomainRecommendation])
        - Return NotificationResult
        """
        from services.interfaces.recommendation_email_notifier_interface import (
            IRecommendationEmailNotifier
        )
        import inspect

        methods = []
        for name, _ in inspect.getmembers(
            IRecommendationEmailNotifier,
            predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x)
        ):
            methods.append(name)

        self.assertIn(
            "send_recommendations",
            methods,
            "IRecommendationEmailNotifier should have send_recommendations method"
        )


# ============================================================================
# SECTION 4: RecommendationEmailFormatter Implementation Tests
# ============================================================================

class TestRecommendationEmailFormatterExists(unittest.TestCase):
    """
    Tests for RecommendationEmailFormatter class existence and instantiation.
    """

    def test_formatter_class_exists(self):
        """
        Test that RecommendationEmailFormatter class exists.

        The implementation should be in:
        services/recommendation_email_formatter.py
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )

        self.assertTrue(
            callable(RecommendationEmailFormatter),
            "RecommendationEmailFormatter should be a callable class"
        )

    def test_formatter_can_be_instantiated(self):
        """
        Test that RecommendationEmailFormatter can be instantiated.
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )

        # Act
        formatter = RecommendationEmailFormatter()

        # Assert
        self.assertIsNotNone(formatter)

    def test_formatter_implements_interface(self):
        """
        Test that RecommendationEmailFormatter implements IRecommendationEmailFormatter.
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )
        from services.interfaces.recommendation_email_formatter_interface import (
            IRecommendationEmailFormatter
        )

        formatter = RecommendationEmailFormatter()

        self.assertIsInstance(
            formatter,
            IRecommendationEmailFormatter,
            "RecommendationEmailFormatter should implement IRecommendationEmailFormatter"
        )


class TestRecommendationEmailFormatterFormatMethod(unittest.TestCase):
    """
    Scenario: Email notification includes all recommendation details

    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email                | category      | count |
      | spam@marketing.com          | Marketing     | 10    |
      | ads@advertising.com         | Advertising   | 5     |
    When the process_account function runs for "user@gmail.com"
    Then a notification email should be sent to "user@gmail.com"
    And the email should contain domain "marketing.com" with 10 emails
    And the email should contain domain "advertising.com" with 5 emails
    And the email should group domains by category
    """

    def test_format_returns_tuple_of_two_strings(self):
        """
        Test that format method returns a tuple of (html_body, text_body).
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )
        from models.domain_recommendation_models import DomainRecommendation

        # Arrange
        formatter = RecommendationEmailFormatter()
        recommendations = [
            DomainRecommendation(domain="marketing.com", category="Marketing", count=10)
        ]

        # Act
        result = formatter.format(recommendations)

        # Assert
        self.assertIsInstance(
            result,
            tuple,
            f"format() should return a tuple, got {type(result)}"
        )
        self.assertEqual(
            len(result),
            2,
            f"format() should return 2 elements (html, text), got {len(result)}"
        )
        self.assertIsInstance(result[0], str, "First element should be HTML string")
        self.assertIsInstance(result[1], str, "Second element should be text string")

    def test_format_html_contains_domain_name(self):
        """
        Test that HTML body contains the domain name.
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )
        from models.domain_recommendation_models import DomainRecommendation

        # Arrange
        formatter = RecommendationEmailFormatter()
        recommendations = [
            DomainRecommendation(domain="marketing.com", category="Marketing", count=10)
        ]

        # Act
        html_body, _ = formatter.format(recommendations)

        # Assert
        self.assertIn(
            "marketing.com",
            html_body,
            "HTML body should contain the domain name"
        )

    def test_format_html_contains_email_count(self):
        """
        Test that HTML body contains the email count.
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )
        from models.domain_recommendation_models import DomainRecommendation

        # Arrange
        formatter = RecommendationEmailFormatter()
        recommendations = [
            DomainRecommendation(domain="marketing.com", category="Marketing", count=10)
        ]

        # Act
        html_body, _ = formatter.format(recommendations)

        # Assert
        self.assertIn(
            "10",
            html_body,
            "HTML body should contain the email count"
        )

    def test_format_text_contains_domain_name(self):
        """
        Test that plain text body contains the domain name.
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )
        from models.domain_recommendation_models import DomainRecommendation

        # Arrange
        formatter = RecommendationEmailFormatter()
        recommendations = [
            DomainRecommendation(domain="advertising.com", category="Advertising", count=5)
        ]

        # Act
        _, text_body = formatter.format(recommendations)

        # Assert
        self.assertIn(
            "advertising.com",
            text_body,
            "Text body should contain the domain name"
        )

    def test_format_text_contains_email_count(self):
        """
        Test that plain text body contains the email count.
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )
        from models.domain_recommendation_models import DomainRecommendation

        # Arrange
        formatter = RecommendationEmailFormatter()
        recommendations = [
            DomainRecommendation(domain="advertising.com", category="Advertising", count=5)
        ]

        # Act
        _, text_body = formatter.format(recommendations)

        # Assert
        self.assertIn(
            "5",
            text_body,
            "Text body should contain the email count"
        )

    def test_format_groups_domains_by_category_in_html(self):
        """
        Test that HTML body groups domains by category.

        Given multiple recommendations with different categories,
        the formatter should organize them by category.
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )
        from models.domain_recommendation_models import DomainRecommendation

        # Arrange
        formatter = RecommendationEmailFormatter()
        recommendations = [
            DomainRecommendation(domain="spam1.com", category="Marketing", count=10),
            DomainRecommendation(domain="spam2.com", category="Marketing", count=8),
            DomainRecommendation(domain="ads1.com", category="Advertising", count=5),
            DomainRecommendation(domain="ads2.com", category="Advertising", count=3),
        ]

        # Act
        html_body, _ = formatter.format(recommendations)

        # Assert - Both categories should appear
        self.assertIn(
            "Marketing",
            html_body,
            "HTML body should contain 'Marketing' category header"
        )
        self.assertIn(
            "Advertising",
            html_body,
            "HTML body should contain 'Advertising' category header"
        )

    def test_format_groups_domains_by_category_in_text(self):
        """
        Test that plain text body groups domains by category.
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )
        from models.domain_recommendation_models import DomainRecommendation

        # Arrange
        formatter = RecommendationEmailFormatter()
        recommendations = [
            DomainRecommendation(domain="spam1.com", category="Marketing", count=10),
            DomainRecommendation(domain="ads1.com", category="Advertising", count=5),
        ]

        # Act
        _, text_body = formatter.format(recommendations)

        # Assert - Both categories should appear
        self.assertIn(
            "Marketing",
            text_body,
            "Text body should contain 'Marketing' category header"
        )
        self.assertIn(
            "Advertising",
            text_body,
            "Text body should contain 'Advertising' category header"
        )

    def test_format_html_includes_multiple_domains(self):
        """
        Test that HTML body includes all domains from the recommendations.

        Scenario: Email notification includes all recommendation details
        And the email should contain domain "marketing.com" with 10 emails
        And the email should contain domain "advertising.com" with 5 emails
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )
        from models.domain_recommendation_models import DomainRecommendation

        # Arrange
        formatter = RecommendationEmailFormatter()
        recommendations = [
            DomainRecommendation(domain="marketing.com", category="Marketing", count=10),
            DomainRecommendation(domain="advertising.com", category="Advertising", count=5),
        ]

        # Act
        html_body, _ = formatter.format(recommendations)

        # Assert
        self.assertIn("marketing.com", html_body)
        self.assertIn("10", html_body)
        self.assertIn("advertising.com", html_body)
        self.assertIn("5", html_body)

    def test_format_text_includes_multiple_domains(self):
        """
        Test that plain text body includes all domains from the recommendations.
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )
        from models.domain_recommendation_models import DomainRecommendation

        # Arrange
        formatter = RecommendationEmailFormatter()
        recommendations = [
            DomainRecommendation(domain="marketing.com", category="Marketing", count=10),
            DomainRecommendation(domain="advertising.com", category="Advertising", count=5),
        ]

        # Act
        _, text_body = formatter.format(recommendations)

        # Assert
        self.assertIn("marketing.com", text_body)
        self.assertIn("10", text_body)
        self.assertIn("advertising.com", text_body)
        self.assertIn("5", text_body)

    def test_format_empty_recommendations_returns_appropriate_message(self):
        """
        Test that formatting empty recommendations returns appropriate content.

        When there are no recommendations, the formatter should still return
        valid HTML and text bodies, potentially with a "no recommendations" message.
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )

        # Arrange
        formatter = RecommendationEmailFormatter()
        recommendations = []

        # Act
        html_body, text_body = formatter.format(recommendations)

        # Assert - Should return valid strings
        self.assertIsInstance(html_body, str)
        self.assertIsInstance(text_body, str)
        # Both should have some content (even if just indicating no recommendations)
        self.assertTrue(len(html_body) > 0, "HTML body should not be empty")
        self.assertTrue(len(text_body) > 0, "Text body should not be empty")


class TestRecommendationEmailFormatterHtmlStructure(unittest.TestCase):
    """
    Scenario: Email notification has both HTML and plain text versions

    Given the blocked domains list is empty
    And the inbox contains emails from "spam@example.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the notification email should include an HTML body
    And the notification email should include a plain text body
    And both bodies should contain the recommendation details
    """

    def test_html_body_contains_html_tags(self):
        """
        Test that HTML body contains proper HTML structure.
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )
        from models.domain_recommendation_models import DomainRecommendation

        # Arrange
        formatter = RecommendationEmailFormatter()
        recommendations = [
            DomainRecommendation(domain="example.com", category="Marketing", count=5)
        ]

        # Act
        html_body, _ = formatter.format(recommendations)

        # Assert - Should have basic HTML structure
        self.assertTrue(
            "<" in html_body and ">" in html_body,
            "HTML body should contain HTML tags"
        )

    def test_text_body_is_plain_text(self):
        """
        Test that plain text body does not contain HTML tags.
        """
        from services.recommendation_email_formatter import (
            RecommendationEmailFormatter
        )
        from models.domain_recommendation_models import DomainRecommendation

        # Arrange
        formatter = RecommendationEmailFormatter()
        recommendations = [
            DomainRecommendation(domain="example.com", category="Marketing", count=5)
        ]

        # Act
        _, text_body = formatter.format(recommendations)

        # Assert - Should not have HTML tags
        import re
        html_tag_pattern = re.compile(r'<[^>]+>')
        matches = html_tag_pattern.findall(text_body)
        self.assertEqual(
            len(matches),
            0,
            f"Text body should not contain HTML tags, found: {matches}"
        )


# ============================================================================
# SECTION 5: RecommendationEmailNotifier Implementation Tests
# ============================================================================

class TestRecommendationEmailNotifierExists(unittest.TestCase):
    """
    Tests for RecommendationEmailNotifier class existence and instantiation.
    """

    def test_notifier_class_exists(self):
        """
        Test that RecommendationEmailNotifier class exists.

        The implementation should be in:
        services/recommendation_email_notifier.py
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )

        self.assertTrue(
            callable(RecommendationEmailNotifier),
            "RecommendationEmailNotifier should be a callable class"
        )

    def test_notifier_can_be_instantiated_with_dependencies(self):
        """
        Test that RecommendationEmailNotifier can be instantiated with required dependencies.

        The notifier requires:
        - email_provider: Interface for sending emails (IEmailProvider/EmailProviderInterface)
        - formatter: Interface for formatting recommendations (IRecommendationEmailFormatter)
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )

        # Arrange - Create mock dependencies
        mock_email_provider = Mock()
        mock_formatter = Mock()

        # Act
        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        # Assert
        self.assertIsNotNone(notifier)

    def test_notifier_implements_interface(self):
        """
        Test that RecommendationEmailNotifier implements IRecommendationEmailNotifier.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from services.interfaces.recommendation_email_notifier_interface import (
            IRecommendationEmailNotifier
        )

        mock_email_provider = Mock()
        mock_formatter = Mock()

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        self.assertIsInstance(
            notifier,
            IRecommendationEmailNotifier,
            "RecommendationEmailNotifier should implement IRecommendationEmailNotifier"
        )


class TestRecommendationEmailNotifierSendRecommendations(unittest.TestCase):
    """
    Scenario: Generate recommendations for unblocked Marketing domain

    Given the blocked domains list is empty
    And the inbox contains emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "marketing-spam.com" with category "Marketing"
    And a notification email should be sent to "user@gmail.com"
    And the notification email subject should be "Domains recommended to be blocked"
    """

    def test_send_recommendations_returns_notification_result(self):
        """
        Test that send_recommendations returns a NotificationResult.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import (
            DomainRecommendation,
            NotificationResult
        )
        from models.email_models import EmailSendResponse, EmailSendStatus

        # Arrange
        mock_email_provider = Mock()
        mock_email_provider.send_email.return_value = EmailSendResponse(
            status=EmailSendStatus.SUCCESS,
            message_id="test-123",
            provider="mailtrap"
        )

        mock_formatter = Mock()
        mock_formatter.format.return_value = ("<html>test</html>", "test")

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = [
            DomainRecommendation(domain="marketing-spam.com", category="Marketing", count=5)
        ]

        # Act
        result = notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert
        self.assertIsInstance(
            result,
            NotificationResult,
            f"send_recommendations should return NotificationResult, got {type(result)}"
        )

    def test_send_recommendations_with_correct_subject(self):
        """
        Test that send_recommendations sends email with correct subject.

        The notification email subject should be "Domains recommended to be blocked"
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import DomainRecommendation
        from models.email_models import EmailSendResponse, EmailSendStatus

        # Arrange
        mock_email_provider = Mock()
        mock_email_provider.send_email.return_value = EmailSendResponse(
            status=EmailSendStatus.SUCCESS,
            message_id="test-123",
            provider="mailtrap"
        )

        mock_formatter = Mock()
        mock_formatter.format.return_value = ("<html>test</html>", "test")

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = [
            DomainRecommendation(domain="marketing-spam.com", category="Marketing", count=5)
        ]

        # Act
        notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert
        mock_email_provider.send_email.assert_called_once()
        call_args = mock_email_provider.send_email.call_args
        email_message = call_args[0][0]  # First positional argument

        self.assertEqual(
            email_message.subject,
            "Domains recommended to be blocked",
            f"Subject should be 'Domains recommended to be blocked', got '{email_message.subject}'"
        )

    def test_send_recommendations_uses_formatter(self):
        """
        Test that send_recommendations calls the formatter with recommendations.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import DomainRecommendation
        from models.email_models import EmailSendResponse, EmailSendStatus

        # Arrange
        mock_email_provider = Mock()
        mock_email_provider.send_email.return_value = EmailSendResponse(
            status=EmailSendStatus.SUCCESS,
            message_id="test-123",
            provider="mailtrap"
        )

        mock_formatter = Mock()
        mock_formatter.format.return_value = ("<html>formatted</html>", "formatted text")

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = [
            DomainRecommendation(domain="marketing-spam.com", category="Marketing", count=5)
        ]

        # Act
        notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert
        mock_formatter.format.assert_called_once_with(recommendations)

    def test_send_recommendations_sends_email_to_correct_recipient(self):
        """
        Test that send_recommendations sends email to the correct recipient.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import DomainRecommendation
        from models.email_models import EmailSendResponse, EmailSendStatus

        # Arrange
        mock_email_provider = Mock()
        mock_email_provider.send_email.return_value = EmailSendResponse(
            status=EmailSendStatus.SUCCESS,
            message_id="test-123",
            provider="mailtrap"
        )

        mock_formatter = Mock()
        mock_formatter.format.return_value = ("<html>test</html>", "test")

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = [
            DomainRecommendation(domain="marketing-spam.com", category="Marketing", count=5)
        ]

        # Act
        notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert
        mock_email_provider.send_email.assert_called_once()
        call_args = mock_email_provider.send_email.call_args
        email_message = call_args[0][0]

        # Check the recipient
        recipient_emails = [addr.email for addr in email_message.to]
        self.assertIn(
            "user@gmail.com",
            recipient_emails,
            f"Email should be sent to 'user@gmail.com', got {recipient_emails}"
        )

    def test_send_recommendations_includes_html_and_text_bodies(self):
        """
        Test that the sent email includes both HTML and plain text bodies.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import DomainRecommendation
        from models.email_models import EmailSendResponse, EmailSendStatus

        # Arrange
        mock_email_provider = Mock()
        mock_email_provider.send_email.return_value = EmailSendResponse(
            status=EmailSendStatus.SUCCESS,
            message_id="test-123",
            provider="mailtrap"
        )

        mock_formatter = Mock()
        html_content = "<html><body>Recommendations</body></html>"
        text_content = "Recommendations in plain text"
        mock_formatter.format.return_value = (html_content, text_content)

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = [
            DomainRecommendation(domain="marketing-spam.com", category="Marketing", count=5)
        ]

        # Act
        notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert
        mock_email_provider.send_email.assert_called_once()
        call_args = mock_email_provider.send_email.call_args
        email_message = call_args[0][0]

        self.assertEqual(
            email_message.html,
            html_content,
            "Email should include HTML body from formatter"
        )
        self.assertEqual(
            email_message.text,
            text_content,
            "Email should include text body from formatter"
        )

    def test_send_recommendations_success_returns_success_result(self):
        """
        Test that successful send returns NotificationResult with success=True.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import (
            DomainRecommendation,
            NotificationResult
        )
        from models.email_models import EmailSendResponse, EmailSendStatus

        # Arrange
        mock_email_provider = Mock()
        mock_email_provider.send_email.return_value = EmailSendResponse(
            status=EmailSendStatus.SUCCESS,
            message_id="test-123",
            provider="mailtrap"
        )

        mock_formatter = Mock()
        mock_formatter.format.return_value = ("<html>test</html>", "test")

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = [
            DomainRecommendation(domain="marketing-spam.com", category="Marketing", count=5)
        ]

        # Act
        result = notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert
        expected = {
            "success": True,
            "recipient": "user@gmail.com",
            "recommendations_count": 1,
            "error_message": None
        }
        actual = {
            "success": result.success,
            "recipient": result.recipient,
            "recommendations_count": result.recommendations_count,
            "error_message": result.error_message
        }
        self.assertEqual(
            actual,
            expected,
            f"Expected {expected}, got {actual}"
        )


class TestRecommendationEmailNotifierErrorHandling(unittest.TestCase):
    """
    Scenario: Email notification failure does not break main processing

    Given the blocked domains list is empty
    And the inbox contains emails from "spam@marketing.com" categorized as "Marketing"
    And the email notification service is failing
    When the process_account function runs for "user@gmail.com"
    Then the processing should complete successfully
    And the response "success" should be true
    And "notification_sent" should be false
    And "notification_error" should contain the failure reason
    And the recommendations should still be included in the response
    """

    def test_send_failure_returns_failed_notification_result(self):
        """
        Test that when email sending fails, a failed NotificationResult is returned.

        The notifier should NOT throw exceptions - always return a result.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import (
            DomainRecommendation,
            NotificationResult
        )
        from models.email_models import EmailErrorResponse, EmailSendStatus

        # Arrange
        mock_email_provider = Mock()
        mock_email_provider.send_email.return_value = EmailErrorResponse(
            status=EmailSendStatus.FAILED,
            error_code="CONNECTION_ERROR",
            error_message="Connection refused",
            provider="mailtrap"
        )

        mock_formatter = Mock()
        mock_formatter.format.return_value = ("<html>test</html>", "test")

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = [
            DomainRecommendation(domain="marketing.com", category="Marketing", count=5)
        ]

        # Act
        result = notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert
        self.assertIsInstance(result, NotificationResult)
        self.assertFalse(
            result.success,
            "send_recommendations should return success=False when send fails"
        )
        self.assertEqual(result.recipient, "user@gmail.com")
        self.assertIsNotNone(
            result.error_message,
            "error_message should contain the failure reason"
        )
        self.assertIn(
            "Connection refused",
            result.error_message,
            f"error_message should contain 'Connection refused', got '{result.error_message}'"
        )

    def test_send_exception_returns_failed_notification_result(self):
        """
        Test that when email sending throws an exception, a failed NotificationResult is returned.

        The notifier should catch exceptions and return a result, NOT propagate exceptions.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import (
            DomainRecommendation,
            NotificationResult
        )

        # Arrange
        mock_email_provider = Mock()
        mock_email_provider.send_email.side_effect = Exception("Network timeout")

        mock_formatter = Mock()
        mock_formatter.format.return_value = ("<html>test</html>", "test")

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = [
            DomainRecommendation(domain="marketing.com", category="Marketing", count=5)
        ]

        # Act - Should NOT raise an exception
        result = notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert
        self.assertIsInstance(
            result,
            NotificationResult,
            "Should return NotificationResult even when exception occurs"
        )
        self.assertFalse(result.success)
        self.assertIn(
            "Network timeout",
            result.error_message,
            f"error_message should contain exception message, got '{result.error_message}'"
        )

    def test_formatter_exception_returns_failed_notification_result(self):
        """
        Test that when formatter throws an exception, a failed NotificationResult is returned.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import (
            DomainRecommendation,
            NotificationResult
        )

        # Arrange
        mock_email_provider = Mock()
        mock_formatter = Mock()
        mock_formatter.format.side_effect = Exception("Formatting error")

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = [
            DomainRecommendation(domain="marketing.com", category="Marketing", count=5)
        ]

        # Act - Should NOT raise an exception
        result = notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert
        self.assertIsInstance(result, NotificationResult)
        self.assertFalse(result.success)
        self.assertIn(
            "Formatting error",
            result.error_message,
            f"error_message should contain formatter error, got '{result.error_message}'"
        )


class TestRecommendationEmailNotifierNoSendCases(unittest.TestCase):
    """
    Scenario: No recommendations when all domains are already blocked

    Given the blocked domains list contains:
      | domain              |
      | marketing-spam.com  |
      | ads-network.io      |
    And the inbox contains emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    And the inbox contains emails from "promo@ads-network.io" categorized as "Advertising"
    When the process_account function runs for "user@gmail.com"
    Then the "recommended_domains_to_block" should be an empty list
    And no notification email should be sent
    And "notification_sent" should be false
    """

    def test_empty_recommendations_does_not_send_email(self):
        """
        Test that when recommendations list is empty, no email is sent.

        When there are no recommendations (e.g., all domains already blocked),
        the notifier should not attempt to send an email.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import NotificationResult

        # Arrange
        mock_email_provider = Mock()
        mock_formatter = Mock()

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = []  # Empty list - no recommendations

        # Act
        result = notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert
        mock_email_provider.send_email.assert_not_called()
        mock_formatter.format.assert_not_called()

        self.assertIsInstance(result, NotificationResult)
        self.assertFalse(
            result.success,
            "Empty recommendations should return success=False (no email sent)"
        )
        self.assertEqual(result.recommendations_count, 0)


class TestRecommendationEmailNotifierSingleEmail(unittest.TestCase):
    """
    Scenario: Single email generates recommendation

    Given the blocked domains list is empty
    And the inbox contains exactly 1 email from "spam@single-sender.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include domain "single-sender.com" with count 1
    And a notification email should be sent
    """

    def test_single_recommendation_sends_email(self):
        """
        Test that a single recommendation triggers email notification.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import (
            DomainRecommendation,
            NotificationResult
        )
        from models.email_models import EmailSendResponse, EmailSendStatus

        # Arrange
        mock_email_provider = Mock()
        mock_email_provider.send_email.return_value = EmailSendResponse(
            status=EmailSendStatus.SUCCESS,
            message_id="test-123",
            provider="mailtrap"
        )

        mock_formatter = Mock()
        mock_formatter.format.return_value = ("<html>test</html>", "test")

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = [
            DomainRecommendation(domain="single-sender.com", category="Marketing", count=1)
        ]

        # Act
        result = notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert
        mock_email_provider.send_email.assert_called_once()
        self.assertTrue(result.success)
        self.assertEqual(result.recommendations_count, 1)


class TestRecommendationEmailNotifierMultipleRecommendations(unittest.TestCase):
    """
    Test handling of multiple recommendations in a single notification.
    """

    def test_multiple_recommendations_counts_correctly(self):
        """
        Test that recommendations_count reflects the number of recommendations.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import (
            DomainRecommendation,
            NotificationResult
        )
        from models.email_models import EmailSendResponse, EmailSendStatus

        # Arrange
        mock_email_provider = Mock()
        mock_email_provider.send_email.return_value = EmailSendResponse(
            status=EmailSendStatus.SUCCESS,
            message_id="test-123",
            provider="mailtrap"
        )

        mock_formatter = Mock()
        mock_formatter.format.return_value = ("<html>test</html>", "test")

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = [
            DomainRecommendation(domain="spam1.com", category="Marketing", count=10),
            DomainRecommendation(domain="spam2.com", category="Advertising", count=5),
            DomainRecommendation(domain="spam3.com", category="Wants-Money", count=3),
        ]

        # Act
        result = notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert
        self.assertEqual(
            result.recommendations_count,
            3,
            f"recommendations_count should be 3, got {result.recommendations_count}"
        )


# ============================================================================
# SECTION 6: Integration Tests (with mocked MailtrapProvider)
# ============================================================================

class TestRecommendationEmailNotifierWithMailtrapProvider(unittest.TestCase):
    """
    Integration tests verifying the notifier works with MailtrapProvider interface.

    These tests verify that the RecommendationEmailNotifier correctly uses
    the MailtrapProvider's send_email method signature.
    """

    def test_notifier_works_with_mailtrap_provider_interface(self):
        """
        Test that the notifier creates an EmailMessage compatible with MailtrapProvider.
        """
        from services.recommendation_email_notifier import (
            RecommendationEmailNotifier
        )
        from models.domain_recommendation_models import DomainRecommendation
        from models.email_models import (
            EmailMessage,
            EmailAddress,
            EmailSendResponse,
            EmailSendStatus
        )

        # Arrange
        mock_email_provider = Mock()
        mock_email_provider.send_email.return_value = EmailSendResponse(
            status=EmailSendStatus.SUCCESS,
            message_id="test-123",
            provider="mailtrap"
        )

        mock_formatter = Mock()
        mock_formatter.format.return_value = ("<html>test</html>", "test")

        notifier = RecommendationEmailNotifier(
            email_provider=mock_email_provider,
            formatter=mock_formatter
        )

        recommendations = [
            DomainRecommendation(domain="test.com", category="Marketing", count=5)
        ]

        # Act
        notifier.send_recommendations("user@gmail.com", recommendations)

        # Assert - Verify the EmailMessage structure
        mock_email_provider.send_email.assert_called_once()
        call_args = mock_email_provider.send_email.call_args
        email_message = call_args[0][0]

        # Verify it's an EmailMessage
        self.assertIsInstance(email_message, EmailMessage)

        # Verify required fields are set
        self.assertIsNotNone(email_message.sender)
        self.assertIsNotNone(email_message.to)
        self.assertIsNotNone(email_message.subject)
        self.assertTrue(
            email_message.html or email_message.text,
            "EmailMessage must have either html or text content"
        )


if __name__ == '__main__':
    unittest.main()
