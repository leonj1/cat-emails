#!/usr/bin/env python3
"""
Extract Python tracebacks from test output files.

Usage:
    python extract_errors.py <input_file> [output_file]

Arguments:
    input_file: File containing test output with potential errors
    output_file: File to write extracted errors (default: errors.txt)
"""

import sys
import re
from pathlib import Path


def extract_tracebacks(input_text: str) -> list[str]:
    """
    Extract all Python tracebacks from input text.

    A traceback starts with "Traceback (most recent call last):"
    and continues until we hit a blank line or a line that doesn't
    start with spaces (indicating the end of the traceback).

    Args:
        input_text: The input text containing test output

    Returns:
        List of extracted traceback strings
    """
    tracebacks = []
    lines = input_text.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this line starts a traceback
        if line.strip().startswith('Traceback (most recent call last):'):
            traceback_lines = [line]
            i += 1

            # Collect all lines that are part of this traceback
            while i < len(lines):
                current_line = lines[i]

                # End of traceback: blank line or non-indented line after exception
                if not current_line.strip():
                    break

                # Check if we've reached the exception line (not indented with File/spaces)
                # Exception lines typically don't start with spaces or "File"
                if (traceback_lines and
                    not current_line.startswith('  ') and
                    not current_line.startswith('File ') and
                    not current_line.strip().startswith('^')):
                    # This is likely the exception line
                    traceback_lines.append(current_line)
                    i += 1
                    break

                traceback_lines.append(current_line)
                i += 1

            # Join the traceback lines and add to results
            tracebacks.append('\n'.join(traceback_lines))
        else:
            i += 1

    return tracebacks


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Error: Input file required", file=sys.stderr)
        print(f"Usage: {sys.argv[0]} <input_file> [output_file]", file=sys.stderr)
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2] if len(sys.argv) > 2 else "errors.txt")

    # Validate input file exists
    if not input_file.exists():
        print(f"Error: Input file '{input_file}' not found", file=sys.stderr)
        sys.exit(1)

    # Read input file
    try:
        input_text = input_file.read_text()
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract tracebacks
    tracebacks = extract_tracebacks(input_text)

    if not tracebacks:
        print("No Python tracebacks found in input file", file=sys.stderr)
        sys.exit(0)

    # Write to output file
    try:
        output_content = '\n\n' + '='*80 + '\n\n'
        output_content = output_content.join(tracebacks)
        output_file.write_text(output_content)
        print(f"Extracted {len(tracebacks)} traceback(s) to '{output_file}'")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
