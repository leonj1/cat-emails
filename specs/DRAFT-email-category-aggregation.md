# DRAFT: Email Category Aggregation and Blocking Recommendations

**Status**: DRAFT
**Created**: 2025-11-28
**Feature**: Aggregate email categories during background processing and provide 7-day rolling blocking recommendations

---

## Overview

This feature aggregates email category tallies during background processing, stores historical data, and provides an API endpoint that recommends categories to block based on 7-day rolling statistics.

---

## 1. Interfaces Needed

### 1.1 ICategoryAggregator

Responsible for aggregating category counts during email processing.

```python
from abc import ABC, abstractmethod
from typing import Dict
from datetime import datetime

class ICategoryAggregator(ABC):
    """Interface for aggregating email categories during processing."""

    @abstractmethod
    def record_category(self, email_address: str, category: str, timestamp: datetime) -> None:
        """Record a single email categorization event."""
        pass

    @abstractmethod
    def record_batch(self, email_address: str, category_counts: Dict[str, int], timestamp: datetime) -> None:
        """Record multiple category counts from a batch processing run."""
        pass

    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered records to persistent storage."""
        pass
```

### 1.2 ICategoryTallyRepository

Responsible for persisting and retrieving category tallies.

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, date

class ICategoryTallyRepository(ABC):
    """Interface for storing and retrieving category tallies."""

    @abstractmethod
    def save_daily_tally(self, tally: 'DailyCategoryTally') -> None:
        """Save or update a daily category tally."""
        pass

    @abstractmethod
    def get_tallies_for_period(
        self,
        email_address: str,
        start_date: date,
        end_date: date
    ) -> List['DailyCategoryTally']:
        """Retrieve tallies for a specific email account within a date range."""
        pass

    @abstractmethod
    def get_aggregated_tallies(
        self,
        email_address: str,
        start_date: date,
        end_date: date
    ) -> 'AggregatedCategoryTally':
        """Get aggregated tallies across a date range."""
        pass

    @abstractmethod
    def delete_tallies_before(self, cutoff_date: date) -> int:
        """Delete tallies older than the cutoff date. Returns count deleted."""
        pass
```

### 1.3 IBlockingRecommendationService

Responsible for analyzing tallies and generating blocking recommendations.

```python
from abc import ABC, abstractmethod
from typing import List

class IBlockingRecommendationService(ABC):
    """Interface for generating category blocking recommendations."""

    @abstractmethod
    def get_recommendations(
        self,
        email_address: str,
        days: int = 7
    ) -> 'BlockingRecommendationResult':
        """Generate blocking recommendations based on category tallies."""
        pass

    @abstractmethod
    def get_recommendation_reasons(
        self,
        email_address: str,
        category: str
    ) -> 'RecommendationReason':
        """Get detailed reasoning for why a category is recommended for blocking."""
        pass
```

### 1.4 ICategoryAggregationConfig

Configuration interface for tunable parameters.

```python
from abc import ABC, abstractmethod

class ICategoryAggregationConfig(ABC):
    """Interface for category aggregation configuration."""

    @abstractmethod
    def get_recommendation_threshold_percentage(self) -> float:
        """Minimum percentage of total emails for a category to be recommended for blocking."""
        pass

    @abstractmethod
    def get_minimum_email_count(self) -> int:
        """Minimum number of emails in a category before it can be recommended."""
        pass

    @abstractmethod
    def get_excluded_categories(self) -> List[str]:
        """Categories that should never be recommended for blocking."""
        pass

    @abstractmethod
    def get_retention_days(self) -> int:
        """Number of days to retain historical tally data."""
        pass
```

---

## 2. Data Models

### 2.1 DailyCategoryTally

Represents category counts for a single day per account.

```python
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Dict

class DailyCategoryTally(BaseModel):
    """Daily aggregation of email categories for an account."""

    id: int | None = None
    email_address: str = Field(..., description="The email account this tally belongs to")
    tally_date: date = Field(..., description="The date these tallies are for")
    category_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Map of category name to count"
    )
    total_emails: int = Field(default=0, description="Total emails processed this day")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "email_address": "user@gmail.com",
                "tally_date": "2025-11-28",
                "category_counts": {
                    "Marketing": 45,
                    "Advertising": 32,
                    "Personal": 12,
                    "Work-related": 8,
                    "Financial-Notification": 3
                },
                "total_emails": 100
            }
        }
