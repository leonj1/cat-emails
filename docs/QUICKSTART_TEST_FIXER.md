# Quick Start Guide - Test Error Fixer

Get started fixing unit test errors with Claude Code Agent in 5 minutes!

## Prerequisites

```bash
# Install required packages
pip install claude-agent-sdk rich python-dotenv
```

## Step 1: Set Up Authentication

Choose one of these options:

**Option A: Use Anthropic API Key**
```bash
# Create .env file
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
```

**Option B: Use Claude Code Auth**
```bash
# Authenticate with Claude Code
claude-code auth
# No need for .env file
```

## Step 2: Collect Test Errors

### Method 1: Automatic Extraction (Recommended)

```bash
# Run tests and extract errors automatically
python -m pytest tests/ -v 2>&1 | python3 extract_test_errors.py > errors.txt
```

### Method 2: Manual Copy-Paste

1. Run your tests:
   ```bash
   python -m pytest tests/ -v
   ```

2. Copy error tracebacks to a file called `errors.txt`

3. Separate errors with a line of equals signs:
   ```
   ================================================================================
   ```

## Step 3: Run the Fixer

### Test with 1 Error First

```bash
# Fix just the first error to test
python3 fix_test_errors.py errors.txt --limit 1 --model haiku
```

### Fix All Errors

```bash
# Fix all errors with recommended model
python3 fix_test_errors.py errors.txt --model sonnet
```

## What to Expect

```
Reading error file: errors.txt
Found 6 unique test errors

╭─────────────────────────────────────╮
│        🚀 Test Fixer                │
│  Starting test error fixing process │
│  Total unique errors to fix: 6      │
╰─────────────────────────────────────╯

Progress: 1/6
╭─────────────────────────────────────╮
│      🔧 Test Fixer Agent            │
│  Fixing: tests/test_example.py::   │
│         test_create_account         │
│  Error: AttributeError              │
╰─────────────────────────────────────╯

[Agent analyzes error, reads files, makes fixes, runs test...]

✓ Successfully fixed: tests/test_example.py::test_create_account

[Continues for all errors...]

╭────────────────────────────╮
│   Final Statistics         │
├────────────┬──────────────┤
│ Total      │            6 │
│ Fixed      │            5 │
│ Failed     │            1 │
│ Skipped    │            0 │
│ Success    │        83.3% │
╰────────────┴──────────────╯
```

## Model Selection Guide

| Model    | Speed  | Cost      | Best For                |
|----------|--------|-----------|-------------------------|
| `haiku`  | Fast   | Cheapest  | Simple errors, testing  |
| `sonnet` | Medium | Moderate  | Most use cases ⭐       |
| `opus`   | Slow   | Expensive | Complex, tricky errors  |

## Common Commands

```bash
# Fix all errors (recommended)
python3 fix_test_errors.py errors.txt --model sonnet

# Test with one error first
python3 fix_test_errors.py errors.txt --limit 1

# Fast/cheap for simple errors
python3 fix_test_errors.py errors.txt --model haiku

# Maximum capability for hard errors
python3 fix_test_errors.py errors.txt --model opus

# Show help
python3 fix_test_errors.py --help
```

## After Running

1. **Review Changes**: Check the git diff to see what was fixed
   ```bash
   git diff tests/
   ```

2. **Run All Tests**: Verify no regressions
   ```bash
   python -m pytest tests/ -v
   ```

3. **Commit**: If everything looks good
   ```bash
   git add tests/
   git commit -m "fix: resolve test errors with Claude Code Agent"
   ```

## Troubleshooting

### "ModuleNotFoundError: No module named 'claude_agent_sdk'"

```bash
pip install claude-agent-sdk
```

### "API authentication error"

```bash
# Set API key in .env
echo "ANTHROPIC_API_KEY=your-key" > .env

# Or use Claude Code auth
claude-code auth
```

### Tests Still Failing

- The agent fixes **test code**, not source code
- Review the agent's changes - they may need adjustment
- Try running with `--model opus` for harder errors
- Some errors may need manual fixing

### No Errors Found in File

```bash
# Check file format
cat errors.txt

# Should have tracebacks separated by ====...====
# Try re-extracting:
python -m pytest tests/ -v 2>&1 | python3 extract_test_errors.py > errors.txt
```

## Files Created

- `fix_test_errors.py` - Main script with Claude Code agent
- `extract_test_errors.py` - Helper to extract errors from pytest
- `FIX_TEST_ERRORS_README.md` - Full documentation
- `QUICKSTART_TEST_FIXER.md` - This guide
- `example_usage.sh` - Example commands

## Next Steps

1. Start with `--limit 1` to test the workflow
2. Increase to more errors once comfortable
3. Review and understand the fixes the agent makes
4. Run full test suite after fixing
5. Commit working changes

## Cost Estimates

Approximate costs per error:

- **Haiku**: $0.01 - $0.05 per error
- **Sonnet**: $0.05 - $0.15 per error
- **Opus**: $0.15 - $0.50 per error

For 10 errors:
- Haiku: ~$0.10 - $0.50
- Sonnet: ~$0.50 - $1.50
- Opus: ~$1.50 - $5.00

Start with Haiku for testing, use Sonnet for production.

## Support

- Full docs: See `FIX_TEST_ERRORS_README.md`
- Claude SDK docs: https://docs.claude.com/en/api/agent-sdk/python
- Test the parser: `python3 test_error_parser.py`

## Tips

1. ✅ **Always start with --limit 1** to test the setup
2. ✅ **Review git diff** after agent finishes
3. ✅ **Run full test suite** before committing
4. ✅ **Use Sonnet** for most cases (best balance)
5. ✅ **Keep errors.txt** for reference

Good luck! 🚀
