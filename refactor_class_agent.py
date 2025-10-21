#!/usr/bin/env python3
"""
Class Refactoring Agent System

This script orchestrates Claude Code agents to refactor large classes by:
1. Identifying the primary function of a class
2. Extracting other functions into dedicated service classes
3. Validating the extracted code through multiple post-hooks
4. Ensuring functions don't exceed 30 lines
5. Creating and validating unit tests

Usage:
    python refactor_class_agent.py <path_to_file>
"""

import argparse
import ast
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import nest_asyncio
from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, ClaudeSDKClient
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Apply nest_asyncio for compatibility
nest_asyncio.apply()
load_dotenv()


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class FunctionInfo:
    """Information about a function in the source file"""
    name: str
    line_count: int
    start_line: int
    end_line: int
    is_primary: bool = False


@dataclass
class ExtractionAttempt:
    """Record of a single extraction attempt"""
    timestamp: datetime
    function_name: str
    success: bool
    failure_reasons: List[str] = field(default_factory=list)
    code_hash: Optional[str] = None  # Hash of generated code to detect duplicates


@dataclass
class RefactoringState:
    """Overall state of the refactoring process"""
    source_file: Path
    class_name: str
    primary_function: Optional[str] = None
    functions_to_extract: List[FunctionInfo] = field(default_factory=list)
    extracted_functions: Set[str] = field(default_factory=set)
    failed_functions: Dict[str, List[ExtractionAttempt]] = field(default_factory=dict)
    extraction_history: List[ExtractionAttempt] = field(default_factory=list)

    def add_attempt(self, attempt: ExtractionAttempt):
        """Add an extraction attempt to history"""
        self.extraction_history.append(attempt)
        if not attempt.success:
            if attempt.function_name not in self.failed_functions:
                self.failed_functions[attempt.function_name] = []
            self.failed_functions[attempt.function_name].append(attempt)

    def is_repeating_failure(self, function_name: str, max_repeats: int = 3) -> bool:
        """Check if the agent is repeating the same implementation"""
        if function_name not in self.failed_functions:
            return False

        attempts = self.failed_functions[function_name]
        if len(attempts) < max_repeats:
            return False

        # Check last N attempts
        recent_attempts = attempts[-max_repeats:]
        code_hashes = [a.code_hash for a in recent_attempts if a.code_hash]

        # If we have at least 2 identical hashes in recent attempts, it's repeating
        if len(code_hashes) >= 2:
            hash_counts = {}
            for h in code_hashes:
                hash_counts[h] = hash_counts.get(h, 0) + 1
                if hash_counts[h] >= 2:
                    return True

        return False


# ============================================================================
# File Analysis
# ============================================================================

class FileAnalyzer:
    """Analyze Python source files to extract function information"""

    @staticmethod
    def count_function_lines(func_node: ast.FunctionDef, source_lines: List[str]) -> int:
        """Count non-empty, non-comment lines in a function"""
        start = func_node.lineno - 1
        end = func_node.end_lineno

        count = 0
        for line in source_lines[start:end]:
            stripped = line.strip()
            # Skip empty lines and comments
            if stripped and not stripped.startswith('#'):
                count += 1

        return count

    @staticmethod
    def extract_functions(file_path: Path) -> Tuple[str, List[FunctionInfo]]:
        """Extract all functions from a Python file"""
        with open(file_path, 'r') as f:
            content = f.read()
            source_lines = content.splitlines()

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse {file_path}: {e}")

        # Find the first class
        class_name = None
        class_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                class_node = node
                break

        if not class_node:
            raise ValueError(f"No class found in {file_path}")

        functions = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                # Skip special methods
                if node.name.startswith('__') and node.name.endswith('__'):
                    continue

                line_count = FileAnalyzer.count_function_lines(node, source_lines)
                func_info = FunctionInfo(
                    name=node.name,
                    line_count=line_count,
                    start_line=node.lineno,
                    end_line=node.end_lineno
                )
                functions.append(func_info)

        return class_name, functions


