# DataConverter

A professional CLI tool for converting data between JSON, YAML, TOML, and XML formats with powerful query and filtering capabilities.

## Features

- 🔄 **Multi-Format Support**: Convert between JSON, YAML, TOML, and XML
- 🎯 **Interactive CLI**: SQL-like query interface with live REPL
- 🔍 **JSONPath Queries**: Extract specific data using path expressions
- ⚡ **Conditional Filtering**: Filter data with WHERE clauses
- ✅ **Format Validation**: Built-in validators for each format
- 🛡️ **Type Safety**: Full mypy type checking support
- 🧪 **Comprehensive Testing**: Complete test suite included

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd DataConverter

# Install dependencies
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Quick Start

### Interactive Mode

Launch the interactive CLI:

```bash
python main.py
```

### Basic Conversion

```
DataConv> from data.json to output.yaml
[+] Loaded from: data.json
[+] Saved to: output.yaml
```

### With JSONPath

```
DataConv> from users.json[$.users[*].name] to names.yaml
```

### With Filtering

```
DataConv> from products.json to sale_items.yaml where price < 50
```

## CLI Commands

### Data Operations

- **`load <file>`** - Load data from a file
- **`save <file>`** - Save current data to a file
- **`convert to <file> [where <conditions>]`** - Convert with optional filtering

### Query Syntax

```
from <source_file>[path_expression] to <dest_file> [where conditions]
```

**Examples:**
```
from input.json to output.yaml
from data.json[$.users[*]] to users.toml
from items.yaml to cheap.json where price < 100
from users.json to active.yaml where status == "active"
```

### Helper Commands

- **`show [path]`** - Display loaded data or specific path
- **`status`** - Show current session state
- **`validate`** - Run format validation on loaded data
- **`help`** - Display all available commands
- **`clear`** - Clear the screen
- **`exit`** - Quit the application

## Query Language

### Path Expressions

Uses JSONPath syntax for data extraction:

```
$.users[*]           # All users
$.users[0]           # First user
$.users[*].name      # All user names
$..email             # All email fields (recursive)
```

### Condition Operators

- `==` - Equal to
- `!=` - Not equal to
- `<` - Less than
- `>` - Greater than
- `<=` - Less than or equal
- `>=` - Greater than or equal

### Condition Examples

```
where price < 50
where status == "active"
where age >= 18 and score > 75
```

## Supported Formats

| Format | Extension | Read | Write | Validation |
|--------|-----------|------|-------|------------|
| JSON   | `.json`   | ✅   | ✅    | ✅         |
| YAML   | `.yaml`, `.yml` | ✅ | ✅  | ✅         |
| TOML   | `.toml`   | ✅   | ✅    | ✅         |
| XML    | `.xml`    | ✅   | ✅    | ✅         |

## Project Structure

```
DataConverter/
├── main.py                 # Entry point
├── pyproject.toml          # Project configuration
├── src/
│   ├── __init__.py        # Public API exports
│   ├── cli.py             # Interactive CLI implementation
│   ├── grammar.py         # Query language grammar
│   ├── io.py              # File I/O operations
│   ├── parser.py          # Query parser
│   ├── processor.py       # Data processing and filtering
│   └── validation.py      # Format validators
└── test/
    ├── cli_test.py        # CLI tests
    ├── grammar_test.py    # Grammar tests
    ├── io_test.py         # I/O tests
    ├── parser_test.py     # Parser tests
    ├── processor_test.py  # Processor tests
    └── validation_test.py # Validation tests
```

## Development

### Running Tests

```bash
# Run all tests
pytest test/

# Run specific test file
pytest test/cli_test.py

# Run with coverage
pytest --cov=src test/
```

### Code Quality

```bash
# Format code
black src/ test/

# Lint code
ruff check src/ test/

# Type checking
mypy src/
```

### Requirements

- Python 3.10+
- Dependencies listed in `pyproject.toml`

## Usage Examples

### Example 1: Convert JSON to YAML

```python
# data.json
{
  "users": [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25}
  ]
}
```

```
DataConv> from data.json to users.yaml
[+] Loaded from: data.json
[+] Saved to: users.yaml
```

### Example 2: Extract Specific Fields

```
DataConv> from data.json[$.users[*].name] to names.toml
```

Output:
```toml
names = ["Alice", "Bob"]
```

### Example 3: Filter Data

```
DataConv> from products.json to cheap.yaml where price < 100
```

### Example 4: Validate Before Conversion

```
DataConv> load data.json
[+] Loaded from: data.json

DataConv> validate
[+] Validation passed - no issues found

DataConv> save output.yaml
[+] Saved to: output.yaml
```

## Error Handling

The tool provides clear, color-coded error messages:

- 🟢 **Green** - Success messages
- 🔴 **Red** - Error messages
- 🟡 **Yellow** - Warnings
- 🔵 **Blue** - Information

## API Usage

You can also use DataConverter as a library:

```python
from src.io import smart_load, smart_save
from src.parser import QueryParser
from src.processor import process_data

# Load data
data = smart_load(Path("input.json"))

# Parse query
parser = QueryParser()
query = parser.parse("from input.json to output.yaml where status == 'active'")

# Process data
result = process_data(data, query.path, query.conditions)

# Save result
smart_save(result, Path("output.yaml"))
```

## Version

Current version: **0.1.0**

## License

MIT License

## Contributing

Contributions are welcome! Please ensure:
1. All tests pass (`pytest test/`)
2. Code is formatted (`black src/ test/`)
3. Type checking passes (`mypy src/`)
4. Linting passes (`ruff check src/ test/`)

## Roadmap

- [ ] CSV format support
- [ ] Batch conversion
- [ ] Configuration file support
- [ ] Plugin system for custom formats
- [ ] Advanced filtering with regex
- [ ] Output formatting options

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

Made with ❤️ by thaisya
