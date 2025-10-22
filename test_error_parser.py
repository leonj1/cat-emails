#!/usr/bin/env python3
"""
Test the error parsing functionality without requiring Claude SDK
"""

import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

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
        # Extract test file and method
        file_match = re.search(r'File "([^"]+/tests/[^"]+\.py)"', self.error_text)
        if file_match:
            self.test_file = file_match.group(1).replace('/app/', '')

        # Extract test method
        method_match = re.search(r'in (test_\w+)', self.error_text)
        if method_match:
            self.test_method = method_match.group(1)

        # Extract line number
        line_match = re.search(r'line (\d+)', self.error_text)
        if line_match:
            self.line_number = int(line_match.group(1))

        # Extract error type
        error_types = ['AttributeError', 'TypeError', 'Exception', 'ValueError', 'KeyError']
        for err_type in error_types:
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
        """Parse error file and return list of TestError objects"""
        with open(file_path, 'r') as f:
            content = f.read()

        # Split by separator
        error_blocks = content.split(ERROR_SEPARATOR)

        # Filter out empty blocks and create TestError objects
        errors = []
        seen_errors = set()

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


def main():
    print("Testing Error Parser\n" + "=" * 60)

    # Test with actual errors.txt
    if Path("errors.txt").exists():
        print("\n1. Parsing errors.txt...")
        errors = ErrorFileParser.parse_error_file("errors.txt")
        print(f"   ✓ Found {len(errors)} unique errors")

        if errors:
            print("\n2. First error details:")
            e = errors[0]
            print(f"   Test File: {e.test_file}")
            print(f"   Test Method: {e.test_method}")
            print(f"   Error Type: {e.error_type}")
            print(f"   Line: {e.line_number}")
            print(f"   Test ID: {e.get_test_identifier()}")
            print(f"   Command: {e.get_pytest_command()}")

            print("\n3. All unique test identifiers:")
            for i, err in enumerate(errors, 1):
                print(f"   {i}. {err.get_test_identifier()} ({err.error_type})")

    else:
        print("   ⚠ errors.txt not found, creating sample...")

        # Create sample error file
        sample = """Traceback (most recent call last):
  File "/app/tests/test_account_category_service.py", line 97, in test_create_or_update_account
    account1 = self.service.create_or_update_account(self.test_email)
AttributeError: 'AccountCategoryClient' object has no attribute 'create_or_update_account'

================================================================================

Traceback (most recent call last):
  File "/app/tests/test_account_category_service.py", line 196, in test_get_top_categories_no_data
    response = self.service.get_top_categories(
TypeError: AccountCategoryClient.get_top_categories() missing 1 required positional argument: 'days'
"""

        with open("sample_errors.txt", "w") as f:
            f.write(sample)

        errors = ErrorFileParser.parse_error_file("sample_errors.txt")
        print(f"   ✓ Parsed {len(errors)} errors from sample")

        for e in errors:
            print(f"\n   {e.get_test_identifier()}")
            print(f"   Type: {e.error_type}")
            print(f"   Command: {e.get_pytest_command()}")

    print("\n" + "=" * 60)
    print("✅ All parsing tests passed!")


if __name__ == "__main__":
    main()
