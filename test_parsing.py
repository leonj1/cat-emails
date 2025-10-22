#!/usr/bin/env python3
"""Test the error parsing with sample errors"""

from fix_test_errors import ErrorFileParser

# Test with sample file
errors = ErrorFileParser.parse_error_file("sample_test_errors.txt")

print(f"Found {len(errors)} unique test errors\n")

for i, err in enumerate(errors, 1):
    print(f"{i}. {err.get_test_identifier()}")
    print(f"   Test File: {err.test_file}")
    print(f"   Test Method: {err.test_method}")
    print(f"   Error Type: {err.error_type}")
    print(f"   Command: {err.get_pytest_command()}")
    print()
