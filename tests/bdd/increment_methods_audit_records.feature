Feature: Increment Methods for Categorized and Skipped Email Counts
  As an email processing system
  I want to increment audit counters for categorized and skipped emails
  So that processing statistics are accurately tracked throughout each session

  Background:
    Given the audit recording system is available

  Scenario: Increment categorized count with default value
    Given an active processing session exists
    When the system records an email as categorized
    Then the categorized email count increases by one

  Scenario: Increment skipped count with batch value
    Given an active processing session exists
    When the system records five emails as skipped
    Then the skipped email count increases by five

  Scenario: Increment is silent when no session is active
    Given no processing session is active
    When the system attempts to record an email as categorized
    Then no error occurs
    And no count is recorded

  Scenario: Increments are cumulative within a session
    Given an active processing session exists
    When the system records three emails as categorized
    And the system records two more emails as categorized
    Then the categorized email count shows five total
