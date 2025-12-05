---
executor: bdd
source_feature: ./tests/bdd/audit-counts-phase1-database.feature
---

<objective>
Implement the Email Processing Audit Count Database Columns feature as defined by the BDD scenarios below.
Add three new integer columns (emails_reviewed, emails_tagged, emails_deleted) to the ProcessingRun model
with proper defaults and not-null constraints. The implementation must make all Gherkin scenarios pass.
</objective>

<gherkin>
Feature: Email Processing Audit Count Database Columns
  As a system administrator
  I want the ProcessingRun table to include audit count columns
  So that email processing statistics can be persisted for reporting

  Background:
    Given the database schema has been initialized

  Scenario: ProcessingRun model includes emails_reviewed column
    When a new ProcessingRun record is created
    Then the record should have an "emails_reviewed" field
    And the "emails_reviewed" field should be an integer
    And the "emails_reviewed" field should default to 0
    And the "emails_reviewed" field should not accept null values

  Scenario: ProcessingRun model includes emails_tagged column
    When a new ProcessingRun record is created
    Then the record should have an "emails_tagged" field
    And the "emails_tagged" field should be an integer
    And the "emails_tagged" field should default to 0
    And the "emails_tagged" field should not accept null values

  Scenario: ProcessingRun model includes emails_deleted column
    When a new ProcessingRun record is created
    Then the record should have an "emails_deleted" field
    And the "emails_deleted" field should be an integer
    And the "emails_deleted" field should default to 0
    And the "emails_deleted" field should not accept null values

  Scenario: ProcessingRun record stores custom audit count values
    Given a ProcessingRun record is created with:
      | emails_reviewed | 150 |
      | emails_tagged   | 25  |
      | emails_deleted  | 42  |
    When the record is retrieved from the database
    Then the "emails_reviewed" value should be 150
    And the "emails_tagged" value should be 25
    And the "emails_deleted" value should be 42

  Scenario: New ProcessingRun records default audit counts to zero
    Given a ProcessingRun record is created without specifying audit counts
    When the record is retrieved from the database
    Then the "emails_reviewed" value should be 0
    And the "emails_tagged" value should be 0
    And the "emails_deleted" value should be 0
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. Add emails_reviewed column to ProcessingRun model
   - Type: Integer
   - Default: 0
   - Nullable: False (NOT NULL)

2. Add emails_tagged column to ProcessingRun model
   - Type: Integer
   - Default: 0
   - Nullable: False (NOT NULL)

3. Add emails_deleted column to ProcessingRun model
   - Type: Integer
   - Default: 0
   - Nullable: False (NOT NULL)

4. Create database migration script
   - File: /root/repo/migrations/003_add_audit_count_columns.py
   - Follow existing migration pattern from 002_modify_processing_runs.py
   - Add ALTER TABLE statements for each new column

5. Write unit tests that verify:
   - Column existence on ProcessingRun model
   - Column type is Integer
   - Default values are 0
   - NOT NULL constraint is enforced
   - Custom values can be stored and retrieved

Edge Cases to Handle:
- Existing ProcessingRun records should get default value of 0 for new columns
- Creating record without specifying audit counts should use defaults
- Creating record with explicit values should store those values correctly
</requirements>

<context>
BDD Specification: specs/DRAFT-audit-counts-phase1-database.md
Gap Analysis: specs/GAP-ANALYSIS.md

Reuse Opportunities (from gap analysis):
- Follow existing column definition pattern: `Column(Integer, default=0)`
- Follow migration pattern from `/root/repo/migrations/002_modify_processing_runs.py`
- Test patterns from `/root/repo/tests/test_integration_background_processing.py`

New Components Needed:
- 3 new column definitions in ProcessingRun class
- Migration script (003_add_audit_count_columns.py)
- Test file (test_processing_run_audit_columns.py)

Existing File to Modify:
- `/root/repo/models/database.py` - ProcessingRun class (lines 204-225)
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios FIRST
2. Tests should initially FAIL (Red phase)
3. Implement code to make tests pass (Green phase)
4. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Maintain consistency with project structure
- Migration file should follow the pattern in migrations/002_modify_processing_runs.py

Implementation Steps:
1. Create test file: /root/repo/tests/test_processing_run_audit_columns.py
2. Write failing tests for each Gherkin scenario
3. Add columns to ProcessingRun model in /root/repo/models/database.py
4. Create migration file: /root/repo/migrations/003_add_audit_count_columns.py
5. Run tests to verify all pass

Column Definition Pattern:
```python
# Add after emails_processed in ProcessingRun class
emails_reviewed = Column(Integer, default=0, nullable=False)
emails_tagged = Column(Integer, default=0, nullable=False)
emails_deleted = Column(Integer, default=0, nullable=False)
```
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: ProcessingRun model includes emails_reviewed column
- [ ] Scenario: ProcessingRun model includes emails_tagged column
- [ ] Scenario: ProcessingRun model includes emails_deleted column
- [ ] Scenario: ProcessingRun record stores custom audit count values
- [ ] Scenario: New ProcessingRun records default audit counts to zero
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- Migration script applies cleanly to existing databases
- Existing tests continue to pass
- ProcessingRun model has three new Integer columns with default=0 and nullable=False
</success_criteria>
