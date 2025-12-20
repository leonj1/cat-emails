# DRAFT: Gantt Chart Generator Core

> Status: Draft
> Sub-task: 1.2 of "Generate Mermaid Gantt Chart Text for Email Categorization Runs"
> Dependencies: Sub-task 1.1 (State Transition Tracking) - COMPLETED

## Overview

This sub-task implements the core Gantt chart text generator that converts state transition data into valid Mermaid Gantt chart syntax. The generator takes a list of `StateTransition` objects (from Sub-task 1.1) and produces a complete Mermaid Gantt chart string suitable for rendering.

## Interfaces Needed

### IGanttChartGenerator

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from services.state_transition import StateTransition


class IGanttChartGenerator(ABC):
    """Interface for generating Mermaid Gantt chart text from state transitions."""

    @abstractmethod
    def generate(
        self,
        transitions: List[StateTransition],
        title: str,
        include_zero_duration: bool = False
    ) -> str:
        """
        Generate Mermaid Gantt chart text from state transitions.

        Args:
            transitions: List of finalized StateTransition objects with durations
            title: Chart title (e.g., "Email Processing: user@gmail.com")
            include_zero_duration: Whether to include tasks with 0s duration

        Returns:
            Complete Mermaid Gantt chart text as a string
        """
        pass

    @abstractmethod
    def validate_syntax(self, gantt_text: str) -> bool:
        """
        Validate that the generated Gantt text has correct Mermaid syntax.

        Args:
            gantt_text: The Mermaid Gantt chart text to validate

        Returns:
            True if syntax is valid, False otherwise
        """
        pass
```

## Data Models

### ProcessingState Enum

```python
from enum import Enum


class ProcessingState(Enum):
    """Processing states that map to Gantt chart sections."""
    CONNECTING = "Initialization"
    FETCHING = "Fetching"
    PROCESSING = "Processing"
    CATEGORIZING = "AI Categorization"
    LABELING = "Labeling"
    COMPLETED = "Completion"
    ERROR = "Error"
```

### GanttTask (Internal)

```python
@dataclass
class GanttTask:
    """Internal representation of a Gantt task line."""
    description: str
    status: str  # 'done', 'active', 'crit'
    task_id: str
    start_time: str  # formatted datetime
    duration: str  # e.g., '5s', '30s', '2m'
```

## Implementation Details

### State-to-Section Mapping

States are grouped into logical sections for visual organization:

| State | Section Name |
|-------|--------------|
| CONNECTING | Initialization |
| FETCHING | Fetching |
| PROCESSING | Processing |
| CATEGORIZING | AI Categorization |
| LABELING | Labeling |
| COMPLETED | Completion |
| ERROR | Error |

Unknown states default to section "Other".

### Date/Time Format Handling

- Input: `datetime` objects from `StateTransition.timestamp`
- Output format for Mermaid: `YYYY-MM-DD HH:mm:ss`
- Header configuration: `dateFormat YYYY-MM-DD HH:mm:ss`
- Axis format: `axisFormat %H:%M:%S` (show only time on x-axis)

```python
def format_timestamp(self, dt: datetime) -> str:
    """Format datetime for Mermaid Gantt syntax."""
    return dt.strftime('%Y-%m-%d %H:%M:%S')
```

### Duration Formatting

Convert `duration_seconds` (float) to Mermaid duration syntax:

| Seconds | Mermaid Syntax |
|---------|----------------|
| 0 | Skip or `1s` (minimum) |
| 0.5 | `1s` (round up) |
| 5 | `5s` |
| 60 | `1m` |
| 90 | `90s` or `1m 30s` |
| 3600 | `1h` |

```python
def format_duration(self, seconds: float) -> str:
    """Convert seconds to Mermaid duration syntax."""
    if seconds <= 0:
        return "1s"  # Minimum visible duration

    rounded = max(1, int(round(seconds)))

    if rounded >= 3600:
        hours = rounded // 3600
        remaining = rounded % 3600
        if remaining > 0:
            return f"{hours}h {remaining}s"
        return f"{hours}h"
    elif rounded >= 60:
        minutes = rounded // 60
        remaining = rounded % 60
        if remaining > 0:
            return f"{minutes}m {remaining}s"
        return f"{minutes}m"
    else:
        return f"{rounded}s"
```

### Task ID Generation

Task IDs must be unique and valid Mermaid identifiers (alphanumeric, no spaces):

```python
def generate_task_id(self, state: str, index: int) -> str:
    """Generate unique task ID for Mermaid."""
    # Sanitize state name: lowercase, replace spaces with underscores
    sanitized = state.lower().replace(' ', '_').replace('-', '_')
    return f"{sanitized}_{index}"
```

### Task Status Markers

| Status | Meaning | When to Use |
|--------|---------|-------------|
| `done` | Completed task | For all finalized transitions |
| `active` | Currently running | For in-progress runs (future) |
| `crit` | Critical/error | For ERROR state or failures |

```python
def determine_status(self, state: str, is_final: bool) -> str:
    """Determine task status marker."""
    if state == "ERROR":
        return "crit"
    return "done"
