Feature: Category Tally Repository Operations
  As a system component
  I need to persist and retrieve category tallies
  So that recommendations can be generated from historical data

  Background:
    Given the database is initialized with the category tallies schema

  Scenario: Save a new daily tally
    Given no tally exists for "test@gmail.com" on "2025-11-28"
    When a daily tally is saved with:
      | email_address   | test@gmail.com |
      | tally_date      | 2025-11-28     |
      | Marketing       | 45             |
      | Advertising     | 32             |
      | Personal        | 12             |
      | total_emails    | 89             |
    Then the tally should be persisted in the database
    And retrieving the tally should return the saved data

  Scenario: Update an existing daily tally
    Given a tally exists for "test@gmail.com" on "2025-11-28" with:
      | category  | count |
      | Marketing | 20    |
    When the tally is updated with:
      | category  | count |
      | Marketing | 45    |
      | Personal  | 10    |
    Then the tally should reflect the updated values
    And the updated_at timestamp should be newer than created_at

  Scenario: Retrieve tallies for a date range
    Given tallies exist for "test@gmail.com":
      | date       | Marketing | Personal |
      | 2025-11-22 | 30        | 10       |
      | 2025-11-23 | 35        | 12       |
      | 2025-11-24 | 28        | 8        |
      | 2025-11-25 | 40        | 15       |
      | 2025-11-26 | 32        | 11       |
      | 2025-11-27 | 38        | 9        |
      | 2025-11-28 | 42        | 13       |
    When tallies are retrieved for "2025-11-22" to "2025-11-28"
    Then 7 daily tallies should be returned
    And each tally should contain the correct category counts

  Scenario: Get aggregated tallies across date range
    Given tallies exist for "test@gmail.com":
      | date       | Marketing | Personal | Other |
      | 2025-11-22 | 30        | 10       | 5     |
      | 2025-11-23 | 35        | 12       | 8     |
      | 2025-11-24 | 28        | 8        | 4     |
      | 2025-11-25 | 40        | 15       | 10    |
      | 2025-11-26 | 32        | 11       | 7     |
      | 2025-11-27 | 38        | 9        | 6     |
      | 2025-11-28 | 42        | 13       | 5     |
    When aggregated tallies are requested for "2025-11-22" to "2025-11-28"
    Then the total_emails should be 368
    And days_with_data should be 7
    And category_summaries should include "Marketing" with total_count 245
    And category_summaries should include "Personal" with total_count 78
    And category_summaries should include percentages for each category

  Scenario: Calculate percentages correctly in aggregation
    Given tallies exist for "test@gmail.com":
      | date       | Marketing | Personal |
      | 2025-11-28 | 70        | 30       |
    When aggregated tallies are requested for "2025-11-28" to "2025-11-28"
    Then "Marketing" percentage should be 70.0
    And "Personal" percentage should be 30.0

  Scenario: Calculate daily averages in aggregation
    Given tallies exist for "test@gmail.com":
      | date       | Marketing |
      | 2025-11-25 | 30        |
      | 2025-11-26 | 40        |
      | 2025-11-27 | 50        |
      | 2025-11-28 | 60        |
    When aggregated tallies are requested for "2025-11-25" to "2025-11-28"
    Then "Marketing" daily_average should be 45.0

  Scenario: Delete tallies older than cutoff date
    Given tallies exist for "test@gmail.com":
      | date       | Marketing |
      | 2025-10-01 | 100       |
      | 2025-10-15 | 100       |
      | 2025-11-01 | 100       |
      | 2025-11-28 | 100       |
    When tallies before "2025-11-01" are deleted
    Then 2 tallies should be deleted
    And tallies for "2025-11-01" and "2025-11-28" should still exist

  Scenario: Retrieve single tally by account and date
    Given a tally exists for "test@gmail.com" on "2025-11-28" with:
      | category  | count |
      | Marketing | 50    |
    When the tally is retrieved for "test@gmail.com" on "2025-11-28"
    Then the tally should be returned
    And the category_counts should match the stored data

  Scenario: Return None for non-existent tally
    Given no tally exists for "unknown@gmail.com" on "2025-11-28"
    When the tally is retrieved for "unknown@gmail.com" on "2025-11-28"
    Then the result should be None

  Scenario: Handle multiple accounts independently
    Given tallies exist:
      | email           | date       | Marketing |
      | user1@gmail.com | 2025-11-28 | 100       |
      | user2@gmail.com | 2025-11-28 | 200       |
    When aggregated tallies are requested for "user1@gmail.com"
    Then total_emails should be 100
    When aggregated tallies are requested for "user2@gmail.com"
    Then total_emails should be 200

  Scenario: Empty aggregation for account with no data
    Given no tallies exist for "empty@gmail.com"
    When aggregated tallies are requested for "empty@gmail.com"
    Then total_emails should be 0
    And days_with_data should be 0
    And category_summaries should be empty