```

### 2.2 AggregatedCategoryTally

Represents aggregated tallies over a time period.

```python
from pydantic import BaseModel, Field
from datetime import date
from typing import Dict, List

class CategorySummary(BaseModel):
    """Summary statistics for a single category."""

    category: str
    total_count: int
    percentage: float = Field(..., ge=0, le=100)
    daily_average: float
    trend: str = Field(..., description="'increasing', 'decreasing', or 'stable'")

class AggregatedCategoryTally(BaseModel):
    """Aggregated category tallies over a time period."""

    email_address: str
    start_date: date
    end_date: date
    total_emails: int
    days_with_data: int
    category_summaries: List[CategorySummary] = Field(default_factory=list)

    def get_category_percentage(self, category: str) -> float:
        """Get the percentage for a specific category."""
        for summary in self.category_summaries:
            if summary.category == category:
                return summary.percentage
        return 0.0
```

### 2.3 BlockingRecommendation

Represents a single blocking recommendation.

```python
from pydantic import BaseModel, Field
from enum import Enum

class RecommendationStrength(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class BlockingRecommendation(BaseModel):
    """A recommendation to block a specific category."""

    category: str
    strength: RecommendationStrength
    email_count: int = Field(..., description="Number of emails in this category")
    percentage: float = Field(..., ge=0, le=100)
    reason: str = Field(..., description="Human-readable reason for recommendation")

    class Config:
        json_schema_extra = {
            "example": {
                "category": "Marketing",
                "strength": "high",
                "email_count": 245,
                "percentage": 35.2,
                "reason": "Marketing emails represent 35.2% of your inbox over the past 7 days (245 emails)"
            }
        }
```

### 2.4 BlockingRecommendationResult

Represents the full recommendation response.

```python
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import List

class BlockingRecommendationResult(BaseModel):
    """Result containing all blocking recommendations for an account."""

    email_address: str
    period_start: date
    period_end: date
    total_emails_analyzed: int
    recommendations: List[BlockingRecommendation] = Field(default_factory=list)
    already_blocked: List[str] = Field(
        default_factory=list,
        description="Categories already blocked for this account"
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "email_address": "user@gmail.com",
                "period_start": "2025-11-21",
                "period_end": "2025-11-28",
                "total_emails_analyzed": 695,
                "recommendations": [
                    {
                        "category": "Marketing",
                        "strength": "high",
                        "email_count": 245,
                        "percentage": 35.2,
                        "reason": "Marketing emails represent 35.2% of your inbox"
                    },
                    {
                        "category": "Advertising",
                        "strength": "medium",
                        "email_count": 156,
                        "percentage": 22.4,
                        "reason": "Advertising emails represent 22.4% of your inbox"
                    }
                ],
                "already_blocked": ["Wants-Money"]
            }
        }
```

### 2.5 RecommendationReason

Detailed reasoning for a recommendation.

```python
from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import date

class DailyBreakdown(BaseModel):
    """Daily count for trend analysis."""
    date: date
    count: int

class RecommendationReason(BaseModel):
    """Detailed reasoning for a blocking recommendation."""

    category: str
    total_count: int
    percentage: float
    daily_breakdown: List[DailyBreakdown]
    trend_direction: str
    trend_percentage_change: float
    comparable_categories: Dict[str, float] = Field(
        description="Other categories with similar percentages for context"
    )
    recommendation_factors: List[str] = Field(
        description="List of factors that contributed to this recommendation"
    )
