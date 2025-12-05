"""
Tests for Gantt Chart Generator Core (TDD Red Phase).

This module tests the Gantt chart text generation functionality that converts
state transition data into Mermaid Gantt chart syntax for UI visualization.

Components tested:
1. IGanttChartGenerator Interface - Contract for chart generation operations
2. GanttChartGenerator Implementation - Mermaid syntax generation

Based on Gherkin scenarios from tests/bdd/gantt_chart_generator_core.feature:
- Generate Gantt chart for a completed processing run
- Generate Gantt chart with proper date format
- Generate Gantt chart with section groupings
- Generate Gantt chart with duration formatting
- Gantt chart text is valid Mermaid syntax

These tests follow TDD Red phase - they will fail until implementation is complete.
"""
import unittest
from datetime import datetime, timezone
from typing import List


# ============================================================================
# SECTION 1: IGanttChartGenerator Interface Tests
# ============================================================================

class TestIGanttChartGeneratorInterfaceExists(unittest.TestCase):
    """
    Tests to verify the IGanttChartGenerator interface exists
    and has the correct methods.

    The interface should define:
    - generate(transitions, title, include_zero_duration) -> str
    - validate_syntax(gantt_text) -> bool
    """

    def test_interface_exists(self):
        """
        Test that IGanttChartGenerator interface exists.

        The implementation should define an interface in:
        services/interfaces/gantt_chart_generator_interface.py
        """
        # Act & Assert
        from services.interfaces.gantt_chart_generator_interface import (
            IGanttChartGenerator
        )

        import inspect
        self.assertTrue(
            inspect.isabstract(IGanttChartGenerator) or
            hasattr(IGanttChartGenerator, '__protocol_attrs__'),
            "IGanttChartGenerator should be an abstract class or Protocol"
        )

    def test_interface_has_generate_method(self):
        """
        Test that interface defines generate method.

        The generate method should:
        - Accept transitions (List[StateTransition]), title (str), include_zero_duration (bool)
        - Return str (Mermaid Gantt chart text)
        """
        from services.interfaces.gantt_chart_generator_interface import (
            IGanttChartGenerator
        )
        import inspect

        methods = [name for name, _ in inspect.getmembers(
            IGanttChartGenerator,
            predicate=inspect.isfunction
        )]
        self.assertIn(
            "generate",
            methods,
            "IGanttChartGenerator should have generate method"
        )

    def test_interface_has_validate_syntax_method(self):
        """
        Test that interface defines validate_syntax method.

        The validate_syntax method should:
        - Accept gantt_text (str)
        - Return bool (whether the text is valid Mermaid syntax)
        """
        from services.interfaces.gantt_chart_generator_interface import (
            IGanttChartGenerator
        )
        import inspect

        methods = [name for name, _ in inspect.getmembers(
            IGanttChartGenerator,
            predicate=inspect.isfunction
        )]
        self.assertIn(
            "validate_syntax",
            methods,
            "IGanttChartGenerator should have validate_syntax method"
        )


# ============================================================================
# SECTION 2: GanttChartGenerator Implementation Tests
# ============================================================================

class TestGanttChartGeneratorCreation(unittest.TestCase):
    """
    Tests for GanttChartGenerator instantiation.
    """

    def test_generator_class_exists(self):
        """
        Test that GanttChartGenerator class exists.

        The implementation should be in:
        services/gantt_chart_generator.py
        """
        from services.gantt_chart_generator import GanttChartGenerator

        self.assertTrue(
            callable(GanttChartGenerator),
            "GanttChartGenerator should be a callable class"
        )

    def test_generator_can_be_instantiated(self):
        """
        Test that GanttChartGenerator can be instantiated.
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Act
        generator = GanttChartGenerator()

        # Assert
        self.assertIsNotNone(generator)

    def test_generator_implements_interface(self):
        """
        Test that GanttChartGenerator implements IGanttChartGenerator.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.interfaces.gantt_chart_generator_interface import (
            IGanttChartGenerator
        )

        generator = GanttChartGenerator()

        self.assertIsInstance(
            generator,
            IGanttChartGenerator,
            "GanttChartGenerator should implement IGanttChartGenerator"
        )


