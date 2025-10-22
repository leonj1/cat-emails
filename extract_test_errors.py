#!/usr/bin/env python3
"""
Extract test errors from pytest output and save to a file.

Usage:
    python -m pytest tests/ -v 2>&1 | python3 extract_test_errors.py > errors.txt

Or:
    python3 extract_test_errors.py pytest_output.txt > errors.txt
"""

import sys
import re
from typing import List


def extract_errors_from_text(text: str) -> List[str]:
    """
    Extract error tracebacks from pytest output.

    Returns a list of error text blocks.
    """
    errors = []

    # Split by common pytest separators
    lines = text.split('\n')

    current_error = []
    in_traceback = False

    for line in lines:
        # Start of a traceback
        if line.strip().startswith('Traceback (most recent call last):'):
            in_traceback = True
            current_error = [line]
        elif in_traceback:
            # Continue collecting traceback lines
            current_error.append(line)

            # Check if we've reached the end of the error
            # Errors usually end with the exception type and message
            if line and not line.startswith(' ') and any(
                err_type in line for err_type in [
                    'Error:', 'Exception:', 'AttributeError:', 'TypeError:',
                    'ValueError:', 'KeyError:', 'IndexError:', 'NameError:',
                    'ImportError:', 'ModuleNotFoundError:', 'RuntimeError:',
                    'AssertionError:', 'FileNotFoundError:'
                ]
            ):
                # We've reached the error message line
                error_text = '\n'.join(current_error)
                if error_text.strip():
                    errors.append(error_text)
                current_error = []
                in_traceback = False

    # Catch any remaining error
    if current_error and in_traceback:
        error_text = '\n'.join(current_error)
        if error_text.strip():
            errors.append(error_text)

    return errors


def format_errors_for_file(errors: List[str], separator: str = "=" * 80) -> str:
    """
    Format errors for output file with separators.
    """
    if not errors:
        return ""

    formatted = []
    for error in errors:
        formatted.append(error.strip())
        formatted.append(separator)

    return '\n\n'.join(formatted)


def main():
    if len(sys.argv) > 1:
        # Read from file
        input_file = sys.argv[1]
        try:
            with open(input_file, 'r') as f:
                text = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {input_file}", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin (piped input)
        text = sys.stdin.read()

    if not text.strip():
        print("Error: No input provided", file=sys.stderr)
        print("", file=sys.stderr)
        print("Usage:", file=sys.stderr)
        print("  python -m pytest tests/ -v 2>&1 | python3 extract_test_errors.py > errors.txt", file=sys.stderr)
        print("Or:", file=sys.stderr)
        print("  python3 extract_test_errors.py pytest_output.txt > errors.txt", file=sys.stderr)
        sys.exit(1)

    # Extract errors
    errors = extract_errors_from_text(text)

    if not errors:
        print("No errors found in input", file=sys.stderr)
        sys.exit(0)

    # Format and print
    formatted_output = format_errors_for_file(errors)
    print(formatted_output)

    # Print summary to stderr
    print(f"\nExtracted {len(errors)} error(s)", file=sys.stderr)


if __name__ == "__main__":
    main()
