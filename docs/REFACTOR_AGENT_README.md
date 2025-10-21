# Class Refactoring Agent System

An intelligent Python script that uses Claude Code agents to automatically refactor large classes by extracting oversized functions into dedicated service classes.

## Overview

This tool orchestrates multiple AI agents to:

1. **Analyze** your Python class to identify its primary function
2. **Extract** large functions (>30 lines) into dedicated service classes
3. **Validate** the extracted code through comprehensive post-hooks
4. **Test** that all extracted services have passing unit tests
5. **Iterate** intelligently, detecting and avoiding repeated failures

## Features

### Multi-Agent Architecture

- **PrimaryFunctionIdentifierAgent**: Analyzes class structure to identify the core function
- **ExtractorAgent**: Extracts functions into properly structured service classes
- **Automated Validators**: Post-hook validation system ensuring code quality

### Intelligent Validation

The system enforces strict code quality rules:

1. **No Direct Environment Variable Access**
   - All configuration must be passed as function parameters
   - Prevents tight coupling to environment

2. **No External Client Instantiation**
   - HTTP clients, database clients, etc. must be injected via constructor
   - Enforces dependency injection pattern

3. **Function Line Limits**
   - All functions must not exceed 30 lines (configurable)
   - Encourages single responsibility principle

4. **Unit Test Coverage**
   - Every service class must have a test file
   - Tests must pass before extraction is considered successful

### Smart Failure Handling

- **Retry Logic**: Up to 5 attempts per function extraction
- **Failure Context**: Each retry includes details of previous failures
- **Duplicate Detection**: Detects when agent repeats the same implementation
- **Graceful Degradation**: Skips functions with repeated failures rather than infinite loops

## Installation

### Prerequisites

```bash
# Python 3.9+
python --version

# Install dependencies
pip install claude-agent-sdk rich python-dotenv nest-asyncio pytest
```

### Environment Setup

Create a `.env` file with your Anthropic API key:

```bash
ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

### Basic Usage

```bash
python refactor_class_agent.py path/to/your/class.py
```

### With Custom Line Limit

```bash
python refactor_class_agent.py path/to/your/class.py --max-lines 50
```

### Example

Given a file `services/account_email_processor_service.py`:

```bash
python refactor_class_agent.py services/account_email_processor_service.py
```

The script will:

1. Analyze all functions in the class
2. Display a table of functions with line counts
3. Identify the primary function (e.g., `process_emails` for `AccountEmailProcessorService`)
4. Extract each large function into its own service class
5. Create unit tests for each extracted service
6. Validate all code quality requirements
7. Display a summary of successful and failed extractions

## Output Structure

For each extracted function, the script creates:

```
services/
  └── <classname>_<functionname>_service.py  # The extracted service class

tests/
  └── test_<classname>_<functionname>_service.py  # Unit tests
```

### Example Output

```
services/
  └── accountemailprocessor_validate_email_service.py
  └── accountemailprocessor_send_notification_service.py

tests/
  └── test_accountemailprocessor_validate_email_service.py
  └── test_accountemailprocessor_send_notification_service.py
```

## Service Class Pattern

Each extracted service follows this pattern:

```python
from typing import Protocol

# Define interfaces for dependencies
class EmailClientProtocol(Protocol):
    def send(self, message: str) -> bool: ...

class AccountEmailProcessorValidateEmailService:
    """Service for validating email addresses"""

    def __init__(self, email_client: EmailClientProtocol, config: dict):
        """
        Args:
            email_client: Injected email client interface
            config: Configuration dict (not from env vars directly)
        """
        self.email_client = email_client
        self.config = config

    def validate_email(self, email: str) -> bool:
        """
        Validate an email address

        Args:
            email: Email address to validate

        Returns:
            True if valid, False otherwise
        """
        # Implementation here (max 30 lines)
        pass
```

## How It Works

### Phase 1: Analysis

1. Parses the Python file using AST
2. Extracts all non-dunder methods from the main class
3. Counts non-empty, non-comment lines per function
4. Displays analysis table to user

### Phase 2: Primary Function Identification

1. Invokes `PrimaryFunctionIdentifierAgent`
2. Agent analyzes class name and function names
3. Returns the name of the primary/core function
4. Marks this function to be handled last

### Phase 3: Function Extraction

For each function with >30 lines (excluding primary):

1. **Invokes ExtractorAgent** with:
   - Function name and context
   - Previous failure reasons (if any)
   - Strict requirements

2. **Agent Creates**:
   - Service class file
   - Unit test file

3. **Validates**:
   - No env var access
   - No client instantiation
   - All functions <30 lines
   - Unit tests exist and pass

4. **Retries** if validation fails:
   - Provides specific failure reasons
   - Tracks code hash to detect duplicates
   - Skips after repeated failures

### Phase 4: Primary Function

If the primary function exceeds 30 lines:
- Apply same extraction process
- This ensures core functionality is also refactored

### Phase 5: Summary

Displays comprehensive summary:
- Total functions analyzed
- Successfully extracted
- Failed extractions
- Total attempts made

## Advanced Configuration

### Customizing Validators

Edit `Validators` class in `refactor_class_agent.py`:

```python
class Validators:
    @staticmethod
    def validate_custom_rule(file_path: Path) -> Tuple[bool, str]:
        """Add your custom validation logic"""
        # Implementation
        pass
