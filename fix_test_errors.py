#!/usr/bin/env python3
"""
Test Error Fixer using Claude Code Agent SDK

This script reads a file containing Python test errors (separated by "====...====")
and uses a Claude Code agent to fix each error by:
1. Analyzing the error
2. Fixing the test file
3. Running the test to validate the fix
4. Retrying if the test still fails
"""

import sys
import argparse
import asyncio
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

# Lazy imports to avoid dependency issues when only using parser classes
# from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AgentDefinition
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.table import Table
    from rich import print as rprint
except ImportError:
    # Fallback if rich is not installed
    Console = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Error separator pattern
ERROR_SEPARATOR = "=" * 80

@dataclass
class TestError:
    """Represents a single test error"""
    error_text: str
    test_file: Optional[str] = None
    test_method: Optional[str] = None
    error_type: Optional[str] = None
    line_number: Optional[int] = None

    def __post_init__(self):
        """Extract test metadata from error text"""
        self._parse_error()

    def _parse_error(self):
        """Parse error text to extract metadata"""
        # Split into lines for more robust parsing
        lines = self.error_text.split('\n')

        # Look for test file and method in the traceback
        # Try multiple patterns to find test context
        for i, line in enumerate(lines):
            # Pattern 1: File in tests directory
            if 'File "' in line and '/tests/' in line:
                file_match = re.search(r'File "([^"]+)"', line)
                if file_match:
                    self.test_file = file_match.group(1).replace('/app/', '')

                # Get line number from same line
                line_match = re.search(r'line (\d+)', line)
                if line_match:
                    self.line_number = int(line_match.group(1))

                # Check next line for method name (pattern: "in test_something")
                if i + 1 < len(lines):
                    method_match = re.search(r'in (test_\w+)', lines[i + 1])
                    if method_match:
                        self.test_method = method_match.group(1)

        # Fallback: search entire text for test method if not found yet
        if not self.test_method:
            method_match = re.search(r'in (test_\w+)', self.error_text)
            if method_match:
                self.test_method = method_match.group(1)

        # Fallback: search for any test file if not found yet
        if not self.test_file:
            file_match = re.search(r'File "([^"]+/tests/[^"]+\.py)"', self.error_text)
            if file_match:
                self.test_file = file_match.group(1).replace('/app/', '')

        # Extract error type (last occurrence is usually the actual error)
        error_types = ['AssertionError', 'AttributeError', 'TypeError', 'Exception',
                      'ValueError', 'KeyError', 'IndexError', 'NameError',
                      'ImportError', 'ModuleNotFoundError', 'RuntimeError']
        for err_type in reversed(error_types):  # Check from most specific to generic
            if err_type in self.error_text:
                self.error_type = err_type
                break

    def get_test_identifier(self) -> str:
        """Get unique identifier for this test"""
        if self.test_file and self.test_method:
            return f"{self.test_file}::{self.test_method}"
        return "Unknown test"

    def get_pytest_command(self) -> str:
        """Get pytest command to run this specific test"""
        if self.test_file and self.test_method:
            return f"python -m pytest {self.test_file}::{self.test_method} -v"
        elif self.test_file:
            return f"python -m pytest {self.test_file} -v"
        return ""


class ErrorFileParser:
    """Parses error file and extracts individual test errors"""

    @staticmethod
    def parse_error_file(file_path: str) -> List[TestError]:
        """
        Parse error file and return list of TestError objects.
        Errors are separated by "======...=====" lines.
        """
        with open(file_path, 'r') as f:
            content = f.read()

        # Split by separator
        error_blocks = content.split(ERROR_SEPARATOR)

        # Filter out empty blocks and create TestError objects
        errors = []
        seen_errors = set()  # Track unique errors to avoid duplicates

        for block in error_blocks:
            block = block.strip()
            if not block:
                continue

            error = TestError(error_text=block)

            # Only add if we haven't seen this exact test error before
            error_id = error.get_test_identifier()
            if error_id not in seen_errors:
                errors.append(error)
                seen_errors.add(error_id)

        return errors


