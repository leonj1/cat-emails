# BDD Specification: Enhance Audit Records with Categorized and Skipped Email Counts

## Overview

This feature enhances the audit record system to track two new metrics during email processing:
- **emails_categorized**: Count of emails successfully categorized during a processing session
- **emails_skipped**: Count of emails skipped during a processing session

These metrics provide visibility into processing effectiveness and help identify potential issues with email categorization.

## User Stories

- As a system administrator, I want audit records to track how many emails were categorized so that I can monitor processing effectiveness
- As a system administrator, I want audit records to track how many emails were skipped so that I can identify potential issues
- As a developer, I want reliable increment methods so that counts are accurate even under concurrent processing

## Feature Files

| Feature File | Scenarios | Coverage |
|--------------|-----------|----------|
| enhance_audit_records.feature | 23 | Database model, increment methods, processing flow, API response, edge cases, migration, thread safety, data integrity |

## Scenarios Summary

### enhance_audit_records.feature

**Database Model (2 scenarios)**
1. Audit record contains emails_categorized field
2. Audit record contains emails_skipped field

**Increment Methods (3 scenarios)**
3. Categorized count increments when email is successfully categorized
4. Skipped count increments when email is skipped
5. Multiple emails increment counts correctly

**Complete Processing Flow (2 scenarios)**
6. Audit record reflects complete processing batch
7. Audit record persists after session completion

**API Response (2 scenarios)**
8. Audit summary endpoint returns categorized count
9. Audit summary endpoint returns skipped count

**Zero Counts Edge Cases (4 scenarios)**
10. Audit record handles zero categorized emails
11. Audit record handles zero skipped emails
12. Audit record handles empty batch
13. New audit record initializes counts to zero

**No Active Session Edge Cases (2 scenarios)**
14. System handles increment without active session gracefully
15. System logs warning when incrementing without session

**Large Counts Edge Cases (2 scenarios)**
16. Audit record handles large categorized counts
17. Audit record handles large skipped counts

**Database Migration (2 scenarios)**
18. Existing audit records receive default values after migration
19. New audit records work correctly after migration

**Thread Safety (2 scenarios)**
20. Concurrent categorization increments are handled correctly
21. Concurrent skip increments are handled correctly

**Data Integrity (2 scenarios)**
22. Categorized and skipped counts sum correctly
23. Audit record maintains count accuracy across restarts

## Acceptance Criteria

### Functional Requirements
- [ ] Audit records must contain `emails_categorized` field (non-negative integer)
- [ ] Audit records must contain `emails_skipped` field (non-negative integer)
- [ ] Increment methods must correctly update counts
- [ ] API endpoints must return both counts in audit summaries
- [ ] Counts must persist after session completion

### Edge Case Handling
- [ ] Zero counts must be handled correctly
- [ ] Empty batches must result in zero counts
- [ ] New sessions must initialize counts to zero
- [ ] Missing active session must be handled gracefully (no errors, warning logged)
- [ ] Large counts (100,000+) must be stored accurately

### Migration Requirements
- [ ] Existing audit records must receive default values of 0
- [ ] New records must work correctly after migration

### Non-Functional Requirements
- [ ] Thread-safe increment operations for concurrent processing
- [ ] Data integrity: categorized + skipped should equal total processed
- [ ] Counts must survive system restarts

## Technical Notes

- Fields should be non-negative integers with default value of 0
- Consider using atomic operations for thread-safe increments
- Database migration must handle existing records gracefully
- Logging should warn when increment attempted without active session

## Ready For

This specification is ready for the `gherkin-to-test` agent to convert scenarios into TDD prompts.
