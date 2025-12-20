# Markdown Coding Standards

Standards for writing markdown files and documentation.

## Code Blocks

### Language Identifiers Required

All fenced code blocks **MUST** include a language identifier. This enables syntax highlighting, linting, and proper rendering.

```
// ❌ BAD - No language identifier
```
code here
```

// ✅ GOOD - Language identifier specified
```python
code here
```
```

**Common language identifiers:**

| Language | Identifier |
|----------|------------|
| Python | `python` |
| JavaScript | `javascript` or `js` |
| TypeScript | `typescript` or `ts` |
| Go | `go` |
| Rust | `rust` |
| C# | `csharp` or `cs` |
| Java | `java` |
| SQL | `sql` |
| Bash/Shell | `bash` or `shell` |
| JSON | `json` |
| YAML | `yaml` |
| HTML | `html` |
| CSS | `css` |
| Markdown | `markdown` or `md` |
| Diff | `diff` |
| Plain text | `text` or `plaintext` |

**For mixed or pseudo-code**, use `text` or the dominant language:

```text
// ❌ BAD - Unlabeled pseudo-code
```
if user.isAdmin then allow()
```

// ✅ GOOD - Labeled as text or pseudo-code
```text
if user.isAdmin then allow()
```
```

### Inline Code

Use backticks for inline code references:

- File names: `config.yaml`
- Function names: `getUserById()`
- Variables: `userId`
- Commands: `npm install`
- Values: `true`, `null`, `200`

## List Formatting

### Unordered Lists

- Use `-` for unordered list items (consistent with markdownlint defaults)
- Top-level items start at column 0
- Nested items use 2-space indentation

```markdown
// ❌ BAD - Inconsistent markers and indentation
* Item one
  - Sub-item with wrong indent
   - Another wrong indent

// ✅ GOOD - Consistent markers and indentation
- Item one
  - Sub-item (2-space indent)
  - Another sub-item
- Item two
```

### Ordered Lists

- Use `1.` for all items (auto-numbering)
- Or use sequential numbers `1.`, `2.`, `3.`
- Nested items use 3-space indentation

```markdown
// ✅ GOOD - Auto-numbering
1. First step
1. Second step
1. Third step

// ✅ GOOD - Sequential numbering
1. First step
2. Second step
3. Third step
```

## Headings

### Hierarchy

- Use ATX-style headings (`#`, `##`, `###`)
- Start with `#` for document title
- Don't skip heading levels (e.g., `#` → `###`)
- Leave one blank line before and after headings

```markdown
// ❌ BAD - Skipped heading level
# Title
### Subsection

// ✅ GOOD - Proper hierarchy
# Title
## Section
### Subsection
```

### Heading Style

- Use sentence case for headings: "Code block standards"
- Or title case consistently: "Code Block Standards"
- Don't end headings with punctuation

## Tables

### Alignment

- Use `|` to separate columns
- Include header separator row with `---`
- Align columns for readability in source

```markdown
// ✅ GOOD - Properly formatted table
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |
```

## Links

### Reference Style for Repeated Links

Use reference-style links when the same URL appears multiple times:

```markdown
// ✅ GOOD - Reference-style links
See the [documentation][docs] for more info.
Check the [docs][docs] again.

[docs]: https://example.com/docs
```

### Descriptive Link Text

- Avoid "click here" or "link"
- Use descriptive text that makes sense out of context

```markdown
// ❌ BAD
Click [here](url) for more info.

// ✅ GOOD
See the [API documentation](url) for more info.
```

## File Organization

### Structure

- Start with a level-1 heading (document title)
- Include a brief description after the title
- Use consistent section ordering
- End files with a single newline

### Line Length

- Prefer lines under 120 characters for readability
- Break long lines at natural points (after punctuation, before conjunctions)
- Exception: URLs and code blocks can exceed line length

## Agent Documentation

When writing agent or skill documentation:

- Include frontmatter with `name` and `description`
- Use clear "When to use" and "When NOT to use" sections
- Provide concrete examples with code blocks
- Include expected output format

```markdown
---
name: example-agent
description: Brief description of what this agent does.
---

# Agent Title

## When to Use

- Condition 1
- Condition 2

## Example

```python
example_code()
```
```
