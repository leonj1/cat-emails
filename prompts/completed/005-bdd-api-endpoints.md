---
executor: bdd
source_feature: ./tests/bdd/api-endpoints.feature
---

<objective>
Implement the REST API endpoints for accessing category recommendations and statistics, integrating with the existing FastAPI service to expose the blocking recommendation functionality to client applications.
</objective>

<gherkin>
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
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **GET /api/accounts/{email_address}/recommendations** endpoint
   - Query parameter: `days` (optional, default=7, range 1-30)
   - Returns: `BlockingRecommendationResult`
   - 404 if account not found
   - 400 if days out of range

2. **GET /api/accounts/{email_address}/recommendations/{category}/details** endpoint
   - Path parameter: `category` (category name)
   - Returns: `RecommendationReason`
   - 404 if account or category not found

3. **GET /api/accounts/{email_address}/category-stats** endpoint
   - Query parameter: `days` (optional, default=7)
   - Returns: `AggregatedCategoryTally`
   - Raw statistics without recommendation logic

4. **Response Models** (Pydantic)
   - All models should be properly typed
   - JSON schema export for OpenAPI documentation
   - ISO 8601 timestamps

5. **API Integration**
   - Add to existing `/root/repo/api_service.py`
   - Follow existing tag structure (add "recommendations" tag)
   - Use existing authentication middleware
   - Follow account-based endpoint patterns

6. **Error Handling**
   - 404 for non-existent accounts
   - 400 for invalid parameters
   - Consistent error response format

Endpoint Specifications (per spec section 5):
- All endpoints under `/api/accounts/{email_address}/`
- Standard REST conventions
- JSON response format
- Proper HTTP status codes
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-email-category-aggregation.md (Section 5)
Gap Analysis: specs/GAP-ANALYSIS.md

Reuse Opportunities (from gap analysis):
- Follow endpoint patterns in `/root/repo/api_service.py`
- Reuse authentication middleware
- Follow response model patterns from `/root/repo/models/account_models.py`
- Use existing FastAPI app configuration

Dependencies (must be implemented first):
- `IBlockingRecommendationService` from prompt 004
- `BlockingRecommendationResult` model from prompt 004
- `RecommendationReason` model from prompt 003
- `ICategoryTallyRepository` from prompt 001

Integration Points:
- Add endpoints to `/root/repo/api_service.py`
- Initialize recommendation service in app startup
- Add "recommendations" tag to OpenAPI spec
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Follow FastAPI best practices
- Use Pydantic for request/response validation
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Get blocking recommendations for an account
- [ ] Scenario: Get recommendations with custom rolling window
- [ ] Scenario: Validate days parameter range
- [ ] Scenario: Account not found returns 404
- [ ] Scenario: Get detailed recommendation reasons
- [ ] Scenario: Get details for non-recommended category returns 404
- [ ] Scenario: Get raw category statistics
- [ ] Scenario: Category stats include trend information
- [ ] Scenario: API returns already blocked categories
- [ ] Scenario: Response format matches OpenAPI spec
- [ ] Scenario: Daily breakdown is sorted chronologically
- [ ] Scenario: API handles concurrent requests
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- API documentation is complete in OpenAPI spec
- Error handling is consistent with existing endpoints
- Response models properly validate output
</success_criteria>
