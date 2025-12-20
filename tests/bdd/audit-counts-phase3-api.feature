Feature: Email Processing Audit Counts - API Response
  As a client application
  I want the processing runs API to include audit count fields
  So that I can display email processing statistics in the dashboard

  Background:
    Given the database contains processing run records

  Scenario: API response includes emails_reviewed field
    Given a processing run exists with emails_reviewed set to 100
    When I retrieve the processing runs via the API
    Then the response should include an "emails_reviewed" field
    And the "emails_reviewed" value should be 100

  Scenario: API response includes emails_tagged field
    Given a processing run exists with emails_tagged set to 45
    When I retrieve the processing runs via the API
    Then the response should include an "emails_tagged" field
    And the "emails_tagged" value should be 45

  Scenario: API response includes emails_deleted field from database
    Given a processing run exists with emails_deleted set to 30
    When I retrieve the processing runs via the API
    Then the response should include an "emails_deleted" field
    And the "emails_deleted" value should be 30

  Scenario: Null audit count values default to zero in API response
    Given a processing run exists with null audit count values
    When I retrieve the processing runs via the API
    Then the "emails_reviewed" value should be 0
    And the "emails_tagged" value should be 0
    And the "emails_deleted" value should be 0

  Scenario: API response includes all audit fields together
    Given a processing run exists with:
      | emails_reviewed | 150 |
      | emails_tagged   | 60  |
      | emails_deleted  | 25  |
    When I retrieve the processing runs via the API
    Then the response should contain all audit count fields
    And the "emails_reviewed" value should be 150
    And the "emails_tagged" value should be 60
    And the "emails_deleted" value should be 25
