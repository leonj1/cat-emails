---
executor: bdd
source_feature: ./tests/bdd/blocking-recommendations-email.feature
---

<objective>
Integrate the domain recommendation collector and email notifier into the AccountEmailProcessorService.process_account() function, ensuring recommendations are collected during email processing and notifications are sent at the end.
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

  # INTEGRATION - Full Flow
  Scenario: Generate recommendations for unblocked Marketing domain
    Given the blocked domains list is empty
    And the inbox contains emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "marketing-spam.com" with category "Marketing"
    And a notification email should be sent to "user@gmail.com"
    And the notification email subject should be "Domains recommended to be blocked"

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
    And the "total_emails_matched" should be 23
    And domain "legit-news.com" should not be in recommendations

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

  Scenario: Email notification failure does not break main processing
    Given the blocked domains list is empty
    And the inbox contains emails from "spam@marketing.com" categorized as "Marketing"
    And the email notification service is failing
    When the process_account function runs for "user@gmail.com"
    Then the processing should complete successfully
    And the response "success" should be true
    And "notification_sent" should be false
    And "notification_error" should contain the failure reason
    And the recommendations should still be included in the response

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

  Scenario: Collector is cleared between processing runs
    Given the blocked domains list is empty
    And account "user@gmail.com" was previously processed with recommendations
    When the process_account function runs again for "user@gmail.com"
    Then the recommendations should only reflect the current processing run
    And previous recommendations should not be carried over

  Scenario: No recommendations when inbox is empty
    Given the blocked domains list is empty
    And the inbox is empty
    When the process_account function runs for "user@gmail.com"
    Then the "recommended_domains_to_block" should be an empty list
    And no notification email should be sent
    And the processing should complete successfully
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **Integrate BlockingRecommendationCollector into AccountEmailProcessorService**
   - Inject collector via constructor
   - Clear collector at start of each process_account() call
   - Collect domain recommendations during email processing loop
   - Get recommendations after processing completes

2. **Integrate RecommendationEmailNotifier into AccountEmailProcessorService**
   - Inject notifier via constructor
   - Send notification after recommendations are collected (if any)
   - Handle notification failures gracefully
   - Include notification result in response

3. **Update AccountEmailProcessorService.process_account() Response**
   - Add: recommended_domains_to_block (list)
   - Add: total_emails_matched (int)
   - Add: unique_domains_count (int)
   - Add: notification_sent (bool)
   - Add: notification_error (Optional[str])
   - Maintain all existing fields

Integration Flow (pseudocode):
```python
def process_account(self, email_address: str) -> Dict:
    # ... existing setup code ...

    # Clear collector for fresh run
    self.recommendation_collector.clear()

    # Fetch blocked domains for filtering
    blocked_domains = self.domain_service.fetch_blocked_domains()
    blocked_domain_set = {d.domain for d in blocked_domains}

    # ... existing email fetching code ...

    for email in emails:
        # ... existing processing ...
        category = categorize_email(email)
        sender_domain = extract_domain(email.sender)

        # Collect recommendation if qualifying category and not blocked
        self.recommendation_collector.collect(
            sender_domain=sender_domain,
            category=category,
            blocked_domains=blocked_domain_set
        )

        # ... rest of existing processing ...

    # Get recommendations
    summary = self.recommendation_collector.get_summary()

    # Send notification if there are recommendations
    notification_result = None
    if summary.domain_count > 0:
        notification_result = self.email_notifier.send_recommendations(
            recipient_email=email_address,
            recommendations=summary.recommendations
        )

    # Build response with new fields
    result = {
        # ... existing fields ...
        "recommended_domains_to_block": [r.to_dict() for r in summary.recommendations],
        "total_emails_matched": summary.total_count,
        "unique_domains_count": summary.domain_count,
        "notification_sent": notification_result.success if notification_result else False,
        "notification_error": notification_result.error_message if notification_result else None
    }

    return result
```

Edge Cases to Handle:
- Empty inbox (recommendations empty, no notification)
- All domains blocked (recommendations empty, no notification)
- Notification failure (success=true, notification_sent=false, error captured)
- Previous run state (collector cleared at start)
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-blocking-recommendations-email.md
Draft Specification: specs/DRAFT-blocking-recommendations-email.md

Dependencies (from previous prompts):
- `BlockingRecommendationCollector` from prompt 007
- `RecommendationSummary` from prompt 008
- `RecommendationEmailNotifier` from prompt 009
- Domain extraction from prompt 010

Existing Services to Modify:
- `/home/jose/src/cat-emails/services/account_email_processor_service.py`
  - Add new constructor parameters
  - Add collection logic in processing loop
  - Add notification after processing
  - Extend response with new fields

Integration Points:
- `DomainService.fetch_blocked_domains()` for blocked domains list
- `EmailProcessorService.process_email()` - after categorization, collect recommendation
- Response dict - add new fields while maintaining existing ones
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use constructor injection for collector and notifier
- Maintain backward compatibility with existing response
- Notification failure must NOT break processing (catch and capture error)
- Collector must be cleared at start of each run
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Generate recommendations for unblocked Marketing domain
- [ ] Scenario: Multiple domains with different categories and counts
- [ ] Scenario: Response includes complete recommendation summary
- [ ] Scenario: Email notification failure does not break main processing
- [ ] Scenario: Response maintains existing fields
- [ ] Scenario: Collector is cleared between processing runs
- [ ] Scenario: No recommendations when inbox is empty
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Integration with existing process_account() is seamless
- Backward compatibility maintained (existing fields present)
- New recommendation fields included in response
- Notification failures handled gracefully
- Collector cleared between runs (no state leakage)
- Empty recommendations handled correctly (no notification sent)
</success_criteria>
