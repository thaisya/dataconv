# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-27

**Production Release** - First stable release with stable API.

### Added

- **Library API** with 6 core functions:
  - `load()` - Load data from any format with JSONPath support
  - `save()` - Save data with atomic writes and format auto-detection
  - `convert()` - One-step format conversion
  - `extract_path()` - Apply JSONPath to loaded data
  - `filter()` - Filter data using WHERE clause syntax
  - `query()` - Execute full query language
- JSONPath support in `load()` function (e.g., `load("data.json[$.users[*]]")`)
- 38 comprehensive API test cases covering all functions
- Cross-platform path handling for Windows absolute paths
- Literal bracket handling for filenames like `archive[2024].json`
- orjson as core dependency for 3x faster JSON processing by default
- Flexible installation options (library-only, CLI, full)

### Changed

- Enhanced `load()` to use `parse_source_with_path()` for API consistency
- Moved orjson from optional to core dependencies
- Improved error messages with better context
- Complete documentation rewrite (README, CHANGELOG)
- Source folder name changed from `src` to `dataconv`

### Fixed

- Query parser now handles Windows paths with quoted syntax
- Filter function accepts double quotes for string values
- Edge case handling for filenames with literal brackets

### Testing

- 226 tests passing (up from 188)
- 100% API coverage
- Cross-platform compatibility verified

---

## [0.3.0] - 2026-01-23

### Added

- **Options System** - Runtime configuration management
  - `OptionsConfig` dataclass with 8 configuration options
  - CLI commands: `options` (view), `set` (change)
- **View-Only Queries** - Queries without destination file
  - Syntax: `from data.json where age > 25`
- Literal brackets support in filenames
- Standalone conditions parsing for internal API

### Changed

- Made `to` clause optional in grammar
- Updated CLI to handle destination-less queries

### Fixed

- `_execute_query()` no longer crashes when destination is `None`
- Corrected grammar for optional `to` clause

---

## [0.2.1] - 2026-01-03

### Added

- **Standalone Field Boolean Checks**
  - Syntax: `where status` (truthy), `where !status` (falsy)
  - Works with boolean operators: `where premium and active`
- 11 comprehensive tests for field checks

### Changed

- Enhanced grammar with `field_check` rule
- Updated parser for truthiness comparisons

---

## [0.2.0] - 2025-12-17

### Added

- **Boolean Field Negation** in comparisons
  - Syntax: `where status == !active`
- **Explicit JSONPath Prefix Requirement** (breaking change)
  - Now require `$` prefix: `data.json[$.users[*]]`

### Changed

- **BREAKING**: All JSONPath expressions must start with `$`
- Removed automatic `$` prefix insertion

### Testing

- 11 tests for boolean negation
- Updated 50+ tests to use `$.` prefix

---

## [0.1.0] - 2025-12-15

Initial release.

### Added

- **Boolean Expression Support** - AND, OR, NOT, XOR operators
- **Interactive CLI** - MySQL-style REPL
- **Multi-Format Support** - JSON, YAML, TOML, XML, CSV
- **Query Language** with Lark parser
  - JSONPath extraction
  - WHERE clauses with comparison operators
- **Validation System** - Format-specific validators
- **Smart File I/O** - Auto-detection, atomic writes
- 188 comprehensive tests

---

## Migration Guides

### From 0.3.0 to 1.0.0

**No breaking changes.** This release adds library API without modifying CLI behavior.

```python
# New library API
from dataconv import load, save, convert, query, filter, extract_path

# load() now supports JSONPath
users = load("data.json[$.users[*]]")
```

### From 0.2.x to 0.3.0

**No breaking changes.** New features:
- Can omit `to` clause for view-only queries
- Use `options` and `set` commands for runtime configuration

### From 0.1.0 to 0.2.0

**BREAKING**: JSONPath expressions now require `$` prefix.

```bash
# Before (0.1.0)
from data.json[users[*]] to output.yaml

# After (0.2.0+)
from data.json[$.users[*]] to output.yaml
```

---

[1.0.0]: https://github.com/yourusername/dataconv/releases/tag/v1.0.0
[0.3.0]: https://github.com/yourusername/dataconv/releases/tag/v0.3.0
[0.2.1]: https://github.com/yourusername/dataconv/releases/tag/v0.2.1
[0.2.0]: https://github.com/yourusername/dataconv/releases/tag/v0.2.0
[0.1.0]: https://github.com/yourusername/dataconv/releases/tag/v0.1.0
