"""
Recommendation Email Notifier Interface.

This interface defines the contract for sending email notifications about
domain blocking recommendations to users.
"""
from typing import List
from typing_extensions import Protocol, runtime_checkable

from models.domain_recommendation_models import DomainRecommendation, NotificationResult


@runtime_checkable
class IRecommendationEmailNotifier(Protocol):
    """
    Protocol interface for sending recommendation email notifications.

    This interface defines the contract for notifying users via email
    about domains that are recommended for blocking based on email analysis.
    """

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

        The implementation should:
        - Format the recommendations into a user-friendly email
        - Send both HTML and plain text versions
        - Handle errors gracefully without raising exceptions
        - Return success=False with no email sent if recommendations is empty
        """
        ...