```

---

## 3. Database Schema

### 3.1 Table: category_daily_tallies

```sql
CREATE TABLE category_daily_tallies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_address VARCHAR(255) NOT NULL,
    tally_date DATE NOT NULL,
    category VARCHAR(100) NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(email_address, tally_date, category),
    INDEX idx_email_date (email_address, tally_date),
    INDEX idx_date (tally_date)
);
```

### 3.2 Table: category_tally_summaries

Optional denormalized table for faster queries on large datasets.

```sql
CREATE TABLE category_tally_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_address VARCHAR(255) NOT NULL,
    tally_date DATE NOT NULL,
    total_emails INTEGER NOT NULL DEFAULT 0,
    category_json TEXT NOT NULL,  -- JSON blob of {category: count}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(email_address, tally_date),
    INDEX idx_email_date_summary (email_address, tally_date)
);
```

---

## 4. Logic Flow

### 4.1 Recording Categories During Background Processing

```
FUNCTION process_email_batch(email_address, emails):
    category_counts = {}

    FOR EACH email IN emails:
        category = categorize_email(email)
        category_counts[category] = category_counts.get(category, 0) + 1
    END FOR

    // Aggregate into daily tally
    aggregator.record_batch(
        email_address=email_address,
        category_counts=category_counts,
        timestamp=current_timestamp()
    )

    RETURN processed_count
END FUNCTION
```

### 4.2 Category Aggregator Implementation

```
CLASS CategoryAggregator IMPLEMENTS ICategoryAggregator:

    CONSTRUCTOR(repository: ICategoryTallyRepository):
        self.repository = repository
        self.buffer = {}  // In-memory buffer for batching
        self.buffer_size_limit = 100

    FUNCTION record_category(email_address, category, timestamp):
        tally_date = timestamp.date()
        key = (email_address, tally_date)

        IF key NOT IN self.buffer:
            self.buffer[key] = {}
        END IF

        self.buffer[key][category] = self.buffer[key].get(category, 0) + 1

        IF total_buffer_size() >= self.buffer_size_limit:
            self.flush()
        END IF
    END FUNCTION

    FUNCTION record_batch(email_address, category_counts, timestamp):
        tally_date = timestamp.date()
        key = (email_address, tally_date)

        IF key NOT IN self.buffer:
            self.buffer[key] = {}
        END IF

        FOR EACH category, count IN category_counts:
            self.buffer[key][category] = self.buffer[key].get(category, 0) + count
        END FOR

        self.flush()  // Flush immediately after batch
    END FUNCTION

    FUNCTION flush():
        FOR EACH (email_address, tally_date), counts IN self.buffer:
            existing = self.repository.get_tally(email_address, tally_date)

            IF existing:
                // Merge counts
                FOR EACH category, count IN counts:
                    existing.category_counts[category] =
                        existing.category_counts.get(category, 0) + count
                END FOR
                existing.total_emails += sum(counts.values())
                self.repository.save_daily_tally(existing)
            ELSE:
                new_tally = DailyCategoryTally(
                    email_address=email_address,
                    tally_date=tally_date,
                    category_counts=counts,
                    total_emails=sum(counts.values())
                )
                self.repository.save_daily_tally(new_tally)
            END IF
        END FOR

        self.buffer.clear()
    END FUNCTION