# ============================================================================
# Validators
# ============================================================================

class Validators:
    """Post-hook validators for extracted code"""

    @staticmethod
    def validate_no_env_vars(file_path: Path) -> Tuple[bool, str]:
        """Ensure no direct environment variable access"""
        with open(file_path, 'r') as f:
            content = f.read()

        # Look for os.getenv, os.environ patterns
        env_patterns = [
            r'os\.getenv\(',
            r'os\.environ\[',
            r'os\.environ\.get\(',
        ]

        violations = []
        for i, line in enumerate(content.splitlines(), 1):
            for pattern in env_patterns:
                if re.search(pattern, line):
                    violations.append(f"Line {i}: {line.strip()}")

        if violations:
            return False, "Direct environment variable access found:\n" + "\n".join(violations)

        return True, ""

    @staticmethod
    def validate_no_external_clients(file_path: Path) -> Tuple[bool, str]:
        """Ensure no external clients are instantiated directly"""
        with open(file_path, 'r') as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return False, "File has syntax errors"

        # Find class constructor
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    # Check methods other than __init__
                    if isinstance(item, ast.FunctionDef) and item.name != '__init__':
                        for subnode in ast.walk(item):
                            # Look for instantiation of common client types
                            if isinstance(subnode, ast.Call):
                                if isinstance(subnode.func, ast.Name):
                                    # Common client/connection patterns
                                    client_keywords = [
                                        'Client', 'Connection', 'Session', 'Pool',
                                        'HTTPClient', 'SQLClient', 'MongoClient',
                                        'RedisClient', 'requests.', 'httpx.'
                                    ]
                                    func_name = subnode.func.id
                                    if any(keyword in func_name for keyword in client_keywords):
                                        violations.append(
                                            f"Function {item.name} instantiates {func_name}"
                                        )

        if violations:
            return False, "External clients instantiated in methods:\n" + "\n".join(violations)

        return True, ""

    @staticmethod
    def validate_function_length(file_path: Path, max_lines: int = 30) -> Tuple[bool, str]:
        """Ensure all functions are under max_lines"""
        with open(file_path, 'r') as f:
            content = f.read()
            source_lines = content.splitlines()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return False, "File has syntax errors"

        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        line_count = FileAnalyzer.count_function_lines(item, source_lines)
                        if line_count > max_lines:
                            violations.append(
                                f"Function {item.name}: {line_count} lines (max {max_lines})"
                            )

        if violations:
            return False, "Functions exceed maximum length:\n" + "\n".join(violations)

        return True, ""

    @staticmethod
    def validate_unit_test_exists(service_file: Path) -> Tuple[bool, str]:
        """Ensure a unit test file exists and tests pass"""
        # Determine test file path
        service_name = service_file.stem
        test_dir = service_file.parent.parent / "tests"
        test_file = test_dir / f"test_{service_name}.py"

        if not test_file.exists():
            return False, f"Test file not found: {test_file}"

        # Run the test
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_file), "-v"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return False, f"Tests failed:\n{result.stdout}\n{result.stderr}"

            return True, ""
        except subprocess.TimeoutExpired:
            return False, "Tests timed out after 60 seconds"
        except Exception as e:
            return False, f"Error running tests: {e}"


# ============================================================================
# Agent Orchestrator
# ============================================================================

