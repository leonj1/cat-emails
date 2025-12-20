---
executor: bdd
source_feature: ./tests/bdd/remove_logs_collector_phase1.feature
---

<objective>
Implement the Remove Logs Collector Phase 1 feature as defined by the BDD scenarios below.
Delete the 5 core logs collector service files to begin the removal of centralized logging infrastructure.
</objective>

<gherkin>
Feature: Remove Logs Collector Phase 1 - Delete Core Service Files
  As a maintainer
  I want to remove the centralized logs collector infrastructure
  So that the codebase is simplified and unnecessary dependencies are eliminated

  Background:
    Given the codebase is under version control

  Scenario: Logs collector service file is deleted
    When the logs collector removal phase 1 is complete
    Then the file "services/logs_collector_service.py" should not exist

  Scenario: Logs collector interface file is deleted
    When the logs collector removal phase 1 is complete
    Then the file "services/logs_collector_interface.py" should not exist

  Scenario: Logs collector client file is deleted
    When the logs collector removal phase 1 is complete
    Then the file "clients/logs_collector_client.py" should not exist

  Scenario: Central logging service files are deleted
    When the logs collector removal phase 1 is complete
    Then the file "services/logging_service.py" should not exist
    And the file "services/logging_factory.py" should not exist
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. Delete `services/logs_collector_service.py` - Main LogsCollectorService class
2. Delete `services/logs_collector_interface.py` - ILogsCollector interface
3. Delete `clients/logs_collector_client.py` - RemoteLogsCollectorClient and FakeLogsCollectorClient
4. Delete `services/logging_service.py` - CentralLoggingService
5. Delete `services/logging_factory.py` - Factory for RemoteLogsCollectorClient

Important Notes:
- This is Phase 1 of a 4-phase removal process
- Import errors in other files are EXPECTED after deletion (Phase 2 will fix those)
- Test failures are EXPECTED after deletion (Phase 4 will fix those)
- Do NOT modify any other files in this phase
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-remove-logs-collector-phase1.md
Gap Analysis: specs/GAP-ANALYSIS.md
Draft Spec: specs/DRAFT-remove-logs-collector-phase1.md

Reuse Opportunities (from gap analysis):
- None - this is a deletion-only task

New Components Needed:
- None - this phase only removes code
</context>

<implementation>
Implementation Steps:

1. Delete the following files using rm or equivalent:
   - /root/repo/services/logs_collector_service.py
   - /root/repo/services/logs_collector_interface.py
   - /root/repo/clients/logs_collector_client.py
   - /root/repo/services/logging_service.py
   - /root/repo/services/logging_factory.py

2. Verify each file no longer exists

3. Do NOT attempt to fix import errors in other files - that is Phase 2

Deletion Commands:
```bash
rm -f /root/repo/services/logs_collector_service.py
rm -f /root/repo/services/logs_collector_interface.py
rm -f /root/repo/clients/logs_collector_client.py
rm -f /root/repo/services/logging_service.py
rm -f /root/repo/services/logging_factory.py
```

Verification Commands:
```bash
test ! -f /root/repo/services/logs_collector_service.py && echo "DELETED: logs_collector_service.py"
test ! -f /root/repo/services/logs_collector_interface.py && echo "DELETED: logs_collector_interface.py"
test ! -f /root/repo/clients/logs_collector_client.py && echo "DELETED: logs_collector_client.py"
test ! -f /root/repo/services/logging_service.py && echo "DELETED: logging_service.py"
test ! -f /root/repo/services/logging_factory.py && echo "DELETED: logging_factory.py"
```
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Logs collector service file is deleted
- [ ] Scenario: Logs collector interface file is deleted
- [ ] Scenario: Logs collector client file is deleted
- [ ] Scenario: Central logging service files are deleted

Verification Steps:
1. Confirm services/logs_collector_service.py does not exist
2. Confirm services/logs_collector_interface.py does not exist
3. Confirm clients/logs_collector_client.py does not exist
4. Confirm services/logging_service.py does not exist
5. Confirm services/logging_factory.py does not exist
</verification>

<success_criteria>
- All 5 files are deleted from the repository
- Files are completely removed (not just emptied)
- Verification commands confirm deletion
- No other files have been modified

Expected Side Effects (acceptable):
- Import errors in services/api_service.py (Phase 2 will fix)
- Import errors in services/gmail_fetcher.py (Phase 2 will fix)
- Test failures for logs collector tests (Phase 4 will fix)
</success_criteria>
