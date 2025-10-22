# Understanding Test Error Formats

## Why Your errors.txt Shows "0 unique test errors"

### The Problem

Your `errors.txt` file contains errors that occur **during** test execution, but they don't show **which test** triggered them. The script needs to know which specific test file and test method to fix.

### Example of What You Have (Won't Work)

```python
Traceback (most recent call last):
  File "/app/services/logging_service.py", line 160, in _send_to_remote_sync
    return self.logs_collector_client.send(log_entry)
Exception: Timeout
```

**Problem**: This shows an error in `logging_service.py` but doesn't tell us:
- Which test file triggered this?
- Which test method was running?
- What to fix?

### Example of What You Need (Will Work)

```python
Traceback (most recent call last):
  File "/app/tests/test_account_category_service.py", line 97, in test_create_or_update_account
    account1 = self.service.create_or_update_account(self.test_email)
AttributeError: 'AccountCategoryClient' object has no attribute 'create_or_update_account'
```

**This works because it shows**:
- ✅ Test file: `tests/test_account_category_service.py`
- ✅ Test method: `test_create_or_update_account`
- ✅ Error type: `AttributeError`
- ✅ What went wrong: method doesn't exist

## How to Get Proper Test Errors

### Method 1: Run Specific Test Files

```bash
# Run a specific test file
python3 -m pytest tests/test_account_category_service.py -v 2>&1 > test_output.txt

# Extract errors
python3 extract_test_errors.py test_output.txt > errors.txt
```

### Method 2: Run Tests with --tb=short

```bash
# Shorter tracebacks that focus on test code
python3 -m pytest tests/ --tb=short -v 2>&1 > test_output.txt
```

### Method 3: Run Tests with -x (Stop on First Failure)

```bash
# Stop at first failure, get cleaner output
python3 -m pytest tests/ -x -v 2>&1 > test_output.txt
```

### Method 4: Capture Only Failures

```bash
# Run tests and grep for FAILED
python3 -m pytest tests/ -v 2>&1 | grep -A 30 "FAILED" > test_output.txt
```

## Checking Your Error File

### Good Indicators

Your error file should have:

```bash
# Check for test files
grep "File.*tests/test_" errors.txt

# Check for test methods
grep "in test_" errors.txt

# Should see output like:
#   File "/app/tests/test_example.py", line 42, in test_something
```

### Test Your Error File

```bash
# See how many errors were found
python3 -c "
from fix_test_errors import ErrorFileParser
errors = ErrorFileParser.parse_error_file('errors.txt')
print(f'Found {len(errors)} test errors')
for e in errors:
    print(f'  - {e.get_test_identifier()}')
"
```

## Current Situation with Your errors.txt

Your current `errors.txt` contains:

1. **Timeout errors in logging_service** - These happen during tests but don't show which test
2. **Import errors** - Module import failures

Neither of these can be automatically fixed because we don't know:
- Which test to run to validate the fix
- What test code needs to be changed

## Solution: Generate a New Error File

### Step 1: Find Which Tests Are Failing

```bash
# Run all tests and see which ones fail
python3 -m pytest tests/ -v

# You'll see output like:
# FAILED tests/test_example.py::test_something - AttributeError: ...
```

### Step 2: Run Only Failing Tests

```bash
# Example: If test_account_email_processor_service.py fails due to missing faker
python3 -m pytest tests/test_account_email_processor_service.py -v 2>&1 > new_errors.txt
```

### Step 3: Extract Errors

```bash
python3 extract_test_errors.py new_errors.txt > errors_to_fix.txt
```

### Step 4: Verify

```bash
# Should show actual test errors now
python3 fix_test_errors.py errors_to_fix.txt --limit 1 --model haiku
```

## Example Workflow

```bash
# 1. Run tests and find failures
python3 -m pytest tests/ -v 2>&1 | tee pytest_output.txt

# 2. Look for FAILED tests
grep FAILED pytest_output.txt

# 3. If you see something like:
#    FAILED tests/test_example.py::test_something - AttributeError
#    Then run just that test:

python3 -m pytest tests/test_example.py::test_something -v 2>&1 > specific_error.txt

# 4. Extract the error
python3 extract_test_errors.py specific_error.txt > errors.txt

# 5. Now fix it
python3 fix_test_errors.py errors.txt --model sonnet
```

## Understanding What the Script Can Fix

### ✅ CAN Fix

1. **Test code issues:**
   - Wrong method names in tests
   - Wrong parameters in test calls
   - Missing mocks
   - Incorrect assertions
   - Wrong test setup

2. **Example:**
   ```python
   # Error: test calls self.service.old_method() but it's now new_method()
   # Script will: update the test to call new_method()
   ```

### ❌ CANNOT Fix

1. **Source code bugs** - Script fixes tests, not source code
2. **Import errors** - Missing dependencies need to be installed
3. **Environment issues** - Database not running, etc.
4. **Errors without test context** - Like your timeout errors

### What About Those Timeout Errors?

The timeout errors in `logging_service.py` are happening during test execution. To fix these:

1. **Find which tests trigger them:**
   ```bash
   python3 -m pytest tests/test_logging_service.py -v
   ```

2. **If tests pass** - The errors might be expected/handled
3. **If tests fail** - You'll see the actual test error with test method name

## Sample Error File

I've created `sample_test_errors.txt` with proper test errors for demonstration:

```bash
# Test the sample
python3 fix_test_errors.py sample_test_errors.txt --limit 1 --model haiku
```

## Quick Checklist

Before running the fixer:

- [ ] Error file has lines like `File "/app/tests/test_*.py"`
- [ ] Error file has lines like `in test_something`
- [ ] Errors are separated by `====...====`
- [ ] Running `grep "in test_" errors.txt` shows results
- [ ] Each error block has a test file and method name

If any are missing, regenerate your error file using the methods above.

## Still Having Issues?

1. **Check if tests actually fail:**
   ```bash
   python3 -m pytest tests/ -v
   ```

2. **Manually create error file:**
   Copy-paste actual test failure output into a file

3. **Use sample file:**
   ```bash
   python3 fix_test_errors.py sample_test_errors.txt --model haiku
   ```

4. **Check parsing:**
   The script should show "Found N unique test errors" not "Found 0"
