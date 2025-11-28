---
executor: bdd
source_feature: ./tests/bdd/category-aggregation.feature
---

<objective>
Implement the Category Aggregator feature that records and buffers email category counts during background processing, with automatic flushing to persistent storage when buffer limits are reached.
</objective>

<gherkin>
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
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **ICategoryAggregator Interface** (`services/interfaces/category_aggregator_interface.py`)
   - Define abstract methods: `record_category`, `record_batch`, `flush`
   - Follow existing service interface patterns

2. **CategoryAggregator Implementation** (`services/category_aggregator_service.py`)
   - In-memory buffer with configurable size limit
   - Automatic flush when buffer size limit is reached
   - Merge logic for combining buffered data with existing tallies
   - Thread-safe buffer operations

3. **Constructor Requirements**:
   ```python
   def __init__(self, repository: ICategoryTallyRepository, buffer_size: int = 100):
   ```

Key Implementation Details:
- Buffer keyed by (email_address, tally_date) tuple
- Each buffer entry contains Dict[str, int] of category counts
- Flush merges with existing database records using get_tally/save_daily_tally
- Total buffer size = sum of all category counts across all keys

Edge Cases to Handle:
- Empty buffer flush (no-op)
- Partial flush on application shutdown
- Concurrent record_category calls (thread safety)
- Buffer overflow (immediate flush before recording more)
- Date boundary during processing (midnight rollover)
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-email-category-aggregation.md
Gap Analysis: specs/GAP-ANALYSIS.md

Reuse Opportunities (from gap analysis):
- Follow service interface pattern from `/root/repo/services/background_processor_interface.py`
- Dependency injection pattern from existing services
- Logging patterns using `utils.logger.get_logger`

Dependencies (must be implemented first):
- `ICategoryTallyRepository` from prompt 001
- `DailyCategoryTally` model from prompt 001

New Components Needed:
- `/root/repo/services/interfaces/category_aggregator_interface.py` (interface)
- `/root/repo/services/category_aggregator_service.py` (implementation)
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
- Thread-safe implementation for concurrent access
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Record a single email categorization
- [ ] Scenario: Record multiple categories for the same account on the same day
- [ ] Scenario: Record batch of category counts
- [ ] Scenario: Buffer flushes when size limit is reached
- [ ] Scenario: Flush merges with existing daily tally
- [ ] Scenario: Categories accumulate across multiple processing runs
- [ ] Scenario: Separate tallies are maintained for different accounts
- [ ] Scenario: Separate tallies are maintained for different days
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- Buffer management is efficient and thread-safe
- Flush operations correctly merge with existing data
</success_criteria>