# ============================================================================
# SECTION 3: Generate Gantt Chart for Completed Processing Run
# ============================================================================

class TestGenerateGanttChartCompletedRun(unittest.TestCase):
    """
    Scenario: Generate Gantt chart for a completed processing run

    Given a completed email processing run exists for "user@gmail.com"
    And the run has the following state transitions:
      | state        | step_description          | timestamp           | duration_seconds |
      | CONNECTING   | Connecting to Gmail IMAP  | 2025-01-01 10:00:00 | 5.0              |
      | FETCHING     | Fetching emails from inbox| 2025-01-01 10:00:05 | 30.0             |
      | CATEGORIZING | Categorizing 45 emails    | 2025-01-01 10:00:35 | 85.0             |
      | LABELING     | Applying Gmail labels     | 2025-01-01 10:02:00 | 25.0             |
      | COMPLETED    | Processing completed      | 2025-01-01 10:02:25 | 5.0              |
    When the Gantt chart is generated for this run
    Then the gantt_chart_text should contain the Mermaid header "gantt"
    And the gantt_chart_text should contain a title with "user@gmail.com"
    And the gantt_chart_text should contain sections for each processing phase
    And all tasks should be marked as "done"
    """

    def setUp(self):
        """Set up test fixtures with sample state transitions."""
        from services.state_transition import StateTransition

        self.transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting to Gmail IMAP",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
            StateTransition(
                state="FETCHING",
                step_description="Fetching emails from inbox",
                timestamp=datetime(2025, 1, 1, 10, 0, 5, tzinfo=timezone.utc),
                duration_seconds=30.0
            ),
            StateTransition(
                state="CATEGORIZING",
                step_description="Categorizing 45 emails",
                timestamp=datetime(2025, 1, 1, 10, 0, 35, tzinfo=timezone.utc),
                duration_seconds=85.0
            ),
            StateTransition(
                state="LABELING",
                step_description="Applying Gmail labels",
                timestamp=datetime(2025, 1, 1, 10, 2, 0, tzinfo=timezone.utc),
                duration_seconds=25.0
            ),
            StateTransition(
                state="COMPLETED",
                step_description="Processing completed",
                timestamp=datetime(2025, 1, 1, 10, 2, 25, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

    def test_gantt_chart_contains_mermaid_header(self):
        """
        Test that the generated Gantt chart contains the Mermaid "gantt" header.

        Then the gantt_chart_text should contain the Mermaid header "gantt"
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        self.assertTrue(
            result.strip().startswith("gantt"),
            f"Gantt chart should start with 'gantt' header. Got: {result[:50]}..."
        )

    def test_gantt_chart_contains_title_with_email(self):
        """
        Test that the generated Gantt chart contains a title with the email address.

        Then the gantt_chart_text should contain a title with "user@gmail.com"
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        self.assertIn(
            "title",
            result.lower(),
            "Gantt chart should contain 'title' directive"
        )
        self.assertIn(
            "user@gmail.com",
            result,
            "Gantt chart title should contain the email address 'user@gmail.com'"
        )

    def test_gantt_chart_contains_sections_for_phases(self):
        """
        Test that the generated Gantt chart contains sections for processing phases.

        Then the gantt_chart_text should contain sections for each processing phase
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        self.assertIn(
            "section",
            result.lower(),
            "Gantt chart should contain 'section' directives for phases"
        )

    def test_gantt_chart_tasks_marked_as_done(self):
        """
        Test that all tasks in the generated Gantt chart are marked as "done".

        And all tasks should be marked as "done"
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert - Each task line should contain ":done,"
        lines = result.split('\n')
        task_lines = [
            line for line in lines
            if line.strip() and
            not line.strip().startswith('gantt') and
            not line.strip().startswith('title') and
            not line.strip().startswith('dateFormat') and
            not line.strip().startswith('axisFormat') and
            not line.strip().startswith('section')
        ]

        # There should be task lines
        self.assertGreater(
            len(task_lines),
            0,
            "Gantt chart should have task lines"
        )

        # Each task line should have :done, marker
        for task_line in task_lines:
            self.assertIn(
                "done",
                task_line.lower(),
                f"Task should be marked as 'done': {task_line}"
            )


# ============================================================================
# SECTION 4: Generate Gantt Chart with Proper Date Format
# ============================================================================

class TestGenerateGanttChartDateFormat(unittest.TestCase):
    """
    Scenario: Generate Gantt chart with proper date format

    Given a completed email processing run exists for "test@gmail.com"
    And the run started at "2025-01-01 10:00:00"
    And the run ended at "2025-01-01 10:02:30"
    When the Gantt chart is generated for this run
    Then the gantt_chart_text should specify dateFormat as "YYYY-MM-DD HH:mm:ss"
    And the gantt_chart_text should specify axisFormat as "%H:%M:%S"
    And timestamps should be formatted correctly in the output
    """

    def setUp(self):
        """Set up test fixtures with sample state transitions."""
        from services.state_transition import StateTransition

        self.transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
            StateTransition(
                state="COMPLETED",
                step_description="Completed",
                timestamp=datetime(2025, 1, 1, 10, 2, 30, tzinfo=timezone.utc),
                duration_seconds=0.0
            ),
        ]

    def test_gantt_chart_specifies_date_format(self):
        """
        Test that the Gantt chart specifies dateFormat as "YYYY-MM-DD HH:mm:ss".

        Then the gantt_chart_text should specify dateFormat as "YYYY-MM-DD HH:mm:ss"
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "test@gmail.com", False)

        # Assert
        self.assertIn(
            "dateFormat",
            result,
            "Gantt chart should contain 'dateFormat' directive"
        )
        self.assertIn(
            "YYYY-MM-DD HH:mm:ss",
            result,
            "dateFormat should be 'YYYY-MM-DD HH:mm:ss'"
        )

    def test_gantt_chart_specifies_axis_format(self):
        """
        Test that the Gantt chart specifies axisFormat as "%H:%M:%S".

        And the gantt_chart_text should specify axisFormat as "%H:%M:%S"
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "test@gmail.com", False)

        # Assert
        self.assertIn(
            "axisFormat",
            result,
            "Gantt chart should contain 'axisFormat' directive"
        )
        self.assertIn(
            "%H:%M:%S",
            result,
            "axisFormat should be '%H:%M:%S'"
        )

    def test_timestamps_formatted_correctly(self):
        """
        Test that timestamps are formatted correctly in the output.

        And timestamps should be formatted correctly in the output
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "test@gmail.com", False)

        # Assert - Should contain timestamp in format YYYY-MM-DD HH:mm:ss
        self.assertIn(
            "2025-01-01 10:00:00",
            result,
            "Gantt chart should contain formatted timestamp '2025-01-01 10:00:00'"
        )


# ============================================================================
# SECTION 5: Generate Gantt Chart with Section Groupings
# ============================================================================

class TestGenerateGanttChartSectionGroupings(unittest.TestCase):
    """
    Scenario: Generate Gantt chart with section groupings

    Given a completed email processing run with all phases
    And the run transitioned through CONNECTING, FETCHING, CATEGORIZING, LABELING, COMPLETED
    When the Gantt chart is generated for this run
    Then the gantt_chart_text should have an "Initialization" section
    And the gantt_chart_text should have a "Fetching" section
    And the gantt_chart_text should have a "Categorization" section
    And the gantt_chart_text should have a "Labeling" section
    And the gantt_chart_text should have a "Completion" section
    """

    def setUp(self):
        """Set up test fixtures with all phases."""
        from services.state_transition import StateTransition

        self.transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting to Gmail IMAP",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
            StateTransition(
                state="FETCHING",
                step_description="Fetching emails",
                timestamp=datetime(2025, 1, 1, 10, 0, 5, tzinfo=timezone.utc),
                duration_seconds=30.0
            ),
            StateTransition(
                state="CATEGORIZING",
                step_description="Categorizing emails",
                timestamp=datetime(2025, 1, 1, 10, 0, 35, tzinfo=timezone.utc),
                duration_seconds=60.0
            ),
            StateTransition(
                state="LABELING",
                step_description="Applying labels",
                timestamp=datetime(2025, 1, 1, 10, 1, 35, tzinfo=timezone.utc),
                duration_seconds=20.0
            ),
            StateTransition(
                state="COMPLETED",
                step_description="Processing completed",
                timestamp=datetime(2025, 1, 1, 10, 1, 55, tzinfo=timezone.utc),
                duration_seconds=0.0
            ),
        ]

    def test_gantt_chart_has_initialization_section(self):
        """
        Test that the Gantt chart has an "Initialization" section.

        Then the gantt_chart_text should have an "Initialization" section
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        self.assertIn(
            "section Initialization",
            result,
            f"Gantt chart should have 'section Initialization'. Got:\n{result}"
        )

    def test_gantt_chart_has_fetching_section(self):
        """
        Test that the Gantt chart has a "Fetching" section.

        And the gantt_chart_text should have a "Fetching" section
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        self.assertIn(
            "section Fetching",
            result,
            f"Gantt chart should have 'section Fetching'. Got:\n{result}"
        )

    def test_gantt_chart_has_categorization_section(self):
        """
        Test that the Gantt chart has a "Categorization" section.

        And the gantt_chart_text should have a "Categorization" section
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        self.assertIn(
            "section Categorization",
            result,
            f"Gantt chart should have 'section Categorization'. Got:\n{result}"
        )

    def test_gantt_chart_has_labeling_section(self):
        """
        Test that the Gantt chart has a "Labeling" section.

        And the gantt_chart_text should have a "Labeling" section
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        self.assertIn(
            "section Labeling",
            result,
            f"Gantt chart should have 'section Labeling'. Got:\n{result}"
        )

    def test_gantt_chart_has_completion_section(self):
        """
        Test that the Gantt chart has a "Completion" section.

        And the gantt_chart_text should have a "Completion" section
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        self.assertIn(
            "section Completion",
            result,
            f"Gantt chart should have 'section Completion'. Got:\n{result}"
        )


