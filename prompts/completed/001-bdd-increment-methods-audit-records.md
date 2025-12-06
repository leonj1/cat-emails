---
executor: bdd
source_feature: ./tests/bdd/increment_methods_audit_records.feature
---

<objective>
Implement the Increment Methods feature for tracking categorized and skipped email counts during processing sessions. The implementation must add `increment_categorized()` and `increment_skipped()` methods to the `ProcessingStatusManager` class, following the existing pattern of `increment_reviewed()`, `increment_tagged()`, and `increment_deleted()` methods. All Gherkin scenarios must pass.
</objective>

<gherkin>
Feature: Increment Methods for Categorized and Skipped Email Counts
  As an email processing system
  I want to increment audit counters for categorized and skipped emails
  So that processing statistics are accurately tracked throughout each session

  Background:
    Given the audit recording system is available

  Scenario: Increment categorized count with default value
    Given an active processing session exists
    When the system records an email as categorized
    Then the categorized email count increases by one

  Scenario: Increment skipped count with batch value
    Given an active processing session exists
    When the system records five emails as skipped
    Then the skipped email count increases by five

  Scenario: Increment is silent when no session is active
    Given no processing session is active
    When the system attempts to record an email as categorized
    Then no error occurs
    And no count is recorded

  Scenario: Increments are cumulative within a session
    Given an active processing session exists
    When the system records three emails as categorized
    And the system records two more emails as categorized
    Then the categorized email count shows five total
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **increment_categorized() method**
   - Add to `ProcessingStatusManager` class after line 315
   - Accept optional `count` parameter with default value of 1
   - Increment `self._current_status.emails_categorized` by the count
   - Thread-safe using `self._lock`
   - Silent no-op when no active session (no exception thrown)

2. **increment_skipped() method**
   - Add to `ProcessingStatusManager` class after `increment_categorized()`
   - Accept optional `count` parameter with default value of 1
   - Increment `self._current_status.emails_skipped` by the count
   - Thread-safe using `self._lock`
   - Silent no-op when no active session (no exception thrown)

3. **Method Signature**
   ```python
   def increment_categorized(self, count: int = 1) -> None:
   def increment_skipped(self, count: int = 1) -> None:
   ```

Edge Cases to Handle:
- No active session: Return silently without raising exception
- Batch increments: Accept any positive integer count value
- Cumulative behavior: Multiple calls should accumulate within a session

Business Rules:
- Default increment value is 1
- Increments must be additive (cumulative) within a session
- Thread-safe operations are mandatory
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-increment-methods-audit-records.md
Gap Analysis: specs/GAP-ANALYSIS.md (Section: Increment Methods for Audit Records Sub-task 1.2)

Reuse Opportunities (from gap analysis):
- Follow exact pattern from existing `increment_reviewed()` (lines 263-279)
- Follow exact pattern from existing `increment_tagged()` (lines 281-297)
- Follow exact pattern from existing `increment_deleted()` (lines 299-315)
- `AccountStatus` dataclass already has `emails_categorized` and `emails_skipped` fields
- `complete_processing()` already archives these fields in run history

Pattern to Follow:
```python
def increment_xxx(self, count: int = 1) -> None:
    """
    Increment the count of emails xxx during processing.

    Args:
        count: Number of emails to add to the xxx count (default: 1)

    Note:
        This is a no-op if no processing session is active.
        Thread-safe operation using internal lock.
    """
    with self._lock:
        if not self._current_status:
            # Silently ignore if no active session
            return

        self._current_status.emails_xxx += count
```

New Components Needed:
- `increment_categorized()` method in ProcessingStatusManager
- `increment_skipped()` method in ProcessingStatusManager
</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Target File: `/root/repo/services/processing_status_manager.py`
Insert Location: After line 315 (after `increment_deleted()` method)

Architecture Guidelines:
- Follow strict-architecture rules (methods are small and focused)
- Use existing patterns from codebase (identical to increment_reviewed/tagged/deleted)
- Maintain consistency with project structure
- Thread-safe using existing `self._lock` pattern
- No new dependencies required
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Increment categorized count with default value
- [ ] Scenario: Increment skipped count with batch value
- [ ] Scenario: Increment is silent when no session is active
- [ ] Scenario: Increments are cumulative within a session
</verification>

<success_criteria>
- All 4 Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- Methods follow existing increment_xxx pattern exactly
- Thread-safe operations verified
- Silent no-op behavior when no session active
</success_criteria>
