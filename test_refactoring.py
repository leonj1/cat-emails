#!/usr/bin/env python3
"""
Test script to verify EmailProcessorService refactoring.
This script validates that EmailProcessorService now accepts
EmailCategorizerInterface instead of a Callable.
"""

import inspect
import sys
import os

# Add the repo to the path
sys.path.insert(0, '/root/repo')

def test_email_processor_service_signature():
    """Test that EmailProcessorService constructor accepts EmailCategorizerInterface."""

    print("Testing EmailProcessorService refactoring...")
    print("=" * 60)

    # Read the file to check imports and constructor
    with open('/root/repo/services/email_processor_service.py', 'r') as f:
        content = f.read()

    # Check 1: Verify the import is for EmailCategorizerInterface
    if 'from services.email_categorizer_interface import EmailCategorizerInterface' in content:
        print("✓ Import check: EmailCategorizerInterface is imported")
    else:
        print("✗ Import check: EmailCategorizerInterface is NOT imported")
        return False

    # Check 2: Verify Callable is not imported
    if 'from typing import Callable' not in content:
        print("✓ Typing check: Callable is NOT imported (good!)")
    else:
        print("✗ Typing check: Callable is still imported (should be removed)")
        return False

    # Check 3: Verify the constructor parameter type hint
    if 'email_categorizer: EmailCategorizerInterface' in content:
        print("✓ Constructor check: Parameter uses EmailCategorizerInterface")
    else:
        print("✗ Constructor check: Parameter does NOT use EmailCategorizerInterface")
        return False

    # Check 4: Verify the old callable parameter is gone
    if 'categorize_fn: Callable' not in content:
        print("✓ Legacy check: Old Callable parameter is removed")
    else:
        print("✗ Legacy check: Old Callable parameter still exists")
        return False

    # Check 5: Verify the method call uses the interface
    if 'self.email_categorizer.categorize(' in content:
        print("✓ Method call check: Uses email_categorizer.categorize()")
    else:
        print("✗ Method call check: Does not use email_categorizer.categorize()")
        return False

    print("=" * 60)
    print("All checks passed! ✓")
    return True

def test_account_email_processor_service():
    """Test that AccountEmailProcessorService also uses the interface."""

    print("\nTesting AccountEmailProcessorService refactoring...")
    print("=" * 60)

    with open('/root/repo/services/account_email_processor_service.py', 'r') as f:
        content = f.read()

    # Check 1: Verify the import
    if 'from services.email_categorizer_interface import EmailCategorizerInterface' in content:
        print("✓ Import check: EmailCategorizerInterface is imported")
    else:
        print("✗ Import check: EmailCategorizerInterface is NOT imported")
        return False

    # Check 2: Verify the constructor parameter
    if 'email_categorizer: EmailCategorizerInterface' in content:
        print("✓ Constructor check: Parameter uses EmailCategorizerInterface")
    else:
        print("✗ Constructor check: Parameter does NOT use EmailCategorizerInterface")
        return False

    # Check 3: Verify it passes the categorizer to EmailProcessorService
    if 'self.email_categorizer' in content:
        print("✓ Storage check: Stores email_categorizer as instance variable")
    else:
        print("✗ Storage check: Does not store email_categorizer")
        return False

    print("=" * 60)
    print("All checks passed! ✓")
    return True

def test_factory_interfaces():
    """Test that factory classes also use the interface."""

    print("\nTesting Factory classes refactoring...")
    print("=" * 60)

    # Test EmailProcessorFactory
    with open('/root/repo/services/email_processor_factory.py', 'r') as f:
        factory_content = f.read()

    if 'from services.email_categorizer_interface import EmailCategorizerInterface' in factory_content:
        print("✓ Factory import check: EmailCategorizerInterface is imported")
    else:
        print("✗ Factory import check: EmailCategorizerInterface is NOT imported")
        return False

    if 'email_categorizer: EmailCategorizerInterface' in factory_content:
        print("✓ Factory parameter check: Uses EmailCategorizerInterface")
    else:
        print("✗ Factory parameter check: Does not use EmailCategorizerInterface")
        return False

    # Test EmailProcessorFactoryInterface
    with open('/root/repo/services/email_processor_factory_interface.py', 'r') as f:
        interface_content = f.read()

    if 'from services.email_categorizer_interface import EmailCategorizerInterface' in interface_content:
        print("✓ Factory interface import check: EmailCategorizerInterface is imported")
    else:
        print("✗ Factory interface import check: EmailCategorizerInterface is NOT imported")
        return False

    if 'email_categorizer: EmailCategorizerInterface' in interface_content:
        print("✓ Factory interface parameter check: Uses EmailCategorizerInterface")
    else:
        print("✗ Factory interface parameter check: Does not use EmailCategorizerInterface")
        return False

    print("=" * 60)
    print("All checks passed! ✓")
    return True

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("EMAILPROCESSORSERVICE REFACTORING VALIDATION")
    print("=" * 60)

    all_passed = True

    # Run all tests
    all_passed &= test_email_processor_service_signature()
    all_passed &= test_account_email_processor_service()
    all_passed &= test_factory_interfaces()

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✓✓✓ ALL TESTS PASSED! ✓✓✓")
        print("EmailProcessorService has been successfully refactored to use")
        print("EmailCategorizerInterface instead of Callable[[str, str], str]")
    else:
        print("✗✗✗ SOME TESTS FAILED ✗✗✗")
        print("Please review the failures above")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)