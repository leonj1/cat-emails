# Test Fixer - Setup and Usage Checklist

Use this checklist to get started quickly!

## 📋 Setup Checklist

- [ ] **Install Python packages**
  ```bash
  pip install claude-agent-sdk rich python-dotenv
  ```

- [ ] **Set up authentication** (choose one):
  - [ ] Option A: Create `.env` with `ANTHROPIC_API_KEY=your-key`
  - [ ] Option B: Run `claude-code auth`

- [ ] **Verify installation**
  ```bash
  python3 fix_test_errors.py --help
  ```

## 🔧 First Time Usage

- [ ] **Run your tests and save output**
  ```bash
  python -m pytest tests/ -v 2>&1 > pytest_output.txt
  ```

- [ ] **Extract errors to file**
  ```bash
  python3 extract_test_errors.py pytest_output.txt > errors.txt
  ```
  Or use pipe:
  ```bash
  python -m pytest tests/ -v 2>&1 | python3 extract_test_errors.py > errors.txt
  ```

- [ ] **Verify errors were extracted**
  ```bash
  cat errors.txt
  # Should see tracebacks separated by ====...====
  ```

- [ ] **Test with ONE error first**
  ```bash
  python3 fix_test_errors.py errors.txt --limit 1 --model haiku
  ```

- [ ] **Review what the agent did**
  ```bash
  git diff tests/
  ```

- [ ] **Run the fixed test**
  ```bash
  # Use the pytest command from the agent's output
  python -m pytest tests/test_example.py::test_method -v
  ```

## 🚀 Production Usage

- [ ] **Fix all errors** (after successful test)
  ```bash
  python3 fix_test_errors.py errors.txt --model sonnet
  ```

- [ ] **Review all changes**
  ```bash
  git diff tests/
  ```

- [ ] **Run full test suite**
  ```bash
  python -m pytest tests/ -v
  ```

- [ ] **Check for new failures**
  - [ ] If tests pass → Continue to commit
  - [ ] If tests fail → Review agent's changes, may need manual fixes

- [ ] **Commit working changes**
  ```bash
  git add tests/
  git commit -m "fix: resolve test errors with Claude Code Agent"
  ```

## 📊 After Running

- [ ] Review the statistics table
- [ ] Note which errors were fixed vs failed
- [ ] For failed errors, review the output to understand why
- [ ] Consider using `--model opus` for remaining hard errors

## 🐛 Troubleshooting Checklist

### If agent isn't fixing errors:

- [ ] Check that error file has proper format (tracebacks separated by `====...====`)
- [ ] Verify test file paths are correct
- [ ] Try with `--model sonnet` or `--model opus`
- [ ] Review agent output for clues

### If tests still fail after fix:

- [ ] Agent fixes **test code**, not source code
- [ ] Check if source code has actual bugs
- [ ] Review the changes the agent made
- [ ] May need manual adjustment
- [ ] Try with more capable model (`--model opus`)

### If getting errors:

- [ ] `ModuleNotFoundError` → Run `pip install claude-agent-sdk rich python-dotenv`
- [ ] `API authentication error` → Set up `.env` or run `claude-code auth`
- [ ] `File not found` → Verify error file path is correct
- [ ] `No errors found` → Check error file format

## 📝 Quick Reference Commands

```bash
# Extract errors from test run
python -m pytest tests/ -v 2>&1 | python3 extract_test_errors.py > errors.txt

# Test with 1 error
python3 fix_test_errors.py errors.txt --limit 1 --model haiku

# Fix all errors (recommended)
python3 fix_test_errors.py errors.txt --model sonnet

# Review changes
git diff tests/

# Run all tests
python -m pytest tests/ -v

# View help
python3 fix_test_errors.py --help
```

## ✅ Success Indicators

You'll know it's working when:

- ✅ Agent reads test files and source code
- ✅ Agent makes edits to test files
- ✅ Agent runs `pytest` commands
- ✅ You see "1 passed" in the output
- ✅ Status shows "✓ Successfully fixed: ..."
- ✅ Tests pass when you run them manually

## 📖 Documentation

- **Quick Start**: `QUICKSTART_TEST_FIXER.md`
- **Full Documentation**: `FIX_TEST_ERRORS_README.md`
- **Project Overview**: `TEST_FIXER_SUMMARY.md`
- **This Checklist**: `TEST_FIXER_CHECKLIST.md`

## 💡 Tips

1. ⭐ Always test with `--limit 1` first
2. ⭐ Use `--model sonnet` for best balance
3. ⭐ Review changes before committing
4. ⭐ Run full test suite after fixing
5. ⭐ Keep backup of working tests

## 🎯 Expected Workflow

```
Run tests → Extract errors → Test with 1 error →
Review → Fix all errors → Review all changes →
Run full suite → Commit
```

Total time: 10-20 minutes for 5-10 errors with Sonnet model

---

**Ready to start?** Begin with the Setup Checklist! ✨