END CLASS
```

### 4.3 Recommendation Algorithm

```
CLASS BlockingRecommendationService IMPLEMENTS IBlockingRecommendationService:

    CONSTRUCTOR(
        repository: ICategoryTallyRepository,
        config: ICategoryAggregationConfig
    ):
        self.repository = repository
        self.config = config

    FUNCTION get_recommendations(email_address, days=7):
        end_date = today()
        start_date = end_date - days

        // Get aggregated tallies
        aggregated = self.repository.get_aggregated_tallies(
            email_address, start_date, end_date
        )

        IF aggregated.total_emails == 0:
            RETURN BlockingRecommendationResult(
                email_address=email_address,
                period_start=start_date,
                period_end=end_date,
                total_emails_analyzed=0,
                recommendations=[]
            )
        END IF

        recommendations = []
        excluded = self.config.get_excluded_categories()
        threshold_pct = self.config.get_recommendation_threshold_percentage()
        min_count = self.config.get_minimum_email_count()

        // Sort categories by count descending
        sorted_categories = SORT(
            aggregated.category_summaries,
            BY=total_count,
            DESCENDING
        )

        FOR EACH summary IN sorted_categories:
            // Skip excluded categories
            IF summary.category IN excluded:
                CONTINUE
            END IF

            // Check minimum count threshold
            IF summary.total_count < min_count:
                CONTINUE
            END IF

            // Determine recommendation strength
            strength = calculate_strength(summary.percentage, threshold_pct)

            IF strength IS NOT NULL:
                reason = generate_reason(summary, days)

                recommendations.append(BlockingRecommendation(
                    category=summary.category,
                    strength=strength,
                    email_count=summary.total_count,
                    percentage=summary.percentage,
                    reason=reason
                ))
            END IF
        END FOR

        // Get already blocked categories for context
        already_blocked = get_blocked_categories_for_account(email_address)

        RETURN BlockingRecommendationResult(
            email_address=email_address,
            period_start=start_date,
            period_end=end_date,
            total_emails_analyzed=aggregated.total_emails,
            recommendations=recommendations,
            already_blocked=already_blocked
        )
    END FUNCTION

    FUNCTION calculate_strength(percentage, threshold):
        // High: >= 25% of inbox
        IF percentage >= 25.0:
            RETURN RecommendationStrength.HIGH
        // Medium: >= 15% of inbox
        ELSE IF percentage >= 15.0:
            RETURN RecommendationStrength.MEDIUM
        // Low: >= threshold (default 10%)
        ELSE IF percentage >= threshold:
            RETURN RecommendationStrength.LOW
        ELSE:
            RETURN NULL  // Not significant enough to recommend
        END IF
    END FUNCTION

    FUNCTION generate_reason(summary, days):
        base = f"{summary.category} emails represent {summary.percentage:.1f}% "
        base += f"of your inbox over the past {days} days "
        base += f"({summary.total_count} emails)"

        IF summary.trend == "increasing":
            base += ". This category is trending upward."
        END IF

        RETURN base
    END FUNCTION
END CLASS
```

### 4.4 7-Day Rolling Aggregation Query

```sql
-- Get aggregated tallies for the past 7 days
SELECT
    category,
    SUM(count) as total_count,
    ROUND(SUM(count) * 100.0 /
        (SELECT SUM(count) FROM category_daily_tallies
         WHERE email_address = :email
         AND tally_date BETWEEN :start_date AND :end_date), 2) as percentage,
    ROUND(AVG(count), 2) as daily_average,
    COUNT(DISTINCT tally_date) as days_present
FROM category_daily_tallies
WHERE email_address = :email
    AND tally_date BETWEEN :start_date AND :end_date