```

## Logic Flow

```
generate(transitions, title, include_zero_duration):
    1. Initialize output lines with header
       - Add "gantt"
       - Add "    title {title}"
       - Add "    dateFormat YYYY-MM-DD HH:mm:ss"
       - Add "    axisFormat %H:%M:%S"
       - Add empty line

    2. Group transitions by section
       - Map each state to its section name
       - Maintain order within each section

    3. For each section with transitions:
       - Add "    section {section_name}"
       - For each transition in section:
         - Skip if duration_seconds == 0 and not include_zero_duration
         - Format: "    {description} :{status}, {task_id}, {start_time}, {duration}"
       - Add empty line after section

    4. Join all lines with newline
    5. Validate syntax
    6. Return complete Gantt text
```

## Example Output

### Input

```python
transitions = [
    StateTransition(
        state="CONNECTING",
        step_description="Connecting to Gmail IMAP",
        timestamp=datetime(2025, 1, 1, 10, 0, 0),
        duration_seconds=5.0
    ),
    StateTransition(
        state="FETCHING",
        step_description="Fetching emails from inbox",
        timestamp=datetime(2025, 1, 1, 10, 0, 5),
        duration_seconds=30.0
    ),
    StateTransition(
        state="CATEGORIZING",
        step_description="Categorizing 15 emails",
        timestamp=datetime(2025, 1, 1, 10, 0, 35),
        duration_seconds=45.0
    ),
    StateTransition(
        state="LABELING",
        step_description="Applying labels to emails",
        timestamp=datetime(2025, 1, 1, 10, 1, 20),
        duration_seconds=10.0
    ),
    StateTransition(
        state="COMPLETED",
        step_description="Processing complete",
        timestamp=datetime(2025, 1, 1, 10, 1, 30),
        duration_seconds=0.0
    ),
]
```

### Output

```
gantt
    title Email Processing: user@gmail.com
    dateFormat YYYY-MM-DD HH:mm:ss
    axisFormat %H:%M:%S

    section Initialization
    Connecting to Gmail IMAP :done, connecting_0, 2025-01-01 10:00:00, 5s

    section Fetching
    Fetching emails from inbox :done, fetching_1, 2025-01-01 10:00:05, 30s

    section AI Categorization
    Categorizing 15 emails :done, categorizing_2, 2025-01-01 10:00:35, 45s

    section Labeling
    Applying labels to emails :done, labeling_3, 2025-01-01 10:01:20, 10s

    section Completion
    Processing complete :done, completed_4, 2025-01-01 10:01:30, 1s
```

## Syntax Validation

Basic validation rules for generated Gantt text:

1. Must start with `gantt` keyword
2. Must have `title` directive
3. Must have `dateFormat` directive
4. Each task line must follow format: `description :status, id, start, duration`
5. Section names must be valid (no special characters)
6. Task IDs must be unique

```python
def validate_syntax(self, gantt_text: str) -> bool:
    """Validate Mermaid Gantt syntax."""
    lines = gantt_text.strip().split('\n')

    if not lines or lines[0].strip() != 'gantt':
        return False

    has_title = any('title' in line for line in lines)
    has_date_format = any('dateFormat' in line for line in lines)

    if not has_title or not has_date_format:
        return False

    # Check task line format
    task_ids = set()
    for line in lines:
        line = line.strip()
        if ':' in line and not line.startswith('section') and 'title' not in line and 'Format' not in line:
            # Parse task line
            parts = line.split(':')
            if len(parts) >= 2:
                task_parts = parts[1].split(',')
                if len(task_parts) >= 2:
                    task_id = task_parts[1].strip()
                    if task_id in task_ids:
                        return False  # Duplicate ID
                    task_ids.add(task_id)

    return True
```

## Edge Cases

1. **Empty transitions list**: Return minimal valid Gantt chart with just header
2. **Zero duration tasks**: Skip by default, or include with minimum 1s duration
3. **Unknown states**: Map to "Other" section
4. **Special characters in descriptions**: Escape or sanitize
5. **Very long descriptions**: Truncate to reasonable length (50 chars)

## Files to Create

| File | Purpose |
|------|---------|
| `/root/repo/services/interfaces/gantt_chart_generator_interface.py` | Interface definition |
| `/root/repo/services/gantt_chart_generator.py` | Implementation |

## Context Budget Estimate

| Category | Count | Lines |
|----------|-------|-------|
| Files to read | 2 | ~120 lines |
| New code to write | 2 files | ~150 lines |
| Test code to write | 1 file | ~200 lines |
| **Total estimated** | | ~470 lines |
| **Estimated context usage** | | **15%** |

This is well within the 60% context budget threshold.

## Test Scenarios (BDD)

1. Generate Gantt chart for typical processing run with all states
2. Generate Gantt chart with single transition
3. Handle empty transitions list
4. Handle zero-duration tasks (skip by default)
5. Handle zero-duration tasks (include with minimum duration)
6. Validate generated syntax is correct
7. Handle unknown states with "Other" section
8. Generate unique task IDs for repeated states
9. Format durations correctly (seconds, minutes, hours)
10. Handle special characters in descriptions

## Success Criteria

- [ ] Generator produces valid Mermaid Gantt syntax
- [ ] All processing states map to appropriate sections
- [ ] Timestamps formatted correctly for Mermaid
- [ ] Durations converted to readable format
- [ ] Task IDs are unique and valid
- [ ] Syntax validation catches common errors
- [ ] Edge cases handled gracefully