```

Then add to `run_validators`:

```python
results['custom'] = Validators.validate_custom_rule(service_file)
```

### Adjusting Agent Prompts

Modify agent definitions in `RefactoringOrchestrator.__init__`:

```python
agents={
    "extractor": AgentDefinition(
        description="...",
        prompt="Your custom instructions here...",
        model="sonnet",
        tools=[...]
    )
}
```

### Changing Retry Logic

Modify `max_retries` in `extract_function`:

```python
async def extract_function(self, func_info: FunctionInfo) -> bool:
    max_retries = 10  # Increase retries
    # ...
```

## Troubleshooting

### "No class found in file"

Ensure your file contains at least one class definition:

```python
class MyClass:
    def my_method(self):
        pass
```

### "Failed to identify primary function"

The agent couldn't determine the primary function. This might happen if:
- Function names don't relate to class name
- Class has no clear primary purpose

Manually specify in code or rename functions to be clearer.

### "Tests failed"

The generated tests didn't pass. Common causes:
- Missing test dependencies
- Incorrect test file location
- Agent generated incomplete tests

Check `tests/test_*.py` and fix manually, or retry.

### "External clients instantiated"

The validator detected client creation in methods. Example violation:

```python
def process(self):
    client = HTTPClient()  # ❌ Should be injected
    client.get("https://api.example.com")
```

Should be:

```python
def __init__(self, http_client: HTTPClientProtocol):
    self.http_client = http_client

def process(self):
    self.http_client.get("https://api.example.com")  # ✅
```

### "Repeating failures detected"

The agent produced the same flawed code multiple times. This indicates:
- Requirements might be conflicting
- Function is too complex to auto-extract
- Agent needs clearer instructions

Manual intervention required.

## Best Practices

### Before Running

1. **Commit your code** - The script will modify files
2. **Review the class** - Ensure it's suitable for refactoring
3. **Check dependencies** - Make sure all imports are available

### After Running

1. **Review generated code** - While validated, manual review is recommended
2. **Run full test suite** - Ensure nothing broke
3. **Check imports** - Verify all necessary imports were included
4. **Update original class** - May need to update to use new services

### When to Use

Ideal for:
- Large service classes with multiple responsibilities
- Classes with functions exceeding 30-50 lines
- Codebases needing better separation of concerns

Not ideal for:
- Simple classes with a few small methods
- Classes with tightly coupled logic
- Generated code or third-party libraries

## Architecture Details

### Data Structures

```python
@dataclass
class FunctionInfo:
    """Metadata about a function"""
    name: str
    line_count: int
    start_line: int
    end_line: int
    is_primary: bool = False

@dataclass
class ExtractionAttempt:
    """Record of an extraction attempt"""
    timestamp: datetime
    function_name: str
    success: bool
    failure_reasons: List[str]
    code_hash: Optional[str]

@dataclass
class RefactoringState:
    """Overall refactoring session state"""
    source_file: Path
    class_name: str
    primary_function: Optional[str]
    functions_to_extract: List[FunctionInfo]
    extracted_functions: Set[str]
    failed_functions: Dict[str, List[ExtractionAttempt]]
```

### Agent Flow

```
┌─────────────────────────────────────────┐
│  Initialize: Parse file, extract        │
│  function metadata                       │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  PrimaryFunctionIdentifierAgent:         │
│  Identify core function                  │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  For each non-primary function >30 lines │
│  ┌───────────────────────────┐          │
│  │ ExtractorAgent: Extract   │          │
│  │ into service class        │          │
│  └───────────┬───────────────┘          │
│              │                            │
│              ▼                            │
│  ┌───────────────────────────┐          │
│  │ Run Validators:           │          │
│  │ - No env vars             │          │
│  │ - No client instantiation │          │
│  │ - Function length         │          │
│  │ - Unit tests pass         │          │
│  └───────────┬───────────────┘          │
│              │                            │
│              ▼                            │
│         ┌────────┐                       │
│         │ Pass?  │──No──► Retry (max 5)  │
│         └───┬────┘                       │
│             │ Yes                         │
│             ▼                            │
│         Success                          │
└─────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  If primary function >30 lines:          │
│  Extract using same process              │
└─────────────────────────────────────────┘
```

## Contributing

To extend this script:

1. **Add new validators** - Create methods in `Validators` class
2. **Add new agents** - Define in `AgentDefinition`
3. **Customize extraction logic** - Modify `RefactoringOrchestrator`
4. **Improve AST analysis** - Enhance `FileAnalyzer`

## License

This script is part of the Cat-Emails project.

## Support

For issues or questions:
1. Check this README
2. Review the inline code documentation
3. Examine the example files in `tmp/claude-agent-sdk-intro/`
4. Open an issue in the project repository
