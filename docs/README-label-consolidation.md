# Gmail Label Consolidation

A Python tool that connects to Gmail via IMAP and intelligently consolidates potentially thousands of labels down to a manageable number of categories (default: 25).

## Features

- **Smart Deduplication**: Automatically identifies and groups similar labels (e.g., "Announcement", "announcements", "announcement.")
- **Semantic Grouping**: Groups related labels even with different names (e.g., "Fox News", "CNN News" → "news")
- **Configurable Consolidation**: Set your desired maximum number of categories
- **Multiple Output Formats**: Text report, JSON, or CSV
- **Dry-Run Mode**: Test with sample data without Gmail connection
- **Table-Driven Tests**: Comprehensive test suite with predefined scenarios

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Make the script executable
chmod +x gmail_label_fetcher.py
```

## Usage

### Basic Usage

```bash
# With environment variables
export GMAIL_EMAIL="your-email@gmail.com"
export GMAIL_PASSWORD="your-app-password"
python gmail_label_fetcher.py

# With command-line arguments
python gmail_label_fetcher.py --email your-email@gmail.com --max-categories 20
```

### Dry-Run Mode (Testing)

```bash
# Test with sample data
python gmail_label_fetcher.py --dry-run --max-categories 10

# Verbose output with statistics
python gmail_label_fetcher.py --dry-run --max-categories 10 --verbose
```

### Output Formats

```bash
# Default text report
python gmail_label_fetcher.py --dry-run

# JSON output
python gmail_label_fetcher.py --dry-run --output json --output-file results.json

# CSV mapping
python gmail_label_fetcher.py --dry-run --output csv --output-file mapping.csv
```

## Command-Line Options

- `--email, -e`: Gmail email address (or use GMAIL_EMAIL env var)
- `--max-categories, -m`: Maximum number of consolidated categories (default: 25)
- `--similarity-threshold, -s`: Similarity threshold for grouping (0.0-1.0, default: 0.8)
- `--output, -o`: Output format: text, json, or csv (default: text)
- `--output-file, -f`: Save output to file instead of printing
- `--verbose, -v`: Enable verbose logging with statistics
- `--dry-run`: Test with sample data without Gmail connection

## Gmail Setup

1. **Enable IMAP in Gmail**:
   - Go to Gmail Settings → Forwarding and POP/IMAP
   - Enable IMAP access

2. **Generate App-Specific Password**:
   - Enable 2-factor authentication
   - Go to https://myaccount.google.com/apppasswords
   - Generate a password for "Mail"
   - Use this as your GMAIL_PASSWORD

## How It Works

### Phase 1: Label Normalization & Deduplication
- Converts labels to lowercase
- Removes trailing punctuation and special characters
- Groups exact matches after normalization
- Uses string similarity metrics (Levenshtein, Jaccard n-grams)

### Phase 2: Semantic Consolidation
- Groups similar labels using hierarchical clustering
- Considers conceptual relationships between labels
- Automatically merges related categories

### Phase 3: Force Consolidation
- If still over the limit, creates an "other" category
- Preserves the largest/most important groups
- Ensures the final count meets your requirement

## Example Output

```
============================================================
GMAIL LABEL CONSOLIDATION REPORT
============================================================
Original labels: 45
Consolidated categories: 10
Reduction: 77.8%
Consolidation ratio: 0.22

CONSOLIDATED GROUPS:
------------------------------------------------------------

1. WORK (8 labels)
   - Office
   - Work
   - Work Stuff
   - Work-
   - work
   - work-
   - work-related
   - workplace

2. PERSONAL (6 labels)
   - Personal
   - Personal stuff
   - personal
   - personal-emails
   - personal-items
   - personal_notes

3. NEWS (5 labels)
   - BBC News
   - CNN News
   - Daily News
   - Fox News
   - News
```

## Running Tests

```bash
# Run all tests
python -m unittest test_label_consolidation -v

# Run specific test class
python -m unittest test_label_consolidation.TestLabelConsolidation

# Run with coverage (requires coverage.py)
coverage run -m unittest test_label_consolidation
coverage report
```

## Architecture

### Core Components

1. **`label_consolidation/models.py`**
   - Pydantic models for type safety
   - Configuration and result structures

2. **`label_consolidation/label_consolidation_service.py`**
   - Core consolidation algorithms
   - String similarity calculations
   - Hierarchical clustering implementation

3. **`gmail_label_fetcher.py`**
   - Gmail IMAP integration
   - Command-line interface
   - Output formatting

4. **`test_label_consolidation.py`**
   - Table-driven test cases
   - Performance tests
   - Edge case handling

## Configuration

### ConsolidationConfig Options

```python
config = ConsolidationConfig(
    max_categories=25,              # Maximum final categories
    similarity_threshold=0.8,       # String similarity threshold (0-1)
    normalization_aggressive=True,  # Remove all special characters
    clustering_method="hierarchical" # Clustering algorithm
)
```

## Performance

- Handles 1000+ labels efficiently
- Completes consolidation in seconds
- Memory-efficient processing
- Scalable to large label sets

## Troubleshooting

### IMAP Connection Issues
- Ensure IMAP is enabled in Gmail settings
- Use app-specific password, not regular password
- Check firewall/network settings for port 993

### No Labels Found
- Some Gmail accounts show labels as folders
- System labels are filtered out (e.g., [Gmail]/Spam)
- Nested labels are flattened (Parent/Child → Child)

### Unexpected Grouping
- Adjust similarity_threshold for stricter/looser matching
- Review normalization settings
- Check verbose output for similarity scores

## Future Enhancements

- Gmail API support (alternative to IMAP)
- Content-based consolidation using email samples
- Machine learning model training
- Web interface
- Multi-language support
- Batch processing for multiple accounts