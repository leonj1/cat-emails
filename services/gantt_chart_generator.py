"""
Gantt Chart Generator implementation.

This module provides functionality to generate Mermaid Gantt chart text
from state transition data for email processing run visualizations.
"""
from typing import List, Dict
from services.interfaces.gantt_chart_generator_interface import IGanttChartGenerator
from services.state_transition import StateTransition


class GanttChartGenerator(IGanttChartGenerator):
    """
    Implementation of Gantt chart generation for email processing visualizations.

    This class converts state transition data into valid Mermaid Gantt chart syntax,
    with support for sections, duration formatting, and zero-duration filtering.
    """

    # State-to-section mapping for organizing the Gantt chart
    STATE_TO_SECTION: Dict[str, str] = {
        'CONNECTING': 'Initialization',
        'IDLE': 'Initialization',
        'FETCHING': 'Fetching',
        'CATEGORIZING': 'Categorization',
        'LABELING': 'Labeling',
        'COMPLETED': 'Completion',
        'ERROR': 'Error',
    }

    def generate(
        self,
        transitions: List[StateTransition],
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
        # Start with header and configuration
        lines = [
            'gantt',
            f'    title Email Processing: {title}',
            '    dateFormat YYYY-MM-DD HH:mm:ss',
            '    axisFormat %H:%M:%S',
        ]

        # First pass: Identify all sections that appear in transitions
        # This ensures sections are created even if tasks are filtered out
        all_sections = set()
        for transition in transitions:
            section = self.STATE_TO_SECTION.get(transition.state, 'Other')
            all_sections.add(section)

        # Initialize sections
        sections: Dict[str, List[tuple]] = {section: [] for section in all_sections}
        state_counters: Dict[str, int] = {}

        # Second pass: Add tasks to sections
        for transition in transitions:
            # Get section name for this state
            section = self.STATE_TO_SECTION.get(transition.state, 'Other')

            # Check if we should skip this task based on zero duration
            should_skip = (not include_zero_duration and transition.duration_seconds == 0.0)

            if should_skip:
                # Skip adding the task, but section already exists from first pass
                continue

            # Get task ID counter for this state
            state_lower = transition.state.lower()
            if state_lower not in state_counters:
                state_counters[state_lower] = 0
            task_id = f"{state_lower}_{state_counters[state_lower]}"
            state_counters[state_lower] += 1

            # Format duration (convert to integer seconds with 's' suffix)
            # Minimum duration is 1s for visibility
            duration_seconds = transition.duration_seconds
            if duration_seconds is None:
                duration_seconds = 0.0

            if include_zero_duration and duration_seconds == 0.0:
                # Use 1s minimum for visibility
                duration_str = '1s'
            else:
                duration_str = f'{int(duration_seconds)}s'

            # Format timestamp
            timestamp_str = transition.timestamp.strftime('%Y-%m-%d %H:%M:%S')

            # Store task information for this section
            sections[section].append({
                'description': transition.step_description,
                'task_id': task_id,
                'timestamp': timestamp_str,
                'duration': duration_str
            })

        # Add sections and tasks to the output
        # Order sections consistently
        section_order = ['Initialization', 'Fetching', 'Categorization', 'Labeling', 'Completion', 'Error', 'Other']

        for section_name in section_order:
            if section_name in sections:
                lines.append('')
                lines.append(f'    section {section_name}')

                for task in sections[section_name]:
                    task_line = (
                        f'    {task["description"]} '
                        f':done, {task["task_id"]}, {task["timestamp"]}, {task["duration"]}'
                    )
                    lines.append(task_line)

        return '\n'.join(lines)

    def validate_syntax(self, gantt_text: str) -> bool:
        """
        Validate that the generated text follows valid Mermaid Gantt chart syntax.

        Args:
            gantt_text: The Gantt chart text to validate

        Returns:
            bool: True if the syntax is valid, False otherwise
        """
        if not gantt_text or not gantt_text.strip():
            return False

        lines = gantt_text.strip().split('\n')

        # Check for required elements
        has_gantt_header = False
        has_date_format = False

        for line in lines:
            stripped = line.strip()

            # Check for gantt header (must be first non-empty line)
            if not has_gantt_header:
                if stripped:
                    if stripped == 'gantt':
                        has_gantt_header = True
                    else:
                        return False  # First line must be 'gantt'

            # Check for dateFormat directive
            if stripped.startswith('dateFormat'):
                has_date_format = True

        # Must have both gantt header and dateFormat
        return has_gantt_header and has_date_format
