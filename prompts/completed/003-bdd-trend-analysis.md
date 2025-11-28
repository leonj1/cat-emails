---
executor: bdd
source_feature: ./tests/bdd/trend-analysis.feature
---

<objective>
Implement the Category Trend Analysis feature that calculates trend directions (increasing, decreasing, stable) for email categories based on historical daily tallies, providing insights into email pattern changes over time.
</objective>

<gherkin>
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
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **Trend Calculation Logic** (in `services/blocking_recommendation_service.py` or separate utility)
   - Calculate trend by comparing first half vs second half averages
   - Threshold: +/-15% change for increasing/decreasing classification
   - Handle edge cases: minimal data, zero counts

2. **RecommendationReason Pydantic Model** (`models/recommendation_models.py`)
   - Fields: category, total_count, percentage, daily_breakdown, trend_direction, trend_percentage_change, comparable_categories, recommendation_factors

3. **DailyBreakdown Pydantic Model** (`models/recommendation_models.py`)
   - Fields: date, count

4. **Trend Calculation Functions**:
   ```python
   def calculate_trend(daily_breakdown: List[DailyBreakdown]) -> str:
       """Returns 'increasing', 'decreasing', or 'stable'"""

   def calculate_trend_percentage_change(daily_breakdown: List[DailyBreakdown]) -> float:
       """Returns percentage change between first half and second half"""
   ```

5. **Integration with CategorySummary Model**
   - Add `trend` field to `CategorySummary` from prompt 001
   - Populate trend during aggregation

Trend Classification Rules (per spec section 4.4):
- Increasing: Second half average >= 15% higher than first half
- Decreasing: Second half average <= 15% lower than first half
- Stable: Change between -15% and +15%

Edge Cases to Handle:
- Single data point (return 'stable')
- Zero average in first half (avoid division by zero)
- Empty daily breakdown
- Odd number of data points (split appropriately)
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-email-category-aggregation.md (Section 4.4)
Gap Analysis: specs/GAP-ANALYSIS.md

Reuse Opportunities (from gap analysis):
- Integrate with `CategorySummary` model from prompt 001
- Use repository aggregation methods from prompt 001
- Follow Pydantic model patterns

Dependencies (must be implemented first):
- `ICategoryTallyRepository` from prompt 001
- `AggregatedCategoryTally` model from prompt 001

New Components Needed:
- `/root/repo/models/recommendation_models.py` (Pydantic models for detailed reasons)
- Trend calculation utility functions (can be in service or separate module)
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Keep trend calculation as pure functions for testability
- Integrate trend into CategorySummary during aggregation
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Increasing trend is detected
- [ ] Scenario: Decreasing trend is detected
- [ ] Scenario: Stable trend is detected when variation is within threshold
- [ ] Scenario: Trend is stable with minimal data
- [ ] Scenario: Trend handles zero counts in first half
- [ ] Scenario: Recommendation includes trend information
- [ ] Scenario: Detailed recommendation reasons include daily breakdown
- [ ] Scenario: Comparable categories are included in detailed reasons
- [ ] Scenario: Recommendation factors are clearly listed
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- Trend calculations are accurate and handle edge cases
- Trend information is correctly integrated into recommendations
</success_criteria>
