"""
Recommendation Email Notifier Service.

This service sends email notifications to users about domain blocking recommendations,
using an email provider and a formatter to create user-friendly notification emails.
"""
from typing import List

from models.domain_recommendation_models import DomainRecommendation, NotificationResult
from models.email_models import EmailMessage, EmailAddress, EmailSendStatus
from email_providers.base import EmailProviderInterface
from services.interfaces.recommendation_email_formatter_interface import (
    IRecommendationEmailFormatter
)
from services.interfaces.recommendation_email_notifier_interface import (
    IRecommendationEmailNotifier
)


class RecommendationEmailNotifier(IRecommendationEmailNotifier):
    """
    Service for sending domain blocking recommendation email notifications.

    This service coordinates between an email formatter and an email provider
    to send user-friendly notifications about domains that should be blocked.
    """

    def __init__(
        self,
        email_provider: EmailProviderInterface,
        formatter: IRecommendationEmailFormatter
    ):
        """
        Initialize the notifier with dependencies.

        Args:
            email_provider: Email provider for sending emails
            formatter: Formatter for creating email content
        """
        self.email_provider = email_provider
        self.formatter = formatter

    def send_recommendations(
        self,
        recipient_email: str,
        recommendations: List[DomainRecommendation]
    ) -> NotificationResult:
        """
        Send recommendation email notification to a user.

        Args:
            recipient_email: The email address to send the notification to
            recommendations: List of DomainRecommendation objects to include

        Returns:
            NotificationResult indicating success/failure and details

        This method never raises exceptions - all errors are caught and
        returned in the NotificationResult.
        """
        try:
            # If no recommendations, don't send email
            if not recommendations:
                return NotificationResult(
                    success=False,
                    recipient=recipient_email,
                    recommendations_count=0,
                    error_message=None
                )

            # Format the recommendations into HTML and text
            html_body, text_body = self.formatter.format(recommendations)

            # Create the email message
            email_message = EmailMessage(
                sender=EmailAddress(
                    email="info@joseserver.com",
                    name="Cat Emails"
                ),
                to=[EmailAddress(email=recipient_email)],
                subject="Domains recommended to be blocked",
                html=html_body,
                text=text_body
            )

            # Send the email
            response = self.email_provider.send_email(email_message)

            # Check if send was successful
            if response.status == EmailSendStatus.SUCCESS:
                return NotificationResult(
                    success=True,
                    recipient=recipient_email,
                    recommendations_count=len(recommendations),
                    error_message=None
                )
            else:
                # Email provider returned an error response
                error_msg = getattr(response, 'error_message', 'Unknown error')
                return NotificationResult(
                    success=False,
                    recipient=recipient_email,
                    recommendations_count=len(recommendations),
                    error_message=error_msg
                )

        except Exception as e:
            # Catch all exceptions and return failed result
            return NotificationResult(
                success=False,
                recipient=recipient_email,
                recommendations_count=len(recommendations) if recommendations else 0,
                error_message=str(e)
            )
