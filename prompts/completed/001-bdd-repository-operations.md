---
executor: bdd
source_feature: ./tests/bdd/repository-operations.feature
---

<objective>
Implement the Category Tally Repository feature that provides persistent storage and retrieval of daily email category tallies. This is the data layer foundation for the email category aggregation and blocking recommendations system.
</objective>

<gherkin>
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
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **ICategoryTallyRepository Interface** (`repositories/category_tally_repository_interface.py`)
   - Define abstract methods: `save_daily_tally`, `get_tally`, `get_tallies_for_period`, `get_aggregated_tallies`, `delete_tallies_before`
   - Follow existing `DatabaseRepositoryInterface` pattern

2. **DailyCategoryTally Pydantic Model** (`models/category_tally_models.py`)
   - Fields: id, email_address, tally_date, category_counts (Dict[str, int]), total_emails, created_at, updated_at
   - Validation for required fields

3. **AggregatedCategoryTally Pydantic Model** (`models/category_tally_models.py`)
   - Fields: email_address, start_date, end_date, total_emails, days_with_data, category_summaries
   - CategorySummary nested model with: category, total_count, percentage, daily_average, trend

4. **CategoryTallyRepository Implementation** (`repositories/category_tally_repository.py`)
   - Implement all interface methods
   - Use SQLAlchemy for database operations
   - Support percentage calculations in aggregation
   - Support daily average calculations

5. **Database Migration** (`migrations/004_add_category_tallies.py`)
   - Create `category_daily_tallies` table with proper indexes
   - UNIQUE constraint on (email_address, tally_date, category)

Edge Cases to Handle:
- Empty result sets (no tallies for account/date range)
- Percentage calculation with zero total
- Date boundary handling
- Concurrent access (upsert semantics)
- Large date ranges with many records
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-email-category-aggregation.md
Gap Analysis: specs/GAP-ANALYSIS.md

Reuse Opportunities (from gap analysis):
- Follow `DatabaseRepositoryInterface` pattern from `/root/repo/repositories/database_repository_interface.py`
- Reuse SQLAlchemy Base from `/root/repo/models/database.py`
- Follow Pydantic model patterns from `/root/repo/models/account_models.py`
- Reference `AccountCategoryStats` model structure from `/root/repo/models/database.py`

New Components Needed:
- `/root/repo/repositories/category_tally_repository_interface.py` (interface)
- `/root/repo/repositories/category_tally_repository.py` (implementation)
- `/root/repo/models/category_tally_models.py` (Pydantic models)
- `/root/repo/migrations/004_add_category_tallies.py` (database migration)
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Maintain consistency with project structure
- Constructor dependency injection with max 3 parameters
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Save a new daily tally
- [ ] Scenario: Update an existing daily tally
- [ ] Scenario: Retrieve tallies for a date range
- [ ] Scenario: Get aggregated tallies across date range
- [ ] Scenario: Calculate percentages correctly in aggregation
- [ ] Scenario: Calculate daily averages in aggregation
- [ ] Scenario: Delete tallies older than cutoff date
- [ ] Scenario: Retrieve single tally by account and date
- [ ] Scenario: Return None for non-existent tally
- [ ] Scenario: Handle multiple accounts independently
- [ ] Scenario: Empty aggregation for account with no data
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- Repository interface is cleanly abstracted
- Database operations are efficient with proper indexing
</success_criteria>
