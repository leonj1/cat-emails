Feature: Gantt Chart Text Generation for Email Processing Runs
  As a system administrator
  I want to see a Gantt chart visualization of email processing runs
  So that I can understand the timing of each processing phase and identify bottlenecks

  Background:
    Given the processing status manager is initialized
    And state transition tracking is enabled

  # ============================================
  # GANTT CHART GENERATION - HAPPY PATHS
  # ============================================

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
    And the run transitioned through CONNECTING, FETCHING, PROCESSING, CATEGORIZING, LABELING, COMPLETED
    When the Gantt chart is generated for this run
    Then the gantt_chart_text should have an "Initialization" section
    And the gantt_chart_text should have a "Fetching" section
    And the gantt_chart_text should have a "Processing" section
    And the gantt_chart_text should have a "Labeling" section
    And the gantt_chart_text should have a "Completion" section

  Scenario: Generate Gantt chart for multi-run history
    Given completed processing runs exist for:
      | email_address      | start_time          | end_time            |
      | user1@gmail.com    | 2025-01-01 10:00:00 | 2025-01-01 10:02:00 |
      | user2@gmail.com    | 2025-01-01 11:00:00 | 2025-01-01 11:03:00 |
    When a combined Gantt chart is generated for all runs
    Then each run should have its own section in the combined chart
    And the chart should be valid Mermaid syntax

  # ============================================
  # STATE TRANSITION TRACKING
  # ============================================

  Scenario: Record state transitions during email processing
    Given a processing run is started for "user@gmail.com"
    When the processing state changes to "CONNECTING" with step "Connecting to Gmail IMAP"
    And the processing state changes to "FETCHING" with step "Fetching emails"
    And the processing state changes to "CATEGORIZING" with step "Categorizing emails"
    Then 3 state transitions should be recorded
    And each transition should have a timestamp
    And each transition should have the state and step description

  Scenario: Calculate duration between state transitions
    Given a processing run is started for "user@gmail.com" at "2025-01-01 10:00:00"
    When the processing state changes to "CONNECTING" at "2025-01-01 10:00:00"
    And the processing state changes to "FETCHING" at "2025-01-01 10:00:05"
    Then the CONNECTING transition should have a duration of 5.0 seconds

  Scenario: Clear state transitions when run completes
    Given a processing run is started for "user@gmail.com"
    And state transitions have been recorded
    When the processing run is archived
    Then the transitions should be included in the archived run
    And the active transition list should be cleared

  Scenario: State transitions persist in archived run data
    Given a completed processing run with transitions
    When the run is archived to history
    Then the archived run should contain state_transitions array
    And each transition should have state, step_description, timestamp, and duration_seconds

  # ============================================
  # API RESPONSE ENHANCEMENT
  # ============================================

  Scenario: Include gantt_chart_text in processing history response
    Given completed processing runs exist with state transitions
    When the processing history is requested
    Then each run in the response should include a gantt_chart_text field
    And the gantt_chart_text should be valid Mermaid syntax

  Scenario: Return gantt chart for each run per account
    Given completed processing runs exist for:
      | email_address   | run_count |
      | user1@gmail.com | 3         |
      | user2@gmail.com | 2         |
    When the processing history is requested
    Then each of the 5 runs should have its own gantt_chart_text
    And each gantt chart should reference the correct email address

  Scenario: Handle empty history with no completed runs
    Given no processing runs have been completed
    When the processing history is requested
    Then the response should contain an empty recent_runs array
    And no gantt_chart_text fields should be present

  Scenario: Maintain backward compatibility with existing API consumers
    Given a completed processing run exists with state transitions
    When the processing history is requested
    Then the response should include all existing fields:
      | field            |
      | email_address    |
      | start_time       |
      | end_time         |
      | duration_seconds |
      | final_state      |
      | final_step       |
      | emails_reviewed  |
      | emails_tagged    |
      | emails_deleted   |
    And new fields should be additional, not replacing existing fields

  # ============================================
  # EDGE CASES - ERROR HANDLING
  # ============================================

  Scenario: Generate Gantt chart for run that failed during processing
    Given a processing run for "user@gmail.com" failed during CATEGORIZING
    And the run has the following state transitions:
      | state        | step_description          | timestamp           | duration_seconds |
      | CONNECTING   | Connecting to Gmail IMAP  | 2025-01-01 10:00:00 | 5.0              |
      | FETCHING     | Fetching emails           | 2025-01-01 10:00:05 | 30.0             |
      | CATEGORIZING | Categorizing emails       | 2025-01-01 10:00:35 | 45.0             |
      | ERROR        | AI API Error              | 2025-01-01 10:01:20 | 0                |
    When the Gantt chart is generated for this run
    Then the gantt_chart_text should contain an "Error" section
    And the error task should be marked as "crit"
    And the title should indicate "(ERROR)"

  Scenario: Generate Gantt chart for run with connection failure
    Given a processing run for "user@gmail.com" failed during CONNECTING
    And the run has only a CONNECTING transition followed by ERROR
    When the Gantt chart is generated for this run
    Then the gantt_chart_text should show the partial progress
    And the CONNECTING task should be marked as "crit"
    And the error should be reflected in the chart

  # ============================================
  # EDGE CASES - ZERO AND MINIMAL DURATION
  # ============================================

  Scenario: Generate Gantt chart with zero-duration phase
    Given a processing run has a transition with zero duration
    And the FETCHING phase completed in 0 seconds
    When the Gantt chart is generated for this run
    Then the zero-duration phase should appear in the chart
    And the chart should display a minimal visual representation

  Scenario: Generate Gantt chart with very short run
    Given a processing run completed in less than 1 second total
    And all transitions occurred within 1 second
    When the Gantt chart is generated for this run
    Then the gantt_chart_text should be valid
    And all phases should be represented

  Scenario: Generate Gantt chart with very long run
    Given a processing run took over 1 hour to complete
    And the CATEGORIZING phase took 45 minutes
    When the Gantt chart is generated for this run
    Then the duration should be formatted appropriately
    And the chart should remain readable

  # ============================================
  # EDGE CASES - MISSING OR INCOMPLETE DATA
  # ============================================

  Scenario: Generate Gantt chart with minimal transitions
    Given a processing run exists with only start and end states
    And only CONNECTING and COMPLETED transitions were recorded
    When the Gantt chart is generated for this run
    Then the gantt_chart_text should show available phases only
    And missing phases should not cause errors

  Scenario: Handle run with missing end time
    Given a processing run is still in progress
    And the end_time is not yet set
    When the Gantt chart is requested for this run
    Then the chart should show phases up to the current state
    And the final phase should be marked as "active" instead of "done"

  Scenario: Handle legacy runs without transition data
    Given a processing run exists from before transition tracking was enabled
    And the run has no state_transitions recorded
    When the processing history is requested
    Then the run should still be included in the response
    And the gantt_chart_text should be empty or indicate no data available

  # ============================================
  # EDGE CASES - MULTIPLE ACCOUNTS
  # ============================================

  Scenario: Handle multiple accounts in history with varying completion states
    Given the following processing history exists:
      | email_address   | final_state | has_transitions |
      | user1@gmail.com | COMPLETED   | yes             |
      | user2@gmail.com | ERROR       | yes             |
      | user3@gmail.com | COMPLETED   | no              |
    When the processing history is requested
    Then user1 should have a complete Gantt chart
    And user2 should have a Gantt chart with error indication
    And user3 should have minimal or empty Gantt data

  Scenario: Ensure account isolation in Gantt chart data
    Given concurrent processing runs exist for:
      | email_address   | processing_at   |
      | user1@gmail.com | 2025-01-01 10:00 |
      | user2@gmail.com | 2025-01-01 10:00 |
    When both runs complete
    Then each run should have its own independent Gantt chart
    And transitions from one account should not appear in another

  # ============================================
  # MERMAID SYNTAX VALIDATION
  # ============================================

  Scenario: Gantt chart text is valid Mermaid syntax
    Given a completed processing run with all phases
    When the Gantt chart is generated
    Then the output should start with "gantt"
    And the output should contain a valid "title" directive
    And the output should contain a valid "dateFormat" directive
    And the output should contain a valid "axisFormat" directive
    And each task line should follow Mermaid task syntax

  Scenario: Special characters in email address are escaped
    Given a processing run for "user+test@gmail.com"
    When the Gantt chart is generated
    Then the title should handle the special characters safely
    And the Mermaid syntax should remain valid

  Scenario: Long step descriptions are handled gracefully
    Given a processing run with a very long step description
    And the step description exceeds 100 characters
    When the Gantt chart is generated
    Then the task name should be truncated or wrapped appropriately
    And the Mermaid syntax should remain valid