# ============================================================================
# SECTION 6: Generate Gantt Chart with Duration Formatting
# ============================================================================

class TestGenerateGanttChartDurationFormatting(unittest.TestCase):
    """
    Scenario: Generate Gantt chart with duration formatting

    Given a completed email processing run with varying durations
    And the run has the following state transitions:
      | state        | step_description    | timestamp           | duration_seconds |
      | CONNECTING   | Connecting          | 2025-01-01 10:00:00 | 5.0              |
      | FETCHING     | Fetching emails     | 2025-01-01 10:00:05 | 90.0             |
      | CATEGORIZING | Categorizing emails | 2025-01-01 10:01:35 | 3600.0           |
    When the Gantt chart is generated for this run
    Then the gantt_chart_text should contain duration "5s" for the CONNECTING task
    And the gantt_chart_text should contain duration "90s" for the FETCHING task
    And the gantt_chart_text should contain duration "3600s" for the CATEGORIZING task
    """

    def setUp(self):
        """Set up test fixtures with varying durations."""
        from services.state_transition import StateTransition

        self.transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
            StateTransition(
                state="FETCHING",
                step_description="Fetching emails",
                timestamp=datetime(2025, 1, 1, 10, 0, 5, tzinfo=timezone.utc),
                duration_seconds=90.0
            ),
            StateTransition(
                state="CATEGORIZING",
                step_description="Categorizing emails",
                timestamp=datetime(2025, 1, 1, 10, 1, 35, tzinfo=timezone.utc),
                duration_seconds=3600.0
            ),
        ]

    def test_connecting_task_has_5s_duration(self):
        """
        Test that the CONNECTING task shows 5s duration.

        Then the gantt_chart_text should contain duration "5s" for the CONNECTING task
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert - Look for the 5s duration in context of CONNECTING
        self.assertIn(
            "5s",
            result,
            f"Gantt chart should contain '5s' duration. Got:\n{result}"
        )

    def test_fetching_task_has_90s_duration(self):
        """
        Test that the FETCHING task shows 90s duration.

        And the gantt_chart_text should contain duration "90s" for the FETCHING task
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        self.assertIn(
            "90s",
            result,
            f"Gantt chart should contain '90s' duration. Got:\n{result}"
        )

    def test_categorizing_task_has_3600s_duration(self):
        """
        Test that the CATEGORIZING task shows 3600s duration.

        And the gantt_chart_text should contain duration "3600s" for the CATEGORIZING task
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        self.assertIn(
            "3600s",
            result,
            f"Gantt chart should contain '3600s' duration. Got:\n{result}"
        )

    def test_duration_format_is_integer_seconds(self):
        """
        Test that duration is formatted as integer seconds (no decimals).

        Duration should be "5s" not "5.0s"
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.5  # fractional seconds
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert - Should round to integer
        self.assertNotIn(
            "5.5s",
            result,
            "Duration should be formatted as integer, not '5.5s'"
        )
        # Either 5s or 6s (depending on rounding strategy) is acceptable
        has_valid_duration = "5s" in result or "6s" in result
        self.assertTrue(
            has_valid_duration,
            f"Duration should be formatted as integer seconds. Got:\n{result}"
        )


