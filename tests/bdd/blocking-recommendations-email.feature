Feature: Blocking Recommendations Email Notification
  As a Gmail account owner
  I want to receive recommendations for domains to block based on email categories
  So that I can reduce unwanted Marketing, Advertising, and Wants-Money emails

  Background:
    Given a registered Gmail account "user@gmail.com"
    And the account has an app password configured
    And the email notification service is available

  # ============================================
  # HAPPY PATH SCENARIOS
  # ============================================

  Scenario: Generate recommendations for unblocked Marketing domain
    Given the blocked domains list is empty
    And the inbox contains emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "marketing-spam.com" with category "Marketing"
    And a notification email should be sent to "user@gmail.com"
    And the notification email subject should be "Domains recommended to be blocked"

  Scenario: Generate recommendations for unblocked Advertising domain
    Given the blocked domains list is empty
    And the inbox contains emails from "ads@ads-network.io" categorized as "Advertising"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "ads-network.io" with category "Advertising"
    And a notification email should be sent to "user@gmail.com"

  Scenario: Generate recommendations for unblocked Wants-Money domain
    Given the blocked domains list is empty
    And the inbox contains emails from "donate@pay-now.biz" categorized as "Wants-Money"
    When the process_account function runs for "user@gmail.com"
    Then the response should include "recommended_domains_to_block" list
    And the recommendations should include domain "pay-now.biz" with category "Wants-Money"
    And a notification email should be sent to "user@gmail.com"

  Scenario: Aggregate count for multiple emails from same domain
    Given the blocked domains list is empty
    And the inbox contains 5 emails from "newsletter@marketing-spam.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include domain "marketing-spam.com" with count 5
    And the "total_emails_matched" should be 5
    And the "unique_domains_count" should be 1

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

  # ============================================
  # NO RECOMMENDATIONS SCENARIOS
  # ============================================

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
      | sender_email                 | category    |
      | spam@marketing-spam.com      | Marketing   |
      | ads@new-ads-domain.com       | Advertising |
    When the process_account function runs for "user@gmail.com"
    Then the recommendations should include only domain "new-ads-domain.com"
    And domain "marketing-spam.com" should not be in recommendations

  # ============================================
  # EMAIL NOTIFICATION SCENARIOS
  # ============================================

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

  # ============================================
  # EDGE CASES
  # ============================================

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

  # ============================================
  # DATA MODEL VALIDATION SCENARIOS
  # ============================================

  Scenario: DomainRecommendation contains required fields
    Given the blocked domains list is empty
    And the inbox contains emails from "spam@test.com" categorized as "Marketing"
    When the process_account function runs for "user@gmail.com"
    Then each recommendation object should contain:
      | field    | type    |
      | domain   | string  |
      | category | string  |
      | count    | integer |

  Scenario: Response maintains existing fields
    Given the blocked domains list is empty
    And the inbox contains 10 emails with 3 categorized as "Marketing" from unblocked domains
    When the process_account function runs for "user@gmail.com"
    Then the response should include all existing fields:
      | field                   |
      | account                 |
      | emails_found            |
      | emails_processed        |
      | emails_categorized      |
      | processing_time_seconds |
      | timestamp               |
      | success                 |
    And the response should also include new recommendation fields

  # ============================================
  # COLLECTOR BEHAVIOR SCENARIOS
  # ============================================

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
