---
executor: bdd
source_feature: ./tests/bdd/gantt_chart_generator_core.feature
---

<objective>
Implement the Gantt Chart Generator Core feature that converts state transition data into valid Mermaid Gantt chart text. The generator must take a list of StateTransition objects and produce properly formatted Mermaid syntax that can be rendered in the UI.
</objective>

<gherkin>
Feature: Gantt Chart Generator Core
  As a system administrator
  I want to convert state transition data into Mermaid Gantt chart text
  So that I can visualize email processing timelines in the UI

  Background:
    Given the Gantt chart generator is initialized

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

  Scenario: Generate Gantt chart with proper date format
    Given a completed email processing run exists for "test@gmail.com"
    And the run started at "2025-01-01 10:00:00"
    And the run ended at "2025-01-01 10:02:30"
    When the Gantt chart is generated for this run
    Then the gantt_chart_text should specify dateFormat as "YYYY-MM-DD HH:mm:ss"
    And the gantt_chart_text should specify axisFormat as "%H:%M:%S"
    And timestamps should be formatted correctly in the output

  Scenario: Generate Gantt chart with section groupings
    Given a completed email processing run with all phases
    And the run transitioned through CONNECTING, FETCHING, CATEGORIZING, LABELING, COMPLETED
    When the Gantt chart is generated for this run
    Then the gantt_chart_text should have an "Initialization" section
    And the gantt_chart_text should have a "Fetching" section
    And the gantt_chart_text should have a "Categorization" section
    And the gantt_chart_text should have a "Labeling" section
    And the gantt_chart_text should have a "Completion" section

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

  Scenario: Gantt chart text is valid Mermaid syntax
    Given a completed processing run with all phases
    When the Gantt chart is generated
    Then the output should start with "gantt"
    And the output should contain a valid "title" directive
    And the output should contain a valid "dateFormat" directive
    And the output should contain a valid "axisFormat" directive
    And each task line should follow Mermaid task syntax
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. IGanttChartGenerator Interface
   - Define abstract method `generate(transitions, title, include_zero_duration) -> str`
   - Define abstract method `validate_syntax(gantt_text) -> bool`
   - Place in `/root/repo/services/interfaces/gantt_chart_generator_interface.py`

2. GanttChartGenerator Implementation
   - Implement `generate()` to produce valid Mermaid Gantt chart text
   - Implement `validate_syntax()` to verify Mermaid syntax correctness
   - Place in `/root/repo/services/gantt_chart_generator.py`

3. State-to-Section Mapping
   - CONNECTING -> "Initialization"
   - FETCHING -> "Fetching"
   - PROCESSING -> "Processing"
   - CATEGORIZING -> "Categorization"
   - LABELING -> "Labeling"
   - COMPLETED -> "Completion"
   - ERROR -> "Error"
   - Unknown states -> "Other"

4. Date/Time Formatting
   - dateFormat: `YYYY-MM-DD HH:mm:ss`
   - axisFormat: `%H:%M:%S`
   - Timestamps formatted as `YYYY-MM-DD HH:mm:ss` in task lines

5. Duration Formatting
   - Convert `duration_seconds` (float) to Mermaid duration syntax
   - Format as `Ns` where N is the rounded integer seconds
   - Minimum duration is 1s for visibility

6. Task ID Generation
   - Generate unique, valid Mermaid identifiers
   - Format: `{state_lowercase}_{index}` (e.g., `connecting_0`, `fetching_1`)
   - Sanitize: lowercase, replace spaces/hyphens with underscores

7. Task Status Markers
   - `done` for completed transitions
   - `crit` for ERROR state
   - `active` for in-progress (future enhancement)

Edge Cases to Handle:
- Empty transitions list: Return minimal valid Gantt chart
- Zero-duration tasks: Skip by default unless include_zero_duration=True
- Unknown states: Map to "Other" section
- Special characters in descriptions: Escape or sanitize
- Very long descriptions: Truncate to 50 characters
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-gantt-chart-generator-core.md
Gap Analysis: specs/GAP-ANALYSIS-gantt-chart-generator-core.md

Dependency from Sub-task 1 (State Transition Tracking):
- `StateTransition` dataclass in `/root/repo/services/state_transition.py`
- Fields: state, step_description, timestamp, duration_seconds
- Import: `from services.state_transition import StateTransition`

Reuse Opportunities (from gap analysis):
- StateTransition dataclass provides clean input format
- Follow interface pattern from `/root/repo/services/interfaces/`
- Follow service implementation patterns from existing services

New Components Needed:
- `/root/repo/services/interfaces/gantt_chart_generator_interface.py` - Interface definition
- `/root/repo/services/gantt_chart_generator.py` - Implementation
- `/root/repo/tests/unit/test_gantt_chart_generator.py` - Unit tests

Example Mermaid Output:
```
gantt
    title Email Processing: user@gmail.com
    dateFormat YYYY-MM-DD HH:mm:ss
    axisFormat %H:%M:%S

    section Initialization
    Connecting to Gmail IMAP :done, connecting_0, 2025-01-01 10:00:00, 5s

    section Fetching
    Fetching emails from inbox :done, fetching_1, 2025-01-01 10:00:05, 30s

    section Categorization
    Categorizing 45 emails :done, categorizing_2, 2025-01-01 10:00:35, 85s

    section Labeling
    Applying Gmail labels :done, labeling_3, 2025-01-01 10:02:00, 25s

    section Completion
    Processing completed :done, completed_4, 2025-01-01 10:02:25, 5s
```
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max per file, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Maintain consistency with project structure
- Interface in `/root/repo/services/interfaces/`
- Implementation in `/root/repo/services/`
- Tests in `/root/repo/tests/unit/`

File Structure:
```
/root/repo/
  services/
    interfaces/
      gantt_chart_generator_interface.py  # New: IGanttChartGenerator
    gantt_chart_generator.py              # New: GanttChartGenerator
    state_transition.py                   # Existing: StateTransition (input)
  tests/
    unit/
      test_gantt_chart_generator.py       # New: Unit tests
    bdd/
      gantt_chart_generator_core.feature  # Existing: BDD scenarios
```
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Generate Gantt chart for a completed processing run
- [ ] Scenario: Generate Gantt chart with proper date format
- [ ] Scenario: Generate Gantt chart with section groupings
- [ ] Scenario: Generate Gantt chart with duration formatting
- [ ] Scenario: Gantt chart text is valid Mermaid syntax
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- Generated Mermaid syntax is valid and renderable
- StateTransition dataclass is used as input
- Interface pattern is followed consistently
</success_criteria>
