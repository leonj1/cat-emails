Feature: Core Audit Fields for Categorized and Skipped Emails
  As an account administrator
  I want processing audit records to track emails categorized and skipped
  So that I can monitor email processing effectiveness and identify issues

  Background:
    Given the email processing system is operational
    And audit recording is enabled

  Scenario: ProcessingRun model includes emails_categorized column
    Given a processing run is initiated for an account
    When the processing completes with some emails categorized
    Then the processing run record stores the emails_categorized count
    And the count reflects the actual number of emails that were categorized

  Scenario: ProcessingRun model includes emails_skipped column
    Given a processing run is initiated for an account
    When the processing completes with some emails skipped
    Then the processing run record stores the emails_skipped count
    And the count reflects the actual number of emails that were skipped

  Scenario: AccountStatus dataclass includes emails_categorized field
    Given an account has completed processing runs
    When the account status is retrieved
    Then the status includes the emails_categorized field
    And the field contains the cumulative count of categorized emails

  Scenario: AccountStatus dataclass includes emails_skipped field
    Given an account has completed processing runs
    When the account status is retrieved
    Then the status includes the emails_skipped field
    And the field contains the cumulative count of skipped emails
