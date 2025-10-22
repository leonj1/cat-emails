#!/bin/bash
# Quick script to check if your error file has proper test errors

ERROR_FILE="${1:-errors.txt}"

echo "==========================================="
echo "Checking Error File: $ERROR_FILE"
echo "==========================================="
echo ""

if [ ! -f "$ERROR_FILE" ]; then
    echo "❌ Error file not found: $ERROR_FILE"
    exit 1
fi

echo "1. File size:"
ls -lh "$ERROR_FILE" | awk '{print "   " $5}'
echo ""

echo "2. Number of error blocks (separated by ===):"
grep -c "^=====" "$ERROR_FILE" | awk '{print "   " $0 " blocks"}'
echo ""

echo "3. Test file references:"
# Check for test files in tests/ directory
TEST_FILES=$(grep -c 'File ".*tests/test_.*\.py"' "$ERROR_FILE")
# Also check for test files at root level
ROOT_TEST_FILES=$(grep -c 'File ".*/test_.*\.py"' "$ERROR_FILE" | grep -v tests/ || echo 0)
TOTAL_TEST_FILES=$((TEST_FILES + ROOT_TEST_FILES))

if [ "$TEST_FILES" -gt 0 ]; then
    echo "   ✅ Found $TEST_FILES test file references in tests/ directory"
    grep 'File ".*tests/test_.*\.py"' "$ERROR_FILE" | head -3 | sed 's/^/   /'
elif [ "$ROOT_TEST_FILES" -gt 0 ]; then
    echo "   ⚠️  Found $ROOT_TEST_FILES test files at root level (not in tests/)"
    grep 'File ".*/test_.*\.py"' "$ERROR_FILE" | grep -v tests/ | head -3 | sed 's/^/   /'
else
    echo "   ❌ No test file references found"
fi
echo ""

echo "4. Test method references:"
TEST_METHODS=$(grep -c "in test_" "$ERROR_FILE")
if [ "$TEST_METHODS" -gt 0 ]; then
    echo "   ✅ Found $TEST_METHODS test method references"
    grep "in test_" "$ERROR_FILE" | head -3 | sed 's/^/   /'
else
    echo "   ❌ No test method references found"
fi
echo ""

echo "5. Error types found:"
echo "   AttributeError: $(grep -c AttributeError "$ERROR_FILE")"
echo "   TypeError: $(grep -c TypeError "$ERROR_FILE")"
echo "   ValueError: $(grep -c ValueError "$ERROR_FILE")"
echo "   ImportError: $(grep -c 'ImportError\|ModuleNotFoundError' "$ERROR_FILE")"
echo "   Other Exceptions: $(grep -c '^Exception:' "$ERROR_FILE")"
echo ""

echo "==========================================="
echo "Assessment:"
echo "==========================================="

if [ "$TEST_FILES" -gt 0 ] && [ "$TEST_METHODS" -gt 0 ]; then
    echo "✅ This file appears to have proper test errors!"
    echo "   You can use: python3 fix_test_errors.py $ERROR_FILE --model sonnet"
else
    echo "❌ This file does NOT have proper test errors"
    echo ""
    echo "Common issues in your file:"
    if [ "$TEST_FILES" -eq 0 ]; then
        echo "   • No test file references (tests/test_*.py)"
    fi
    if [ "$TEST_METHODS" -eq 0 ]; then
        echo "   • No test method names (in test_*)"
    fi
    echo ""
    echo "Solutions:"
    echo "   1. Generate new error file:"
    echo "      python3 -m pytest tests/ -v 2>&1 | python3 extract_test_errors.py > new_errors.txt"
    echo ""
    echo "   2. Try the sample file:"
    echo "      python3 fix_test_errors.py sample_test_errors.txt --model haiku"
    echo ""
    echo "   3. Read the guide:"
    echo "      cat WHY_ZERO_ERRORS_FOUND.md"
fi

echo ""
