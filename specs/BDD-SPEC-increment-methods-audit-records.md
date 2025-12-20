# BDD Specification: Increment Methods for Audit Records

## Overview

This specification covers the increment methods for tracking categorized and skipped email counts within the processing audit system. These methods allow the email processing system to accumulate statistics throughout a processing session.

## User Stories

- As an email processing system, I want to increment audit counters for categorized and skipped emails so that processing statistics are accurately tracked throughout each session.

## Feature Files

| Feature File | Scenarios | Coverage |
|--------------|-----------|----------|
| increment_methods_audit_records.feature | 4 | Happy path, batch operations, error handling, cumulative behavior |

## Scenarios Summary

### increment_methods_audit_records.feature

1. **Increment categorized count with default value** - Verifies that recording a single categorized email increments the count by one
2. **Increment skipped count with batch value** - Verifies that batch increments correctly increase the skipped count by the specified amount
3. **Increment is silent when no session is active** - Verifies graceful handling when no active session exists (no error, no count recorded)
4. **Increments are cumulative within a session** - Verifies that multiple increment operations accumulate correctly within a single session

## Acceptance Criteria

### Happy Path
- [x] Increment categorized count by 1 (default)
- [x] Increment skipped count by specified batch value
- [x] Cumulative increments within a session

### Error Handling
- [x] Silent failure when no session is active (no exception thrown)
- [x] No count recorded when no session exists

### Business Rules
- Increments must be additive within a session
- Default increment value is 1
- Batch increments accept any positive integer
- No active session results in silent no-op behavior

## Technical Notes

These increment methods work with the existing `ProcessingRun` and `AccountStatus` audit structures that were created in previous tasks. The methods should:

1. Check for an active session before attempting to increment
2. Use atomic increment operations where applicable
3. Support both single-item and batch increment patterns
4. Fail silently (log warning) when no session is active

## Related Specifications

- `BDD-SPEC-core-fields-audit-records.md` - Core audit field definitions
- `BDD-SPEC-enhance-audit-records.md` - Parent specification for audit enhancements
