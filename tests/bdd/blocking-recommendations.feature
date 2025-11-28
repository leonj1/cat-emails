Feature: Email Category Blocking Recommendations
  As a user of the email categorization system
  I want to receive recommendations for categories to block
  So that I can reduce unwanted email volume in my inbox

  Background:
    Given the recommendation system is initialized
    And the following configuration is set:
      | parameter             | value                                   |
      | threshold_percentage  | 10.0                                    |
      | minimum_count         | 10                                      |
      | excluded_categories   | Personal,Work-related,Financial-Notification |

  Scenario: User receives high-strength recommendation for dominant category
    Given a user "test@gmail.com" has processed emails over 7 days
    And the category tallies for "test@gmail.com" are:
      | category    | count |
      | Marketing   | 250   |
      | Advertising | 150   |
      | Personal    | 100   |
      | Other       | 200   |
    When the user requests blocking recommendations
    Then they should receive a "high" strength recommendation for "Marketing"
    And the recommendation reason should mention "35" percent
    And the recommendation reason should mention "250 emails"

  Scenario: User receives medium-strength recommendation
    Given a user "test@gmail.com" has processed emails over 7 days
    And the category tallies for "test@gmail.com" are:
      | category    | count |
      | Marketing   | 100   |
      | Advertising | 150   |
      | Personal    | 300   |
      | Other       | 450   |
    When the user requests blocking recommendations
    Then they should receive a "medium" strength recommendation for "Advertising"
    And "Advertising" percentage should be approximately 15 percent

  Scenario: User receives low-strength recommendation
    Given a user "test@gmail.com" has processed emails over 7 days
    And the category tallies for "test@gmail.com" are:
      | category        | count |
      | Marketing       | 60    |
      | Advertising     | 40    |
      | Personal        | 200   |
      | Service-Updates | 100   |
      | Other           | 200   |
    When the user requests blocking recommendations
    Then they should receive a "low" strength recommendation for "Marketing"
    And "Marketing" percentage should be approximately 10 percent

  Scenario: Personal emails are never recommended for blocking
    Given a user "test@gmail.com" has processed emails over 7 days
    And the category tallies for "test@gmail.com" are:
      | category  | count |
      | Personal  | 400   |
      | Marketing | 50    |
      | Other     | 50    |
    When the user requests blocking recommendations
    Then "Personal" should not appear in recommendations
    And the recommendation list should be empty or only contain non-excluded categories

  Scenario: Work-related emails are never recommended for blocking
    Given a user "test@gmail.com" has processed emails over 7 days
    And the category tallies for "test@gmail.com" are:
      | category     | count |
      | Work-related | 350   |
      | Marketing    | 100   |
      | Other        | 50    |
    When the user requests blocking recommendations
    Then "Work-related" should not appear in recommendations

  Scenario: Financial notifications are never recommended for blocking
    Given a user "test@gmail.com" has processed emails over 7 days
    And the category tallies for "test@gmail.com" are:
      | category               | count |
      | Financial-Notification | 300   |
      | Marketing              | 100   |
      | Other                  | 100   |
    When the user requests blocking recommendations
    Then "Financial-Notification" should not appear in recommendations

  Scenario: Low volume categories are not recommended
    Given a user "test@gmail.com" has processed emails over 7 days
    And the category tallies for "test@gmail.com" are:
      | category             | count |
      | Marketing            | 200   |
      | Appointment-Reminder | 5     |
      | Other                | 295   |
    When the user requests blocking recommendations
    Then "Appointment-Reminder" should not appear in recommendations
    # Because the count is below the minimum threshold of 10

  Scenario: Categories below percentage threshold are not recommended
    Given a user "test@gmail.com" has processed emails over 7 days
    And the category tallies for "test@gmail.com" are:
      | category    | count |
      | Marketing   | 30    |
      | Advertising | 20    |
      | Personal    | 450   |
      | Other       | 500   |
    When the user requests blocking recommendations
    Then "Marketing" should not appear in recommendations
    # Because the percentage is below the threshold of 10 percent

  Scenario: Multiple recommendations are sorted by strength and count
    Given a user "test@gmail.com" has processed emails over 7 days
    And the category tallies for "test@gmail.com" are:
      | category        | count |
      | Marketing       | 280   |
      | Advertising     | 180   |
      | Service-Updates | 120   |
      | Personal        | 100   |
      | Other           | 120   |
    When the user requests blocking recommendations
    Then the recommendations should be ordered by total count descending
    And the first recommendation should be for "Marketing"
    And the second recommendation should be for "Advertising"
    And the third recommendation should be for "Service-Updates"

  Scenario: Recommendations show already blocked categories
    Given a user "test@gmail.com" has processed emails over 7 days
    And the user has already blocked the following categories:
      | category   |
      | Wants-Money |
    And the category tallies for "test@gmail.com" are:
      | category    | count |
      | Marketing   | 200   |
      | Wants-Money | 50    |
      | Other       | 250   |
    When the user requests blocking recommendations
    Then the response should include "Wants-Money" in the already_blocked list

  Scenario: No recommendations when no email data exists
    Given a user "test@gmail.com" exists but has no email data
    When the user requests blocking recommendations
    Then the total_emails_analyzed should be 0
    And the recommendations list should be empty

  Scenario: Custom rolling window period
    Given a user "test@gmail.com" has processed emails over 14 days
    And the daily tallies are distributed over 14 days
    When the user requests blocking recommendations with days=14
    Then the period_start should be 14 days before today
    And the period_end should be today
    And the analysis should include data from all 14 days
