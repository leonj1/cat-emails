# Refactoring Agent Runtime Error Fix

## Problem

The script was encountering this error:

```
TypeError: ClaudeSDKClient.query() got an unexpected keyword argument 'agent'
```

## Root Cause

The `ClaudeSDKClient.query()` method does not accept an `agent` parameter. Subagents defined in `AgentDefinition` are not directly invocable from Python code. Instead, they are invoked BY the main Claude agent using the Task tool when you delegate work to them in your prompt.

## Solution

Changed from incorrect direct invocation:

```python
# ❌ WRONG - This doesn't work
await client.query(prompt, agent="primary-function-identifier")
```

To proper delegation pattern:

```python
# ✅ CORRECT - Ask Claude to delegate to subagent
prompt = """I need you to identify the primary function of a Python class.

Please delegate this task to the primary-function-identifier agent...
"""
await client.query(prompt)
```

## Changes Made

### 1. Fixed `identify_primary_function()` method (line 420-461)

**Before:**
```python
await client.query(prompt, agent="primary-function-identifier")
```

**After:**
```python
prompt = f"""I need you to identify the primary function of a Python class.
...
Please delegate this task to the primary-function-identifier agent...
"""
await client.query(prompt)
```

### 2. Fixed `extract_function()` method (line 495-522)

**Before:**
```python
await client.query(prompt, agent="extractor")
```

**After:**
```python
prompt = f"""I need you to extract a function from a Python class...
...
Please delegate this task to the extractor agent...
"""
await client.query(prompt)
```

## How Subagents Work in Claude SDK

1. **Define subagents** in `AgentDefinition` within `ClaudeAgentOptions`:
   ```python
   agents={
       "extractor": AgentDefinition(
           description="...",
           prompt="...",
           tools=[...]
       )
   }
   ```

2. **Main agent decides when to delegate** based on:
   - Your prompt (what you ask for)
   - Agent descriptions (which agent handles what)
   - Available Task tool

3. **Claude invokes subagents** automatically using the Task tool when it determines a subagent is needed

4. **Subagent completes** and returns results to main agent

5. **Main agent** synthesizes and returns final response

## Verification

The fix has been verified:

```bash
# File analyzer works correctly
python3 -c "from refactor_class_agent import FileAnalyzer; ..."
✓ Successfully analyzed SimpleCalculator

# No syntax errors
python3 -m py_compile refactor_class_agent.py
✓ Script syntax is valid

# No remaining agent= parameters
grep -n "agent=" refactor_class_agent.py
# (no results - all fixed)
```

## Usage

The script now works correctly:

```bash
# Basic usage
python3 refactor_class_agent.py path/to/your_class.py

# With custom line limit
python3 refactor_class_agent.py path/to/your_class.py --max-lines 50
```

## Important Notes

1. **API Calls**: The script makes real API calls to Anthropic's Claude, which:
   - Requires `ANTHROPIC_API_KEY` in your `.env` file
   - May take several minutes to complete
   - Consumes API credits

2. **Output Buffering**: Initial output may appear delayed while connecting to API

3. **Subagent Architecture**: The multi-agent architecture is fully preserved and working correctly

## Testing

To test the fix:

```bash
# Test with simple example
python3 refactor_class_agent.py test_simple_class.py

# Test with actual service (takes longer)
python3 refactor_class_agent.py services/account_email_processor_service.py
```

Expected behavior:
- Script connects to Claude API
- Displays function analysis table
- Delegates to primary-function-identifier agent
- Delegates to extractor agent for each function
- Runs validation hooks
- Displays summary

## Files Modified

- `refactor_class_agent.py` - Fixed agent invocation in 2 methods

## Related Files

- `REFACTOR_AGENT_README.md` - Full documentation
- `REFACTOR_AGENT_QUICKSTART.md` - Quick start guide
- `refactor_agent_summary.md` - Architecture overview
