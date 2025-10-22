#!/bin/bash
# Example usage of fix_test_errors.py script

echo "======================================"
echo "Test Error Fixer - Example Usage"
echo "======================================"
echo ""

# Make sure the script is executable
chmod +x fix_test_errors.py

echo "1. Basic usage - fix all errors in errors.txt"
echo "   Command: python3 fix_test_errors.py errors.txt"
echo ""

echo "2. Fix with Haiku model (faster, cheaper)"
echo "   Command: python3 fix_test_errors.py errors.txt --model haiku"
echo ""

echo "3. Fix only the first 3 errors (for testing)"
echo "   Command: python3 fix_test_errors.py errors.txt --limit 3"
echo ""

echo "4. Fix with Sonnet model (recommended)"
echo "   Command: python3 fix_test_errors.py errors.txt --model sonnet"
echo ""

echo "5. Fix with Opus model (most capable)"
echo "   Command: python3 fix_test_errors.py errors.txt --model opus"
echo ""

echo "6. View help"
echo "   Command: python3 fix_test_errors.py --help"
echo ""

# Uncomment to actually run a limited test
# echo "Running a test with first 1 error..."
# python3 fix_test_errors.py errors.txt --limit 1 --model haiku
