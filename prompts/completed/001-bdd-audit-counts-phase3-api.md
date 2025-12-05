---
executor: bdd
source_feature: ./tests/bdd/audit-counts-phase3-api.feature
---

<objective>
Implement the Email Processing Audit Counts API Response feature as defined by the BDD scenarios below.
The implementation must make all Gherkin scenarios pass.

Update the `DatabaseService.get_processing_runs()` method to expose the audit count fields
(`emails_reviewed`, `emails_tagged`, `emails_deleted`) in API responses.
</objective>

<gherkin>
Feature: Email Processing Audit Counts - API Response
  As a client application
  I want the processing runs API to include audit count fields
  So that I can display email processing statistics in the dashboard

  Background:
    Given the database contains processing run records

  Scenario: API response includes emails_reviewed field
    Given a processing run exists with emails_reviewed set to 100
    When I retrieve the processing runs via the API
    Then the response should include an "emails_reviewed" field
    And the "emails_reviewed" value should be 100

  Scenario: API response includes emails_tagged field
    Given a processing run exists with emails_tagged set to 45
    When I retrieve the processing runs via the API
    Then the response should include an "emails_tagged" field
    And the "emails_tagged" value should be 45

  Scenario: API response includes emails_deleted field from database
    Given a processing run exists with emails_deleted set to 30
    When I retrieve the processing runs via the API
    Then the response should include an "emails_deleted" field
    And the "emails_deleted" value should be 30

  Scenario: Null audit count values default to zero in API response
    Given a processing run exists with null audit count values
    When I retrieve the processing runs via the API
    Then the "emails_reviewed" value should be 0
    And the "emails_tagged" value should be 0
    And the "emails_deleted" value should be 0

  Scenario: API response includes all audit fields together
    Given a processing run exists with:
      | emails_reviewed | 150 |
      | emails_tagged   | 60  |
      | emails_deleted  | 25  |
    When I retrieve the processing runs via the API
    Then the response should contain all audit count fields
    And the "emails_reviewed" value should be 150
    And the "emails_tagged" value should be 60
    And the "emails_deleted" value should be 25
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. Add `emails_reviewed` field to `get_processing_runs()` return dictionary
   - Read from `run.emails_reviewed` model attribute
   - Default to 0 if value is None (backward compatibility)

2. Add `emails_tagged` field to `get_processing_runs()` return dictionary
   - Read from `run.emails_tagged` model attribute
   - Default to 0 if value is None (backward compatibility)

3. Fix `emails_deleted` field in `get_processing_runs()` return dictionary
   - Change from hardcoded `0` to actual `run.emails_deleted` value
   - Default to 0 if value is None (backward compatibility)

Edge Cases to Handle:
- Legacy ProcessingRun records with None audit values should return 0
- All audit fields should be present in every response
- Integer overflow not expected but noted (database uses Integer type)
</requirements>

<context>
BDD Specification: specs/DRAFT-audit-counts-phase3-api.md
Gap Analysis: specs/GAP-ANALYSIS-phase3-api.md

Reuse Opportunities (from gap analysis):
- ProcessingRun model already has audit columns (Phase 1 complete)
- Use `or 0` pattern to handle None values (matches existing code patterns)
- DashboardService will automatically benefit from this change

New Components Needed:
- Update return dictionary in `get_processing_runs()` method (~3 lines)
- Create unit tests for audit field mapping

Target File: /root/repo/services/database_service.py
Target Method: get_processing_runs() at lines 287-305
Target Change: Lines 294-305 (return statement)
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Specific Implementation:

Update the return dictionary in `get_processing_runs()` method:

```python
return [
    {
        'run_id': f"run-{run.id}",
        'started_at': run.start_time,
        'completed_at': run.end_time,
        'duration_seconds': (run.end_time - run.start_time).total_seconds() if run.end_time else None,
        'emails_processed': run.emails_processed,
        # UPDATED: Read actual audit counts from model
        'emails_reviewed': run.emails_reviewed or 0,
        'emails_tagged': run.emails_tagged or 0,
        'emails_deleted': run.emails_deleted or 0,
        'success': run.state == 'completed' and not run.error_message,
        'error_message': run.error_message
    } for run in runs
]
```

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Maintain consistency with project structure
- database_service.py is currently 363 lines (well under 500)
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: API response includes emails_reviewed field
- [ ] Scenario: API response includes emails_tagged field
- [ ] Scenario: API response includes emails_deleted field from database
- [ ] Scenario: Null audit count values default to zero in API response
- [ ] Scenario: API response includes all audit fields together
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- Backward compatible with existing API consumers
- No breaking changes to existing fields
</success_criteria>
