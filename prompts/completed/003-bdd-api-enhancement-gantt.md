---
executor: bdd
source_feature: ./tests/bdd/api_enhancement_gantt.feature
---

<objective>
Implement the API Enhancement for Gantt Chart Text feature as defined by the BDD scenarios.
The implementation must integrate the GanttChartGenerator (from Sub-task 2) into ProcessingStatusManager
to include `gantt_chart_text` in the archived run dictionary returned by the processing history API.
</objective>

<gherkin>
Feature: API Enhancement for Gantt Chart Text
  As a client application
  I want the processing history API to include gantt_chart_text for each run
  So that I can render Gantt chart visualizations in the dashboard

  Background:
    Given the processing status manager is initialized
    And completed processing runs exist with state transitions

  Scenario: Include gantt_chart_text in processing history response
    Given a completed processing run exists for "user@gmail.com"
    And the run has recorded state transitions
    When the processing history is requested
    Then the response should include a "gantt_chart_text" field for the run
    And the gantt_chart_text should contain valid Mermaid syntax starting with "gantt"
    And the gantt_chart_text should contain a title with "user@gmail.com"

  Scenario: Return gantt chart for each run per account
    Given completed processing runs exist for:
      | email_address   |
      | user1@gmail.com |
      | user2@gmail.com |
      | user1@gmail.com |
    When the processing history is requested
    Then each of the 3 runs should have its own gantt_chart_text
    And the gantt chart for user1 runs should reference "user1@gmail.com"
    And the gantt chart for user2 runs should reference "user2@gmail.com"

  Scenario: Handle empty history with no completed runs
    Given no processing runs have been completed
    When the processing history is requested
    Then the response should contain an empty recent_runs array
    And total_retrieved should be 0

  Scenario: Maintain backward compatibility with existing API consumers
    Given a completed processing run exists with state transitions
    When the processing history is requested
    Then the response should include all existing fields:
      | field            |
      | email_address    |
      | start_time       |
      | end_time         |
      | duration_seconds |
      | final_state      |
      | final_step       |
      | emails_reviewed  |
      | emails_tagged    |
      | emails_deleted   |
      | state_transitions |
    And gantt_chart_text should be an additional field, not replacing any existing field

  Scenario: Generate Gantt chart for run that failed during processing
    Given a processing run for "user@gmail.com" ended with ERROR state
    And the run has recorded state transitions including the error
    When the processing history is requested
    Then the response should include the failed run
    And the gantt_chart_text should contain partial progress up to the error
    And the gantt_chart_text should indicate the error state
</gherkin>

<requirements>
Based on the Gherkin scenarios, implement:

1. **Integrate GanttChartGenerator into ProcessingStatusManager**
   - Import GanttChartGenerator from services.gantt_chart_generator
   - In complete_processing() method, after transitions are finalized:
     - Create GanttChartGenerator instance
     - Call generate() with transitions, email_address, and include_zero_duration=False
   - Add gantt_chart_text field to the archived_run dictionary

2. **Gantt Chart Text Field in Archived Run**
   - Field name: `gantt_chart_text`
   - Type: Optional[str]
   - Value: Mermaid Gantt chart syntax string or None
   - Position: After state_transitions field in the dictionary

3. **Handle Gantt Generation for All Run Types**
   - Successful runs (COMPLETED state): Full Gantt chart with all transitions
   - Failed runs (ERROR state): Partial Gantt chart showing progress up to error
   - Runs with no transitions: gantt_chart_text should be None

4. **API Response Enhancement**
   - GET /api/processing/history automatically includes gantt_chart_text (no endpoint changes needed)
   - GET /api/status with include_recent=true includes gantt_chart_text
   - Each run in recent_runs array has its own gantt_chart_text

Edge Cases to Handle:
- Empty transitions list: Set gantt_chart_text to None
- ERROR state runs: Generate partial chart up to error point
- Multiple runs: Each run gets its own independent gantt_chart_text
- Legacy runs without state_transitions: gantt_chart_text should be None

</requirements>

<context>
BDD Specification: specs/BDD-SPEC-api-enhancement-gantt.md
Gap Analysis: specs/GAP-ANALYSIS-api-enhancement-gantt.md
DRAFT Specification: specs/DRAFT-api-enhancement-gantt.md

Dependencies from Previous Sub-tasks:

**Sub-task 1 (State Transition Tracking):**
- StateTransition dataclass: `/root/repo/services/state_transition.py`
- StateTransitionTracker: Integrated in ProcessingStatusManager
- state_transitions field: Already in archived_run dictionary

**Sub-task 2 (Gantt Chart Generator Core):**
- GanttChartGenerator: `/root/repo/services/gantt_chart_generator.py`
- Methods: generate(transitions, title, include_zero_duration), validate_syntax(gantt_text)
- Interface: `/root/repo/services/interfaces/gantt_chart_generator_interface.py`

Reuse Opportunities (from gap analysis):
- ProcessingStatusManager.complete_processing() is the integration point (lines 191-245)
- GanttChartGenerator already handles all Gantt generation logic
- StateTransitionTracker.finalize() returns List[StateTransition] ready for Gantt generation
- No changes needed to API endpoints - they already return archived_run data

Files to Modify:
- `/root/repo/services/processing_status_manager.py` (add import, modify complete_processing)

Files Unchanged:
- `/root/repo/api_service.py` - No changes needed, returns get_recent_runs() output
- `/root/repo/services/gantt_chart_generator.py` - Use as-is
- `/root/repo/services/state_transition.py` - Use as-is

</context>

<implementation>
Follow TDD approach:
1. Tests will be created from Gherkin scenarios
2. Implement code to make tests pass
3. Ensure all scenarios are green

Implementation Steps:

1. **Add Import to ProcessingStatusManager**
   ```python
   from services.gantt_chart_generator import GanttChartGenerator
   ```

2. **Modify complete_processing() Method**
   After line where transitions are finalized:
   ```python
   # Finalize transitions with duration calculations
   transitions = self._transition_tracker.finalize()

   # Generate Gantt chart text if we have transitions
   gantt_chart_text = None
   if transitions:
       generator = GanttChartGenerator()
       gantt_chart_text = generator.generate(
           transitions=transitions,
           title=self._current_status.email_address,
           include_zero_duration=False
       )
   ```

3. **Add Field to archived_run Dictionary**
   ```python
   archived_run = {
       # ... existing fields ...
       'state_transitions': [t.to_dict() for t in transitions],
       'gantt_chart_text': gantt_chart_text  # NEW FIELD
   }
   ```

Architecture Guidelines:
- Follow strict-architecture rules (500 lines max, interfaces, no env vars in functions)
- Use existing patterns from codebase (see state_transitions integration pattern)
- Maintain consistency with project structure
- GanttChartGenerator is instantiated fresh each time (stateless)
</implementation>

<verification>
All Gherkin scenarios must pass:
- [ ] Scenario: Include gantt_chart_text in processing history response
- [ ] Scenario: Return gantt chart for each run per account
- [ ] Scenario: Handle empty history with no completed runs
- [ ] Scenario: Maintain backward compatibility with existing API consumers
- [ ] Scenario: Generate Gantt chart for run that failed during processing
</verification>

<success_criteria>
- All Gherkin scenarios pass
- Code follows project coding standards
- Tests provide complete coverage of scenarios
- Implementation matches user's confirmed intent
- Backward compatibility maintained (all existing API fields unchanged)
- gantt_chart_text field contains valid Mermaid syntax for completed runs
- gantt_chart_text is None for runs without state_transitions
- Each run has its own independent gantt_chart_text
- Error state runs include partial Gantt charts
</success_criteria>
