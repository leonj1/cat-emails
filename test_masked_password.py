#!/usr/bin/env python3
"""
Test script to verify masked password functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.password_utils import mask_password


def test_mask_password():
    """Test the mask_password function with various inputs"""

    test_cases = [
        # (input, expected_output, description)
        (None, None, "None password"),
        ("", None, "Empty password"),
        ("ab", "**", "2 character password"),
        ("abc", "***", "3 character password"),
        ("abcd", "****", "4 character password"),
        ("abcde", "ab*de", "5 character password"),
        ("abcdef", "ab**ef", "6 character password"),
        ("abcdefghijklmnop", "ab************op", "16 character password (typical app password)"),
        ("1234567890123456", "12************56", "Another 16 char password"),
        ("verylongpassword123", "ve***************23", "Long password"),
    ]

    print("Testing mask_password function:")
    print("-" * 60)

    all_passed = True
    for password, expected, description in test_cases:
        result = mask_password(password)
        passed = result == expected

        if passed:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            all_passed = False

        # Format display of None and empty strings
        display_input = repr(password) if password is None or password == "" else password
        display_result = repr(result) if result is None else result
        display_expected = repr(expected) if expected is None else expected

        print(f"{status} - {description}")
        print(f"    Input:    {display_input}")
        print(f"    Expected: {display_expected}")
        print(f"    Got:      {display_result}")

        if not passed:
            print(f"    ERROR: Result doesn't match!")
        print()

    print("-" * 60)
    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


def test_api_response_format():
    """Test that the EmailAccountInfo model accepts masked_password field"""
    from models.account_models import EmailAccountInfo
    from datetime import datetime

    print("\nTesting EmailAccountInfo model with masked_password:")
    print("-" * 60)

    try:
        # Create an account info with masked password
        account_info = EmailAccountInfo(
            id=1,
            email_address="test@example.com",
            display_name="Test Account",
            masked_password="ab************yz",
            is_active=True,
            last_scan_at=datetime.now(),
            created_at=datetime.now()
        )

        print("✅ Successfully created EmailAccountInfo with masked_password")
        print(f"   Email: {account_info.email_address}")
        print(f"   Masked Password: {account_info.masked_password}")

        # Test with None password
        account_info_no_pwd = EmailAccountInfo(
            id=2,
            email_address="nopwd@example.com",
            display_name="No Password Account",
            masked_password=None,
            is_active=True,
            last_scan_at=None,
            created_at=datetime.now()
        )

        print("✅ Successfully created EmailAccountInfo with None masked_password")
        print(f"   Email: {account_info_no_pwd.email_address}")
        print(f"   Masked Password: {account_info_no_pwd.masked_password}")

        return 0

    except Exception as e:
        print(f"❌ Failed to create EmailAccountInfo: {e}")
        return 1


def main():
    """Run all tests"""
    print("=" * 60)
    print("MASKED PASSWORD FUNCTIONALITY TEST")
    print("=" * 60)

    # Run tests
    result1 = test_mask_password()
    result2 = test_api_response_format()

    # Overall result
    print("\n" + "=" * 60)
    if result1 == 0 and result2 == 0:
        print("✅ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()