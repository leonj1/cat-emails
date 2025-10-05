#!/usr/bin/env python3
"""
Simple test to verify that AccountCategoryClient has the correct method names.
This test can run without all dependencies installed.
"""
import ast
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_account_service_methods():
    """Test that AccountCategoryClient has correct method names."""
    # Read the client file
    service_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'clients', 'account_category_client.py')

    with open(service_file, 'r') as f:
        content = f.read()

    # Parse the AST
    tree = ast.parse(content)

    # Find the AccountCategoryClient class
    service_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'AccountCategoryClient':
            service_class = node
            break

    if not service_class:
        print("❌ ERROR: AccountCategoryClient class not found!")
        return False

    # Get all method names
    method_names = []
    for item in service_class.body:
        if isinstance(item, ast.FunctionDef):
            method_names.append(item.name)

    # Check for correct method
    has_correct_method = 'get_account_by_email' in method_names
    has_wrong_method = 'get_account' in method_names

    print(f"✅ Has get_account_by_email: {has_correct_method}")
    print(f"✅ Does NOT have get_account: {not has_wrong_method}")

    if has_wrong_method:
        print("❌ ERROR: AccountCategoryClient should not have 'get_account' method!")
        print("         Use 'get_account_by_email' instead.")
        return False

    if not has_correct_method:
        print("❌ ERROR: AccountCategoryClient is missing 'get_account_by_email' method!")
        return False

    # Also check api_service.py for correct usage
    api_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api_service.py')

    with open(api_file, 'r') as f:
        api_content = f.read()

    # Check for wrong method usage
    if '.get_account(' in api_content:
        print("❌ ERROR: api_service.py contains calls to 'get_account' method!")
        print("         This should be 'get_account_by_email'.")

        # Find line numbers
        lines = api_content.split('\n')
        for i, line in enumerate(lines, 1):
            if '.get_account(' in line:
                print(f"         Line {i}: {line.strip()}")
        return False

    # Check for correct method usage
    if '.get_account_by_email(' in api_content:
        print("✅ api_service.py uses correct method 'get_account_by_email'")

    print("\n✅ All tests passed! The AttributeError should be fixed.")
    return True


if __name__ == '__main__':
    success = test_account_service_methods()
    sys.exit(0 if success else 1)