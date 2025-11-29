# BDD Specification: Blocking Recommendations Email Notification

## Overview

This feature enables the email processing system to identify domains that should be blocked based on email categories (Marketing, Advertising, Wants-Money) and notify users via email with recommendations. The system collects domain statistics during email processing, filters out already-blocked domains, and sends a formatted notification email to the account owner.

## User Stories

- As a Gmail account owner, I want to receive recommendations for domains to block based on email categories so that I can reduce unwanted Marketing, Advertising, and Wants-Money emails.

## Feature Files

| Feature File | Scenarios | Coverage |
|--------------|-----------|----------|
| blocking-recommendations-email.feature | 24 | Happy paths, no recommendations, email notifications, edge cases, data model, collector behavior |

## Scenarios Summary

### blocking-recommendations-email.feature

#### Happy Path Scenarios (7)
1. **Generate recommendations for unblocked Marketing domain** - Verifies Marketing category emails trigger recommendations
2. **Generate recommendations for unblocked Advertising domain** - Verifies Advertising category emails trigger recommendations
3. **Generate recommendations for unblocked Wants-Money domain** - Verifies Wants-Money category emails trigger recommendations
4. **Aggregate count for multiple emails from same domain** - Verifies email counts are aggregated per domain
5. **Multiple domains with different categories and counts** - Verifies handling of mixed categories with proper sorting
6. **Recommendations sorted by count descending then alphabetically** - Verifies sorting logic (count desc, then alpha)
7. **Response includes complete recommendation summary** - Verifies all response fields are present

#### No Recommendations Scenarios (4)
8. **No recommendations when all domains are already blocked** - Verifies blocked domains are filtered out
9. **No recommendations when no emails match qualifying categories** - Verifies only Marketing/Advertising/Wants-Money qualify
10. **No recommendations when inbox is empty** - Verifies graceful handling of empty inbox
11. **Partial blocking - some domains blocked, some not** - Verifies mixed blocking state handling

#### Email Notification Scenarios (3)
12. **Email notification failure does not break main processing** - Verifies resilient error handling
13. **Email notification includes all recommendation details** - Verifies email content completeness
14. **Email notification has both HTML and plain text versions** - Verifies multipart email format

#### Edge Cases (5)
15. **Single email generates recommendation** - Verifies minimum case (1 email)
16. **Domain with special characters in sender email** - Verifies domain extraction from complex emails
17. **Same domain appears with different categories** - Verifies per-category tracking
18. **Very long domain name handling** - Verifies no truncation issues
19. **International domain names** - Verifies TLD handling (e.g., .co.jp)

#### Data Model Validation Scenarios (2)
20. **DomainRecommendation contains required fields** - Verifies data structure (domain, category, count)
21. **Response maintains existing fields** - Verifies backward compatibility with existing response

#### Collector Behavior Scenarios (2)
22. **Collector is cleared between processing runs** - Verifies no state leakage between runs
23. **Collector only tracks qualifying categories** - Verifies category filtering logic

## Acceptance Criteria

### Core Functionality
- [ ] System identifies emails from Marketing, Advertising, and Wants-Money categories
- [ ] System extracts sender domains from email addresses
- [ ] System aggregates email counts per domain per category
- [ ] System filters out domains already in the blocked domains list
- [ ] System returns recommendations sorted by count (descending), then alphabetically

### Response Structure
- [ ] Response includes `recommended_domains_to_block` list
- [ ] Response includes `total_emails_matched` count
- [ ] Response includes `unique_domains_count` count
- [ ] Response includes `notification_sent` boolean
- [ ] Response includes `notification_error` (null or error message)
- [ ] Each recommendation contains: domain, category, count
- [ ] Existing response fields are preserved (account, emails_found, etc.)

### Email Notification
- [ ] Notification email sent when recommendations exist
- [ ] No notification sent when no recommendations
- [ ] Email subject: "Domains recommended to be blocked"
- [ ] Email includes HTML body
- [ ] Email includes plain text body
- [ ] Email groups recommendations by category
- [ ] Notification failure does not break main processing
- [ ] Notification errors are captured in response

### Edge Case Handling
- [ ] Empty inbox handled gracefully
- [ ] Single email generates valid recommendation
- [ ] Complex email addresses parsed correctly (user+tag@sub.domain.co.uk)
- [ ] Long domain names handled without truncation
- [ ] International TLDs supported (.co.jp, .co.uk, etc.)
- [ ] Same domain with different categories tracked separately

### State Management
- [ ] Collector cleared between processing runs
- [ ] No state leakage between accounts
- [ ] Only qualifying categories tracked (Marketing, Advertising, Wants-Money)

## Technical Notes

### Qualifying Categories
The following email categories qualify for blocking recommendations:
- Marketing
- Advertising
- Wants-Money

Categories that do NOT qualify:
- Personal
- Work
- Newsletter
- (any other category)

### Domain Extraction
Domains should be extracted from sender email addresses:
- `user@example.com` -> `example.com`
- `user+tag@sub.domain.co.uk` -> `sub.domain.co.uk`

### Sorting Logic
Recommendations should be sorted:
1. Primary: count (descending - highest first)
2. Secondary: domain name (alphabetically ascending)

### Response Fields
New fields to add:
```python
recommended_domains_to_block: List[DomainRecommendation]
total_emails_matched: int
unique_domains_count: int
notification_sent: bool
notification_error: Optional[str]
```

DomainRecommendation structure:
```python
class DomainRecommendation:
    domain: str
    category: str
    count: int
```

## Dependencies

- Existing email categorization system
- Existing blocked domains list/repository
- SMTP email sending capability (for notifications)
- `process_account` function in background processing

## Related Features

- `blocking-recommendations.feature` - Core recommendation logic (may overlap)
- `category-aggregation.feature` - Category aggregation patterns
