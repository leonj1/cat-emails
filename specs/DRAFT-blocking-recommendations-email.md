# DRAFT: Blocking Recommendations Email Notification

**Status**: DRAFT
**Created**: 2025-11-29
**Feature**: Automated Domain Blocking Recommendations with Email Notification

---

## Overview

When processing emails for an account, the system should identify domains that are sending Marketing, Advertising, or Wants-Money content but are not yet blocked. These domains should be collected, included in the processing response, and emailed to the account owner as recommendations for blocking.

---

## Interfaces Needed

### IBlockingRecommendationCollector

Responsible for collecting and filtering domain recommendations during email processing.

```python
from abc import ABC, abstractmethod
from typing import List, Set

class IBlockingRecommendationCollector(ABC):
    """Collects domains that should be recommended for blocking."""

    @abstractmethod
    def collect(
        self,
        sender_domain: str,
        category: str,
        blocked_domains: Set[str]
    ) -> None:
        """
        Evaluate a sender domain and category, collecting if recommendation-worthy.

        Args:
            sender_domain: The domain of the email sender
            category: The categorization result (e.g., "Marketing", "Advertising")
            blocked_domains: Set of already-blocked domain names
        """
        pass

    @abstractmethod
    def get_recommendations(self) -> List["DomainRecommendation"]:
        """
        Return aggregated recommendations with counts.

        Returns:
            List of DomainRecommendation objects, sorted by count descending
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Reset the collector for a new processing session."""
        pass
```

### IRecommendationEmailNotifier

Responsible for formatting and sending recommendation emails.

```python
from abc import ABC, abstractmethod
from typing import List

class IRecommendationEmailNotifier(ABC):
    """Sends domain blocking recommendation emails."""

    @abstractmethod
    def send_recommendations(
        self,
        recipient_email: str,
        recommendations: List["DomainRecommendation"]
    ) -> "NotificationResult":
        """
        Send a recommendation email to the account owner.

        Args:
            recipient_email: The Gmail account that was processed
            recommendations: List of domains recommended for blocking

        Returns:
            NotificationResult indicating success/failure
        """
        pass
```

### IEmailSender

Generic email sending abstraction (wraps existing email provider).

```python
from abc import ABC, abstractmethod

class IEmailSender(ABC):
    """Abstraction for sending emails."""

    @abstractmethod
    def send(
        self,
        to_address: str,
        subject: str,
        body_html: str,
        body_text: str
    ) -> bool:
        """
        Send an email.

        Args:
            to_address: Recipient email address
            subject: Email subject line
            body_html: HTML body content
            body_text: Plain text body content

        Returns:
            True if sent successfully, False otherwise
        """
        pass
```

### IRecommendationEmailFormatter

Responsible for formatting recommendation data into email content.

```python
from abc import ABC, abstractmethod
from typing import List, Tuple

class IRecommendationEmailFormatter(ABC):
    """Formats domain recommendations into email content."""

    @abstractmethod
    def format(
        self,
        recommendations: List["DomainRecommendation"]
    ) -> Tuple[str, str]:
        """
        Format recommendations into email body content.

        Args:
            recommendations: List of domain recommendations

        Returns:
            Tuple of (html_body, text_body)
        """
        pass
```

---

## Data Models

### DomainRecommendation

Represents a single domain recommendation with metadata.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class DomainRecommendation:
    """A domain recommended for blocking."""

    domain: str
    category: str  # "Marketing" | "Advertising" | "Wants-Money"
    count: int     # Number of emails from this domain in this category

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "category": self.category,
            "count": self.count
        }
```

### RecommendationSummary

Aggregate container for all recommendations from a processing run.

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class RecommendationSummary:
    """Summary of all blocking recommendations from a processing run."""

    recommendations: List[DomainRecommendation] = field(default_factory=list)
    total_count: int = 0

    @property
    def domain_count(self) -> int:
        """Number of unique domains recommended."""
        return len(self.recommendations)

    def to_dict(self) -> dict:
        return {
            "recommended_domains_to_block": [r.to_dict() for r in self.recommendations],
            "total_emails_matched": self.total_count,
            "unique_domains_count": self.domain_count
        }
```

### NotificationResult

Result of attempting to send a notification email.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class NotificationResult:
    """Result of sending a recommendation notification."""

    success: bool
    recipient: str
    recommendations_count: int
    error_message: Optional[str] = None
