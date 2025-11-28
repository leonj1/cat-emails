Feature: Integration with Background Email Processing
  As a background email processor
  I want to integrate category aggregation into the email processing flow
  So that tallies are automatically recorded during normal operation

  Background:
    Given the email processing system is initialized
    And category aggregation is enabled

  Scenario: Categories are recorded during email processing
    Given a user "test@gmail.com" is configured for processing
    And the following emails are fetched:
      | subject                | category    |
      | Special Offer!         | Marketing   |
      | Your Invoice           | Wants-Money |
      | Hey, how are you?      | Personal    |
      | Weekly Newsletter      | Marketing   |
      | Bank Statement         | Financial-Notification |
    When the background processor processes the emails
    Then the category aggregator should receive a batch with:
      | category              | count |
      | Marketing             | 2     |
      | Wants-Money           | 1     |
      | Personal              | 1     |
      | Financial-Notification | 1    |

  Scenario: Aggregator is flushed after each processing run
    Given a user "test@gmail.com" is configured for processing
    And the aggregator buffer size is 100
    When the background processor processes 10 emails
    Then the aggregator should be flushed
    And the tallies should be persisted to the database

  Scenario: Multiple accounts are processed independently
    Given the following users are configured for processing:
      | email           |
      | user1@gmail.com |
      | user2@gmail.com |
    When the background processor processes emails for all accounts
    Then each account should have separate tally records
    And the aggregator should flush after each account

  Scenario: Processing continues if aggregation fails
    Given a user "test@gmail.com" is configured for processing
    And the aggregation database is temporarily unavailable
    When the background processor processes emails
    Then the email processing should complete successfully
    And an error should be logged for aggregation failure

  Scenario: Aggregator initialization at application startup
    When the application starts
    Then the CategoryAggregator should be initialized
    And the CategoryTallyRepository should be initialized
    And the BlockingRecommendationService should be initialized

  Scenario: Aggregator shutdown flushes remaining buffer
    Given the aggregator has buffered data
    When the application shuts down
    Then the aggregator should flush all buffered data
    And no data should be lost

  Scenario: Data cleanup job removes old tallies
    Given tallies exist older than 30 days
    When the data cleanup job runs
    Then tallies older than 30 days should be deleted
    And recent tallies should be preserved

  Scenario: Hourly processing accumulates daily tallies
    Given a user "test@gmail.com" is configured for processing
    When the background processor runs at "2025-11-28 10:00:00" with:
      | category  | count |
      | Marketing | 5     |
    And the background processor runs at "2025-11-28 14:00:00" with:
      | category  | count |
      | Marketing | 8     |
    Then the daily tally for "2025-11-28" should show:
      | category  | count |
      | Marketing | 13    |

  Scenario: Processing spans midnight correctly
    Given a user "test@gmail.com" is configured for processing
    When the background processor runs at "2025-11-27 23:30:00" with:
      | category  | count |
      | Marketing | 5     |
    And the background processor runs at "2025-11-28 00:30:00" with:
      | category  | count |
      | Marketing | 3     |
    Then the tally for "2025-11-27" should show 5 "Marketing" emails
    And the tally for "2025-11-28" should show 3 "Marketing" emails
