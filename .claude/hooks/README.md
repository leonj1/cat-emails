# Claude Code Hooks

This directory contains hook scripts that automatically enforce quality gates during development.

## Hook Scripts

### 1. `post-coder-standards-check.sh`

**Trigger**: SubagentStop event when the `coder` agent completes

**Purpose**: Signals the orchestrator that the coding-standards-checker should be invoked

**Actions**:
- Validates the triggering agent is "coder"
- Creates state file: `.claude/.state/coder-completed-{session_id}`
- Outputs system message for the orchestrator

### 2. `post-todowrite-task-check.py`

**Trigger**: SubagentStop event when the `coder` agent completes

**Purpose**: Ensures all TodoWrite tasks are completed before allowing the agent to stop

**Actions**:
- Reads the todos from the hook input
- Checks if any tasks have status "pending" or "in_progress"
- If incomplete tasks exist, FAILS with a clear error message listing them
- If all tasks are "completed", allows the agent to stop

**Behavior**:
- Runs BEFORE `post-coder-standards-check.sh` to enforce task completion
- Provides actionable guidance when tasks remain
- Prevents premature agent termination

### 3. `post-standards-testing.sh`

**Trigger**: SubagentStop event when the `coding-standards-checker` agent completes

**Purpose**: Signals the orchestrator that the tester should be invoked

**Actions**:
- Validates the triggering agent is "coding-standards-checker"
- Creates state file: `.claude/.state/standards-checked-{session_id}`
- Outputs system message for the orchestrator

## Hook Configuration

Hooks are configured in `.claude/config.json`:

```json
{
  "hooks": {
    "SubagentStop": [...]
  }
}
```

## Testing Hooks

Test hooks manually:

```bash
# Test post-coder hook
echo '{"session_id":"test","cwd":"/root/repo","subagent_name":"coder"}' | \
  .claude/hooks/post-coder-standards-check.sh

# Test post-standards hook
echo '{"session_id":"test","cwd":"/root/repo","subagent_name":"coding-standards-checker"}' | \
  .claude/hooks/post-standards-testing.sh

# Test todowrite task check - should FAIL (incomplete tasks)
echo '{"session_id":"test","cwd":"/root/repo","subagent_name":"coder","todos":[{"content":"Task 1","status":"completed","activeForm":"Task 1"},{"content":"Task 2","status":"pending","activeForm":"Task 2"}]}' | \
  python3 .claude/hooks/post-todowrite-task-check.py

# Test todowrite task check - should PASS (all completed)
echo '{"session_id":"test","cwd":"/root/repo","subagent_name":"coder","todos":[{"content":"Task 1","status":"completed","activeForm":"Task 1"},{"content":"Task 2","status":"completed","activeForm":"Task 2"}]}' | \
  python3 .claude/hooks/post-todowrite-task-check.py
```

## State Files

Hooks create state files in `.claude/.state/` for audit tracking:

- `coder-completed-{session_id}` - Timestamp when coder completed
- `standards-checked-{session_id}` - Timestamp when standards were verified

## Requirements

- `bash` - Shell interpreter
- `jq` - JSON parsing utility

## Documentation

See `/docs/HOOKS.md` for comprehensive documentation.
