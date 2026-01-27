"""Public API for DataConverter library.

This module provides a clean, Pythonic interface for programmatic data conversion.
All functions accept configuration options as keyword arguments.
"""

from pathlib import Path
from typing import Any

from dataconv.io import parse_source_with_path, smart_load, smart_save
from dataconv.options import OptionsConfig
from dataconv.parser import QueryParser
from dataconv.processor import apply_conditions, apply_path


def load(path: str | Path, **options: Any) -> dict | list:
    """Load data from any supported format with auto-detection.
    
    Automatically detects file format from extension and uses the appropriate
    parser. Supports JSON, YAML, TOML, XML, and CSV formats.
    Also supports JSONPath extraction syntax in the path.
    
    Args:
        path: Path to file to load, optionally with JSONPath (e.g., "data.json[$.users[*]]")
        **options: Configuration options (encoding, separator, etc.)
    
    Returns:
        Loaded data as dict or list (extracted if JSONPath was provided)
    
    Keyword Args:
        encoding (str): File encoding (default: "utf-8")
        separator (str): CSV flatten separator (default: ".")
        ... (all OptionsConfig fields)
    
    Example:
        >>> data = load("config.json")
        >>> data = load("data.yaml", encoding="utf-16")
        >>> data = load("users.csv", separator="_")
        >>> users = load("data.json[$.users[*]]")  # Load and extract in one call
        >>> archive = load("backup[2024].json")  # Handles literal brackets in filenames
    """
    opts = OptionsConfig(**options)
    
    file_path, json_path = parse_source_with_path(str(path))
    
    data = smart_load(file_path, options=opts)
    
    if json_path:
        data = apply_path(data, json_path)
    
    return data


def save(data: dict | list, path: str | Path, **options: Any) -> None:
    """Save data to any supported format with auto-detection.
    
    Automatically detects file format from extension and uses the appropriate
    serializer. Supports atomic writes by default for data safety.
    
    Args:
        data: Data to save (dict or list)
        path: Destination file path
        **options: Configuration options (indent, atomic, etc.)
    
    Keyword Args:
        atomic (bool): Use atomic writes (default: True)
        indent (int): JSON indentation (default: 2)
        encoding (str): File encoding (default: "utf-8")
        ensure_ascii (bool): ASCII-only output (default: False)
        array_strategy (str): CSV array handling (default: "json")
        ... (all OptionsConfig fields)
    
    Example:
        >>> save(data, "output.json")
        >>> save(data, "output.yaml", indent=4, atomic=False)
        >>> save(data, "output.csv", array_strategy="explode")
    """
    opts = OptionsConfig(**options)
    smart_save(data, Path(path), options=opts)


def extract_path(data: dict | list, path: str) -> Any:
    """Extract data using JSONPath expression.
    
    Navigate nested data structures using JSONPath syntax.
    Returns the matched data.
    
    Args:
        data: Source data (dict or list)
        path: JSONPath expression (e.g., "$.users[*].name")
    
    Returns:
        Extracted data (could be dict, list, or primitive)
    
    Example:
        >>> data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        >>> extract_path(data, "$.users[*]")
        [{"name": "Alice"}, {"name": "Bob"}]
        >>> extract_path(data, "$.users[*].name")
        ["Alice", "Bob"]
    """
    return apply_path(data, path)


def convert(source: str | Path, dest: str | Path, **options: Any) -> None:
    """Convert between file formats with optional JSONPath extraction.
    
    Simple format conversion with support for JSONPath in source path.
    Auto-detects formats from file extensions.
    
    Args:
        source: Source file path, optionally with JSONPath (e.g., "data.json[$.users[*]]")
        dest: Destination file path
        **options: Configuration options
    
    Keyword Args:
        Same as load() and save()
    
    Example:
        >>> convert("data.json", "output.yaml")
        >>> convert("data.json[$.users[*]]", "output.yaml", indent=4)
        >>> convert("data.json", "output.csv", array_strategy="explode")
    """
    opts = OptionsConfig(**options)
    
    file_path, json_path = parse_source_with_path(str(source))
    
    data = smart_load(file_path, options=opts)
    
    if json_path:
        data = apply_path(data, json_path)
    
    smart_save(data, Path(dest), options=opts)


def filter(data: dict | list, condition: str) -> dict | list:
    """Filter data using WHERE clause syntax.
    
    Filter loaded data in-memory using conditional expressions.
    Supports complex boolean logic (and, or, not, xor).
    
    Args:
        data: Data to filter (dict or list)
        condition: WHERE clause (e.g., "age > 25", "status == 'active'")
    
    Returns:
        Filtered data (same type as input)
    
    Example:
        >>> data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 17}]
        >>> filter(data, "age >= 18")
        [{"name": "Alice", "age": 30}]
        >>> filter(data, "age > 18 and name == 'Alice'")
        [{"name": "Alice", "age": 30}]
    """
    parser = QueryParser()
    expr = parser._parse_conditions(condition)
    
    if isinstance(data, list):
        return apply_conditions(data, expr)
    else:
        result = apply_conditions([data], expr)
        return result[0] if result else {}


def query(query_str: str, **options: Any) -> dict | list | None:
    """Execute query with full DataConverter query language.
    
    Supports the complete query syntax including JSONPath extraction,
    filtering, and format conversion. Returns data for view-only queries
    (no destination), otherwise saves to file and returns None.
    
    Args:
        query_str: Query string (e.g., "from data.json where age > 25")
        **options: Configuration options
    
    Returns:
        Data if view-only query (no destination), None if saving to file
    
    Keyword Args:
        Same as load() and save()
    
    Example:
        >>> query("from data.json to output.yaml")
        >>> data = query("from data.json where age > 25")
        >>> query("from data.json[$.users[*]] to output.yaml where status == 'active'")
        >>> query("from data.json to output.csv", array_strategy="explode")
    """
    opts = OptionsConfig(**options)
    parser = QueryParser()
    parsed = parser.parse(query_str)
    
    source_file = parsed["source"]["file"]
    data = smart_load(Path(source_file), options=opts)
    
    if parsed["source"]["path"]:
        data = apply_path(data, parsed["source"]["path"])
    
    if parsed["conditions"]:
        data = apply_conditions(data, parsed["conditions"])
    
    if parsed["dest"]:
        dest_file = parsed["dest"]["file"]
        smart_save(data, Path(dest_file), options=opts)
        return None
    else:
        return data