GROUP BY category
ORDER BY total_count DESC;
```

---

## 5. API Endpoints

### 5.1 GET /api/accounts/{email_address}/recommendations

Get blocking recommendations for an account.

**Request**:
```
GET /api/accounts/user@gmail.com/recommendations?days=7
```

**Query Parameters**:
- `days` (optional, default=7): Number of days for rolling aggregation (1-30)

**Response** (200 OK):
```json
{
    "email_address": "user@gmail.com",
    "period_start": "2025-11-21",
    "period_end": "2025-11-28",
    "total_emails_analyzed": 695,
    "recommendations": [
        {
            "category": "Marketing",
            "strength": "high",
            "email_count": 245,
            "percentage": 35.2,
            "reason": "Marketing emails represent 35.2% of your inbox over the past 7 days (245 emails). This category is trending upward."
        },
        {
            "category": "Advertising",
            "strength": "medium",
            "email_count": 156,
            "percentage": 22.4,
            "reason": "Advertising emails represent 22.4% of your inbox over the past 7 days (156 emails)"
        }
    ],
    "already_blocked": ["Wants-Money"],
    "generated_at": "2025-11-28T14:30:00Z"
}
```

**Response** (404 Not Found):
```json
{
    "error": "Account not found",
    "email_address": "unknown@gmail.com"
}
```

### 5.2 GET /api/accounts/{email_address}/recommendations/{category}/details

Get detailed reasoning for a specific category recommendation.

**Request**:
```
GET /api/accounts/user@gmail.com/recommendations/Marketing/details
```

**Response** (200 OK):
```json
{
    "category": "Marketing",
    "total_count": 245,
    "percentage": 35.2,
    "daily_breakdown": [
        {"date": "2025-11-22", "count": 32},
        {"date": "2025-11-23", "count": 38},
        {"date": "2025-11-24", "count": 35},
        {"date": "2025-11-25", "count": 30},
        {"date": "2025-11-26", "count": 42},
        {"date": "2025-11-27", "count": 36},
        {"date": "2025-11-28", "count": 32}
    ],
    "trend_direction": "increasing",
    "trend_percentage_change": 8.5,
    "comparable_categories": {
        "Advertising": 22.4,
        "Service-Updates": 12.1
    },
    "recommendation_factors": [
        "High volume: 245 emails in 7 days",
        "Significant percentage: 35.2% of total inbox",
        "Upward trend: 8.5% increase week-over-week",
        "Consistent daily volume: averaging 35 emails/day"
    ]
}
```

### 5.3 GET /api/accounts/{email_address}/category-stats

Get raw category statistics without recommendations.

**Request**:
```
GET /api/accounts/user@gmail.com/category-stats?days=7
```

**Response** (200 OK):
```json
{
    "email_address": "user@gmail.com",
    "period_start": "2025-11-21",
    "period_end": "2025-11-28",
    "total_emails": 695,
    "days_with_data": 7,
    "categories": [
        {
            "category": "Marketing",
            "total_count": 245,
            "percentage": 35.2,
            "daily_average": 35.0,
            "trend": "increasing"
        },
        {
            "category": "Advertising",
            "total_count": 156,
            "percentage": 22.4,
            "daily_average": 22.3,
            "trend": "stable"
        }
    ]
}
```

---

## 6. Constructor Signatures

All constructors follow the rule of fewer than 4 arguments with no environment variable access.

### 6.1 CategoryAggregator

```python
class CategoryAggregator(ICategoryAggregator):
    def __init__(
        self,
        repository: ICategoryTallyRepository,
        buffer_size: int = 100
    ):
        """
        Args:
            repository: Repository for persisting tallies
            buffer_size: Number of records to buffer before flushing (default: 100)
        """
        pass
```

### 6.2 CategoryTallyRepository

```python
class CategoryTallyRepository(ICategoryTallyRepository):
    def __init__(
        self,
        db_connection: DatabaseConnection
    ):
        """
        Args:
            db_connection: Database connection for persistence
        """
        pass
```

### 6.3 BlockingRecommendationService

```python
class BlockingRecommendationService(IBlockingRecommendationService):
    def __init__(
        self,
        repository: ICategoryTallyRepository,
        config: ICategoryAggregationConfig
    ):
        """
        Args:
            repository: Repository for retrieving tallies
            config: Configuration for recommendation thresholds
        """
        pass
```

### 6.4 CategoryAggregationConfig

```python
class CategoryAggregationConfig(ICategoryAggregationConfig):
    def __init__(
        self,
        threshold_percentage: float = 10.0,
        minimum_count: int = 10,
        excluded_categories: List[str] = None
    ):
        """
        Args:
            threshold_percentage: Minimum % of total for recommendation (default: 10.0)
            minimum_count: Minimum email count for recommendation (default: 10)
            excluded_categories: Categories to never recommend blocking (default: ["Personal", "Work-related"])
        """
        pass
```

---

## 7. Integration with Existing Background Processing

### 7.1 Integration Point

The `CategoryAggregator` should be integrated into the existing background email processing flow. After each email is categorized, the aggregator records the category.

```python
# In background processor (conceptual integration)
class BackgroundEmailProcessor:
    def __init__(
        self,
        email_fetcher: IEmailFetcher,
        categorizer: IEmailCategorizer,
        category_aggregator: ICategoryAggregator  # NEW: Add aggregator
    ):
        self.email_fetcher = email_fetcher
        self.categorizer = categorizer
        self.category_aggregator = category_aggregator

    def process_account(self, email_address: str, hours: int):
        emails = self.email_fetcher.fetch(email_address, hours)
        category_counts = {}

        for email in emails:
            category = self.categorizer.categorize(email)
            category_counts[category] = category_counts.get(category, 0) + 1
            # Apply labels, etc.

        # NEW: Record aggregated categories
        self.category_aggregator.record_batch(
            email_address=email_address,
            category_counts=category_counts,
            timestamp=datetime.utcnow()
        )