class TestFixerAgent:
    """Manages Claude Code agent for fixing test errors"""

    def __init__(self, model: str = "sonnet", max_retries: int = 2):
        # Import claude_agent_sdk only when actually needed
        try:
            from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AgentDefinition
            self.ClaudeSDKClient = ClaudeSDKClient
            self.ClaudeAgentOptions = ClaudeAgentOptions
            self.AgentDefinition = AgentDefinition
        except ImportError:
            raise ImportError(
                "claude_agent_sdk is required to use TestFixerAgent. "
                "Install it with: pip install claude-agent-sdk"
            )

        self.model = model
        self.max_retries = max_retries
        self.console = Console() if Console else None
        self.stats = {
            "total": 0,
            "fixed": 0,
            "failed": 0,
            "skipped": 0
        }

    def _create_agent_options(self):
        """Create Claude agent options with TestFixerAgent subagent"""
        return self.ClaudeAgentOptions(
            model=self.model,
            permission_mode="acceptEdits",
            allowed_tools=[
                'Read',
                'Write',
                'Edit',
                'MultiEdit',
                'Grep',
                'Glob',
                'Bash',
                'Task',
                'TodoWrite'
            ],
            agents={
                "TestFixerAgent": self.AgentDefinition(
                    description="Expert at analyzing and fixing Python unit test errors. Fixes test code and validates changes by running tests.",
                    prompt="""You are an expert Python test engineer specialized in fixing unit test errors.

Your workflow:
1. Read and analyze the error message carefully
2. Identify the root cause (missing method, wrong signature, invalid args, etc.)
3. Read the test file to understand the test
4. Read related source files to understand the actual implementation
5. Fix the test to match the actual implementation
6. Run the specific test to validate the fix using pytest
7. If the test still fails, analyze the new error and retry

IMPORTANT RULES:
- Always read the test file before making changes
- Always read the related source code to understand what the test is testing
- Fix the TEST code, not the source code (unless the source code has obvious bugs)
- Run the SPECIFIC test after fixing (not all tests)
- Use the exact pytest command provided in the task
- If a test fails after your fix, analyze the new error and fix it
- Be thorough but efficient - don't make unnecessary changes
- Update test assertions, mock configurations, or test setup as needed

Output format:
- Describe what you found
- Explain the fix you're making
- Show the test result
- Confirm if the test now passes
""",
                    model=self.model,
                    tools=[
                        'Read',
                        'Write',
                        'Edit',
                        'MultiEdit',
                        'Grep',
                        'Glob',
                        'Bash',
                        'TodoWrite'
                    ]
                )
            }
        )

    async def fix_error(self, error: TestError) -> bool:
        """
        Fix a single test error using Claude Code agent.
        Returns True if fixed successfully, False otherwise.
        """
        test_id = error.get_test_identifier()

        if not error.test_file or not error.test_method:
            self.console.print(f"[yellow]⚠ Skipping error - cannot identify test file/method[/yellow]")
            self.stats["skipped"] += 1
            return False

        # Create the prompt for the agent
        pytest_cmd = error.get_pytest_command()

        prompt = f"""Fix this Python unit test error:

TEST FILE: {error.test_file}
TEST METHOD: {error.test_method}
ERROR TYPE: {error.error_type or 'Unknown'}

ERROR TRACEBACK:
```
{error.error_text}
```

VALIDATION COMMAND:
After fixing, run this exact command to validate:
```bash
{pytest_cmd}
```

Please:
1. Read the test file: {error.test_file}
2. Analyze the error and identify the root cause
3. Read any related source files to understand the implementation
4. Fix the test to match the actual implementation
5. Run the validation command to confirm the fix works
6. If it still fails, analyze the new error and fix again

Report back whether the test passes after your fix.
"""

        options = self._create_agent_options()

        self.console.print(Panel(
            f"[cyan]Fixing: {test_id}[/cyan]\n"
            f"Error: {error.error_type or 'Unknown'}",
            title="🔧 Test Fixer Agent",
            border_style="cyan"
        ))

        try:
            async with self.ClaudeSDKClient(options=options) as client:
                # Send the task to the agent
                await client.query(prompt)

                # Collect the response
                success = False
                async for message in client.receive_response():
                    # Check if test passes in the response
                    message_str = str(message)
                    if "passed" in message_str.lower() or "1 passed" in message_str:
                        success = True

                if success:
                    self.console.print(f"[green]✓ Successfully fixed: {test_id}[/green]\n")
                    self.stats["fixed"] += 1
                    return True
                else:
                    self.console.print(f"[red]✗ Failed to fix: {test_id}[/red]\n")
                    self.stats["failed"] += 1
                    return False

        except Exception as e:
            self.console.print(f"[red]✗ Error during fix: {str(e)}[/red]\n")
            self.stats["failed"] += 1
            return False

    async def fix_all_errors(self, errors: List[TestError]) -> Dict[str, int]:
        """
        Fix all errors sequentially.
        Returns statistics about fixes.
        """
        self.stats["total"] = len(errors)

        self.console.print(Panel(
            f"[bold]Starting test error fixing process[/bold]\n"
            f"Total unique errors to fix: {len(errors)}",
            title="🚀 Test Fixer",
            border_style="blue"
        ))

        for i, error in enumerate(errors, 1):
            self.console.print(f"\n[bold blue]Progress: {i}/{len(errors)}[/bold blue]")
            await self.fix_error(error)

        # Print final statistics
        self._print_stats()

        return self.stats

    def _print_stats(self):
        """Print final statistics table"""
        table = Table(title="Final Statistics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="yellow", justify="right")

        table.add_row("Total Errors", str(self.stats["total"]))
        table.add_row("Fixed", f"[green]{self.stats['fixed']}[/green]")
        table.add_row("Failed", f"[red]{self.stats['failed']}[/red]")
        table.add_row("Skipped", f"[yellow]{self.stats['skipped']}[/yellow]")

        if self.stats["total"] > 0:
            success_rate = (self.stats["fixed"] / self.stats["total"]) * 100
            table.add_row("Success Rate", f"{success_rate:.1f}%")

        self.console.print("\n")
        self.console.print(table)


async def main():
    parser = argparse.ArgumentParser(
        description="Fix Python unit test errors using Claude Code Agent"
    )
    parser.add_argument(
        "error_file",
        help="Path to file containing test errors (separated by ====...====)"
    )
    parser.add_argument(
        "--model", "-m",
        default="sonnet",
        choices=["haiku", "sonnet", "opus"],
        help="Claude model to use (default: sonnet)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum retry attempts per test (default: 2)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of errors to fix (for testing)"
    )

    args = parser.parse_args()

    # Validate error file exists
    if not Path(args.error_file).exists():
        print(f"Error: File not found: {args.error_file}")
        sys.exit(1)

    # Parse error file
    console = Console()
    console.print(f"[cyan]Reading error file: {args.error_file}[/cyan]")

    errors = ErrorFileParser.parse_error_file(args.error_file)

    if not errors:
        console.print("[yellow]No errors found in file[/yellow]")
        sys.exit(0)

    # Apply limit if specified
    if args.limit:
        errors = errors[:args.limit]
        console.print(f"[yellow]Limited to first {args.limit} errors[/yellow]")

    console.print(f"[green]Found {len(errors)} unique test errors[/green]\n")

    # Create fixer and run
    fixer = TestFixerAgent(model=args.model, max_retries=args.max_retries)
    stats = await fixer.fix_all_errors(errors)

    # Exit with appropriate code
    if stats["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
