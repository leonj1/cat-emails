Feature: Category Trend Analysis
  As a user of the email categorization system
  I want to understand trends in my email categories
  So that I can make informed decisions about blocking categories

  Background:
    Given the trend analysis system is initialized

  Scenario: Increasing trend is detected
    Given a user "test@gmail.com" has daily tallies for "Marketing":
      | date       | count |
      | 2025-11-22 | 20    |
      | 2025-11-23 | 22    |
      | 2025-11-24 | 25    |
      | 2025-11-25 | 35    |
      | 2025-11-26 | 40    |
      | 2025-11-27 | 45    |
      | 2025-11-28 | 50    |
    When the trend is calculated for "Marketing"
    Then the trend direction should be "increasing"
    And the trend percentage change should be positive

  Scenario: Decreasing trend is detected
    Given a user "test@gmail.com" has daily tallies for "Marketing":
      | date       | count |
      | 2025-11-22 | 50    |
      | 2025-11-23 | 45    |
      | 2025-11-24 | 40    |
      | 2025-11-25 | 30    |
      | 2025-11-26 | 25    |
      | 2025-11-27 | 22    |
      | 2025-11-28 | 20    |
    When the trend is calculated for "Marketing"
    Then the trend direction should be "decreasing"
    And the trend percentage change should be negative

  Scenario: Stable trend is detected when variation is within threshold
    Given a user "test@gmail.com" has daily tallies for "Marketing":
      | date       | count |
      | 2025-11-22 | 30    |
      | 2025-11-23 | 32    |
      | 2025-11-24 | 28    |
      | 2025-11-25 | 31    |
      | 2025-11-26 | 29    |
      | 2025-11-27 | 30    |
      | 2025-11-28 | 31    |
    When the trend is calculated for "Marketing"
    Then the trend direction should be "stable"
    And the trend percentage change should be between -15 and 15 percent

  Scenario: Trend is stable with minimal data
    Given a user "test@gmail.com" has daily tallies for "Marketing":
      | date       | count |
      | 2025-11-28 | 30    |
    When the trend is calculated for "Marketing"
    Then the trend direction should be "stable"

  Scenario: Trend handles zero counts in first half
    Given a user "test@gmail.com" has daily tallies for "Marketing":
      | date       | count |
      | 2025-11-22 | 0     |
      | 2025-11-23 | 0     |
      | 2025-11-24 | 0     |
      | 2025-11-25 | 10    |
      | 2025-11-26 | 15    |
      | 2025-11-27 | 20    |
      | 2025-11-28 | 25    |
    When the trend is calculated for "Marketing"
    Then the trend direction should be "increasing"

  Scenario: Recommendation includes trend information
    Given a user "test@gmail.com" has daily tallies for "Marketing" showing an increasing trend
    And "Marketing" qualifies for a recommendation
    When the user requests blocking recommendations
    Then the recommendation for "Marketing" should mention the trend
    And the reason should indicate the category is "trending upward"

  Scenario: Detailed recommendation reasons include daily breakdown
    Given a user "test@gmail.com" has daily tallies for "Marketing":
      | date       | count |
      | 2025-11-22 | 32    |
      | 2025-11-23 | 38    |
      | 2025-11-24 | 35    |
      | 2025-11-25 | 30    |
      | 2025-11-26 | 42    |
      | 2025-11-27 | 36    |
      | 2025-11-28 | 32    |
    When the user requests detailed reasons for "Marketing" recommendation
    Then the response should include daily_breakdown with 7 entries
    And each entry should have a date and count
    And the trend_direction should be provided
    And the trend_percentage_change should be provided

  Scenario: Comparable categories are included in detailed reasons
    Given a user "test@gmail.com" has category tallies:
      | category        | percentage |
      | Marketing       | 35.2       |
      | Advertising     | 22.4       |
      | Service-Updates | 12.1       |
    When the user requests detailed reasons for "Marketing" recommendation
    Then the response should include comparable_categories
    And comparable_categories should include "Advertising" with 22.4 percent
    And comparable_categories should include "Service-Updates" with 12.1 percent

  Scenario: Recommendation factors are clearly listed
    Given a user "test@gmail.com" has "Marketing" category with:
      | metric           | value      |
      | total_count      | 245        |
      | percentage       | 35.2       |
      | daily_average    | 35         |
      | trend            | increasing |
      | trend_change     | 8.5        |
    When the user requests detailed reasons for "Marketing" recommendation
    Then the recommendation_factors should include "High volume: 245 emails in 7 days"
    And the recommendation_factors should include "Significant percentage: 35.2% of total inbox"
    And the recommendation_factors should include information about the trend
