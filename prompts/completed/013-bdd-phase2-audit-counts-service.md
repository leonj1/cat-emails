---
executor: bdd
source_feature: ./tests/bdd/audit-counts-phase2-service.feature
---

<objective>
Implement the Email Processing Audit Counts - Service Layer feature as defined by the BDD scenarios below.
The implementation must make all Gherkin scenarios pass by extending the ProcessingStatusManager class
with audit count tracking capabilities.
</objective>

<gherkin>
Feature: Email Processing Audit Counts - Service Layer
  As a system administrator
  I want to track how many emails were reviewed, tagged, and deleted during processing
  So that I can monitor email processing activity and generate audit reports

  Background:
    Given a processing status manager is initialized

  Scenario: Account status includes audit count fields with default values
    When a processing session starts for "user@example.com"
    Then the current status shows emails reviewed as 0
    And the current status shows emails tagged as 0
    And the current status shows emails deleted as 0

  Scenario: Incrementing reviewed count during processing
    Given a processing session is active for "user@example.com"
    When 5 emails are marked as reviewed
    And 3 more emails are marked as reviewed
    Then the current status shows emails reviewed as 8

  Scenario: Incrementing tagged count during processing
    Given a processing session is active for "user@example.com"
    When 4 emails are marked as tagged
    Then the current status shows emails tagged as 4

  Scenario: Incrementing deleted count during processing
    Given a processing session is active for "user@example.com"
    When 2 emails are marked as deleted
    Then the current status shows emails deleted as 2

  Scenario: Audit counts are preserved when processing completes
    Given a processing session is active for "user@example.com"
    And 100 emails are marked as reviewed
    And 50 emails are marked as tagged
    And 25 emails are marked as deleted
    When the processing session completes
    Then the most recent run shows emails reviewed as 100
    And the most recent run shows emails tagged as 50
    And the most recent run shows emails deleted as 25

  Scenario: Incrementing counts without active session is ignored
    When 5 emails are marked as reviewed without an active session
    And 3 emails are marked as tagged without an active session
    And 2 emails are marked as deleted without an active session
    Then no error occurs
    And the audit counts return all zeros
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **AccountStatus Dataclass Extension**
   - Add `emails_reviewed: int = 0` field
   - Add `emails_tagged: int = 0` field
   - Add `emails_deleted: int = 0` field
   - Fields should default to 0 when session starts

2. **increment_reviewed(count=1) Method**
   - Increments `emails_reviewed` counter on current status
   - Thread-safe using existing `self._lock`
   - Accepts optional count parameter (default 1)
   - No-op if no active session (no exception)

3. **increment_tagged(count=1) Method**
   - Increments `emails_tagged` counter on current status
   - Thread-safe using existing `self._lock`
   - Accepts optional count parameter (default 1)
   - No-op if no active session (no exception)

4. **increment_deleted(count=1) Method**
   - Increments `emails_deleted` counter on current status
   - Thread-safe using existing `self._lock`
   - Accepts optional count parameter (default 1)
   - No-op if no active session (no exception)

5. **get_audit_counts() Method**
   - Returns dictionary with keys: emails_reviewed, emails_tagged, emails_deleted
   - Returns current session counts if active
   - Returns all zeros if no active session

6. **Update complete_processing() Method**
   - Include audit counts in the archived_run dictionary
   - Keys: emails_reviewed, emails_tagged, emails_deleted

Edge Cases to Handle:
- Calling increment methods when no session is active (should be a no-op, not raise)
- Multiple increments accumulate correctly
- Counts survive through complete_processing() into archived runs
- Thread safety on all counter operations
</requirements>

<context>
BDD Specification: specs/DRAFT-audit-counts-phase2-service.md
Gap Analysis: specs/GAP-ANALYSIS-phase2-service.md

Prerequisites:
- Phase 1 complete: ProcessingRun model has emails_reviewed, emails_tagged, emails_deleted columns

Target File: /root/repo/services/processing_status_manager.py

Reuse Opportunities (from gap analysis):
- Thread-safe method pattern: `with self._lock:` block
- Dataclass field pattern: `field_name: type = default_value`
- archived_run dictionary in complete_processing() method
- to_dict() auto-serialization via asdict()

New Components Needed:
- 3 dataclass fields in AccountStatus (~3 lines)
- 4 new methods in ProcessingStatusManager (~46 lines)
- Update to complete_processing() archived_run dictionary (~3 lines)
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing thread safety pattern with self._lock (RLock)
- Maintain consistency with existing method signatures
- Docstrings should follow existing style in the file

Implementation Steps:
1. Add three integer fields to AccountStatus dataclass with default=0
2. Add increment_reviewed() method with lock
3. Add increment_tagged() method with lock
4. Add increment_deleted() method with lock
5. Add get_audit_counts() method with lock
6. Update complete_processing() to include audit counts in archived_run

Code Pattern to Follow:
```python
def increment_reviewed(self, count: int = 1) -> None:
    """
    Increment the count of emails reviewed.

    Args:
        count: Number to increment by (default 1)

    Thread-safe: Uses internal RLock
    """
    with self._lock:
        if self._current_status:
            self._current_status.emails_reviewed += count
```
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Account status includes audit count fields with default values
- [ ] Scenario: Incrementing reviewed count during processing
- [ ] Scenario: Incrementing tagged count during processing
- [ ] Scenario: Incrementing deleted count during processing
- [ ] Scenario: Audit counts are preserved when processing completes
- [ ] Scenario: Incrementing counts without active session is ignored
</verification>

<success_criteria>
- All 6 Gherkin scenarios pass
- AccountStatus dataclass has 3 new integer fields with default 0
- ProcessingStatusManager has 4 new methods: increment_reviewed, increment_tagged, increment_deleted, get_audit_counts
- complete_processing() includes audit counts in archived_run
- All operations are thread-safe
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
</success_criteria>
