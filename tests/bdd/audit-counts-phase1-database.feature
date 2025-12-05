Feature: Email Processing Audit Count Database Columns
  As a system administrator
  I want the ProcessingRun table to include audit count columns
  So that email processing statistics can be persisted for reporting

  Background:
    Given the database schema has been initialized

  Scenario: ProcessingRun model includes emails_reviewed column
    When a new ProcessingRun record is created
    Then the record should have an "emails_reviewed" field
    And the "emails_reviewed" field should be an integer
    And the "emails_reviewed" field should default to 0
    And the "emails_reviewed" field should not accept null values

  Scenario: ProcessingRun model includes emails_tagged column
    When a new ProcessingRun record is created
    Then the record should have an "emails_tagged" field
    And the "emails_tagged" field should be an integer
    And the "emails_tagged" field should default to 0
    And the "emails_tagged" field should not accept null values

  Scenario: ProcessingRun model includes emails_deleted column
    When a new ProcessingRun record is created
    Then the record should have an "emails_deleted" field
    And the "emails_deleted" field should be an integer
    And the "emails_deleted" field should default to 0
    And the "emails_deleted" field should not accept null values

  Scenario: ProcessingRun record stores custom audit count values
    Given a ProcessingRun record is created with:
      | emails_reviewed | 150 |
      | emails_tagged   | 25  |
      | emails_deleted  | 42  |
    When the record is retrieved from the database
    Then the "emails_reviewed" value should be 150
    And the "emails_tagged" value should be 25
    And the "emails_deleted" value should be 42

  Scenario: New ProcessingRun records default audit counts to zero
    Given a ProcessingRun record is created without specifying audit counts
    When the record is retrieved from the database
    Then the "emails_reviewed" value should be 0
    And the "emails_tagged" value should be 0
    And the "emails_deleted" value should be 0
