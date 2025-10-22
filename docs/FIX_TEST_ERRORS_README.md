# Test Error Fixer - Claude Code Agent

Automatically fix Python unit test errors using Claude Code Agent SDK.

## Overview

This script uses a specialized Claude Code agent named `TestFixerAgent` to automatically analyze and fix Python unit test errors. The agent:

1. Reads error tracebacks from a file
2. Analyzes each error to understand the root cause
3. Reads the test file and related source code
4. Fixes the test to match the actual implementation
5. Runs the specific test to validate the fix
6. Retries if the test still fails

## Installation

### Prerequisites

1. **Python 3.11+** installed
2. **Claude Code Agent SDK** installed:
   ```bash
   pip install claude-agent-sdk
   ```

3. **Required Python packages**:
   ```bash
   pip install rich python-dotenv
   ```

4. **Anthropic API Key** (Optional):
   - Either set `ANTHROPIC_API_KEY` in `.env` file
   - Or authenticate with Claude Code CLI

### Install Dependencies

```bash
# Install all required packages
pip install claude-agent-sdk rich python-dotenv

# Or if you have requirements.txt
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python fix_test_errors.py errors.txt
```

### With Options

```bash
# Use a specific model
python fix_test_errors.py errors.txt --model sonnet

# Limit number of errors to fix (for testing)
python fix_test_errors.py errors.txt --limit 5

# Use faster/cheaper Haiku model
python fix_test_errors.py errors.txt --model haiku

# Use most capable Opus model
python fix_test_errors.py errors.txt --model opus
```

### Command-Line Arguments

```
positional arguments:
  error_file            Path to file containing test errors

options:
  -h, --help            Show help message
  --model {haiku,sonnet,opus}
                        Claude model to use (default: sonnet)
  --max-retries N       Maximum retry attempts per test (default: 2)
  --limit N             Limit number of errors to fix (for testing)
```

## Error File Format

The error file should contain Python test error tracebacks separated by lines of equal signs:

```
Traceback (most recent call last):
  File "/app/tests/test_example.py", line 42, in test_something
    result = self.service.some_method()
AttributeError: 'Service' object has no attribute 'some_method'

================================================================================

Traceback (most recent call last):
  File "/app/tests/test_another.py", line 15, in test_another_thing
    self.assertEqual(result, expected)
TypeError: missing 1 required positional argument: 'param'

================================================================================
```

### Generating Error File

You can generate this file from pytest output:

```bash
# Run tests and capture errors
python -m pytest tests/ -v 2>&1 | grep -A 20 "Traceback" > errors.txt

# Or use the extract_errors.py script if available
python extract_errors.py > errors.txt
```

## How It Works

### Agent Architecture

The script uses a **TestFixerAgent** subagent with the following capabilities:

**Tools Available:**
- `Read` - Read test files and source code
- `Write` - Create new files if needed
- `Edit` - Modify test files
- `MultiEdit` - Make multiple edits efficiently
- `Grep` - Search codebase for patterns
- `Glob` - Find files by pattern
- `Bash` - Run pytest commands to validate fixes
- `TodoWrite` - Track multi-step fixes

**Agent Behavior:**
1. **Analysis**: Reads error traceback to identify the issue
2. **Investigation**: Reads test file and related source code
3. **Fix**: Modifies test code to match actual implementation
4. **Validation**: Runs the specific test using pytest
5. **Retry**: If test still fails, analyzes new error and tries again

### Error Parsing

The script automatically extracts:
- Test file path
- Test method name
- Error type (AttributeError, TypeError, etc.)
- Line numbers
- Generates pytest command to run specific test

### Deduplication

The script automatically deduplicates identical errors, so if the same test appears multiple times in the error file, it will only be fixed once.

## Examples

### Example 1: Fix All Errors in File

```bash
python fix_test_errors.py errors.txt
```