```

### ProcessAccountResponse (Extended)

The response model from process_account, extended with recommendations.

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ProcessAccountResponse:
    """Response from processing an account's emails."""

    account_id: str
    emails_processed: int
    emails_deleted: int
    emails_categorized: int

    # New fields for blocking recommendations
    recommendation_summary: Optional[RecommendationSummary] = None
    notification_sent: bool = False
    notification_error: Optional[str] = None

    def to_dict(self) -> dict:
        result = {
            "account_id": self.account_id,
            "emails_processed": self.emails_processed,
            "emails_deleted": self.emails_deleted,
            "emails_categorized": self.emails_categorized,
            "notification_sent": self.notification_sent
        }

        if self.recommendation_summary:
            result.update(self.recommendation_summary.to_dict())

        if self.notification_error:
            result["notification_error"] = self.notification_error

        return result
```

---

## Logic Flow

### Main Processing Flow (Pseudocode)

```
FUNCTION process_account(account_id):
    # Setup
    account = fetch_account(account_id)
    blocked_domains = domain_service.fetch_blocked_domains(account_id)
    blocked_domain_set = {d.domain for d in blocked_domains}
    recommendation_collector = BlockingRecommendationCollector()

    # Process emails
    FOR each email IN fetch_emails(account):
        sender_domain = extract_domain(email.sender)
        category = categorize_email(email)

        # Collect recommendations for qualifying categories
        IF category IN ["Marketing", "Advertising", "Wants-Money"]:
            recommendation_collector.collect(
                sender_domain=sender_domain,
                category=category,
                blocked_domains=blocked_domain_set
            )

        # Continue with normal email processing...
        process_email_action(email, category)

    # Build recommendation summary
    recommendations = recommendation_collector.get_recommendations()
    summary = RecommendationSummary(
        recommendations=recommendations,
        total_count=sum(r.count for r in recommendations)
    )

    # Send notification if there are recommendations
    notification_result = None
    IF summary.domain_count > 0:
        notification_result = recommendation_notifier.send_recommendations(
            recipient_email=account.email,
            recommendations=recommendations
        )

    # Build and return response
    RETURN ProcessAccountResponse(
        account_id=account_id,
        emails_processed=processed_count,
        emails_deleted=deleted_count,
        emails_categorized=categorized_count,
        recommendation_summary=summary,
        notification_sent=notification_result.success IF notification_result ELSE False,
        notification_error=notification_result.error_message IF notification_result ELSE None
    )
```

### Recommendation Collection Flow (Pseudocode)

```
CLASS BlockingRecommendationCollector:
    PRIVATE domain_category_counts: Dict[Tuple[str, str], int]

    FUNCTION collect(sender_domain, category, blocked_domains):
        # Skip if already blocked
        IF sender_domain IN blocked_domains:
            RETURN

        # Skip if not a recommendation-worthy category
        IF category NOT IN RECOMMENDATION_CATEGORIES:
            RETURN

        # Increment count for this domain+category pair
        key = (sender_domain, category)
        domain_category_counts[key] += 1

    FUNCTION get_recommendations():
        recommendations = []
        FOR (domain, category), count IN domain_category_counts:
            recommendations.append(
                DomainRecommendation(domain, category, count)
            )

        # Sort by count descending, then by domain alphabetically
        SORT recommendations BY (-count, domain)
        RETURN recommendations
```

### Email Notification Flow (Pseudocode)

```
CLASS RecommendationEmailNotifier:
    PRIVATE email_sender: IEmailSender
    PRIVATE formatter: IRecommendationEmailFormatter

    FUNCTION send_recommendations(recipient_email, recommendations):
        IF NOT recommendations:
            RETURN NotificationResult(
                success=True,
                recipient=recipient_email,
                recommendations_count=0
            )

        html_body, text_body = formatter.format(recommendations)

        TRY:
            success = email_sender.send(
                to_address=recipient_email,
                subject="Domains recommended to be blocked",
                body_html=html_body,
                body_text=text_body
            )

            RETURN NotificationResult(
                success=success,
                recipient=recipient_email,
                recommendations_count=len(recommendations)
            )
        CATCH Exception as e:
            RETURN NotificationResult(
                success=False,
                recipient=recipient_email,
                recommendations_count=len(recommendations),
                error_message=str(e)
            )
```

### Email Formatting Flow (Pseudocode)

```
CLASS RecommendationEmailFormatter:

    FUNCTION format(recommendations):
        # Group by category for display
        by_category = group_by(recommendations, key=lambda r: r.category)

        html_body = render_html_template(
            title="Domains Recommended for Blocking",
            categories=by_category,
            total_domains=len(recommendations),
            total_emails=sum(r.count for r in recommendations)
        )

        text_body = render_text_template(
            categories=by_category,
            total_domains=len(recommendations),
            total_emails=sum(r.count for r in recommendations)
        )

        RETURN (html_body, text_body)
```

