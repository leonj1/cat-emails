---
executor: bdd
source_feature: ./tests/bdd/blocking-recommendations-email.feature
---

<objective>
Implement the DomainRecommendationCollector component that collects and aggregates email sender domains during email processing, filtering based on qualifying categories (Marketing, Advertising, Wants-Money) and blocked domains list.
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

  # HAPPY PATH - Core Collection Logic
  Scenario: Generate recommendations for unblocked Marketing domain
    Given the blocked domains list is empty
    And the inbox contains emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "marketing-spam.com" with category "Marketing"

  Scenario: Generate recommendations for unblocked Advertising domain
    Given the blocked domains list is empty
    And the inbox contains emails from "ads@ads-network.io" categorized as "Advertising"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "ads-network.io" with category "Advertising"

  Scenario: Generate recommendations for unblocked Wants-Money domain
    Given the blocked domains list is empty
    And the inbox contains emails from "donate@pay-now.biz" categorized as "Wants-Money"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "pay-now.biz" with category "Wants-Money"

  Scenario: Aggregate count for multiple emails from same domain
    Given the blocked domains list is empty
    And the inbox contains 5 emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include domain "marketing-spam.com" with count 5
    And the "total_emails_matched" should be 5
    And the "unique_domains_count" should be 1

  # COLLECTOR BEHAVIOR - State Management
  Scenario: Collector is cleared between processing runs
    Given the blocked domains list is empty
    And account "user@gmail.com" was previously processed with recommendations
    When the process_account function runs again for "user@gmail.com"
    Then the recommendations should only reflect the current processing run
    And previous recommendations should not be carried over

  Scenario: Collector only tracks qualifying categories
    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email         | category      |
      | spam@junk.com        | Marketing     |
      | work@company.com     | Work          |
      | promo@ads.com        | Advertising   |
      | friend@personal.com  | Personal      |
      | donate@charity.com   | Wants-Money   |
      | news@updates.com     | Newsletter    |
    When the process_account function runs for "user@gmail.com"
    Then only domains from "Marketing", "Advertising", and "Wants-Money" categories should be recommended
    And "Work", "Personal", and "Newsletter" domains should not appear

  # DATA MODEL - DomainRecommendation Structure
  Scenario: DomainRecommendation contains required fields
    Given the blocked domains list is empty
    And the inbox contains emails from "spam@test.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then each recommendation object should contain:
      | field    | type   |
      | domain   | string |
      | category | string |
      | count    | integer|
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **IBlockingRecommendationCollector Interface** (`services/interfaces/blocking_recommendation_collector_interface.py`)
   - Define: `collect(sender_domain, category, blocked_domains)`, `get_recommendations()`, `clear()`
   - This interface was already defined in DRAFT spec

2. **DomainRecommendation Data Model** (`models/domain_recommendation_models.py`)
   - Fields: domain (str), category (str), count (int)
   - Immutable dataclass with `to_dict()` method

3. **BlockingRecommendationCollector Implementation** (`services/blocking_recommendation_collector.py`)
   - Collects domains during email processing
   - Filters by qualifying categories: Marketing, Advertising, Wants-Money
   - Excludes already-blocked domains
   - Aggregates counts per domain+category pair
   - Provides sorted recommendations (count desc, then alpha)
   - Clear method for resetting between runs

Algorithm (per DRAFT spec):
```
collect(sender_domain, category, blocked_domains):
    IF sender_domain IN blocked_domains: RETURN
    IF category NOT IN QUALIFYING_CATEGORIES: RETURN
    key = (sender_domain, category)
    domain_category_counts[key] += 1

get_recommendations():
    recommendations = []
    FOR (domain, category), count IN domain_category_counts:
        recommendations.append(DomainRecommendation(domain, category, count))
    SORT recommendations BY (-count, domain)
    RETURN recommendations
```

Qualifying Categories:
- Marketing
- Advertising
- Wants-Money

Edge Cases to Handle:
- Empty blocked domains list
- Single email generates recommendation
- Same domain with multiple categories tracked separately
- Collector cleared between runs (no state leakage)
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-blocking-recommendations-email.md
Draft Specification: specs/DRAFT-blocking-recommendations-email.md

Existing Services to Integrate With:
- `DomainService.fetch_blocked_domains()` from `/home/jose/src/cat-emails/domain_service.py`
- `ExtractSenderEmailService` from `/home/jose/src/cat-emails/services/extract_sender_email_service.py`

Reuse Opportunities:
- Follow interface pattern from existing `IBlockingRecommendationService`
- Follow Pydantic/dataclass model patterns from `models/recommendation_models.py`
- Use existing blocked domains service pattern

New Components Needed:
- `/home/jose/src/cat-emails/services/interfaces/blocking_recommendation_collector_interface.py`
- `/home/jose/src/cat-emails/models/domain_recommendation_models.py`
- `/home/jose/src/cat-emails/services/blocking_recommendation_collector.py`
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Constructor injection for dependencies
- Stateful collector with clear() method for reset
- Immutable DomainRecommendation dataclass
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Generate recommendations for unblocked Marketing domain
- [ ] Scenario: Generate recommendations for unblocked Advertising domain
- [ ] Scenario: Generate recommendations for unblocked Wants-Money domain
- [ ] Scenario: Aggregate count for multiple emails from same domain
- [ ] Scenario: Collector is cleared between processing runs
- [ ] Scenario: Collector only tracks qualifying categories
- [ ] Scenario: DomainRecommendation contains required fields
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- Collector correctly filters by qualifying categories
- Collector correctly excludes blocked domains
- Aggregation counts are accurate
- Sorting is correct (count desc, then alpha)
</success_criteria>
