---
executor: bdd
source_feature: ./tests/bdd/blocking-recommendations-email.feature
---

<objective>
Implement the sorting, filtering, and aggregation logic for domain recommendations, including handling of multiple domains with different categories, blocked domain filtering, and proper response structure.
</objective>

<gherkin>
Feature: Blocking Recommendations Email Notification
  As a Gmail account owner
  I want to receive recommendations for domains to block based on email categories
  So that I can reduce unwanted Marketing, Advertising, and Wants-Money emails

  Background:
    Given a registered Gmail account "user@gmail.com"
    And the account has an app password configured
    And the email notification service is available

  # SORTING AND AGGREGATION
  Scenario: Multiple domains with different categories and counts
    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email                    | category      | count |
      | spam@marketing-spam.com         | Marketing     | 12    |
      | promo@ads-network.io            | Advertising   | 8     |
      | donate@pay-now.biz              | Wants-Money   | 3     |
      | news@legit-news.com             | Personal      | 5     |
    When the process_account function runs for "user@gmail.com"
    Then the response should include 3 domain recommendations
    And the recommendations should be sorted by count in descending order
    And the first recommendation should have count 12
    And the last recommendation should have count 3
    And the "total_emails_matched" should be 23
    And domain "legit-news.com" should not be in recommendations

  Scenario: Recommendations sorted by count descending then alphabetically
    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email                | category   | count |
      | spam@zebra-ads.com          | Marketing  | 5     |
      | ads@alpha-marketing.com     | Marketing  | 5     |
      | promo@beta-promo.com        | Marketing  | 3     |
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should be sorted by count descending
    And for domains with equal count they should be sorted alphabetically
    And the recommendation order should be "alpha-marketing.com", "zebra-ads.com", "beta-promo.com"

  Scenario: Response includes complete recommendation summary
    Given the blocked domains list is empty
    And the inbox contains 10 emails from "spam@example.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the response should include:
      | field                          | expected_value |
      | recommended_domains_to_block   | list           |
      | total_emails_matched           | 10             |
      | unique_domains_count           | 1              |
      | notification_sent              | true           |
      | notification_error             | null           |

  # NO RECOMMENDATIONS - FILTERING
  Scenario: No recommendations when all domains are already blocked
    Given the blocked domains list contains:
      | domain              |
      | marketing-spam.com  |
      | ads-network.io      |
    And the inbox contains emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    And the inbox contains emails from "promo@ads-network.io" categorized as "Advertising"
    When the process_account function runs for "user@gmail.com"
    Then the "recommended_domains_to_block" should be an empty list
    And the "unique_domains_count" should be 0
    And no notification email should be sent
    And "notification_sent" should be false

  Scenario: No recommendations when no emails match qualifying categories
    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email             | category     |
      | friend@personal.com      | Personal     |
      | work@company.com         | Work         |
      | news@newsletter.com      | Newsletter   |
    When the process_account function runs for "user@gmail.com"
    Then the "recommended_domains_to_block" should be an empty list
    And no notification email should be sent

  Scenario: No recommendations when inbox is empty
    Given the blocked domains list is empty
    And the inbox is empty
    When the process_account function runs for "user@gmail.com"
    Then the "recommended_domains_to_block" should be an empty list
    And no notification email should be sent
    And the processing should complete successfully

  Scenario: Partial blocking - some domains blocked, some not
    Given the blocked domains list contains "marketing-spam.com"
    And the inbox contains:
      | sender_email                 | category   |
      | spam@marketing-spam.com      | Marketing  |
      | ads@new-ads-domain.com       | Advertising|
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include only domain "new-ads-domain.com"
    And domain "marketing-spam.com" should not be in recommendations

  # DATA MODEL - Response Structure
  Scenario: Response maintains existing fields
    Given the blocked domains list is empty
    And the inbox contains 10 emails with 3 categorized as "Marketing" from unblocked domains
    When the process_account function runs for "user@gmail.com"
    Then the response should include all existing fields:
      | field                  |
      | account                |
      | emails_found           |
      | emails_processed       |
      | emails_categorized     |
      | processing_time_seconds|
      | timestamp              |
      | success                |
    And the response should also include new recommendation fields
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **RecommendationSummary Data Model** (`models/domain_recommendation_models.py`)
   - Fields: recommendations (List[DomainRecommendation]), total_count (int)
   - Property: domain_count (derived from len(recommendations))
   - Method: `to_dict()` for response serialization

2. **Enhanced BlockingRecommendationCollector** (extend from prompt 007)
   - Add `get_summary()` method returning RecommendationSummary
   - Ensure proper filtering of blocked domains
   - Implement correct sorting: count DESC, then domain ASC

3. **Extended ProcessAccountResponse** (update existing response model)
   - Add new fields: recommended_domains_to_block, total_emails_matched, unique_domains_count, notification_sent, notification_error
   - Maintain backward compatibility with existing fields

Sorting Algorithm:
```python
recommendations.sort(key=lambda r: (-r.count, r.domain))
```

Response Fields (new):
```python
recommended_domains_to_block: List[DomainRecommendation]
total_emails_matched: int  # sum of all recommendation counts
unique_domains_count: int  # len(recommendations)
notification_sent: bool
notification_error: Optional[str]
```

Edge Cases to Handle:
- All domains already blocked (empty recommendations)
- No qualifying category emails (empty recommendations)
- Empty inbox (empty recommendations, success=true)
- Partial blocking (only unblocked domains in recommendations)
- Equal counts sorted alphabetically
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-blocking-recommendations-email.md
Draft Specification: specs/DRAFT-blocking-recommendations-email.md

Dependencies (from previous prompts):
- `DomainRecommendation` model from prompt 007
- `BlockingRecommendationCollector` from prompt 007

Existing Services:
- `DomainService.fetch_blocked_domains()` for getting blocked domains list
- `AccountEmailProcessorService.process_account()` returns response dict

Existing Response Fields to Preserve:
- account, emails_found, emails_processed, emails_categorized
- processing_time_seconds, timestamp, success

New Components Needed:
- Update `/home/jose/src/cat-emails/models/domain_recommendation_models.py` with RecommendationSummary
- Update response structure in AccountEmailProcessorService
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Maintain backward compatibility with existing response format
- Use Pydantic for response model validation
- Constructor injection for blocked domains service
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Multiple domains with different categories and counts
- [ ] Scenario: Recommendations sorted by count descending then alphabetically
- [ ] Scenario: Response includes complete recommendation summary
- [ ] Scenario: No recommendations when all domains are already blocked
- [ ] Scenario: No recommendations when no emails match qualifying categories
- [ ] Scenario: No recommendations when inbox is empty
- [ ] Scenario: Partial blocking - some domains blocked, some not
- [ ] Scenario: Response maintains existing fields
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Sorting is correct: count DESC, then domain ASC
- Blocked domains are properly filtered out
- Response maintains backward compatibility
- Empty recommendations handled gracefully
- total_emails_matched and unique_domains_count are accurate
</success_criteria>
