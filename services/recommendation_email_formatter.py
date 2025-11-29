"""
Recommendation Email Formatter Service.

This service formats domain blocking recommendations into HTML and plain text
email content for user notifications.
"""
from typing import List, Tuple, Dict
from collections import defaultdict

from models.domain_recommendation_models import DomainRecommendation
from services.interfaces.recommendation_email_formatter_interface import (
    IRecommendationEmailFormatter
)


class RecommendationEmailFormatter(IRecommendationEmailFormatter):
    """
    Formatter for converting domain recommendations into email content.

    This service groups recommendations by category and formats them into
    both HTML (with tables) and plain text versions for email sending.
    """

    def format(self, recommendations: List[DomainRecommendation]) -> Tuple[str, str]:
        """
        Format recommendations into HTML and plain text email content.

        Args:
            recommendations: List of DomainRecommendation objects to format

        Returns:
            Tuple containing (html_body, text_body)
        """
        # Group recommendations by category
        grouped = self._group_by_category(recommendations)

        # Generate HTML and text versions
        html_body = self._generate_html(grouped)
        text_body = self._generate_text(grouped)

        return html_body, text_body

    def _group_by_category(
        self,
        recommendations: List[DomainRecommendation]
    ) -> Dict[str, List[DomainRecommendation]]:
        """
        Group recommendations by category.

        Args:
            recommendations: List of recommendations to group

        Returns:
            Dictionary mapping category names to lists of recommendations
        """
        grouped = defaultdict(list)
        for rec in recommendations:
            grouped[rec.category].append(rec)
        return dict(grouped)

    def _generate_html(
        self,
        grouped: Dict[str, List[DomainRecommendation]]
    ) -> str:
        """
        Generate HTML formatted email body.

        Args:
            grouped: Recommendations grouped by category

        Returns:
            HTML string with styled tables
        """
        if not grouped:
            return "<h1>Domain Blocking Recommendations</h1><p>No recommendations at this time.</p>"

        html = "<h1>Domain Blocking Recommendations</h1>\n"

        for category, recs in sorted(grouped.items()):
            html += f"<h2>{category} ({len(recs)} domains)</h2>\n"
            html += "<table><tr><th>Domain</th><th>Emails</th></tr>\n"

            for rec in recs:
                html += f"<tr><td>{rec.domain}</td><td>{rec.count}</td></tr>\n"

            html += "</table>\n"

        return html

    def _generate_text(
        self,
        grouped: Dict[str, List[DomainRecommendation]]
    ) -> str:
        """
        Generate plain text formatted email body.

        Args:
            grouped: Recommendations grouped by category

        Returns:
            Plain text string with readable formatting
        """
        if not grouped:
            return "Domain Blocking Recommendations\n\nNo recommendations at this time."

        text = "Domain Blocking Recommendations\n\n"

        for category, recs in sorted(grouped.items()):
            text += f"{category} ({len(recs)} domains)\n"
            text += "-" * 40 + "\n"

            for rec in recs:
                text += f"{rec.domain}: {rec.count} emails\n"

            text += "\n"

        return text
