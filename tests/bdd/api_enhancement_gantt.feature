Feature: API Enhancement for Gantt Chart Text
  As a client application
  I want the processing history API to include gantt_chart_text for each run
  So that I can render Gantt chart visualizations in the dashboard

  Background:
    Given the processing status manager is initialized
    And completed processing runs exist with state transitions

  Scenario: Include gantt_chart_text in processing history response
    Given a completed processing run exists for "user@gmail.com"
    And the run has recorded state transitions
    When the processing history is requested
    Then the response should include a "gantt_chart_text" field for the run
    And the gantt_chart_text should contain valid Mermaid syntax starting with "gantt"
    And the gantt_chart_text should contain a title with "user@gmail.com"

  Scenario: Return gantt chart for each run per account
    Given completed processing runs exist for:
      | email_address   |
      | user1@gmail.com |
      | user2@gmail.com |
      | user1@gmail.com |
    When the processing history is requested
    Then each of the 3 runs should have its own gantt_chart_text
    And the gantt chart for user1 runs should reference "user1@gmail.com"
    And the gantt chart for user2 runs should reference "user2@gmail.com"

  Scenario: Handle empty history with no completed runs
    Given no processing runs have been completed
    When the processing history is requested
    Then the response should contain an empty recent_runs array
    And total_retrieved should be 0

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
      | state_transitions |
    And gantt_chart_text should be an additional field, not replacing any existing field

  Scenario: Generate Gantt chart for run that failed during processing
    Given a processing run for "user@gmail.com" ended with ERROR state
    And the run has recorded state transitions including the error
    When the processing history is requested
    Then the response should include the failed run
    And the gantt_chart_text should contain partial progress up to the error
    And the gantt_chart_text should indicate the error state
