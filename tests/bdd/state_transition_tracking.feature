Feature: State Transition Tracking for Email Processing Runs
  As a system administrator
  I want state transitions to be tracked during email processing
  So that I can generate Gantt chart visualizations and analyze processing performance

  Background:
    Given the processing status manager is initialized
    And state transition tracking is enabled

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
