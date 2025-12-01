---
executor: bdd
source_feature: ./tests/bdd/remove_logs_collector_phase2.feature
---

<objective>
Remove all LogsCollectorService references from api_service.py and gmail_fetcher.py so that the application can start without import errors after Phase 1 deleted the core logs collector service files.
</objective>

<gherkin>
Feature: Remove Logs Collector Phase 2 - Update Integration Points
  As a maintainer
  I want to remove LogsCollectorService references from integration points
  So that the application can start without import errors after core files are deleted

  Background:
    Given Phase 1 has deleted the core logs collector files

  Scenario: api_service.py has no LogsCollectorService references
    When the logs collector removal phase 2 is complete
    Then the file "api_service.py" should not contain "LogsCollectorService"
    And the file "api_service.py" should not contain "logs_collector_service"
    And the file "api_service.py" should not contain "SEND_LOGS_ENABLED"

  Scenario: gmail_fetcher.py has no LogsCollectorService references
    When the logs collector removal phase 2 is complete
    Then the file "gmail_fetcher.py" should not contain "LogsCollectorService"
    And the file "gmail_fetcher.py" should not contain "logs_collector"
    And the file "gmail_fetcher.py" should not contain "send_log"

  Scenario: api_service.py can be imported without errors
    When the logs collector removal phase 2 is complete
    Then importing "api_service" in Python should succeed

  Scenario: gmail_fetcher.py can be imported without errors
    When the logs collector removal phase 2 is complete
    Then importing "gmail_fetcher" in Python should succeed
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement the following:

1. Remove LogsCollectorService import from api_service.py (line 32)
2. Remove SEND_LOGS_ENABLED feature flag from api_service.py (lines ~185-186)
3. Remove logs_collector_service global instance from api_service.py (lines ~291-292)
4. Remove logs_collector parameter from AccountEmailProcessorService constructor in api_service.py (line ~367)
5. Remove LogsCollectorService import from gmail_fetcher.py (line 27)
6. Remove logs collector initialization block from gmail_fetcher.py (lines ~612-623)
7. Remove send_log call in API failure handler from gmail_fetcher.py (lines ~632-638)
8. Remove send_log call in success handler from gmail_fetcher.py (lines ~746-755)
9. Remove send_log call in error handler from gmail_fetcher.py (lines ~761-766)

Preservation Requirements (DO NOT REMOVE):
- All logger.info(), logger.error(), logger.warning(), logger.debug() calls
- initialize_central_logging() call in api_service.py
- shutdown_logging() call in api_service.py
- logger = get_logger(__name__) in gmail_fetcher.py
</requirements>

<context>
BDD Specification: specs/BDD-SPEC-remove-logs-collector-phase2.md
Gap Analysis: specs/GAP-ANALYSIS.md (Phase 1 analysis - deletion complete)

Phase Context:
- Phase 1 (COMPLETE): Deleted core service files
  - services/logs_collector_service.py
  - services/logs_collector_interface.py
  - clients/logs_collector_client.py
  - services/logging_service.py
  - services/logging_factory.py
- Phase 2 (THIS PHASE): Remove references from integration points
- Phase 3 (NEXT): Remove test files
- Phase 4 (FINAL): Cleanup configuration

Reuse Opportunities:
- None - this is purely removal of dead code

New Components Needed:
- None - this phase only removes code
</context>

<implementation>
Follow this implementation approach:

1. Read api_service.py and identify all LogsCollectorService references
2. Read gmail_fetcher.py and identify all logs_collector references
3. Remove identified lines while preserving local logging calls
4. Verify imports succeed with Python import test

File: api_service.py
- Remove: from services.logs_collector_service import LogsCollectorService
- Remove: SEND_LOGS_ENABLED = os.getenv("SEND_LOGS", "false")...
- Remove: logs_collector_service = LogsCollectorService(send_logs=SEND_LOGS_ENABLED)
- Remove: logs_collector=logs_collector_service parameter

File: gmail_fetcher.py
- Remove: from services.logs_collector_service import LogsCollectorService
- Remove: send_logs_raw = os.environ.get("SEND_LOGS"...) block
- Remove: logs_collector = LogsCollectorService(...) initialization
- Remove: All logs_collector.send_log(...) calls (4 locations)

Architecture Guidelines:
- This is a removal-only task - no new code should be added
- Preserve all existing local logging functionality
- Maintain code structure and formatting
</implementation>

<verification>
All Gherkin scenarios must pass:

- [ ] Scenario: api_service.py has no LogsCollectorService references
- [ ] Scenario: gmail_fetcher.py has no LogsCollectorService references
- [ ] Scenario: api_service.py can be imported without errors
- [ ] Scenario: gmail_fetcher.py can be imported without errors

Manual Verification Commands:
```bash
# No references should be found
grep -c "LogsCollectorService" api_service.py gmail_fetcher.py
grep -c "logs_collector" api_service.py gmail_fetcher.py
grep -c "send_log" api_service.py gmail_fetcher.py
grep -c "SEND_LOGS_ENABLED" api_service.py

# These should succeed without errors
python -c "import api_service"
python -c "import gmail_fetcher"
```
</verification>

<success_criteria>
- All Gherkin scenarios pass
- No LogsCollectorService references remain in api_service.py
- No logs_collector references remain in gmail_fetcher.py
- No send_log calls remain in gmail_fetcher.py
- No SEND_LOGS_ENABLED references remain in api_service.py
- Both files import successfully in Python
- All existing logger.* calls are preserved
- initialize_central_logging() and shutdown_logging() are preserved
</success_criteria>