Output:
```
Reading error file: errors.txt
Found 8 unique test errors

╭─────────────────────────────────────╮
│        🚀 Test Fixer                │
│  Starting test error fixing process │
│  Total unique errors to fix: 8      │
╰─────────────────────────────────────╯

Progress: 1/8
╭─────────────────────────────────────╮
│      🔧 Test Fixer Agent            │
│  Fixing: tests/test_example.py::   │
│         test_create_account         │
│  Error: AttributeError              │
╰─────────────────────────────────────╯

✓ Successfully fixed: tests/test_example.py::test_create_account

...

╭────────────────────────────╮
│   Final Statistics         │
├────────────┬──────────────┤
│ Metric     │        Count │
├────────────┼──────────────┤
│ Total      │            8 │
│ Fixed      │            6 │
│ Failed     │            2 │
│ Skipped    │            0 │
│ Success    │        75.0% │
╰────────────┴──────────────╯
```

### Example 2: Test with Limited Errors

```bash
# Fix only the first 3 errors
python fix_test_errors.py errors.txt --limit 3
```

### Example 3: Use Different Models

```bash
# Fast and cheap (good for simple errors)
python fix_test_errors.py errors.txt --model haiku

# Balanced (recommended for most cases)
python fix_test_errors.py errors.txt --model sonnet

# Most capable (for complex errors)
python fix_test_errors.py errors.txt --model opus
```

## Exit Codes

- `0` - All errors fixed successfully
- `1` - Some errors could not be fixed

## Troubleshooting

### Common Issues

**Issue: Agent not making changes**
- Check that `permission_mode="acceptEdits"` is set
- Verify the test file path is correct
- Ensure the agent has `Edit` tool permission

**Issue: Tests still failing after fix**
- Agent will retry automatically (up to `max_retries`)
- Check if the source code has bugs (agent fixes tests, not source)
- Review the agent's output for insights

**Issue: Import errors or SDK not found**
- Install: `pip install claude-agent-sdk rich python-dotenv`
- Activate your virtual environment if using one

**Issue: API authentication errors**
- Set `ANTHROPIC_API_KEY` in `.env` file
- Or authenticate with: `claude-code auth`

### Debug Mode

To see more detailed output from the agent:

```python
# Modify the script to print raw messages
# In the fix_error method, add:
async for message in client.receive_response():
    print(message)  # Add this line for debugging
```

## Advanced Usage

### Programmatic Usage

You can also use the components programmatically:

```python
from fix_test_errors import ErrorFileParser, TestFixerAgent
import asyncio

async def fix_my_tests():
    # Parse errors
    errors = ErrorFileParser.parse_error_file("errors.txt")

    # Create fixer
    fixer = TestFixerAgent(model="sonnet")

    # Fix all errors
    stats = await fixer.fix_all_errors(errors)

    print(f"Fixed {stats['fixed']} out of {stats['total']} errors")

asyncio.run(fix_my_tests())
```

### Custom Agent Configuration

You can modify the `TestFixerAgent` definition in the script to:
- Change the system prompt
- Add/remove tools
- Adjust the model
- Customize the workflow

## Best Practices

1. **Review Changes**: After the agent fixes tests, review the changes to ensure they're correct
2. **Run All Tests**: After fixing, run the full test suite to ensure no regressions
3. **Version Control**: Commit working tests before running the fixer
4. **Start Small**: Use `--limit` to test on a few errors first
5. **Choose Right Model**:
   - Haiku: Simple errors, fast, cheap
   - Sonnet: Most cases, balanced
   - Opus: Complex errors, slower, more expensive

## Performance

- **Haiku**: ~30 seconds per error, $0.01-0.05 per error
- **Sonnet**: ~60 seconds per error, $0.05-0.15 per error
- **Opus**: ~90 seconds per error, $0.15-0.50 per error

(Times and costs are approximate and vary by error complexity)

## Limitations

- Only fixes **test code**, not source code
- Works best with clear error messages
- Cannot fix environmental/setup issues
- Requires valid Python syntax in test files
- May need human review for complex fixes

## Contributing

To improve the agent:

1. Modify the agent prompt in `_create_agent_options()`
2. Add more tools if needed
3. Adjust validation logic in `fix_error()`
4. Add more error parsing logic in `TestError._parse_error()`

## License

Same as the parent project.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review Claude Code Agent SDK docs: https://docs.claude.com/en/api/agent-sdk/python
3. Open an issue in the project repository
