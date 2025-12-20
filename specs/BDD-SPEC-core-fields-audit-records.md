# BDD Specification: Core Audit Fields for Categorized and Skipped Emails

## Overview

This specification defines the core fields required to track emails categorized and emails skipped during processing runs. These fields enable account administrators to monitor email processing effectiveness and identify potential issues.

## User Stories

- As an account administrator, I want processing audit records to track emails categorized and skipped so that I can monitor email processing effectiveness and identify issues

## Feature Files

| Feature File | Scenarios | Coverage |
|--------------|-----------|----------|
| core_fields_audit_records.feature | 4 | Model fields, dataclass fields |

## Scenarios Summary

### core_fields_audit_records.feature

1. **ProcessingRun model includes emails_categorized column**
   - Validates that the ProcessingRun database model has an emails_categorized column
   - Ensures the count accurately reflects categorized emails

2. **ProcessingRun model includes emails_skipped column**
   - Validates that the ProcessingRun database model has an emails_skipped column
   - Ensures the count accurately reflects skipped emails

3. **AccountStatus dataclass includes emails_categorized field**
   - Validates that the AccountStatus dataclass exposes emails_categorized
   - Ensures cumulative counts are available for reporting

4. **AccountStatus dataclass includes emails_skipped field**
   - Validates that the AccountStatus dataclass exposes emails_skipped
   - Ensures cumulative counts are available for reporting

## Acceptance Criteria

### ProcessingRun Model
- [ ] emails_categorized column exists in ProcessingRun model
- [ ] emails_skipped column exists in ProcessingRun model
- [ ] Both columns store integer counts
- [ ] Counts are persisted with each processing run record

### AccountStatus Dataclass
- [ ] emails_categorized field is accessible on AccountStatus
- [ ] emails_skipped field is accessible on AccountStatus
- [ ] Fields contain cumulative counts from processing runs
- [ ] Fields are included in status retrieval operations

## Technical Notes

- ProcessingRun is a database model representing individual processing executions
- AccountStatus is a dataclass used for reporting account processing statistics
- Both components must be updated to include the new audit fields

## Ready For

This specification is ready for the `gherkin-to-test` agent to convert scenarios into TDD prompts.
