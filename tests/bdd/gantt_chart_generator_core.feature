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
