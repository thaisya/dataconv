# dataconv

> Professional data format converter with powerful query language and library API

[![Version](https://img.shields.io/badge/version-1.0.3-blue.svg)](https://github.com/thaisya/dataconv)
[![Python](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-226%20passing-success.svg)](./tests)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

dataconv is a versatile tool for converting data between multiple formats (JSON, YAML, TOML, XML, CSV) with advanced filtering, JSONPath extraction, and boolean query capabilities. Use it as a **library** in your Python projects or as an **interactive CLI** tool.

---

## Key Features

- **Multi-Format Support** - JSON, YAML, TOML, XML, CSV with auto-detection
- **Library API** - Clean Pythonic interface for programmatic use  
- **Interactive CLI** - MySQL-style REPL with live command execution
- **JSONPath Queries** - Extract nested data with `$.users[*].name` syntax
- **Boolean Filtering** - Complex WHERE clauses with AND, OR, NOT, XOR operators
- **Type-Safe** - Full mypy compliance with comprehensive type hints
- **Format Validation** - Built-in validators for each format
- **Runtime Configuration** - Customize behavior with options system
- **Battle-Tested** - 226 comprehensive tests, 100% passing
- **Performance** - Fast JSON with orjson (3x speedup), optional C-YAML for 5x boost

---

## Installation

### Choose Your Installation

dataconv offers flexible installation options based on your needs:

#### Library Only

For embedding in your Python projects without the interactive CLI:

```bash
pip install dataconv
```

**Includes**: 
- Core data conversion engine
- Query parser (Lark) 
- JSONPath support (jsonpath-ng)
- All format support (JSON, YAML, TOML, XML, CSV)
- Fast JSON processing (orjson - 3x faster)
- Library API (load, save, convert, query, filter, extract_path)

**Excludes**: Rich (CLI terminal output), interactive REPL  
**Size**: ~7 MB

#### CLI Application (Recommended)

Includes beautiful terminal output for the interactive REPL:

```bash
pip install dataconv[cli]
```

**Includes**: Everything from library + Rich terminal output  
**Use for**: Interactive data conversion, command-line workflows  
**Size**: ~10 MB

#### Full Installation

Complete installation with all extras and development tools:

```bash
pip install dataconv[full]
```

**Includes**: CLI + dev tools (pytest, mypy, black, ruff)  
**Use for**: Development, contributing to the project  
**Size**: ~30 MB

#### From Source

```bash
git clone https://github.com/thaisya/dataconv
cd dataconv

# Library only
pip install -e .

# With CLI
pip install -e ".[cli]"

# Full development setup
pip install -e ".[full]"
```

**Requirements**: Python 3.10+

---

## Quick Start

### As a Library

```python
from dataconv import load, save, convert, query, filter, extract_path

# Load any format (auto-detected)
data = load("config.json")
users = load("data.yaml")

# Convert between formats
convert("input.json", "output.yaml")

# JSONPath extraction
users = load("data.json[$.users[*]]")
names = extract_path(data, "$.users[*].name")

# Filter with conditions
active_users = filter(users, "age > 18 and status == \"active\"")

# Complex queries
result = query('from data.json[$.users[*]] where age > 25 and premium == true')
```

### As a CLI

```bash
# Start interactive REPL
dataconv

# Or run directly
python -m dataconv
```

#### Interactive Session

```
DataConv> from data.json to output.yaml
[+] Successfully converted data.json → output.yaml

DataConv> from users.json[$.users[*]] where age > 25 to adults.yaml
[+] Filtered 15 records → adults.yaml

DataConv> load employees.csv
[+] Loaded employees.csv (247 records)

DataConv> show
{
  "employees": [...]
}
```

---

## Library API Reference

### load()

Load data from any supported format with auto-detection.

```python
def load(path: str | Path, **options: Any) -> dict | list
```

**Features**:
- Auto-detects format from extension
- Supports JSONPath extraction in path
- Handles literal brackets in filenames
- Configurable encoding, separators

**Examples**:

```python
# Basic loading
data = load("config.json")
data = load("data.yaml", encoding="utf-16")

# JSONPath extraction
users = load("data.json[$.users[*]]")
names = load("data.json[$.users[*].name]")

# Literal brackets in filename (file exists)
archive = load("backup[2024].json")
```

### save()

Save data to any format with atomic writes.

```python
def save(data: dict | list, path: str | Path, **options: Any) -> None
```

**Features**:
- Atomic file writes (rename, not overwrite)
- Auto-detects format from extension
- Pretty-printing with configurable indentation
- Custom encoding support

**Examples**:

```python
# Basic saving
save(data, "output.json")
save(data, "config.yaml", indent=4)

# Custom options
save(data, "data.json", sort_keys=True, ensure_ascii=False)
```

### convert()

One-step format conversion with optional JSONPath extraction.

```python
def convert(source: str | Path, dest: str | Path, **options: Any) -> None
```

**Features**:
- Auto-detects source and destination formats
- Supports JSONPath in source path
- Preserves data structure
- Configurable conversion options

**Examples**:

```python
# Simple conversion
convert("data.json", "data.yaml")
convert("config.toml", "config.json")

# Convert with extraction
convert("data.json[$.users[*]]", "users.csv")
convert("nested.yaml[$.items[*]]", "items.toml")
```

### extract_path()

Apply JSONPath expression to data.

```python
def extract_path(data: dict | list, path: str) -> Any
```

**Examples**:

```python
data = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}

# Extract all users
users = extract_path(data, "$.users[*]")
# [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]

# Extract specific fields
names = extract_path(data, "$.users[*].name")
# ["Alice", "Bob"]

# Complex paths
first_user = extract_path(data, "$.users[0]")
```

### filter()

Filter data using WHERE clause conditions.

```python
def filter(data: dict | list, conditions: str) -> dict | list
```

**Features**:
- Comparison operators: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Boolean operators: `and`, `or`, `not`, `xor`
- Standalone field checks: `where active`, `where !deleted`
- Nested field access: `user.profile.age > 18`

**Examples**:

```python
users = [
    {"name": "Alice", "age": 30, "active": True},
    {"name": "Bob", "age": 25, "active": False},
    {"name": "Charlie", "age": 35, "active": True}
]

# Simple conditions
adults = filter(users, 'age >= 30')
active = filter(users, 'active == true')

# Complex boolean logic
result = filter(users, 'age > 25 and active == true')
result = filter(users, '(age < 30 or age > 40) and active')

# Standalone field checks
active_users = filter(users, 'active')  # Truthy check
inactive = filter(users, '!active')     # Falsy check
```

### query()

Execute full query language (source, extraction, filtering).

```python
def query(query_str: str, **options: Any) -> dict | list
```

**Syntax**:
```
from <source>[optional_jsonpath] [where conditions]
```

**Examples**:

```python
# Load and filter
result = query('from data.json where age > 25')

# Extract and filter
result = query('from data.json[$.users[*]] where active == true')

# Complex queries
result = query('''
    from employees.csv[$.data[*]]
    where (department == "Engineering" and salary > 100000)
       or (department == "Sales" and sales > 50000)
''')
```

---

## CLI Reference

### Available Commands

#### Query Execution

**Syntax**:
```
from <source> [to <dest>] [where conditions]
```

**Examples**:
```
from data.json to output.yaml
from users.json[$.users[*]] where age > 25 to adults.yaml
from config.toml to config.json where env == "production"
```

#### Helper Commands

- `load <file>` - Load and display file contents
- `save <file>` - Save current data to file
- `show` - Display currently loaded data
- `validate <file>` - Check file format validity
- `options` - View current configuration
- `set <option> <value>` - Change runtime configuration
- `help` - Show command help
- `clear` - Clear screen
- `exit` / `quit` - Exit REPL

---

## Query Language

### JSONPath Syntax

Extract nested data using JSONPath expressions:

```
$.root                    # Root level
$.users[*]                # All users
$.users[0]                # First user
$.users[*].name           # All names
$.items[?(@.price > 10)]  # Filter in JSONPath
```

### WHERE Clause

Filter data with boolean expressions:

**Comparison Operators**:
- `==` - Equal
- `!=` - Not equal
- `<` - Less than
- `>` - Greater than
- `<=` - Less than or equal
- `>=` - Greater than or equal

**Boolean Operators**:
- `and` - Logical AND
- `or` - Logical OR
- `not` - Logical NOT
- `xor` - Exclusive OR
-  `()` - Grouping/precedence

**Standalone Field Checks**:
- `where active` - Truthy check
- `where !deleted` - Falsy check

**Examples**:
```
where age > 18
where status == "active" and premium == true
where (age < 25 or age > 65) and not deleted
where department == "Sales" xor region == "West"
where active and not archived
```

---

## Configuration Options

Configure behavior at runtime or via API:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `atomic` | bool | true | Use atomic file writes |
| `indent` | int | 2 | JSON/YAML indentation |
| `sort_keys` | bool | false | Sort dictionary keys |
| `encoding` | str | "utf-8" | File encoding |
| `ensure_ascii` | bool | false | Escape non-ASCII in JSON |
| `allow_unicode` | bool | true | Allow Unicode in YAML |
| `pretty` | bool | true | Pretty-print XML |
| `array_strategy` | str | "json" | CSV array handling |

**Usage in Library**:
```python
# Pass as keyword arguments
data = load("file.json", encoding="utf-16", indent=4)
save(data, "out.json", sort_keys=True, ensure_ascii=False)
```

**Usage in CLI**:
```
DataConv> set indent 4
[+] Set indent = 4

DataConv> set sort_keys true
[+] Set sort_keys = true

DataConv> options
Current Configuration:
  atomic: true
  indent: 4
  sort_keys: true
  ...
```

---

## Supported Formats

| Format | Read | Write | Notes |
|--------|------|-------|-------|
| JSON | ✓ | ✓ | Fast with orjson (3x) |
| YAML | ✓ | ✓ | Optional C extensions (5x) |
| TOML | ✓ | ✓ | stdlib tomllib on Python 3.11+ |
| XML | ✓ | ✓ | Via xmltodict |
| CSV | ✓ | ✓ | Nested structure support |

---

## Testing

Run the test suite:

```bash
# Run all tests
python test_runner.py

# With pytest
pytest tests/

# With coverage
pytest --cov=dataconv --cov-report=term-missing
```

**Test Coverage**:
- 226 tests passing
- 100% API coverage
- Cross-platform compatibility (Windows, macOS, Linux)

---

## Project Structure

```
DataConverter/
├── dataconv/
│   ├── api.py           # Public API functions
│   ├── cli.py           # Interactive REPL
│   ├── grammar.py       # Query language grammar
│   ├── parser.py        # Query parser
│   ├── processor.py     # Data processing engine
│   ├── io.py            # File I/O operations
│   ├── validation.py    # Format validators
│   └── options.py       # Configuration management
├── tests/
│   ├── api_test.py
│   ├── cli_test.py
│   ├── grammar_test.py
│   ├── parser_test.py
│   ├── processor_test.py
│   ├── io_test.py
│   └── validation_test.py
├── main.py              # CLI entry point
├── test_runner.py       # Test suite runner
├── pyproject.toml       # Project configuration
├── README.md
├── CHANGELOG.md
└── LICENSE
```

---

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/thaisya/dataconv.git
cd dataconv

# Install with dev dependencies
pip install -e ".[full]"

# Run tests
python test_runner.py

# Format code
black dataconv/ tests/

# Lint
ruff check dataconv/ tests/

# Type check
mypy dataconv/
```

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`python test_runner.py`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for version history and migration guides.

---

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

---

## Acknowledgments

- Built with [Lark](https://github.com/lark-parser/lark) for parsing
- [jsonpath-ng](https://github.com/h2non/jsonpath-ng) for JSONPath
- [orjson](https://github.com/ijl/orjson) for high-performance JSON
- [Rich](https://github.com/Textualize/rich) for beautiful terminal output

---

**Made with ❤️ by [thaisya](https://github.com/thaisya)**
