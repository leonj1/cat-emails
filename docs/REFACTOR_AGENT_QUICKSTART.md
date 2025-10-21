# Quick Start Guide: Class Refactoring Agent

## 5-Minute Setup

### 1. Install Dependencies

```bash
pip install -r refactor_agent_requirements.txt
```

### 2. Set Up Environment

Create a `.env` file (or add to existing):

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 3. Run the Example

Test the agent with the provided example file:

```bash
python refactor_class_agent.py example_large_class.py
```

## What Will Happen

The script will:

1. **Analyze** `example_large_class.py` and identify `UserDataProcessor` class
2. **Identify** `process_user_data` as the primary function
3. **Extract** these large functions into service classes:
   - `fetch_user_from_api` → `UserDataProcessorFetchUserFromApiService`
   - `validate_user_data` → `UserDataProcessorValidateUserDataService`
   - `enrich_user_data` → `UserDataProcessorEnrichUserDataService`
   - `store_user_data` → `UserDataProcessorStoreUserDataService`
   - `send_notification` → `UserDataProcessorSendNotificationService`
   - `generate_user_report` → `UserDataProcessorGenerateUserReportService`

4. **Create** service files in `services/` directory
5. **Create** test files in `tests/` directory
6. **Validate** that each service:
   - Has no direct env var access
   - Has no external client instantiation
   - Has all functions under 30 lines
   - Has passing unit tests

## Expected Output

```
╭─────────────────────────────────────────╮
│ Class Refactoring Agent System          │
│ File: example_large_class.py            │
│ Max lines per function: 30               │
╰─────────────────────────────────────────╯

╭─────────────────────────────────────────╮
│ Analyzing example_large_class.py...     │
╰─────────────────────────────────────────╯

        Functions in UserDataProcessor
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Function Name         ┃ Lines ┃ Range    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ process_user_data     │ 35    │ 26-60   │
│ fetch_user_from_api   │ 45    │ 62-106  │
│ validate_user_data    │ 48    │ 108-155 │
│ enrich_user_data      │ 52    │ 157-208 │
│ store_user_data       │ 46    │ 210-255 │
│ send_notification     │ 38    │ 257-294 │
│ generate_user_report  │ 51    │ 296-346 │
└───────────────────────┴───────┴─────────┘

╭─────────────────────────────────────────╮
│ Step 1: Primary Function Identification │
╰─────────────────────────────────────────╯

✓ Primary function identified: process_user_data

╭─────────────────────────────────────────╮
│ Extraction Plan                          │
│ Found 6 functions to extract (>30 lines)│
╰─────────────────────────────────────────╯

╭─────────────────────────────────────────╮
│ Extraction: fetch_user_from_api         │
╰─────────────────────────────────────────╯

Attempt 1/5
Running validators... ━━━━━━━━━━━━━━━━━━━━
✓ Successfully extracted fetch_user_from_api

... (continues for each function)

       Refactoring Summary
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric                  ┃ Value ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Functions Analyzed│ 7     │
│ Successfully Extracted  │ 7     │
│ Failed Extractions      │ 0     │
│ Total Attempts          │ 7     │
└─────────────────────────┴───────┘

Successfully Extracted:
  ✓ fetch_user_from_api
  ✓ validate_user_data
  ✓ enrich_user_data
  ✓ store_user_data
  ✓ send_notification
  ✓ generate_user_report
  ✓ process_user_data

✓ Refactoring completed successfully!
```

## Using With Your Own Class

Once you've verified it works with the example, use it on your own files:

```bash
# Refactor the account email processor service
python refactor_class_agent.py services/account_email_processor_service.py

# Or any other Python class file
python refactor_class_agent.py path/to/your/class.py
```

## Common Issues

### "ANTHROPIC_API_KEY not found"

Make sure you've created a `.env` file with your API key:

```bash
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

### "ModuleNotFoundError: No module named 'claude_agent_sdk'"

Install dependencies:

```bash
pip install -r refactor_agent_requirements.txt
```

### "No class found in file"

The file must contain at least one class definition:

```python
class MyClass:
    def my_method(self):
        pass
```

## Next Steps

1. **Review the generated services** in `services/` directory
2. **Check the tests** in `tests/` directory
3. **Run tests** to ensure everything works:
   ```bash
   pytest tests/test_*.py -v
   ```
4. **Update your original class** to use the new services
5. **Read the full documentation** in `REFACTOR_AGENT_README.md`

## Understanding the Output

### Service Files

Each extracted function becomes a service class:

```python
# services/userdataprocessor_validate_user_data_service.py

class UserDataProcessorValidateUserDataService:
    def __init__(self, config: dict):
        self.config = config

    def validate_user_data(self, user: dict) -> bool:
        # Extracted implementation
        pass
```

### Test Files

Each service gets comprehensive tests:

```python
# tests/test_userdataprocessor_validate_user_data_service.py

import pytest
from services.userdataprocessor_validate_user_data_service import (
    UserDataProcessorValidateUserDataService
)

def test_validate_user_data_success():
    service = UserDataProcessorValidateUserDataService(config={})
    user = {"id": "123", "email": "test@example.com", "name": "Test"}
    assert service.validate_user_data(user) is True
```

## Tips for Best Results

1. **Start with well-structured classes** - The tool works best when the original code is reasonably organized
2. **Review agent output** - While the tool is powerful, always review the generated code
3. **Commit before running** - The tool modifies files, so commit your work first
4. **Run incrementally** - If you have many large classes, refactor them one at a time

## Getting Help

- **Full documentation**: See `REFACTOR_AGENT_README.md`
- **Code reference**: Check `refactor_class_agent.py` inline comments
- **SDK examples**: Review files in `tmp/claude-agent-sdk-intro/`
- **Troubleshooting**: See the Troubleshooting section in the full README

## What Makes This Different

Traditional refactoring tools:
- Require manual work for each function
- Don't understand context or semantics
- Can't write tests automatically
- Don't validate code quality

This agent system:
- ✅ Automatically identifies what to extract
- ✅ Understands the semantic purpose of functions
- ✅ Generates comprehensive unit tests
- ✅ Validates code quality through multiple hooks
- ✅ Iterates intelligently when validation fails
- ✅ Detects and avoids infinite retry loops

## Performance Notes

- **Time**: Expect 2-5 minutes per function (depending on complexity)
- **API Usage**: Uses Claude Sonnet model, consumes API credits
- **Retries**: Up to 5 attempts per function if validation fails
- **Parallelization**: Processes functions sequentially (not parallel)

## Example Session Transcript

```bash
$ python refactor_class_agent.py example_large_class.py

# Analyzes the file...
# Identifies primary function: process_user_data
# Plans to extract 6 large functions

# For each function:
#   1. Invokes ExtractorAgent
#   2. Agent creates service class
#   3. Agent creates unit test
#   4. Validates (4 checks)
#   5. If any check fails, retries with failure context
#   6. On success, moves to next function

# Finally:
#   - Checks if primary function is still too large
#   - If so, refactors it as well
#   - Displays comprehensive summary
```

## Ready to Start?

```bash
# Make sure you're in the project directory
cd /home/jose/src/cat-emails

# Run the example
python refactor_class_agent.py example_large_class.py

# Watch the magic happen!
```
