# Cat-Emails Web Dashboard REST API Documentation

This document describes the REST API endpoints available in the Cat-Emails Web Dashboard Flask application.

## Base URL
When running locally: `http://localhost:5000`

## Authentication
Currently, no authentication is required for API endpoints.

## Response Format
All API responses follow this general format:

```json
{
  "success": true/false,
  "data": {...},
  "error": "Error message (if success=false)"
}
```

---

## Required API Endpoints

### 1. Get Top Categories
**Endpoint:** `GET /api/categories/top`

**Description:** Get top N categories with counts, percentages, and trends using the DashboardService.

**Query Parameters:**
- `limit` (optional): Number of categories to return (1-100, default: 25)
- `period` (optional): Time period for data aggregation (`day`, `week`, `month`, default: `week`)

**Example Request:**
```
GET /api/categories/top?limit=10&period=week
```

**Example Response:**
```json
{
  "success": true,
  "data": [
    {
      "name": "Marketing",
      "original_name": "MARKETING",
      "count": 152,
      "percentage": 35.2,
      "rank": 1,
      "deleted": 45,
      "trend": "up"
    }
  ],
  "metadata": {
    "limit_applied": 10,
    "categories_returned": 10,
    "total_categories_available": 25,
    "period_info": {...}
  },
  "total_emails": 432,
  "period": "week",
  "last_updated": "2023-01-15T10:30:00.000Z"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid limit (outside 1-100 range) or invalid period
- `500 Internal Server Error`: Server error during data retrieval

---

### 2. Get Historical Trends
**Endpoint:** `GET /api/trends`

**Description:** Get historical trend data for email categories using the DashboardService.

**Query Parameters:**
- `days` (optional): Number of days to look back (1-365, default: 30)
- `categories` (optional): Specific categories to include (can specify multiple)

**Example Request:**
```
GET /api/trends?days=7&categories=Marketing&categories=Personal
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "Marketing": {
      "original_name": "MARKETING",
      "display_name": "Marketing",
      "data_points": [
        {
          "date": "2023-01-10T00:00:00",
          "count": 25
        },
        {
          "date": "2023-01-11T00:00:00",
          "count": 32
        }
      ],
      "total_points": 7,
      "trend_direction": "up",
      "latest_count": 32,
      "max_count": 45
    }
  },
  "metadata": {
    "days": 7,
    "categories_included": ["Marketing", "Personal"],
    "total_categories": 2,
    "date_range": {
      "start": "2023-01-08T10:30:00.000Z",
      "end": "2023-01-15T10:30:00.000Z"
    },
    "last_updated": "2023-01-15T10:30:00.000Z"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid days parameter (outside 1-365 range)
- `500 Internal Server Error`: Server error during data retrieval

---

### 3. Get System Metrics
**Endpoint:** `GET /api/metrics`

**Description:** Get system performance metrics using the DashboardService.

**Query Parameters:**
- `limit` (optional): Number of recent processing runs to include (1-100, default: 10)
- `include_runs` (optional): Include recent processing runs in response (`true`/`false`, default: `true`)

**Example Request:**
```
GET /api/metrics?limit=5&include_runs=true
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "performance_metrics": {
      "total_runs_analyzed": 10,
      "success_rate_percent": 95.2,
      "avg_processing_time_seconds": 12.5,
      "avg_emails_per_run": 45.2,
      "total_emails_processed": 452,
      "total_duration_seconds": 125.0
    },
    "recent_runs": [
      {
        "run_id": "run_20230115_103000",
        "started_at": "2023-01-15T10:30:00.000Z",
        "completed_at": "2023-01-15T10:30:15.000Z",
        "duration_seconds": 15,
        "emails_processed": 50,
        "emails_deleted": 12,
        "success": true,
        "error_message": ""
      }
    ],
    "last_updated": "2023-01-15T10:30:00.000Z"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid limit parameter (outside 1-100 range)
- `500 Internal Server Error`: Server error during data retrieval

---

### 4. Health Check
**Endpoint:** `GET /api/health`

**Description:** Check the health status of the application and its dependencies.

**Query Parameters:** None

**Example Request:**
```
GET /api/health
```

**Example Response (Healthy):**
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2023-01-15T10:30:00.000000",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "dashboard_service": "healthy"
  }
}
```

**Example Response (Degraded):**
```json
{
  "success": true,
  "status": "degraded",
  "timestamp": "2023-01-15T10:30:00.000000",
  "version": "1.0.0",
  "services": {
    "database": "unhealthy",
    "dashboard_service": "healthy"
  }
}
```

**Response Codes:**
- `200 OK`: All services are healthy
- `503 Service Unavailable`: One or more services are unhealthy

---

## Additional API Endpoints

The following endpoints are also available for backward compatibility and additional functionality:

### Legacy Stats Endpoints

#### Overview Statistics
`GET /api/stats/overview?period=week`

#### Category Statistics  
`GET /api/stats/categories?period=week&limit=25`

#### Sender Statistics
`GET /api/stats/senders?period=week&limit=25`

#### Domain Statistics
`GET /api/stats/domains?period=week&limit=25`

#### Legacy Trends (Different format)
`GET /api/stats/trends?days=30`

#### Processing Runs
`GET /api/stats/processing-runs?limit=50`

---

## Error Handling

All endpoints include comprehensive error handling:

### Common HTTP Status Codes
- `200 OK`: Request successful
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Endpoint not found
- `500 Internal Server Error`: Server-side error
- `503 Service Unavailable`: Service dependencies unavailable

### Error Response Format
```json
{
  "success": false,
  "error": "Descriptive error message"
}
```

---

## Data Validation

### Parameter Validation
- **limit**: Must be between 1 and 100
- **period**: Must be one of `day`, `week`, `month`  
- **days**: Must be between 1 and 365
- **include_runs**: Must be `true` or `false`

### Category Name Formatting
- All category names are automatically formatted for display
- Names are truncated to 40 characters maximum with ellipsis if needed
- Underscores are converted to spaces and title case is applied
- Original names are preserved in `original_name` field

---

## Integration with DashboardService

The required API endpoints (`/api/categories/top`, `/api/trends`, `/api/metrics`) use the DashboardService which provides:

- **Intelligent category name formatting** (40-character limit with smart truncation)
- **Percentage calculations** for category distributions
- **Trend analysis** with direction indicators (up/down/stable)
- **Performance metrics** aggregation
- **Error handling** and data validation
- **Consistent response formatting**

This ensures data consistency and proper formatting across all API responses.

---

## Usage Examples

### Get top 5 categories for the current week
```bash
curl "http://localhost:5000/api/categories/top?limit=5&period=week"
```

### Get trend data for last 14 days
```bash
curl "http://localhost:5000/api/trends?days=14"
```

### Get performance metrics without recent runs
```bash
curl "http://localhost:5000/api/metrics?include_runs=false"
```

### Check application health
```bash
curl "http://localhost:5000/api/health"
```