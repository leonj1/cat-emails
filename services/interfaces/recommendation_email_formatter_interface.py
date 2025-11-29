"""
Recommendation Email Formatter Interface.

This interface defines the contract for formatting domain blocking recommendations
into email content (both HTML and plain text).
"""
from typing import List, Tuple
from typing_extensions import Protocol, runtime_checkable

from models.domain_recommendation_models import DomainRecommendation


@runtime_checkable
class IRecommendationEmailFormatter(Protocol):
    """
    Protocol interface for formatting recommendation emails.

    This interface defines the contract for converting a list of domain
    recommendations into formatted email content suitable for sending.
    """

    def format(self, recommendations: List[DomainRecommendation]) -> Tuple[str, str]:
        """
        Format recommendations into HTML and plain text email content.

        Args:
            recommendations: List of DomainRecommendation objects to format

        Returns:
            Tuple containing (html_body, text_body) where:
            - html_body: HTML formatted content with tables and styling
            - text_body: Plain text formatted content

        The formatter should group recommendations by category and present
        them in a clear, readable format.
        """
        ...