# ============================================================================
# SECTION 7: Valid Mermaid Syntax
# ============================================================================

class TestValidMermaidSyntax(unittest.TestCase):
    """
    Scenario: Gantt chart text is valid Mermaid syntax

    Given a completed processing run with all phases
    When the Gantt chart is generated
    Then the output should start with "gantt"
    And the output should contain a valid "title" directive
    And the output should contain a valid "dateFormat" directive
    And the output should contain a valid "axisFormat" directive
    And each task line should follow Mermaid task syntax
    """

    def setUp(self):
        """Set up test fixtures."""
        from services.state_transition import StateTransition

        self.transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting to Gmail IMAP",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
            StateTransition(
                state="FETCHING",
                step_description="Fetching emails",
                timestamp=datetime(2025, 1, 1, 10, 0, 5, tzinfo=timezone.utc),
                duration_seconds=30.0
            ),
            StateTransition(
                state="COMPLETED",
                step_description="Processing completed",
                timestamp=datetime(2025, 1, 1, 10, 0, 35, tzinfo=timezone.utc),
                duration_seconds=0.0
            ),
        ]

    def test_output_starts_with_gantt(self):
        """
        Test that the output starts with "gantt".

        Then the output should start with "gantt"
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        first_line = result.strip().split('\n')[0].strip()
        self.assertEqual(
            first_line,
            "gantt",
            f"First line should be 'gantt', got '{first_line}'"
        )

    def test_output_contains_valid_title_directive(self):
        """
        Test that output contains a valid title directive.

        And the output should contain a valid "title" directive
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert - title directive format: "    title <text>"
        lines = result.split('\n')
        title_lines = [line for line in lines if 'title' in line.lower()]
        self.assertGreater(
            len(title_lines),
            0,
            "Output should contain a title directive"
        )

        # Validate title format
        title_line = title_lines[0].strip()
        self.assertTrue(
            title_line.startswith("title"),
            f"Title line should start with 'title', got '{title_line}'"
        )

    def test_output_contains_valid_date_format_directive(self):
        """
        Test that output contains a valid dateFormat directive.

        And the output should contain a valid "dateFormat" directive
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        lines = result.split('\n')
        date_format_lines = [line for line in lines if 'dateFormat' in line]
        self.assertGreater(
            len(date_format_lines),
            0,
            "Output should contain a dateFormat directive"
        )

        date_format_line = date_format_lines[0].strip()
        self.assertTrue(
            date_format_line.startswith("dateFormat"),
            f"dateFormat line should start with 'dateFormat', got '{date_format_line}'"
        )

    def test_output_contains_valid_axis_format_directive(self):
        """
        Test that output contains a valid axisFormat directive.

        And the output should contain a valid "axisFormat" directive
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert
        lines = result.split('\n')
        axis_format_lines = [line for line in lines if 'axisFormat' in line]
        self.assertGreater(
            len(axis_format_lines),
            0,
            "Output should contain an axisFormat directive"
        )

        axis_format_line = axis_format_lines[0].strip()
        self.assertTrue(
            axis_format_line.startswith("axisFormat"),
            f"axisFormat line should start with 'axisFormat', got '{axis_format_line}'"
        )

    def test_task_lines_follow_mermaid_syntax(self):
        """
        Test that each task line follows Mermaid task syntax.

        Mermaid task syntax:
        <task_name> :<status>, <task_id>, <start_time>, <duration>

        Example:
        Connecting to Gmail IMAP :done, connecting_0, 2025-01-01 10:00:00, 5s
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.generate(self.transitions, "user@gmail.com", False)

        # Assert - Find task lines (not directives or sections)
        lines = result.split('\n')
        task_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and ':' in stripped:
                # Not a directive (gantt, title, dateFormat, axisFormat, section)
                if not any(stripped.startswith(d) for d in
                           ['gantt', 'title', 'dateFormat', 'axisFormat', 'section']):
                    task_lines.append(stripped)

        # Should have at least one task
        self.assertGreater(
            len(task_lines),
            0,
            "Output should have at least one task line"
        )

        # Each task line should contain the key elements
        for task_line in task_lines:
            # Should have task description before :
            self.assertIn(
                ":",
                task_line,
                f"Task line should have ':' separator: {task_line}"
            )

            # After :, should have comma-separated parts
            parts_after_colon = task_line.split(':')[1]
            self.assertIn(
                ",",
                parts_after_colon,
                f"Task specification should have comma-separated parts: {task_line}"
            )


# ============================================================================
# SECTION 8: Validate Syntax Method Tests
# ============================================================================

class TestValidateSyntaxMethod(unittest.TestCase):
    """
    Tests for the validate_syntax method.

    The method should verify that the generated text follows valid Mermaid
    Gantt chart syntax rules.
    """

    def test_validate_syntax_returns_true_for_valid_chart(self):
        """
        Test that validate_syntax returns True for valid Mermaid Gantt chart.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        gantt_text = generator.generate(transitions, "test@gmail.com", True)
        result = generator.validate_syntax(gantt_text)

        # Assert
        self.assertTrue(
            result,
            f"validate_syntax should return True for valid chart. Chart:\n{gantt_text}"
        )

    def test_validate_syntax_returns_false_for_missing_header(self):
        """
        Test that validate_syntax returns False when "gantt" header is missing.
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()
        invalid_text = """
    title Email Processing
    dateFormat YYYY-MM-DD HH:mm:ss
    section Test
    Task :done, task_0, 2025-01-01 10:00:00, 5s