---

## Constructor Signatures

All constructors follow the rule of maximum 3 arguments and no environment variables.

### BlockingRecommendationCollector

```python
def __init__(
    self,
    recommendation_categories: Set[str] = None  # Defaults to {"Marketing", "Advertising", "Wants-Money"}
):
    """
    Args:
        recommendation_categories: Set of category names that trigger recommendations
    """
```

### RecommendationEmailNotifier

```python
def __init__(
    self,
    email_sender: IEmailSender,
    formatter: IRecommendationEmailFormatter
):
    """
    Args:
        email_sender: Service for sending emails
        formatter: Service for formatting recommendation emails
    """
```

### RecommendationEmailFormatter

```python
def __init__(
    self,
    template_engine: ITemplateEngine = None  # Optional, defaults to simple string formatting
):
    """
    Args:
        template_engine: Optional template engine for email rendering
    """
```

### MailtrapEmailSender (Implementation of IEmailSender)

```python
def __init__(
    self,
    mailtrap_client: IMailtrapClient,
    from_address: str
):
    """
    Args:
        mailtrap_client: Configured Mailtrap API client
        from_address: Sender email address for notifications
    """
```

---

## Configuration

### Recommendation Categories

```python
RECOMMENDATION_CATEGORIES = frozenset({
    "Marketing",
    "Advertising",
    "Wants-Money"
})
```

### Email Template Content

**Subject**: `Domains recommended to be blocked`

**HTML Template Structure**:
```html
<h1>Domain Blocking Recommendations</h1>
<p>Based on your recent email processing, we recommend blocking the following domains:</p>

<h2>Marketing ({count} domains)</h2>
<table>
  <tr><th>Domain</th><th>Emails</th></tr>
  <!-- rows -->
</table>

<h2>Advertising ({count} domains)</h2>
<!-- similar -->

<p>Total: {total_domains} domains from {total_emails} emails</p>
```

---

## API Response Schema

The `process_account` endpoint response should include:

```json
{
  "account_id": "abc123",
  "emails_processed": 150,
  "emails_deleted": 45,
  "emails_categorized": 105,
  "recommended_domains_to_block": [
    {
      "domain": "marketing-spam.com",
      "category": "Marketing",
      "count": 12
    },
    {
      "domain": "ads-network.io",
      "category": "Advertising",
      "count": 8
    },
    {
      "domain": "pay-now.biz",
      "category": "Wants-Money",
      "count": 3
    }
  ],
  "total_emails_matched": 23,
  "unique_domains_count": 3,
  "notification_sent": true,
  "notification_error": null
}
```

---

## Error Handling

1. **Email send failure**: Log error, set `notification_sent=false`, populate `notification_error`, but do NOT fail the entire process_account operation
2. **Empty recommendations**: Skip email notification, return empty list in response
3. **Invalid email address**: Return error in `notification_error` field

---

## Testing Considerations

### Unit Test Scenarios

1. **Collector filters blocked domains**: Given a domain in blocked list, when collected, then it should NOT appear in recommendations
2. **Collector aggregates counts**: Given same domain appears 3 times, when get_recommendations called, then count should be 3
3. **Collector ignores non-qualifying categories**: Given category is "Personal", when collected, then no recommendation added
4. **Formatter produces valid HTML/text**: Given list of recommendations, when formatted, then both HTML and text bodies are non-empty
5. **Notifier handles send failure gracefully**: Given email_sender throws, when send_recommendations called, then NotificationResult has success=false

### Integration Test Scenarios

1. **Full flow with recommendations**: Process account with Marketing emails from unblocked domain, verify response includes recommendations and email sent
2. **Full flow without recommendations**: Process account with only blocked domains, verify empty recommendations and no email sent
3. **Notification failure does not break processing**: Mock email failure, verify process_account still returns successfully with error noted

---

## Dependencies

- `IEmailSender` implementation (wrapping existing Mailtrap provider)
- `IDomainService` for fetching blocked domains
- Email template rendering (can be simple string formatting or Jinja2)

---

## Notes

- This is a greenfield design focused on clean abstractions and testability
- All interfaces allow for easy mocking in tests
- The recommendation collector is stateful per processing run and must be cleared/recreated for each account
- Email notification is a "best effort" operation - failure should not affect the core email processing result