```

### 7.2 Initialization

The aggregator and recommendation service should be initialized during application startup:

```python
# Application startup (conceptual)
def create_recommendation_components(db_connection: DatabaseConnection):
    repository = CategoryTallyRepository(db_connection)

    config = CategoryAggregationConfig(
        threshold_percentage=10.0,
        minimum_count=10,
        excluded_categories=["Personal", "Work-related", "Financial-Notification"]
    )

    aggregator = CategoryAggregator(repository)
    recommendation_service = BlockingRecommendationService(repository, config)

    return aggregator, recommendation_service
```

### 7.3 Data Cleanup Job

A scheduled job should clean up old tally data:

```python
# Daily cleanup job (conceptual)
def cleanup_old_tallies(repository: ICategoryTallyRepository, retention_days: int = 30):
    cutoff_date = date.today() - timedelta(days=retention_days)
    deleted_count = repository.delete_tallies_before(cutoff_date)
    logger.info(f"Cleaned up {deleted_count} old tally records")
```

---

## 8. Configuration Defaults

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| `threshold_percentage` | 10.0 | Minimum % of total emails for LOW recommendation |
| `minimum_count` | 10 | Minimum emails in category before recommending |
| `excluded_categories` | ["Personal", "Work-related", "Financial-Notification"] | Never recommend blocking |
| `retention_days` | 30 | Days to keep historical tally data |
| `buffer_size` | 100 | Records to buffer before flushing |

---

## 9. Recommendation Strength Thresholds

| Strength | Percentage Threshold | Interpretation |
|----------|---------------------|----------------|
| HIGH | >= 25% | Strongly recommend blocking |
| MEDIUM | >= 15% | Consider blocking |
| LOW | >= 10% | Optional blocking |

---

## 10. Future Considerations

1. **Machine Learning Enhancement**: Train a model on user blocking behavior to personalize recommendations
2. **Sender-Level Recommendations**: Extend to recommend blocking specific senders within categories
3. **Time-of-Day Analysis**: Factor in when emails arrive for more nuanced recommendations
4. **Cross-Account Insights**: Aggregate anonymized data across accounts for global recommendations
5. **Notification System**: Proactively notify users when new high-volume categories emerge
6. **A/B Testing**: Test different threshold values to optimize recommendation acceptance rates

---

## 11. Testing Strategy

### Unit Tests
- `CategoryAggregator.record_category()` correctly buffers records
- `CategoryAggregator.flush()` correctly merges with existing tallies
- `BlockingRecommendationService.calculate_strength()` returns correct strength levels
- `BlockingRecommendationService.get_recommendations()` excludes configured categories
- Repository correctly calculates percentages and aggregations

### Integration Tests
- Full flow from email processing to recommendation generation
- API endpoint returns correct response format
- Database queries perform within acceptable time limits

### BDD Scenarios
```gherkin
Feature: Email Category Blocking Recommendations

  Scenario: User receives high-strength recommendation for dominant category
    Given a user "test@gmail.com" has processed emails over 7 days
    And "Marketing" category has 250 emails (35% of total)
    When the user requests blocking recommendations
    Then they should receive a "high" strength recommendation for "Marketing"
    And the reason should mention "35%" and "250 emails"

  Scenario: Personal emails are never recommended for blocking
    Given a user "test@gmail.com" has processed emails over 7 days
    And "Personal" category has 300 emails (40% of total)
    When the user requests blocking recommendations
    Then "Personal" should not appear in recommendations

  Scenario: Low volume categories are not recommended
    Given a user "test@gmail.com" has processed emails over 7 days
    And "Appointment-Reminder" category has 5 emails (1% of total)
    When the user requests blocking recommendations
    Then "Appointment-Reminder" should not appear in recommendations
```

---

**End of DRAFT Specification**
