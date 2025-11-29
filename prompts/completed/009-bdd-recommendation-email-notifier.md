---
executor: bdd
source_feature: ./tests/bdd/blocking-recommendations-email.feature
---

<objective>
Implement the RecommendationEmailNotifier service that sends email notifications to Gmail account owners with domain blocking recommendations, integrating with the existing Mailtrap email provider.
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

  # EMAIL NOTIFICATION - Happy Path
  Scenario: Generate recommendations for unblocked Marketing domain
    Given the blocked domains list is empty
    And the inbox contains emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "marketing-spam.com" with category "Marketing"
    And a notification email should be sent to "user@gmail.com"
    And the notification email subject should be "Domains recommended to be blocked"

  Scenario: Email notification includes all recommendation details
    Given the blocked domains list is empty
    And the inbox contains:
      | sender_email                | category      | count |
      | spam@marketing.com          | Marketing     | 10    |
      | ads@advertising.com         | Advertising   | 5     |
    When the process_account function runs for "user@gmail.com"
    Then a notification email should be sent to "user@gmail.com"
    And the email should contain domain "marketing.com" with 10 emails
    And the email should contain domain "advertising.com" with 5 emails
    And the email should group domains by category

  Scenario: Email notification has both HTML and plain text versions
    Given the blocked domains list is empty
    And the inbox contains emails from "spam@example.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the notification email should include an HTML body
    And the notification email should include a plain text body
    And both bodies should contain the recommendation details

  # EMAIL NOTIFICATION - Error Handling
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

  # EMAIL NOTIFICATION - No Send Cases
  Scenario: No recommendations when all domains are already blocked
    Given the blocked domains list contains:
      | domain              |
      | marketing-spam.com  |
      | ads-network.io      |
    And the inbox contains emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    And the inbox contains emails from "promo@ads-network.io" categorized as "Advertising"
    When the process_account function runs for "user@gmail.com"
    Then the "recommended_domains_to_block" should be an empty list
    And no notification email should be sent
    And "notification_sent" should be false

  Scenario: Single email generates recommendation
    Given the blocked domains list is empty
    And the inbox contains exactly 1 email from "spam@single-sender.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include domain "single-sender.com" with count 1
    And a notification email should be sent
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **IRecommendationEmailNotifier Interface** (`services/interfaces/recommendation_email_notifier_interface.py`)
   - Define: `send_recommendations(recipient_email, recommendations) -> NotificationResult`

2. **IRecommendationEmailFormatter Interface** (`services/interfaces/recommendation_email_formatter_interface.py`)
   - Define: `format(recommendations) -> Tuple[str, str]` (html_body, text_body)

3. **NotificationResult Data Model** (`models/domain_recommendation_models.py`)
   - Fields: success (bool), recipient (str), recommendations_count (int), error_message (Optional[str])
   - Immutable dataclass

4. **RecommendationEmailFormatter Implementation** (`services/recommendation_email_formatter.py`)
   - Generates HTML body with:
     - Title: "Domain Blocking Recommendations"
     - Groups domains by category
     - Shows domain name and email count for each
     - Total summary at bottom
   - Generates plain text body with same content
   - Both bodies must contain all recommendation details

5. **RecommendationEmailNotifier Implementation** (`services/recommendation_email_notifier.py`)
   - Uses existing MailtrapProvider for sending
   - Subject: "Domains recommended to be blocked"
   - Handles send failures gracefully (returns NotificationResult with error)
   - Does NOT throw exceptions - always returns result

Email Template Structure (HTML):
```html
<h1>Domain Blocking Recommendations</h1>
<p>Based on your recent email processing, we recommend blocking the following domains:</p>

<h2>Marketing ({count} domains)</h2>
<table>
  <tr><th>Domain</th><th>Emails</th></tr>
  <tr><td>example.com</td><td>10</td></tr>
</table>

<h2>Advertising ({count} domains)</h2>
...

<p>Total: {total_domains} domains from {total_emails} emails</p>
```

Edge Cases to Handle:
- Email send failure (return NotificationResult with success=false)
- Empty recommendations (skip sending, return success=true with count=0)
- Single recommendation (still sends email)
- Service unavailable (capture error in NotificationResult)
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-blocking-recommendations-email.md
Draft Specification: specs/DRAFT-blocking-recommendations-email.md

Dependencies (from previous prompts):
- `DomainRecommendation` model from prompt 007
- `RecommendationSummary` from prompt 008

Existing Services to Integrate With:
- `MailtrapProvider` from `/home/jose/src/cat-emails/email_providers/mailtrap.py`
- `EmailMessage` model from `/home/jose/src/cat-emails/models/email_models.py`
- `EmailAddress` model from `/home/jose/src/cat-emails/models/email_models.py`

Integration Points:
- Notifier wraps MailtrapProvider.send_email()
- Uses existing email models (EmailMessage, EmailAddress)
- Formatter produces content compatible with EmailMessage

New Components Needed:
- `/home/jose/src/cat-emails/services/interfaces/recommendation_email_notifier_interface.py`
- `/home/jose/src/cat-emails/services/interfaces/recommendation_email_formatter_interface.py`
- `/home/jose/src/cat-emails/services/recommendation_email_formatter.py`
- `/home/jose/src/cat-emails/services/recommendation_email_notifier.py`
- Update `/home/jose/src/cat-emails/models/domain_recommendation_models.py` with NotificationResult
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use constructor injection for MailtrapProvider
- Formatter and Notifier are separate concerns (SRP)
- Never throw exceptions from notifier - always return NotificationResult
- Use existing email models from the codebase
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Generate recommendations for unblocked Marketing domain (email sent)
- [ ] Scenario: Email notification includes all recommendation details
- [ ] Scenario: Email notification has both HTML and plain text versions
- [ ] Scenario: Email notification failure does not break main processing
- [ ] Scenario: No recommendations when all domains are already blocked (no email)
- [ ] Scenario: Single email generates recommendation (email sent)
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Email subject is exactly "Domains recommended to be blocked"
- Both HTML and plain text bodies are generated
- Domains are grouped by category in email
- Email failures do not break main processing
- NotificationResult correctly captures success/failure
- Integration with MailtrapProvider works correctly
</success_criteria>
