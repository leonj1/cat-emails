---
executor: bdd
source_feature: ./tests/bdd/blocking-recommendations.feature
---

<objective>
Implement the Blocking Recommendations feature that analyzes email category tallies and generates intelligent recommendations for categories users should consider blocking, based on percentage thresholds and volume analysis.
</objective>

<gherkin>
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
    Because the count is below the minimum threshold of 10

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
    Because the percentage is below the threshold of 10 percent

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
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **IBlockingRecommendationService Interface** (`services/interfaces/blocking_recommendation_interface.py`)
   - Define: `get_recommendations(email_address, days)`, `get_recommendation_reasons(email_address, category)`, `get_blocked_categories_for_account(email_address)`

2. **ICategoryAggregationConfig Interface** (`services/interfaces/category_aggregation_config_interface.py`)
   - Define: `get_recommendation_threshold_percentage()`, `get_minimum_email_count()`, `get_excluded_categories()`, `get_retention_days()`

3. **BlockingRecommendation Pydantic Model** (`models/recommendation_models.py`)
   - Fields: category, strength (enum: HIGH/MEDIUM/LOW), email_count, percentage, reason

4. **BlockingRecommendationResult Pydantic Model** (`models/recommendation_models.py`)
   - Fields: email_address, period_start, period_end, total_emails_analyzed, recommendations (list), already_blocked (list), generated_at

5. **RecommendationStrength Enum** (`models/recommendation_models.py`)
   - Values: HIGH, MEDIUM, LOW

6. **BlockingRecommendationService Implementation** (`services/blocking_recommendation_service.py`)
   - Implement recommendation algorithm per spec section 4.3
   - Integrate with DomainService for blocked categories
   - Calculate strength based on percentage thresholds

7. **CategoryAggregationConfig Implementation** (`services/category_aggregation_config.py`)
   - Configurable thresholds and excluded categories
   - Default values per spec section 8

Recommendation Strength Thresholds (per spec section 9):
- HIGH: >= 25% of inbox
- MEDIUM: >= 15% of inbox
- LOW: >= threshold (default 10%)

Configuration Defaults (per spec section 8):
- threshold_percentage: 10.0
- minimum_count: 10
- excluded_categories: ["Personal", "Work-related", "Financial-Notification"]
- retention_days: 30

Edge Cases to Handle:
- Zero total emails (return empty recommendations)
- All categories excluded
- Already blocked categories in tallies
- Single day vs multi-day analysis
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-email-category-aggregation.md (Sections 4.3, 8, 9)
Gap Analysis: specs/GAP-ANALYSIS.md

Reuse Opportunities (from gap analysis):
- Use `DomainService.fetch_blocked_categories()` from `/root/repo/domain_service.py`
- Follow service interface pattern
- Integrate with repository from prompt 001

Dependencies (must be implemented first):
- `ICategoryTallyRepository` from prompt 001
- `AggregatedCategoryTally` model from prompt 001
- Trend calculation from prompt 003

New Components Needed:
- `/root/repo/services/interfaces/blocking_recommendation_interface.py`
- `/root/repo/services/interfaces/category_aggregation_config_interface.py`
- `/root/repo/services/blocking_recommendation_service.py`
- `/root/repo/services/category_aggregation_config.py`
- `/root/repo/models/recommendation_models.py` (extend from prompt 003)
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Constructor injection for repository and config
- Integration with DomainService for blocked categories
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: User receives high-strength recommendation for dominant category
- [ ] Scenario: User receives medium-strength recommendation
- [ ] Scenario: User receives low-strength recommendation
- [ ] Scenario: Personal emails are never recommended for blocking
- [ ] Scenario: Work-related emails are never recommended for blocking
- [ ] Scenario: Financial notifications are never recommended for blocking
- [ ] Scenario: Low volume categories are not recommended
- [ ] Scenario: Categories below percentage threshold are not recommended
- [ ] Scenario: Multiple recommendations are sorted by strength and count
- [ ] Scenario: Recommendations show already blocked categories
- [ ] Scenario: No recommendations when no email data exists
- [ ] Scenario: Custom rolling window period
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- Recommendation algorithm correctly applies thresholds
- Excluded categories are properly filtered
- Integration with DomainService works correctly
</success_criteria>
