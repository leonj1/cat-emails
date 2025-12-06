# DRAFT Specification: Edge Cases - Zero and Empty Handling

## Sub-task Reference
**Task**: 1.3 Edge Cases - Zero and Empty Handling
**Parent**: Enhance Audit Records for Email Processing
**Status**: Pending
**Type**: TEST-FOCUSED (Implementation exists, need edge case coverage)

---

## Overview

This specification defines the edge case test scenarios for the `emails_categorized` and `emails_skipped` audit fields. The core implementation is complete (sub-tasks 1.1 and 1.2). This sub-task focuses exclusively on verifying edge case behavior through additional tests.

---

## What Already Exists (DO NOT DUPLICATE)

### From Sub-task 1.1 (Core Fields - 37 tests)
- Field existence on AccountStatus dataclass
- Default value of 0 for both fields
- Field type is int
- to_dict() includes both fields
- start_processing() initializes to 0

### From Sub-task 1.2 (Increment Methods - 20 tests)
- increment_categorized(count) works with default 1
- increment_skipped(count) works with batch values
- Multiple increments accumulate correctly
- No-op when no active session (does not raise)
- Archived run includes both fields after complete_processing()
- New session starts fresh (increments without session don't carry over)

---

## Edge Cases Needing Verification

### Edge Case 1: Zero Counts in Completed Runs
**Scenario**: A processing run completes without any emails being categorized or skipped.

**What to verify**:
- Run completes with `emails_categorized = 0` in archived run
- Run completes with `emails_skipped = 0` in archived run
- Both fields are explicitly 0 (not None or missing)

**Why this matters**: Validates that the absence of increments is correctly reflected as zero in the final archived record.

### Edge Case 2: Empty Batch Processing (increment with 0)
**Scenario**: System calls increment methods with count=0.

**What to verify**:
- `increment_categorized(0)` does not change the count
- `increment_skipped(0)` does not change the count
- No errors are raised
- Subsequent increments still work correctly

**Why this matters**: Handles edge case where batch processing returns empty results.

### Edge Case 3: Complete Processing Immediately After Start
**Scenario**: Session starts and completes without any status updates or increments.

**What to verify**:
- Archived run has `emails_categorized = 0`
- Archived run has `emails_skipped = 0`
- Archived run structure is valid (no missing keys)

**Why this matters**: Validates minimal session lifecycle produces correct audit record.

### Edge Case 4: Multiple Runs with Mixed Zero and Non-Zero Counts
**Scenario**: History contains runs with varying counts, some zero.

**What to verify**:
- Each archived run maintains its own independent counts
- Zero-count runs don't affect non-zero runs
- get_recent_runs() returns correct values for all runs

**Why this matters**: Validates history isolation and data integrity.

### Edge Case 5: AccountStatus Default Initialization
**Scenario**: AccountStatus created directly (not through start_processing).

**What to verify**:
- Direct instantiation defaults to 0 for both fields
- No explicit parameter required to get 0

**Why this matters**: Ensures dataclass defaults are correct.

---

## Interfaces Needed

No new interfaces required. All tests use existing:
- `ProcessingStatusManager` class
- `AccountStatus` dataclass
- Existing methods: `start_processing()`, `complete_processing()`, `increment_categorized()`, `increment_skipped()`, `get_recent_runs()`

---

## Data Models

No new data models required. Tests verify existing fields:
- `AccountStatus.emails_categorized: int = 0`
- `AccountStatus.emails_skipped: int = 0`
- `archived_run['emails_categorized']`
- `archived_run['emails_skipped']`

---

## Test Scenarios

### Test Class: TestZeroCountsInCompletedRuns

```python
class TestZeroCountsInCompletedRuns(unittest.TestCase):
    """
    Edge Case: Completed run with no emails categorized or skipped.
    """

    def test_archived_run_shows_zero_categorized_when_none_processed(self):
        """
        Given a processing session starts
        And no emails are categorized
        When the session completes
        Then the archived run shows emails_categorized = 0
        """
        pass  # ~8 lines

    def test_archived_run_shows_zero_skipped_when_none_processed(self):
        """
        Given a processing session starts
        And no emails are skipped
        When the session completes
        Then the archived run shows emails_skipped = 0
        """
        pass  # ~8 lines

    def test_archived_run_has_both_fields_as_zero_not_none(self):
        """
        Given a processing session starts and completes without increments
        Then emails_categorized is exactly 0 (not None)
        And emails_skipped is exactly 0 (not None)
        """
        pass  # ~10 lines
```

### Test Class: TestEmptyBatchIncrement

```python
class TestEmptyBatchIncrement(unittest.TestCase):
    """
    Edge Case: Increment called with count=0 (empty batch).
    """

    def test_increment_categorized_with_zero_does_not_change_count(self):
        """
        Given an active session with emails_categorized = 5
        When increment_categorized(0) is called
        Then emails_categorized remains 5
        """
        pass  # ~10 lines

    def test_increment_skipped_with_zero_does_not_change_count(self):
        """
        Given an active session with emails_skipped = 3
        When increment_skipped(0) is called
        Then emails_skipped remains 3
        """
        pass  # ~10 lines

    def test_zero_increment_followed_by_nonzero_increment(self):
        """
        Given an active session
        When increment_categorized(0) then increment_categorized(5) are called
        Then emails_categorized = 5
        """
        pass  # ~10 lines
```

### Test Class: TestImmediateCompleteAfterStart

```python
class TestImmediateCompleteAfterStart(unittest.TestCase):
    """
    Edge Case: Session starts and completes with no activity.
    """

    def test_start_then_complete_produces_valid_archived_run(self):
        """
        Given a session starts
        When complete_processing is called immediately
        Then archived run has emails_categorized = 0
        And archived run has emails_skipped = 0
        """
        pass  # ~12 lines

    def test_immediate_complete_archived_run_has_all_required_keys(self):
        """
        Verify archived run structure is complete even for minimal session.
        """
        pass  # ~15 lines
```

### Test Class: TestMixedZeroNonZeroHistory

```python
class TestMixedZeroNonZeroHistory(unittest.TestCase):
    """
    Edge Case: Multiple runs with varying counts in history.
    """

    def test_multiple_runs_maintain_independent_counts(self):
        """
        Given run 1 has emails_categorized=10, emails_skipped=5
        And run 2 has emails_categorized=0, emails_skipped=0
        When get_recent_runs is called
        Then each run shows its own counts
        """
        pass  # ~20 lines

    def test_zero_count_run_does_not_affect_subsequent_runs(self):
        """
        Given run 1 has zero counts
        And run 2 has non-zero counts
        Then run 2 counts are not affected by run 1
        """
        pass  # ~18 lines
```

---

## Logic Flow (Test Execution)

```
For each edge case test:
  1. Arrange: Set up ProcessingStatusManager instance
  2. Act: Execute the edge case scenario
  3. Assert: Verify expected zero/empty handling behavior
  4. Cleanup: Complete any active session in tearDown
```

---

## Context Budget

| Metric | Estimate |
|--------|----------|
| Files to read | 2 (~200 lines) |
| New code to write | ~80 lines (test file only) |
| Test code to write | ~80 lines |
| Estimated context usage | 15% |

**Verdict**: APPROVED - Well within 60% budget.

---

## Acceptance Criteria

1. All edge case tests pass
2. No duplication with sub-task 1.1 or 1.2 tests
3. Zero counts are verified as integer 0 (not None)
4. Empty batch (count=0) increments are handled correctly
5. Archived run structure is complete for minimal sessions
6. Multiple runs in history maintain independent counts

---

## File to Create

**Path**: `tests/test_edge_cases_zero_empty_handling.py`

**Purpose**: Verify edge case behavior for emails_categorized and emails_skipped fields when dealing with zero values and empty batches.

---

## Notes

- This is a TEST-ONLY task - no production code changes expected
- All tests should use existing ProcessingStatusManager API
- Focus on behavior verification, not implementation
- Tests should be independent and not rely on test execution order
