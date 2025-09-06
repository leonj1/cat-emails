# Account Tracking Tests

This directory contains comprehensive unit tests for the Cat-Emails account tracking functionality, including the AccountCategoryService, API endpoints, and database models.

## Test Files Overview

### 1. `test_account_category_service.py`
**Comprehensive tests for the AccountCategoryService class.**

**Coverage:**
- Service initialization and configuration
- Email address validation and normalization
- Account creation, retrieval, and updates
- Category statistics recording and retrieval
- Top categories calculation with aggregation
- Account management (activation/deactivation)
- Database session management
- Error handling and logging
- Edge cases and boundary conditions

**Key Test Areas:**
- `get_or_create_account()` - Account lifecycle management
- `get_account_by_email()` - Account retrieval
- `update_account_last_scan()` - Timestamp updates
- `record_category_stats()` - Statistics recording with upsert logic
- `get_top_categories()` - Category ranking and aggregation
- `get_all_accounts()` - Account listing and filtering
- `deactivate_account()` - Account deactivation

### 2. `test_api_endpoints_account.py`
**Comprehensive tests for FastAPI account management endpoints.**

**Coverage:**
- All account-related API endpoints
- Request/response validation
- Authentication (API key validation)
- Error handling and status codes
- Query parameter validation
- JSON request/response formats
- Database integration testing

**API Endpoints Tested:**
- `GET /api/accounts/{email}/categories/top` - Top categories retrieval
- `GET /api/accounts` - Account listing
- `POST /api/accounts` - Account creation
- `PUT /api/accounts/{email}/deactivate` - Account deactivation

**Test Scenarios:**
- Valid requests with various parameters
- Invalid parameters and validation errors
- Authentication scenarios (with/without API keys)
- Error responses (404, 400, 422, 500)
- Content-Type validation
- Edge cases (special characters, long inputs)

### 3. `test_account_models.py`
**Comprehensive tests for database models and Pydantic validation models.**

**Coverage:**
- Database model creation and constraints
- Pydantic model validation
- Relationships and foreign keys
- Unique constraints and indexes
- Model serialization/deserialization
- Data validation and error handling

**Database Models Tested:**
- `EmailAccount` - Account storage and relationships
- `AccountCategoryStats` - Category statistics with constraints
- Database initialization and schema creation
- Cascade deletion behavior
- Index functionality

**Pydantic Models Tested:**
- `AccountCategoryStatsRequest` - API request validation
- `CategoryStats` - Category data with percentage calculation
- `DatePeriod` - Date range validation
- `TopCategoriesResponse` - API response structure
- `EmailAccountInfo` - Account information model
- `AccountListResponse` - Account listing response

### 4. `test_account_service_simple.py`
**Simplified test suite for basic functionality verification.**

This is a streamlined version that focuses on core functionality without complex session management issues. Use this for quick verification that the basic service operations work.

## Running the Tests

### Prerequisites

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Required Packages for Testing:**
   ```bash
   pip install fastapi[all] httpx pytest
   ```

### Running Individual Test Files

```bash
# Basic service functionality (recommended starting point)
python3 -m unittest tests.test_account_service_simple -v

# Full service tests
python3 -m unittest tests.test_account_category_service -v

# API endpoint tests (requires matplotlib for chart generation)
python3 -m unittest tests.test_api_endpoints_account -v

# Database model tests
python3 -m unittest tests.test_account_models -v
```

### Running All Account Tests

```bash
# Run all account-related tests
python3 -m unittest discover tests/ -p "test_account*" -v
```

### Using pytest (if available)

```bash
# Run with pytest for better output
python3 -m pytest tests/test_account_service_simple.py -v
python3 -m pytest tests/test_account_category_service.py -v
python3 -m pytest tests/test_api_endpoints_account.py -v
python3 -m pytest tests/test_account_models.py -v
```

## Test Database

All tests use temporary SQLite databases that are automatically created and cleaned up. Each test gets its own isolated database to ensure no test interference.

## Common Issues and Solutions

### 1. SQLAlchemy DetachedInstanceError
If you encounter "DetachedInstanceError" messages, this is due to SQLAlchemy session management. The tests handle this by capturing object IDs before session closure.

### 2. Missing matplotlib
API endpoint tests require matplotlib for chart generation. Install with:
```bash
pip install matplotlib seaborn
```

### 3. Import Errors
If you get import errors, ensure you're running tests from the project root directory:
```bash
cd /path/to/cat-emails
python3 -m unittest tests.test_account_service_simple
```

### 4. Database Migration Warnings
You may see warnings about database migrations. These are safe to ignore in the test environment.

## Test Coverage Goals

The test suite aims for comprehensive coverage:

- **Service Layer:** 95%+ method coverage with error scenarios
- **API Endpoints:** All endpoints with success/failure scenarios
- **Database Models:** All constraints, relationships, and validations
- **Error Handling:** All exception paths and edge cases
- **Validation:** All input validation and business rules

## Adding New Tests

When adding new functionality to the account tracking system:

1. **Service Methods:** Add tests to `test_account_category_service.py`
2. **API Endpoints:** Add tests to `test_api_endpoints_account.py`
3. **Database Models:** Add tests to `test_account_models.py`
4. **Simple Verification:** Add basic tests to `test_account_service_simple.py`

### Test Naming Convention

- Test methods start with `test_`
- Use descriptive names: `test_get_top_categories_with_include_counts`
- Group related tests in classes
- Use docstrings to describe test purpose

### Test Structure

```python
def test_feature_scenario(self):
    """Test feature under specific scenario."""
    # Arrange - Set up test data
    # Act - Execute the operation
    # Assert - Verify results
```

## Integration with CI/CD

These tests are designed to run in CI/CD environments:

- No external dependencies (uses SQLite)
- Temporary file cleanup
- Isolated test execution
- Clear pass/fail indicators

## Performance Considerations

- Tests use in-memory SQLite for speed
- Temporary files are cleaned up automatically  
- Each test runs in isolation
- Database schema is created fresh for each test class

## Debugging Tests

To debug failing tests:

1. **Run single test:**
   ```bash
   python3 -m unittest tests.test_account_service_simple.TestAccountCategoryServiceSimple.test_create_new_account -v
   ```

2. **Add debug prints:**
   ```python
   print(f"Account created: {account.email_address}")
   ```

3. **Use database inspection:**
   ```python
   # In test method
   session.execute(text("SELECT * FROM email_accounts")).fetchall()
   ```

4. **Check logs:**
   The service includes comprehensive logging that can help debug issues.