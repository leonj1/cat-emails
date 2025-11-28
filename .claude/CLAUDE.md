# Project Configuration

This project uses Claude Code with specialized agents and hooks for orchestrated development workflows.

## Available Commands

### `/architect` - BDD-TDD Development Workflow
Use this command to create implementation prompts following BDD and TDD best practices:
- Creates greenfield specification for the feature
- Generates Gherkin BDD scenarios
- Converts scenarios to TDD prompts
- Tests are written from Gherkin scenarios (Red phase)
- Implementation follows to make tests pass (Green phase)
- Full quality gates: standards checks and testing

**When to use**: For new features where you want comprehensive BDD test coverage.

**Example**: `/architect Build a user authentication system with JWT`

**Flow**: architect → bdd-agent → gherkin-to-test → codebase-analyst → refactor-decision → test-creator → coder → standards → tester → bdd-test-runner

### `/coder` - Orchestrated Development
Use this command when you want to implement features with full orchestration:
- Automatically breaks down tasks into to-do items
- Delegates implementation to specialized coder agents
- Enforces coding standards through automated checks
- Runs tests automatically after implementation
- Provides comprehensive quality gates

**When to use**: For implementing new features, building projects, or complex multi-step coding tasks where you want direct manual orchestration.

**Example**: `/coder Build a REST API with user authentication`

### `/run-prompt` - Execute Saved Prompts
Use this command to execute one or more prompts from `./prompts/` directory:
- Automatically detects task type (TDD, direct code, or research)
- Routes to appropriate workflow based on task type
- Supports parallel execution with `--parallel` flag
- Supports sequential execution with `--sequential` flag
- Can specify executor via frontmatter in prompt files

**When to use**: To execute prompts created by `/architect` or manually created prompts.

**Examples**:
- `/run-prompt 005` (execute prompt 005)
- `/run-prompt 005 006 007 --parallel` (execute three prompts in parallel)
- `/run-prompt 005 006 --sequential` (execute two prompts sequentially)

### `/refactor` - Code Refactoring
Use this command to refactor existing code to adhere to coding standards.

**When to use**: When you need to improve code quality without changing functionality.

**Example**: `/refactor src/components/UserForm.js`

### `/verifier` - Code Verification and Investigation
Use this command to investigate source code and verify claims, answer questions, or determine if queries are true/false.

**When to use**: When you need to verify a claim about the codebase, answer questions about code structure or functionality, or investigate specific code patterns.

**Example**: `/verifier Does the codebase have email validation?`

### `/fix-failing-tests` - Fix Failing Tests
Use this command to run the project's test suite and automatically fix any failures.

**When to use**: When tests are failing and you want to automatically attempt to fix them.

**Example**: `/fix-failing-tests`

## Project Structure

- `.claude/agents/` - Specialized agent configurations
  - `architect.md` - Greenfield spec designer
  - `bdd-agent.md` - BDD specialist that generates Gherkin scenarios
  - `gherkin-to-test.md` - Converts Gherkin to TDD prompts
  - `codebase-analyst.md` - Finds reuse opportunities
  - `refactor-decision-engine.md` - Decides if refactoring needed
  - `test-creator.md` - TDD specialist that writes tests first
  - `coder.md` - Implementation specialist
  - `coding-standards-checker.md` - Code quality verifier
  - `tester.md` - Functionality verification
  - `bdd-test-runner.md` - Test infrastructure validator (Dockerfile.test, Makefile)
  - `refactorer.md` - Code refactoring specialist
  - `fix-failing-tests.md` - Fix failing tests specialist
  - `verifier.md` - Code investigation specialist
  - `stuck.md` - Human escalation agent
- `.claude/coding-standards/` - Code quality standards
- `.claude/commands/` - Custom slash commands
- `.claude/hooks/` - Automated workflow hooks
- `.claude/config.json` - Project configuration
- `tests/bdd/` - Gherkin feature files for BDD scenarios

## Hooks System

This project uses Claude Code hooks to automatically enforce quality gates:

### Configured Hooks

1. **post-bdd-agent.sh** - Signals gherkin-to-test after BDD scenarios generated
2. **post-gherkin-to-test.sh** - Signals run-prompt after prompts created
3. **post-coder-standards-check.sh** - Triggers coding standards check after coder completes
4. **post-standards-testing.sh** - Triggers testing after standards check passes
5. **post-tester-infrastructure.sh** - Triggers bdd-test-runner to validate test infrastructure

Hooks create state files in `.claude/.state/` to track workflow completion.

## Documentation Guidelines

- Place markdown documentation in `./docs/`
- Keep `README.md` in the root directory
- Ensure all header/footer links have actual pages (no 404s)

## Workflow Comparison

### BDD-TDD Workflow (`/architect`)
**Best for**: New features with comprehensive test coverage, behavior-driven development

**Flow**:
1. `/architect` creates greenfield spec
2. `bdd-agent` generates Gherkin scenarios
3. `gherkin-to-test` invokes codebase-analyst and creates prompts
5. `run-prompt` executes prompts sequentially
6. For each prompt:
   - `test-creator` writes tests from Gherkin
   - `coder` implements to pass tests
   - `coding-standards-checker` verifies quality
   - `tester` validates functionality
   - `bdd-test-runner` validates test infrastructure (Dockerfile.test, Makefile, `make test`)

**Benefits**:
- Tests derived from business-readable Gherkin scenarios
- Clear traceability from requirements to tests to code
- Full quality gates
- Living documentation via `.feature` files

### Direct Implementation (`/coder`)
**Best for**: Quick fixes, manual orchestration, iterative development

**Flow**:
1. Orchestrator breaks down task into todos
2. `coder` agent implements each todo
3. `coding-standards-checker` verifies code quality
4. `tester` validates functionality
5. Repeat for each todo item

**Benefits**:
- Manual control over task breakdown
- Direct implementation without test-first approach
- Iterative todo-based workflow

### Prompt Execution (`/run-prompt`)
**Best for**: Executing pre-created prompts, batch operations

**Flow**:
- Detects task type (TDD, BDD, direct code, or research)
- Routes to appropriate workflow
- Can execute multiple prompts in parallel or sequential
- Supports executor override via frontmatter (`tdd`, `bdd`, `coder`, `general-purpose`)

**Benefits**:
- Flexible execution strategies
- Batch processing
- Intelligent routing
- BDD prompts always run sequentially

## General Usage

For exploratory tasks, questions, or non-coding requests, you can interact with Claude Code normally without using specialized commands. Use:
- `/architect` for new features with TDD approach
- `/coder` for direct orchestrated implementation
- `/run-prompt` for executing saved prompts
- `/refactor` for code quality improvements
- `/fix-failing-tests` for fixing failing tests automatically
- `/verifier` for code investigation
