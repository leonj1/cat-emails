Feature: Category Recommendation API Endpoints
  As a client application
  I want to access category recommendations via REST API
  So that I can display blocking recommendations to users

  Background:
    Given the API service is running
    And the recommendation system is initialized

  Scenario: Get blocking recommendations for an account
    Given a user "test@gmail.com" has email data
    And the category tallies show "Marketing" at 35% of total
    When I send GET request to "/api/accounts/test@gmail.com/recommendations"
    Then the response status should be 200
    And the response should contain:
      | field                 | value           |
      | email_address         | test@gmail.com  |
      | total_emails_analyzed | > 0             |
    And the recommendations array should not be empty
    And generated_at should be a valid ISO timestamp

  Scenario: Get recommendations with custom rolling window
    Given a user "test@gmail.com" has email data for 14 days
    When I send GET request to "/api/accounts/test@gmail.com/recommendations?days=14"
    Then the response status should be 200
    And period_start should be 14 days before period_end

  Scenario: Validate days parameter range
    Given a user "test@gmail.com" exists
    When I send GET request to "/api/accounts/test@gmail.com/recommendations?days=45"
    Then the response status should be 400
    And the error message should indicate days must be between 1 and 30

  Scenario: Account not found returns 404
    When I send GET request to "/api/accounts/nonexistent@gmail.com/recommendations"
    Then the response status should be 404
    And the response should contain:
      | field   | value                   |
      | error   | Account not found       |

  Scenario: Get detailed recommendation reasons
    Given a user "test@gmail.com" has "Marketing" category with significant volume
    When I send GET request to "/api/accounts/test@gmail.com/recommendations/Marketing/details"
    Then the response status should be 200
    And the response should contain:
      | field             | type  |
      | category          | string |
      | total_count       | number |
      | percentage        | number |
      | daily_breakdown   | array  |
      | trend_direction   | string |
      | comparable_categories | object |
      | recommendation_factors | array |

  Scenario: Get details for non-recommended category returns 404
    Given a user "test@gmail.com" exists
    And "UnknownCategory" is not in the system
    When I send GET request to "/api/accounts/test@gmail.com/recommendations/UnknownCategory/details"
    Then the response status should be 404

  Scenario: Get raw category statistics
    Given a user "test@gmail.com" has email data
    When I send GET request to "/api/accounts/test@gmail.com/category-stats"
    Then the response status should be 200
    And the response should contain:
      | field          | type   |
      | email_address  | string |
      | period_start   | date   |
      | period_end     | date   |
      | total_emails   | number |
      | days_with_data | number |
      | categories     | array  |

  Scenario: Category stats include trend information
    Given a user "test@gmail.com" has email data
    When I send GET request to "/api/accounts/test@gmail.com/category-stats?days=7"
    Then the response status should be 200
    And each category in the categories array should have:
      | field         |
      | category      |
      | total_count   |
      | percentage    |
      | daily_average |
      | trend         |

  Scenario: API returns already blocked categories
    Given a user "test@gmail.com" has already blocked "Wants-Money"
    And the user has email data
    When I send GET request to "/api/accounts/test@gmail.com/recommendations"
    Then the response status should be 200
    And already_blocked should contain "Wants-Money"

  Scenario: Response format matches OpenAPI spec
    Given a user "test@gmail.com" has email data
    When I send GET request to "/api/accounts/test@gmail.com/recommendations"
    Then the response should match the BlockingRecommendationResult schema
    And each recommendation should match the BlockingRecommendation schema

  Scenario: Daily breakdown is sorted chronologically
    Given a user "test@gmail.com" has daily data for the past 7 days
    When I send GET request to "/api/accounts/test@gmail.com/recommendations/Marketing/details"
    Then the response status should be 200
    And daily_breakdown should be sorted by date ascending

  Scenario: API handles concurrent requests
    Given a user "test@gmail.com" has email data
    When I send 10 concurrent GET requests to "/api/accounts/test@gmail.com/recommendations"
    Then all responses should have status 200
    And all responses should return consistent data
