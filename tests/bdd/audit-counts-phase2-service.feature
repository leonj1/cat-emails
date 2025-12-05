Feature: Email Processing Audit Counts - Service Layer
  As a system administrator
  I want to track how many emails were reviewed, tagged, and deleted during processing
  So that I can monitor email processing activity and generate audit reports

  Background:
    Given a processing status manager is initialized

  Scenario: Account status includes audit count fields with default values
    When a processing session starts for "user@example.com"
    Then the current status shows emails reviewed as 0
    And the current status shows emails tagged as 0
    And the current status shows emails deleted as 0

  Scenario: Incrementing reviewed count during processing
    Given a processing session is active for "user@example.com"
    When 5 emails are marked as reviewed
    And 3 more emails are marked as reviewed
    Then the current status shows emails reviewed as 8

  Scenario: Incrementing tagged count during processing
    Given a processing session is active for "user@example.com"
    When 4 emails are marked as tagged
    Then the current status shows emails tagged as 4

  Scenario: Incrementing deleted count during processing
    Given a processing session is active for "user@example.com"
    When 2 emails are marked as deleted
    Then the current status shows emails deleted as 2

  Scenario: Audit counts are preserved when processing completes
    Given a processing session is active for "user@example.com"
    And 100 emails are marked as reviewed
    And 50 emails are marked as tagged
    And 25 emails are marked as deleted
    When the processing session completes
    Then the most recent run shows emails reviewed as 100
    And the most recent run shows emails tagged as 50
    And the most recent run shows emails deleted as 25

  Scenario: Incrementing counts without active session is ignored
    When 5 emails are marked as reviewed without an active session
    And 3 emails are marked as tagged without an active session
    And 2 emails are marked as deleted without an active session
    Then no error occurs
    And the audit counts return all zeros
