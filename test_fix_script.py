#!/usr/bin/env python3
"""
Simple test script to verify fix_test_errors.py components work correctly
"""

import sys
from pathlib import Path
from fix_test_errors import ErrorFileParser, TestError


def test_error_parsing():
    """Test that error parsing works correctly"""
    print("Testing error parsing...")

    # Test with actual errors.txt file
    if not Path("errors.txt").exists():
        print("❌ errors.txt not found, skipping test")
        return False

    errors = ErrorFileParser.parse_error_file("errors.txt")

    print(f"✓ Parsed {len(errors)} unique errors")

    if len(errors) == 0:
        print("❌ No errors found in file")
        return False

    # Check first error
    first_error = errors[0]
    print(f"\nFirst Error Details:")
    print(f"  Test ID: {first_error.get_test_identifier()}")
    print(f"  Test File: {first_error.test_file}")
    print(f"  Test Method: {first_error.test_method}")
    print(f"  Error Type: {first_error.error_type}")
    print(f"  Line Number: {first_error.line_number}")
    print(f"  Pytest Command: {first_error.get_pytest_command()}")

    if not first_error.test_file:
        print("❌ Could not extract test file")
        return False

    if not first_error.test_method:
        print("❌ Could not extract test method")
        return False

    print("\n✓ Error parsing works correctly")
    return True


def test_deduplication():
    """Test that duplicate errors are removed"""
    print("\nTesting deduplication...")

    # Create a sample error file with duplicates
    sample_error = """Traceback (most recent call last):
  File "/app/tests/test_sample.py", line 10, in test_example
    result = function()
AttributeError: some error"""

    separator = "=" * 80

    sample_file = "test_errors_sample.txt"
    with open(sample_file, "w") as f:
        # Write same error 3 times
        for i in range(3):
            f.write(sample_error)
            f.write(f"\n{separator}\n")

    errors = ErrorFileParser.parse_error_file(sample_file)

    # Clean up
    Path(sample_file).unlink()

    if len(errors) != 1:
        print(f"❌ Expected 1 error after deduplication, got {len(errors)}")
        return False

    print("✓ Deduplication works correctly")
    return True


def test_error_object():
    """Test TestError object functionality"""
    print("\nTesting TestError object...")

    error_text = """Traceback (most recent call last):
  File "/app/tests/test_account_category_service.py", line 97, in test_create_or_update_account
    account1 = self.service.create_or_update_account(self.test_email)
AttributeError: 'AccountCategoryClient' object has no attribute 'create_or_update_account'"""

    error = TestError(error_text=error_text)

    assert error.test_file == "tests/test_account_category_service.py"
    assert error.test_method == "test_create_or_update_account"
    assert error.error_type == "AttributeError"
    assert error.line_number == 97

    expected_cmd = "python -m pytest tests/test_account_category_service.py::test_create_or_update_account -v"
    assert error.get_pytest_command() == expected_cmd

    print("✓ TestError object works correctly")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing fix_test_errors.py components")
    print("=" * 60 + "\n")

    tests = [
        ("Error Parsing", test_error_parsing),
        ("Deduplication", test_deduplication),
        ("TestError Object", test_error_object),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
