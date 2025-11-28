---
description: Implements a feature using the Strict Spec-Analyst-Test-Implement pipeline.
argument-hint: [feature description]
---

# Spec-Driven Feature Implementation with BDD

You are the ORCHESTRATOR for the BDD-TDD pipeline. Use the Task tool to execute the following pipeline sequentially, responding to hook signals between phases.

## Pipeline Overview

```
Architect → BDD-Agent → (hook) → Gherkin-to-Test → (hook) → Run-Prompt →
  [For each prompt: test-creator → coder → standards → tester]
```

## Execution Steps

### 1. **Architect Phase** (Greenfield Spec Design)
Invoke `architect` agent with:
```
Create a DRAFT spec for: $ARGUMENTS

Output to: specs/DRAFT-[feature-name].md
Include: interfaces, data models, logic flow, constructor signatures
```

Wait for architect to complete.

### 2. **BDD Phase** (Behavior-Driven Scenarios)
Invoke `bdd-agent` with:
```
Based on the feature request: $ARGUMENTS
And the DRAFT spec in: specs/DRAFT-*.md

Generate comprehensive Gherkin scenarios that capture the expected behavior.
Present ALL scenarios to the user for confirmation before proceeding.

Save confirmed scenarios to: ./tests/bdd/*.feature
Create BDD spec summary: specs/BDD-SPEC-[feature-name].md
```

Wait for bdd-agent to complete.

**HOOK SIGNAL**: After bdd-agent completes, you will see a system message:
> "BDD Agent completed. Gherkin-to-test agent will be invoked automatically by the orchestrator."

### 3. **Gherkin-to-Test Phase** (Convert BDD to Prompts)
When you see the bdd-agent completion signal, invoke `gherkin-to-test` with:
```
Convert the confirmed BDD scenarios to prompt files:

1. Read feature files from: ./tests/bdd/*.feature
2. Read BDD spec from: specs/BDD-SPEC-*.md
3. Invoke codebase-analyst to find reuse opportunities
4. Invoke refactor-decision-engine for "GO" signal
5. Create prompt files in: ./prompts/NNN-bdd-*.md
6. Report the prompt numbers for run-prompt

Use executor: bdd in frontmatter for all prompts.
```

Wait for gherkin-to-test to complete.

**HOOK SIGNAL**: After gherkin-to-test completes, you will see a system message:
> "Gherkin-to-test agent completed. Run-prompt will be invoked automatically by the orchestrator with: run-prompt [numbers] --sequential"

### 4. **Run-Prompt Phase** (TDD Implementation)
When you see the gherkin-to-test completion signal, invoke `run-prompt` command with the prompt numbers provided in the signal.

Example: If signal says "run-prompt 006 007 008 --sequential", execute:
```
Execute prompts sequentially: [prompt-numbers] --sequential

For each prompt, the TDD flow will execute:
- test-creator: Write tests from Gherkin scenarios
- coder: Implement code to pass tests
- coding-standards-checker: Verify code quality (via hook)
- tester: Validate functionality (via hook)
```

Wait for all prompts to complete.

### 5. **Completion Report**
After all phases complete, provide a summary:

```
**BDD-TDD Pipeline Complete**

**Feature**: $ARGUMENTS

**Phases Completed**:
1. Architect: specs/DRAFT-*.md created
2. BDD: [N] scenarios confirmed by user
3. Gherkin-to-Test: [M] prompt files created
4. Run-Prompt: All prompts executed

**Artifacts Created**:
- specs/DRAFT-[feature].md
- specs/BDD-SPEC-[feature].md
- specs/GAP-ANALYSIS.md
- ./tests/bdd/*.feature
- ./prompts/NNN-bdd-*.md (archived to completed/)

**Implementation**:
- Tests created: [count]
- Code implemented: [files]
- Standards: Passed
- Tests: Passed

**Feature Ready**: Yes
```

## Signal-Response Pattern

This pipeline uses **signal-based orchestration**:

1. You invoke an agent
2. Agent completes its work
3. SubagentStop hook emits a system message signal
4. You see the signal in the conversation
5. You invoke the next agent based on the signal

**CRITICAL**: Do not proceed to the next phase until you see the hook signal confirming the previous phase completed.

## Error Handling

If any phase fails or encounters issues:
- The agent will invoke the `stuck` agent
- The stuck agent will get human guidance
- Follow the guidance to resolve the issue
- Resume the pipeline from the failed step

## Quality Gates

Quality gates are automatically triggered via hooks:
- After `coder` completes → `coding-standards-checker` signal
- After `coding-standards-checker` completes → `tester` signal

These happen automatically within the run-prompt execution.

## Notes

- **BDD Scenarios are Sequential**: Always use `--sequential` flag for BDD prompts
- **User Confirmation Required**: BDD-agent will not proceed without user approval
- **Retry Limit**: BDD-agent has 5 retry attempts for clarifications
- **Codebase Analysis**: gherkin-to-test invokes codebase-analyst internally
- **Refactoring**: refactor-decision-engine runs before prompt creation
