Feature: Email Category Aggregation
  As a background email processor
  I want to aggregate email category counts during processing
  So that I can track email volume patterns over time

  Background:
    Given the category aggregation system is initialized
    And the database is empty

  Scenario: Record a single email categorization
    Given a user "test@gmail.com" exists in the system
    When the system records category "Marketing" for "test@gmail.com" at "2025-11-28 10:00:00"
    Then the buffer should contain 1 record for "test@gmail.com"
    And the category "Marketing" count should be 1 in the buffer

  Scenario: Record multiple categories for the same account on the same day
    Given a user "test@gmail.com" exists in the system
    When the system records the following categories for "test@gmail.com" on "2025-11-28":
      | category    | count |
      | Marketing   | 5     |
      | Advertising | 3     |
      | Personal    | 2     |
    Then the buffer should aggregate to 10 total emails for "test@gmail.com" on "2025-11-28"

  Scenario: Record batch of category counts
    Given a user "test@gmail.com" exists in the system
    When the system records a batch with the following counts for "test@gmail.com":
      | category           | count |
      | Marketing          | 45    |
      | Advertising        | 32    |
      | Personal           | 12    |
      | Work-related       | 8     |
      | Financial-Notification | 3 |
    Then the total emails recorded should be 100

  Scenario: Buffer flushes when size limit is reached
    Given a user "test@gmail.com" exists in the system
    And the buffer size limit is set to 50
    When the system records 50 individual categorization events
    Then the buffer should automatically flush to the database
    And the buffer should be empty after flush

  Scenario: Flush merges with existing daily tally
    Given a user "test@gmail.com" exists in the system
    And a daily tally exists for "test@gmail.com" on "2025-11-28" with:
      | category  | count |
      | Marketing | 20    |
      | Personal  | 5     |
    When the system records and flushes:
      | category  | count |
      | Marketing | 10    |
      | Advertising | 15  |
    Then the daily tally for "test@gmail.com" on "2025-11-28" should show:
      | category    | count |
      | Marketing   | 30    |
      | Personal    | 5     |
      | Advertising | 15    |

  Scenario: Categories accumulate across multiple processing runs
    Given a user "test@gmail.com" exists in the system
    When the system processes run 1 with categories:
      | category  | count |
      | Marketing | 15    |
    And the system processes run 2 with categories:
      | category  | count |
      | Marketing | 25    |
    And both runs are flushed
    Then the daily total for "Marketing" should be 40

  Scenario: Separate tallies are maintained for different accounts
    Given the following users exist:
      | email           |
      | user1@gmail.com |
      | user2@gmail.com |
    When the system records "Marketing" count 50 for "user1@gmail.com"
    And the system records "Marketing" count 30 for "user2@gmail.com"
    And the buffer is flushed
    Then "user1@gmail.com" should have 50 "Marketing" emails
    And "user2@gmail.com" should have 30 "Marketing" emails

  Scenario: Separate tallies are maintained for different days
    Given a user "test@gmail.com" exists in the system
    When the system records "Marketing" count 20 on "2025-11-27"
    And the system records "Marketing" count 35 on "2025-11-28"
    And the buffer is flushed
    Then the tally for "2025-11-27" should show 20 "Marketing" emails
    And the tally for "2025-11-28" should show 35 "Marketing" emails
