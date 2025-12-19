#!/usr/bin/env python3
"""
TodoWrite Task Completion Check Hook

This hook runs after an agent completes and checks if there are incomplete
tasks in the TodoWrite state. If incomplete tasks remain, it fails with
a clear message instructing the agent to continue working on the tasks.

This hook is triggered on SubagentStop events and reads JSON from stdin
in the Claude Code hook format.

Input format:
{
    "session_id": "...",
    "cwd": "...",
    "subagent_name": "...",
    "todos": [
        {"content": "...", "status": "pending|in_progress|completed", "activeForm": "..."},
        ...
    ]
}
"""
import sys
import json


def get_incomplete_todos(todos: list) -> tuple[list, list]:
    """
    Separate todos into pending and in_progress lists.

    Args:
        todos: List of todo items with status field

    Returns:
        Tuple of (pending_todos, in_progress_todos)
    """
    pending = []
    in_progress = []

    for todo in todos:
        status = todo.get("status", "")
        if status == "pending":
            pending.append(todo)
        elif status == "in_progress":
            in_progress.append(todo)

    return pending, in_progress


def format_todo_list(todos: list, label: str) -> str:
    """Format a list of todos for display."""
    if not todos:
        return ""

    lines = [f"\n{label}:"]
    for i, todo in enumerate(todos, 1):
        content = todo.get("content", "Unknown task")
        lines.append(f"  {i}. {content}")

    return "\n".join(lines)


def main():
    try:
        input_data = sys.stdin.read()
        if not input_data or not input_data.strip():
            # No input, nothing to check
            sys.exit(0)

        data = json.loads(input_data)
    except json.JSONDecodeError:
        # Invalid JSON, skip check
        sys.exit(0)
    except Exception:
        sys.exit(0)

    # Extract todos from input
    todos = data.get("todos", [])

    # If no todos in the session, nothing to check
    if not todos:
        sys.exit(0)

    # Get incomplete todos
    pending, in_progress = get_incomplete_todos(todos)

    # If all tasks are completed, allow the agent to stop
    if not pending and not in_progress:
        print(json.dumps({
            "continue": True,
            "systemMessage": "✅ All TodoWrite tasks completed."
        }))
        sys.exit(0)

    # Build error message with incomplete tasks
    incomplete_count = len(pending) + len(in_progress)

    error_parts = [
        f"❌ INCOMPLETE TASKS DETECTED: {incomplete_count} task(s) remain unfinished.",
        "",
        "You MUST continue iterating over the TodoWrite tasks until ALL are completed.",
        "Do NOT stop until every task shows status='completed'.",
    ]

    # Add in_progress tasks (highest priority)
    if in_progress:
        error_parts.append(format_todo_list(in_progress, "🔄 IN PROGRESS (finish these first)"))

    # Add pending tasks
    if pending:
        error_parts.append(format_todo_list(pending, "⏳ PENDING (work on these next)"))

    error_parts.extend([
        "",
        "ACTION REQUIRED:",
        "1. Mark the current in_progress task as 'completed' when done",
        "2. Set the next pending task to 'in_progress'",
        "3. Complete the work for that task",
        "4. Repeat until ALL tasks are 'completed'",
    ])

    error_message = "\n".join(error_parts)

    # Output error and exit with failure
    print(json.dumps({
        "error": error_message
    }))
    sys.exit(1)


if __name__ == "__main__":
    main()
