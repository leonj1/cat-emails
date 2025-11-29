---
executor: bdd
source_feature: ./tests/bdd/blocking-recommendations-email.feature
---

<objective>
Implement robust domain extraction and edge case handling for the domain recommendation system, including special characters, international domains, long domain names, and multi-category domain tracking.
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

  # EDGE CASES - Domain Extraction
  Scenario: Single email generates recommendation
    Given the blocked domains list is empty
    And the inbox contains exactly 1 email from "spam@single-sender.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include domain "single-sender.com" with count 1
    And a notification email should be sent

  Scenario: Domain with special characters in sender email
    Given the blocked domains list is empty
    And the inbox contains emails from "user+tag@sub.domain-name.co.uk" categorized as "Advertising"
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include domain "sub.domain-name.co.uk"
    And the domain should be correctly extracted from the sender email

  Scenario: Same domain appears with different categories
    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email              | category      |
      | marketing@multi.com       | Marketing     |
      | ads@multi.com             | Advertising   |
      | money@multi.com           | Wants-Money   |
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include separate entries for each category
    And domain "multi.com" should appear 3 times with different categories

  Scenario: Very long domain name handling
    Given the blocked domains list is empty
    And the inbox contains emails from "user@very-long-subdomain.extremely-long-domain-name-that-tests-limits.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the domain should be correctly processed
    And the recommendation should include the full domain name

  Scenario: International domain names
    Given the blocked domains list is empty
    And the inbox contains emails from "spam@example.co.jp" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include domain "example.co.jp"
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **Enhanced Domain Extraction** (in BlockingRecommendationCollector or separate utility)
   - Extract domain from email addresses: `user@example.com` -> `example.com`
   - Handle plus addressing: `user+tag@example.com` -> `example.com`
   - Handle subdomains: `user@sub.domain.co.uk` -> `sub.domain.co.uk`
   - Handle long domain names without truncation
   - Support international TLDs (.co.jp, .co.uk, .com.br, etc.)

2. **Multi-Category Domain Tracking**
   - Same domain can appear multiple times with different categories
   - Each domain+category pair is tracked separately
   - domain "multi.com" with Marketing = 1 entry
   - domain "multi.com" with Advertising = 1 entry
   - Both should appear in recommendations

Domain Extraction Algorithm:
```python
def extract_domain(email_address: str) -> str:
    """
    Extract domain from email address.

    Examples:
    - user@example.com -> example.com
    - user+tag@sub.domain.co.uk -> sub.domain.co.uk
    - user@very-long-subdomain.domain.com -> very-long-subdomain.domain.com
    """
    # Split on @ and take the part after
    parts = email_address.split('@')
    if len(parts) != 2:
        raise ValueError(f"Invalid email address: {email_address}")
    return parts[1].lower()  # Normalize to lowercase
```

Edge Cases to Handle:
- Plus addressing (user+tag@domain.com)
- Subdomains with multiple levels
- International TLDs with country codes
- Long domain names (no truncation)
- Single email (count=1)
- Same domain, different categories
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-blocking-recommendations-email.md
Draft Specification: specs/DRAFT-blocking-recommendations-email.md

Dependencies (from previous prompts):
- `BlockingRecommendationCollector` from prompt 007
- `DomainRecommendation` model from prompt 007

Existing Services:
- `ExtractSenderEmailService` from `/home/jose/src/cat-emails/services/extract_sender_email_service.py`
  - May already have domain extraction logic to reuse

Integration Points:
- Collector uses domain extraction during collection
- Domain normalization (lowercase) for consistency
- No truncation of long domains

Patterns to Follow:
- Use existing ExtractSenderEmailService if it has domain extraction
- Otherwise create utility function in collector or separate module
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Reuse existing ExtractSenderEmailService if applicable
- Domain extraction should be case-insensitive
- No truncation of long domain names
- Multi-category tracking uses (domain, category) tuple as key
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Single email generates recommendation
- [ ] Scenario: Domain with special characters in sender email
- [ ] Scenario: Same domain appears with different categories
- [ ] Scenario: Very long domain name handling
- [ ] Scenario: International domain names
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Domain extraction handles all edge cases correctly
- Plus addressing is stripped (user+tag@domain.com -> domain.com)
- International TLDs are supported
- Long domain names are not truncated
- Multi-category domains tracked separately
- Domains are normalized to lowercase
</success_criteria>