class RefactoringOrchestrator:
    """Orchestrates the refactoring process using Claude agents"""

    def __init__(self, source_file: Path, console: Console):
        self.source_file = source_file
        self.console = console
        self.state: Optional[RefactoringState] = None

        # Agent options
        self.options = ClaudeAgentOptions(
            model="sonnet",
            permission_mode="acceptEdits",
            setting_sources=["project"],
            allowed_tools=[
                'Read',
                'Write',
                'Edit',
                'MultiEdit',
                'Grep',
                'Glob',
                'Bash',
                'Task',
            ],
            agents={
                "primary-function-identifier": AgentDefinition(
                    description="Identifies the primary function of a class based on class name and structure",
                    prompt="""You are an expert Python code analyzer. Your task is to identify the PRIMARY function
                    of a class based on its name and the functions it contains.

                    The primary function is typically:
                    1. A function whose name closely matches or relates to the class name
                    2. The main public interface that the class is designed to provide
                    3. Often the most complex or central method

                    Examples:
                    - AudioGenerator -> generate_audio
                    - EmailProcessor -> process_email
                    - DataValidator -> validate_data

                    Read the file, analyze the class structure, and respond with ONLY the function name
                    of the primary function. Do not include parentheses, explanations, or any other text.
                    Just the function name.""",
                    model="sonnet",
                    tools=['Read', 'Grep']
                ),
                "extractor": AgentDefinition(
                    description="Extracts a function from a class into a dedicated service class",
                    prompt="""You are an expert Python refactoring specialist. Your task is to extract a specific
                    function from a class into its own dedicated service class following these STRICT rules:

                    CRITICAL REQUIREMENTS:
                    1. NO direct environment variable access (os.getenv, os.environ) - all config must be passed as function parameters
                    2. NO instantiation of external clients (HTTPClient, database clients, etc.) - must be passed via constructor as interfaces
                    3. ALL functions in the service class must NOT exceed 30 lines
                    4. Create a unit test file in tests/ directory with comprehensive test coverage
                    5. The unit test MUST pass when run with pytest

                    SERVICE CLASS STRUCTURE:
                    - Class name: <OriginalClass><FunctionName>Service
                    - Constructor accepts all dependencies as interfaces/protocols
                    - Single public method that implements the extracted functionality
                    - Helper methods if needed (each under 30 lines)

                    UNIT TEST REQUIREMENTS:
                    - File: tests/test_<service_name>.py
                    - Use pytest framework
                    - Mock all external dependencies
                    - Test happy path and error cases
                    - Test must run successfully

                    After creating the files, verify:
                    - No env var access
                    - No client instantiation
                    - All functions under 30 lines
                    - Test file exists and passes

                    If ANY requirement fails, fix it before completing.""",
                    model="sonnet",
                    tools=['Read', 'Write', 'Edit', 'Grep', 'Bash', 'Glob']
                )
            }
        )

    async def initialize_state(self) -> None:
        """Initialize refactoring state by analyzing the file"""
        self.console.print(Panel(
            f"Analyzing [cyan]{self.source_file}[/cyan]...",
            title="Initialization"
        ))

        class_name, functions = FileAnalyzer.extract_functions(self.source_file)

        self.state = RefactoringState(
            source_file=self.source_file,
            class_name=class_name,
            functions_to_extract=functions
        )

        # Display analysis
        table = Table(title=f"Functions in {class_name}")
        table.add_column("Function Name", style="cyan")
        table.add_column("Lines", style="yellow")
        table.add_column("Range", style="green")

        for func in functions:
            table.add_row(
                func.name,
                str(func.line_count),
                f"{func.start_line}-{func.end_line}"
            )

        self.console.print(table)

    async def identify_primary_function(self) -> str:
        """Use agent to identify the primary function"""
        self.console.print(Panel(
            "Identifying primary function...",
            title="Step 1: Primary Function Identification"
        ))

        async with ClaudeSDKClient(options=self.options) as client:
            # Delegate to primary-function-identifier subagent
            prompt = f"""I need you to identify the primary function of a Python class.

File: {self.source_file}
Class name: {self.state.class_name}
Available functions: {', '.join([f.name for f in self.state.functions_to_extract])}

Please delegate this task to the primary-function-identifier agent. The agent should analyze the class and identify which function is the PRIMARY function (the main purpose of the class, often matching the class name).

After the agent completes, report back with ONLY the function name, nothing else."""

            await client.query(prompt)

            primary_function = None
            async for message in client.receive_response():
                # Extract text from assistant messages
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            # Clean up the response
                            text = block.text.strip()
                            # Look for function name in the text
                            for func in self.state.functions_to_extract:
                                if func.name in text:
                                    primary_function = func.name
                                    break
                            if primary_function:
                                break

        if not primary_function:
            raise ValueError("Failed to identify primary function")

        self.console.print(f"[green]✓[/green] Primary function identified: [cyan]{primary_function}[/cyan]")
        return primary_function

    async def extract_function(self, func_info: FunctionInfo) -> bool:
        """Extract a single function using the extractor agent"""
        self.console.print(Panel(
            f"Extracting function: [cyan]{func_info.name}[/cyan]",
            title="Extraction"
        ))

        max_retries = 5
        attempt_count = 0

        while attempt_count < max_retries:
            attempt_count += 1

            # Check for repeating failures
            if self.state.is_repeating_failure(func_info.name):
                self.console.print(
                    f"[red]✗[/red] Function {func_info.name} has repeated failures. Skipping."
                )
                return False

            self.console.print(f"Attempt {attempt_count}/{max_retries}")

            # Build prompt with previous failure reasons if any
            failure_context = ""
            if func_info.name in self.state.failed_functions:
                recent_failures = self.state.failed_functions[func_info.name][-3:]
                if recent_failures:
                    failure_context = "\n\nPREVIOUS FAILURES (fix these issues):\n"
                    for i, attempt in enumerate(recent_failures, 1):
                        failure_context += f"\nAttempt {i}:\n"
                        failure_context += "\n".join(f"  - {reason}" for reason in attempt.failure_reasons)

            async with ClaudeSDKClient(options=self.options) as client:
                # Delegate to extractor subagent
                prompt = f"""I need you to extract a function from a Python class into a dedicated service class.

File: {self.source_file}
Class name: {self.state.class_name}
Function to extract: {func_info.name}
Current function lines: {func_info.line_count}
{failure_context}

Please delegate this task to the extractor agent. The agent should:

1. Extract function '{func_info.name}' into a new service class
2. Create the service file: services/{self.state.class_name.lower()}_{func_info.name}_service.py
3. Create the test file: tests/test_{self.state.class_name.lower()}_{func_info.name}_service.py

The agent MUST follow these strict requirements:
- NO direct environment variable access (os.getenv, os.environ)
- NO external client instantiation in methods (inject via constructor)
- ALL functions must be under 30 lines
- Unit tests must exist and pass with pytest

After the agent completes, report back that extraction is complete."""

                await client.query(prompt)

                async for message in client.receive_response():
                    pass  # Let agent complete

            # Validate the extraction
            service_file = Path(f"services/{self.state.class_name.lower()}_{func_info.name}_service.py")

            if not service_file.exists():
                attempt = ExtractionAttempt(
                    timestamp=datetime.now(),
                    function_name=func_info.name,
                    success=False,
                    failure_reasons=["Service file was not created"]
                )
                self.state.add_attempt(attempt)
                continue

            # Run validators
            validation_results = await self.run_validators(service_file)

            if all(v[0] for v in validation_results.values()):
                # All validations passed
                code_hash = self.hash_file(service_file)
                attempt = ExtractionAttempt(
                    timestamp=datetime.now(),
                    function_name=func_info.name,
                    success=True,
                    code_hash=code_hash
                )
                self.state.add_attempt(attempt)
                self.state.extracted_functions.add(func_info.name)
                self.console.print(f"[green]✓[/green] Successfully extracted {func_info.name}")
                return True
            else:
                # Some validations failed
                failures = [msg for valid, msg in validation_results.values() if not valid]
                code_hash = self.hash_file(service_file)

                attempt = ExtractionAttempt(
                    timestamp=datetime.now(),
                    function_name=func_info.name,
                    success=False,
                    failure_reasons=failures,
                    code_hash=code_hash
                )
                self.state.add_attempt(attempt)

                self.console.print("[yellow]Validation failed:[/yellow]")
                for failure in failures:
                    self.console.print(f"  [red]✗[/red] {failure}")

        self.console.print(f"[red]✗[/red] Failed to extract {func_info.name} after {max_retries} attempts")
        return False

    async def run_validators(self, service_file: Path) -> Dict[str, Tuple[bool, str]]:
        """Run all post-hook validators"""
        results = {}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Running validators...", total=4)

            progress.update(task, description="Validating no env vars...")
            results['env_vars'] = Validators.validate_no_env_vars(service_file)
            progress.advance(task)

            progress.update(task, description="Validating no external clients...")
            results['external_clients'] = Validators.validate_no_external_clients(service_file)
            progress.advance(task)

            progress.update(task, description="Validating function length...")
            results['function_length'] = Validators.validate_function_length(service_file)
            progress.advance(task)

            progress.update(task, description="Validating unit tests...")
            results['unit_tests'] = Validators.validate_unit_test_exists(service_file)
            progress.advance(task)

        return results

    @staticmethod
    def hash_file(file_path: Path) -> str:
        """Generate hash of file content"""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    async def refactor(self) -> bool:
        """Execute the full refactoring workflow"""
        # Initialize
        await self.initialize_state()

        # Identify primary function
        primary_func_name = await self.identify_primary_function()

        # Mark primary function
        for func in self.state.functions_to_extract:
            if func.name == primary_func_name:
                func.is_primary = True

        # Extract non-primary functions first
        candidates = [f for f in self.state.functions_to_extract if not f.is_primary and f.line_count > 30]

        self.console.print(Panel(
            f"Found {len(candidates)} functions to extract (>{30} lines)",
            title="Extraction Plan"
        ))

        for func in candidates:
            success = await self.extract_function(func)
            if not success:
                self.console.print(f"[yellow]⚠[/yellow] Skipping {func.name} due to repeated failures")

        # Check if primary function needs refactoring
        primary_func = next(f for f in self.state.functions_to_extract if f.is_primary)
        if primary_func.line_count > 30:
            self.console.print(Panel(
                f"Primary function [cyan]{primary_func.name}[/cyan] has {primary_func.line_count} lines - refactoring needed",
                title="Primary Function Refactoring"
            ))
            await self.extract_function(primary_func)

        # Summary
        self.print_summary()

        return len(self.state.extracted_functions) > 0

    def print_summary(self):
        """Print refactoring summary"""
        table = Table(title="Refactoring Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Total Functions Analyzed", str(len(self.state.functions_to_extract)))
        table.add_row("Successfully Extracted", str(len(self.state.extracted_functions)))
        table.add_row("Failed Extractions", str(len(self.state.failed_functions)))
        table.add_row("Total Attempts", str(len(self.state.extraction_history)))

        self.console.print(table)

        if self.state.extracted_functions:
            self.console.print("\n[green]Successfully Extracted:[/green]")
            for func_name in self.state.extracted_functions:
                self.console.print(f"  [green]✓[/green] {func_name}")

        if self.state.failed_functions:
            self.console.print("\n[red]Failed Extractions:[/red]")
            for func_name in self.state.failed_functions:
                self.console.print(f"  [red]✗[/red] {func_name}")


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Refactor a Python class by extracting large functions into service classes"
    )
    parser.add_argument(
        "file",
        type=str,
        help="Path to the Python file to refactor"
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=30,
        help="Maximum lines per function (default: 30)"
    )

    args = parser.parse_args()

    # Validate file
    source_file = Path(args.file)
    if not source_file.exists():
        print(f"Error: File not found: {source_file}")
        sys.exit(1)

    if not source_file.suffix == '.py':
        print(f"Error: File must be a Python file: {source_file}")
        sys.exit(1)

    # Create console
    console = Console()

    console.print(Panel.fit(
        f"[bold cyan]Class Refactoring Agent System[/bold cyan]\n"
        f"File: {source_file}\n"
        f"Max lines per function: {args.max_lines}",
        border_style="cyan"
    ))

    # Create orchestrator and run
    orchestrator = RefactoringOrchestrator(source_file, console)

    try:
        success = await orchestrator.refactor()
        if success:
            console.print("\n[green]✓ Refactoring completed successfully![/green]")
            sys.exit(0)
        else:
            console.print("\n[yellow]⚠ Refactoring completed with some failures[/yellow]")
            sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
