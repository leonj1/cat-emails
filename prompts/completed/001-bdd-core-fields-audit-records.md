---
executor: bdd
source_feature: ./tests/bdd/core_fields_audit_records.feature
---

<objective>
Implement the Core Audit Fields feature as defined by the BDD scenarios below.
Add `emails_categorized` and `emails_skipped` fields to both the ProcessingRun database model and AccountStatus dataclass.
The implementation must make all Gherkin scenarios pass.
</objective>

<gherkin>
Feature: Core Audit Fields for Categorized and Skipped Emails
  As an account administrator
  I want processing audit records to track emails categorized and skipped
  So that I can monitor email processing effectiveness and identify issues

  Background:
    Given the email processing system is operational
    And audit recording is enabled

  Scenario: ProcessingRun model includes emails_categorized column
    Given a processing run is initiated for an account
    When the processing completes with some emails categorized
    Then the processing run record stores the emails_categorized count
    And the count reflects the actual number of emails that were categorized

  Scenario: ProcessingRun model includes emails_skipped column
    Given a processing run is initiated for an account
    When the processing completes with some emails skipped
    Then the processing run record stores the emails_skipped count
    And the count reflects the actual number of emails that were skipped

  Scenario: AccountStatus dataclass includes emails_categorized field
    Given an account has completed processing runs
    When the account status is retrieved
    Then the status includes the emails_categorized field
    And the field contains the cumulative count of categorized emails

  Scenario: AccountStatus dataclass includes emails_skipped field
    Given an account has completed processing runs
    When the account status is retrieved
    Then the status includes the emails_skipped field
    And the field contains the cumulative count of skipped emails
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **ProcessingRun Model - emails_categorized column**
   - Add `emails_categorized` column to ProcessingRun class in models/database.py
   - Column type: Integer
   - Default value: 0
   - Nullable: False
   - Pattern: Follow existing `emails_reviewed` column definition

2. **ProcessingRun Model - emails_skipped column**
   - Add `emails_skipped` column to ProcessingRun class in models/database.py
   - Column type: Integer
   - Default value: 0
   - Nullable: False
   - Pattern: Follow existing `emails_reviewed` column definition

3. **AccountStatus Dataclass - emails_categorized field**
   - Add `emails_categorized: int = 0` field to AccountStatus dataclass
   - Location: services/processing_status_manager.py
   - Pattern: Follow existing `emails_reviewed` field definition

4. **AccountStatus Dataclass - emails_skipped field**
   - Add `emails_skipped: int = 0` field to AccountStatus dataclass
   - Location: services/processing_status_manager.py
   - Pattern: Follow existing `emails_reviewed` field definition

5. **Database Migration**
   - Create sql/V3__add_categorized_skipped_columns.sql
   - ALTER TABLE processing_runs ADD COLUMN emails_categorized INT DEFAULT 0 NOT NULL
   - ALTER TABLE processing_runs ADD COLUMN emails_skipped INT DEFAULT 0 NOT NULL

Edge Cases to Handle:
- New records should default audit counts to 0
- Custom values should be storable and retrievable
- Fields should be included in AccountStatus.to_dict() output
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-core-fields-audit-records.md
Gap Analysis: specs/GAP-ANALYSIS-core-fields-audit-records.md

Reuse Opportunities (from gap analysis):
- ProcessingRun model already has emails_reviewed, emails_tagged, emails_deleted columns with identical pattern
- AccountStatus dataclass already has emails_reviewed, emails_tagged, emails_deleted fields with identical pattern
- Test patterns exist in tests/test_processing_run_audit_columns.py
- Test patterns exist in tests/test_processing_status_manager_audit_counts.py

Existing Files to Modify:
- /root/repo/models/database.py (ProcessingRun class, lines 204-230)
- /root/repo/services/processing_status_manager.py (AccountStatus dataclass, lines 59-83)

New Files to Create:
- /root/repo/sql/V3__add_categorized_skipped_columns.sql
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase
- Maintain consistency with project structure

Implementation Steps:
1. Create Flyway migration V3__add_categorized_skipped_columns.sql
2. Add emails_categorized and emails_skipped columns to ProcessingRun model
3. Add emails_categorized and emails_skipped fields to AccountStatus dataclass
4. Verify to_dict() includes new fields (automatic with @dataclass and asdict)
5. Run tests to verify all scenarios pass
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: ProcessingRun model includes emails_categorized column
- [ ] Scenario: ProcessingRun model includes emails_skipped column
- [ ] Scenario: AccountStatus dataclass includes emails_categorized field
- [ ] Scenario: AccountStatus dataclass includes emails_skipped field
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- ProcessingRun model has emails_categorized and emails_skipped columns
- AccountStatus dataclass has emails_categorized and emails_skipped fields
- Flyway migration V3 is created and valid
- New fields default to 0
- New fields are not nullable
- New fields are included in serialization (to_dict)
</success_criteria>
