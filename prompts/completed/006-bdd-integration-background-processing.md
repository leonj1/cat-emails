---
executor: bdd
source_feature: ./tests/bdd/integration-background-processing.feature
---

<objective>
Implement the integration of Category Aggregation with the existing Background Email Processing system, ensuring categories are automatically recorded during normal email processing operations with proper lifecycle management.
</objective>

<gherkin>
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
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **Integration with BackgroundProcessorService** (`services/background_processor_service.py`)
   - Inject `ICategoryAggregator` into processor
   - Call `record_batch()` after each account's emails are categorized
   - Call `flush()` after processing each account
   - Handle aggregation failures gracefully (log but don't fail processing)

2. **Application Startup Integration** (in `api_service.py`)
   - Initialize `CategoryTallyRepository`
   - Initialize `CategoryAggregator` with repository
   - Initialize `BlockingRecommendationService`
   - Register shutdown handler for aggregator flush

3. **Shutdown Handler**
   ```python
   import atexit
   atexit.register(lambda: aggregator.flush())
   ```

4. **Data Cleanup Job**
   - Scheduled job to delete old tallies
   - Use `repository.delete_tallies_before(cutoff_date)`
   - Default retention: 30 days

5. **Configuration**
   - Feature toggle for category aggregation
   - Environment variable: `ENABLE_CATEGORY_AGGREGATION=true`
   - Configurable retention days

Integration Points (per spec section 7):
- Modify `BackgroundProcessorService.run()` to include aggregation callback
- Add aggregator as dependency in processor initialization
- Integrate with existing error handling patterns

Error Handling Strategy:
- Aggregation failures should NOT stop email processing
- Log errors for aggregation failures
- Continue processing remaining accounts
- Retry flush on next cycle if database temporarily unavailable
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-email-category-aggregation.md (Section 7)
Gap Analysis: specs/GAP-ANALYSIS.md

Reuse Opportunities (from gap analysis):
- Existing `BackgroundProcessorService` at `/root/repo/services/background_processor_service.py`
- Existing app lifecycle in `/root/repo/api_service.py`
- Logging patterns from `utils.logger`
- Error handling patterns from existing services

Dependencies (must be implemented first):
- `ICategoryAggregator` from prompt 002
- `CategoryAggregator` implementation from prompt 002
- `ICategoryTallyRepository` from prompt 001
- `IBlockingRecommendationService` from prompt 004

Modification Points:
- `/root/repo/services/background_processor_service.py` - Add aggregator integration
- `/root/repo/api_service.py` - Add initialization and shutdown handling
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Maintain backward compatibility - existing functionality must not break
- Feature toggle for gradual rollout
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Categories are recorded during email processing
- [ ] Scenario: Aggregator is flushed after each processing run
- [ ] Scenario: Multiple accounts are processed independently
- [ ] Scenario: Processing continues if aggregation fails
- [ ] Scenario: Aggregator initialization at application startup
- [ ] Scenario: Aggregator shutdown flushes remaining buffer
- [ ] Scenario: Data cleanup job removes old tallies
- [ ] Scenario: Hourly processing accumulates daily tallies
- [ ] Scenario: Processing spans midnight correctly
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- Existing email processing functionality is not affected
- Integration is properly guarded by feature toggle
- Graceful degradation on aggregation failures
- Proper lifecycle management (startup/shutdown)
</success_criteria>