"""

        # Act
        result = generator.validate_syntax(invalid_text)

        # Assert
        self.assertFalse(
            result,
            "validate_syntax should return False when 'gantt' header is missing"
        )

    def test_validate_syntax_returns_false_for_empty_string(self):
        """
        Test that validate_syntax returns False for empty string.
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()

        # Act
        result = generator.validate_syntax("")

        # Assert
        self.assertFalse(
            result,
            "validate_syntax should return False for empty string"
        )

    def test_validate_syntax_returns_false_for_missing_date_format(self):
        """
        Test that validate_syntax returns False when dateFormat is missing.
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()
        invalid_text = """gantt
    title Email Processing
    section Test
    Task :done, task_0, 2025-01-01 10:00:00, 5s
"""

        # Act
        result = generator.validate_syntax(invalid_text)

        # Assert
        self.assertFalse(
            result,
            "validate_syntax should return False when 'dateFormat' is missing"
        )


# ============================================================================
# SECTION 9: State-to-Section Mapping Tests
# ============================================================================

class TestStateToSectionMapping(unittest.TestCase):
    """
    Tests for state-to-section mapping functionality.

    States should map to sections as follows:
    - CONNECTING -> Initialization
    - IDLE -> Initialization
    - FETCHING -> Fetching
    - CATEGORIZING -> Categorization
    - LABELING -> Labeling
    - COMPLETED -> Completion
    - ERROR -> Error
    """

    def test_connecting_maps_to_initialization(self):
        """
        Test that CONNECTING state maps to Initialization section.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert
        self.assertIn(
            "section Initialization",
            result,
            "CONNECTING state should map to 'Initialization' section"
        )

    def test_idle_maps_to_initialization(self):
        """
        Test that IDLE state maps to Initialization section.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="IDLE",
                step_description="Idle",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert
        self.assertIn(
            "section Initialization",
            result,
            "IDLE state should map to 'Initialization' section"
        )

    def test_fetching_maps_to_fetching_section(self):
        """
        Test that FETCHING state maps to Fetching section.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="FETCHING",
                step_description="Fetching",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert
        self.assertIn(
            "section Fetching",
            result,
            "FETCHING state should map to 'Fetching' section"
        )

    def test_categorizing_maps_to_categorization_section(self):
        """
        Test that CATEGORIZING state maps to Categorization section.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CATEGORIZING",
                step_description="Categorizing",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert
        self.assertIn(
            "section Categorization",
            result,
            "CATEGORIZING state should map to 'Categorization' section"
        )

    def test_labeling_maps_to_labeling_section(self):
        """
        Test that LABELING state maps to Labeling section.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="LABELING",
                step_description="Labeling",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert
        self.assertIn(
            "section Labeling",
            result,
            "LABELING state should map to 'Labeling' section"
        )

    def test_completed_maps_to_completion_section(self):
        """
        Test that COMPLETED state maps to Completion section.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="COMPLETED",
                step_description="Completed",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert
        self.assertIn(
            "section Completion",
            result,
            "COMPLETED state should map to 'Completion' section"
        )

    def test_error_maps_to_error_section(self):
        """
        Test that ERROR state maps to Error section.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="ERROR",
                step_description="Error occurred",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert
        self.assertIn(
            "section Error",
            result,
            "ERROR state should map to 'Error' section"
        )


