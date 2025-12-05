"""
Interface for Gantt Chart Generator.

This module defines the contract for generating Mermaid Gantt chart text
from state transition data for email processing run visualizations.
"""
from abc import ABC, abstractmethod
from typing import List


class IGanttChartGenerator(ABC):
    """
    Interface for generating Mermaid Gantt chart text from state transitions.

    This interface defines the contract for converting state transition data
    into valid Mermaid Gantt chart syntax for visualization in the UI.
    """

    @abstractmethod
    def generate(
        self,
        transitions: List,
        title: str,
        include_zero_duration: bool
    ) -> str:
        """
        Generate Mermaid Gantt chart text from state transitions.

        Args:
            transitions: List of StateTransition objects to visualize
            title: Title for the Gantt chart (typically the email address)
            include_zero_duration: If True, include transitions with 0.0 duration
                                   If False, skip transitions with 0.0 duration

        Returns:
            str: Valid Mermaid Gantt chart text with proper formatting
        """
        pass

    @abstractmethod
    def validate_syntax(self, gantt_text: str) -> bool:
        """
        Validate that the generated text follows valid Mermaid Gantt chart syntax.

        Args:
            gantt_text: The Gantt chart text to validate

        Returns:
            bool: True if the syntax is valid, False otherwise
        """
        pass