# ============================================================================
# SECTION 10: Task ID Generation Tests
# ============================================================================

class TestTaskIdGeneration(unittest.TestCase):
    """
    Tests for task ID generation.

    Task IDs should follow the format: state_lowercase_index
    Example: connecting_0, fetching_0, categorizing_0
    """

    def test_task_id_uses_lowercase_state(self):
        """
        Test that task ID uses lowercase state name.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert
        self.assertIn(
            "connecting_",
            result.lower(),
            "Task ID should use lowercase state name 'connecting_'"
        )

    def test_task_id_includes_index(self):
        """
        Test that task ID includes an index.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert - Should contain task ID with index like connecting_0
        self.assertIn(
            "connecting_0",
            result.lower(),
            "Task ID should include index, e.g., 'connecting_0'"
        )

    def test_multiple_same_state_transitions_have_unique_ids(self):
        """
        Test that multiple transitions of the same state have unique IDs.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="FETCHING",
                step_description="Fetching page 1",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
            StateTransition(
                state="FETCHING",
                step_description="Fetching page 2",
                timestamp=datetime(2025, 1, 1, 10, 0, 5, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert - Should have fetching_0 and fetching_1
        result_lower = result.lower()
        self.assertIn(
            "fetching_0",
            result_lower,
            "First FETCHING transition should have ID 'fetching_0'"
        )
        self.assertIn(
            "fetching_1",
            result_lower,
            "Second FETCHING transition should have ID 'fetching_1'"
        )


# ============================================================================
# SECTION 11: Include Zero Duration Tests
# ============================================================================

class TestIncludeZeroDuration(unittest.TestCase):
    """
    Tests for include_zero_duration parameter behavior.

    When include_zero_duration is False, transitions with 0.0 duration
    should be excluded from the generated chart.
    """

    def test_zero_duration_excluded_when_flag_is_false(self):
        """
        Test that zero duration transitions are excluded when include_zero_duration is False.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
            StateTransition(
                state="COMPLETED",
                step_description="Completed",
                timestamp=datetime(2025, 1, 1, 10, 0, 5, tzinfo=timezone.utc),
                duration_seconds=0.0  # Zero duration
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", False)

        # Assert - COMPLETED task should not appear (has 0 duration)
        self.assertNotIn(
            "completed_0",
            result.lower(),
            "Zero duration task should be excluded when include_zero_duration is False"
        )

    def test_zero_duration_included_when_flag_is_true(self):
        """
        Test that zero duration transitions are included when include_zero_duration is True.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
            StateTransition(
                state="COMPLETED",
                step_description="Completed",
                timestamp=datetime(2025, 1, 1, 10, 0, 5, tzinfo=timezone.utc),
                duration_seconds=0.0  # Zero duration
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert - COMPLETED task should appear
        self.assertIn(
            "completed_0",
            result.lower(),
            "Zero duration task should be included when include_zero_duration is True"
        )


# ============================================================================
# SECTION 12: Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases(unittest.TestCase):
    """
    Test edge cases and boundary conditions.
    """

    def test_empty_transitions_list_returns_minimal_chart(self):
        """
        Test that an empty transitions list returns a minimal valid chart.
        """
        from services.gantt_chart_generator import GanttChartGenerator

        # Arrange
        generator = GanttChartGenerator()
        transitions = []

        # Act
        result = generator.generate(transitions, "user@gmail.com", False)

        # Assert - Should still have header and title
        self.assertIn(
            "gantt",
            result,
            "Empty transitions should still produce chart with 'gantt' header"
        )
        self.assertIn(
            "user@gmail.com",
            result,
            "Empty transitions should still produce chart with title"
        )

    def test_single_transition_produces_valid_chart(self):
        """
        Test that a single transition produces a valid chart.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert
        self.assertIn("gantt", result)
        self.assertIn("section", result.lower())
        self.assertTrue(
            generator.validate_syntax(result),
            f"Single transition should produce valid chart:\n{result}"
        )

    def test_special_characters_in_step_description_escaped(self):
        """
        Test that special characters in step description are properly handled.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CATEGORIZING",
                step_description="Processing emails: 45 items (Marketing & Ads)",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=60.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert - Should not break the chart
        self.assertTrue(
            generator.validate_syntax(result),
            f"Special characters should be handled properly:\n{result}"
        )

    def test_email_with_special_characters_in_title(self):
        """
        Test that email addresses with + or special chars are handled in title.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user+alias@gmail.com", True)

        # Assert
        self.assertIn(
            "user+alias@gmail.com",
            result,
            "Email with + should appear in title"
        )
        self.assertTrue(
            generator.validate_syntax(result),
            f"Email with special chars should produce valid chart:\n{result}"
        )

    def test_very_long_duration_formatted_correctly(self):
        """
        Test that very long durations (hours) are formatted correctly.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CATEGORIZING",
                step_description="Categorizing",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=36000.0  # 10 hours in seconds
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert - Should contain the duration in seconds
        self.assertIn(
            "36000s",
            result,
            "Very long duration should be formatted as '36000s'"
        )

    def test_none_duration_handled_gracefully(self):
        """
        Test that None duration is handled gracefully (treated as 0).
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=None  # None duration
            ),
        ]

        # Act - Should not raise an exception
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert
        self.assertIn(
            "gantt",
            result,
            "None duration should be handled gracefully"
        )


# ============================================================================
# SECTION 13: Example Output Structure Test
# ============================================================================

class TestExampleOutputStructure(unittest.TestCase):
    """
    Test that the generated output matches the expected structure from requirements.

    Expected output format:
    ```
    gantt
        title Email Processing: user@gmail.com
        dateFormat YYYY-MM-DD HH:mm:ss
        axisFormat %H:%M:%S

        section Initialization
        Connecting to Gmail IMAP :done, connecting_0, 2025-01-01 10:00:00, 5s
    ```
    """

    def test_complete_output_structure(self):
        """
        Test that the complete output matches the expected structure.
        """
        from services.gantt_chart_generator import GanttChartGenerator
        from services.state_transition import StateTransition

        # Arrange
        generator = GanttChartGenerator()
        transitions = [
            StateTransition(
                state="CONNECTING",
                step_description="Connecting to Gmail IMAP",
                timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                duration_seconds=5.0
            ),
        ]

        # Act
        result = generator.generate(transitions, "user@gmail.com", True)

        # Assert - Check all required components
        self.assertIn("gantt", result, "Should start with 'gantt'")
        self.assertIn("title", result, "Should have 'title' directive")
        self.assertIn("user@gmail.com", result, "Should include email in title")
        self.assertIn("dateFormat YYYY-MM-DD HH:mm:ss", result, "Should have dateFormat")
        self.assertIn("axisFormat %H:%M:%S", result, "Should have axisFormat")
        self.assertIn("section Initialization", result, "Should have Initialization section")
        self.assertIn("Connecting to Gmail IMAP", result, "Should have task description")
        self.assertIn(":done,", result, "Should have done status")
        self.assertIn("connecting_0", result.lower(), "Should have task ID")
        self.assertIn("2025-01-01 10:00:00", result, "Should have timestamp")
        self.assertIn("5s", result, "Should have duration")


if __name__ == '__main__':
    unittest.main()
