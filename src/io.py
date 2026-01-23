"""File I/O operations with smart format detection and atomic writes.

This module provides smart loading and saving of data files in multiple formats
(JSON, TOML, YAML, XML, CSV) with automatic format detection and optional atomic writes.

Example:
    >>> from pathlib import Path
    >>> from src.io import smart_load, smart_save
    >>>
    >>> # Load any supported format
    >>> data = smart_load(Path("data.json"))
    >>>
    >>> # Save with atomic write (default)
    >>> smart_save(data, Path("output.yaml"), atomic=True)
"""

import csv
import logging
import os
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    import json
    HAS_ORJSON = False

try:
    import tomllib
    HAS_TOMLLIB = True
except ModuleNotFoundError:
    HAS_TOMLLIB = False

import toml

import yaml
try:
    from yaml import CSafeLoader as YAMLLoader, CDumper as YAMLDumper
    HAS_YAML_C = True
except ImportError:
    from yaml import SafeLoader as YAMLLoader, Dumper as YAMLDumper
    HAS_YAML_C = False

import xmltodict
from src.options import OptionsConfig

logger = logging.getLogger(__name__)

if HAS_ORJSON:
    logger.debug("Using orjson for JSON (3x faster)")
if HAS_TOMLLIB:
    logger.debug("Using tomllib for TOML reading (2x faster)")
if HAS_YAML_C:
    logger.debug("Using PyYAML C extensions (5x faster)")


def normalize_path(path: Path) -> Path:
    """Normalize file path to default to 'files' folder for relative paths.
    
    Args:
        path: Input path (relative or absolute)
    
    Returns:
        Normalized Path object. If path is relative, it will be prefixed with 'files/'.
        Absolute paths are returned unchanged.
    
    Example:
        >>> normalize_path(Path("data.json"))
        Path('files/data.json')
        >>> normalize_path(Path("C:/Users/data.json"))
        Path('C:/Users/data.json')
        >>> normalize_path(Path("files/data.json"))
        Path('files/data.json')
    """
    # If path is absolute, return it as-is
    if path.is_absolute():
        return path
    
    # If path is relative and doesn't start with 'files', prefix it
    if not str(path).startswith("files"):
        return Path("files") / path
    
    # Path already starts with 'files' or is in correct format
    return path


def parse_source_with_path(source: str | Path) -> tuple[Path, str | None]:
    """Parse file path that may contain JSONPath syntax, handling edge cases.
    
    Handles:
    - archive[2024].json (literal filename with brackets)
    - data.json[users[*]] (file + JSONPath)
    - data.json[nested[0][items]] (nested brackets in JSONPath)
    
    Strategy:
    1. Check if full string is a valid file (handles literal brackets in filename)
    2. If not, find first '[' and split there
    3. Check if the file part exists
    4. Return (file_path, jsonpath_or_none)
    
    Args:
        source: File path string, possibly with JSONPath in brackets
    
    Returns:
        Tuple of (file_path, jsonpath_expression_or_none)
    
    Example:
        >>> parse_source_with_path("archive[2024].json")
        (Path("files/archive[2024].json"), None)  # If file exists
        
        >>> parse_source_with_path("data.json[$.users[*]]")
        (Path("files/data.json"), "$.users[*]")
    """
    source_str = str(source)
    
    # First, try the full string as-is (handles filenames with brackets)
    full_path = normalize_path(Path(source_str))
    if full_path.exists():
        logger.debug(f"File '{source_str}' exists with literal brackets in name")
        return (full_path, None)
    
    # Not a literal file, check for JSONPath syntax
    if '[' not in source_str:
        # No brackets at all, just a regular file path
        return (normalize_path(Path(source_str)), None)
    
    # Split on first '[' to separate file from JSONPath
    first_bracket = source_str.index('[')
    file_part = source_str[:first_bracket]
    
    # Remove trailing ']' from the path part
    path_part = source_str[first_bracket+1:]
    if path_part.endswith(']'):
        path_part = path_part[:-1]
    
    file_path = normalize_path(Path(file_part))
    
    # Validate that the file part exists
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
    
    return (file_path, path_part if path_part else None)



def flatten_dict(
    data: dict[str, Any], 
    parent_key: str = "", 
    sep: str = ".",
    options: OptionsConfig = None
) -> dict[str, Any]:
    """Flatten nested dictionary using dot notation.
    
    Args:
        data: Dictionary to flatten
        parent_key: Parent key prefix (for recursion)
        sep: Separator for nested keys (default: ".")
        options: OptionsConfig instance (uses defaults if None)
    
    Returns:
        Flattened dictionary with dot-notation keys
    
    Example:
        >>> flatten_dict({"user": {"name": "Alice", "age": 30}})
        {"user.name": "Alice", "user.age": 30}
        
        >>> opts = OptionsConfig(array_strategy="json")
        >>> flatten_dict({"tags": ["a", "b"]}, options=opts)
        {"tags": '["a", "b"]'}
        
        >>> opts = OptionsConfig(preserve_dots=True)
        >>> flatten_dict({"user.name": "Alice"}, options=opts)
        {"user\\.name": "Alice"}
    """
    # Use default options if not provided
    options = options or OptionsConfig()
    
    items: list[tuple[str, Any]] = []
    
    for key, value in data.items():
        # Escape dots in original keys only if preserve_dots is True
        if options.preserve_dots:
            escaped_key = key.replace(".", "\\.")
        else:
            escaped_key = key
        
        new_key = f"{parent_key}{sep}{escaped_key}" if parent_key else escaped_key
        
        if isinstance(value, dict):
            if options.ignore_nested:
                # Skip nested dictionaries
                continue
            # Recursively flatten nested dict
            items.extend(flatten_dict(value, new_key, sep, options).items())
        elif isinstance(value, list):
            if options.ignore_nested:
                # Skip arrays
                continue
            
            # Handle arrays based on strategy
            if options.array_strategy == "json":
                # JSON-encode for reliable round-trip (use orjson if available)
                if HAS_ORJSON:
                    items.append((new_key, orjson.dumps(value).decode('utf-8')))
                else:
                    import json
                    items.append((new_key, json.dumps(value)))
            elif options.array_strategy == "explode":
                # Keep array as-is, will be exploded at higher level
                items.append((new_key, value))
            elif options.array_strategy == "skip":
                # Skip arrays with warning
                logger.warning(f"Skipping array field '{new_key}' (array_strategy='skip')")
                continue
            else:
                raise ValueError(
                    f"Invalid array_strategy: {options.array_strategy}. "
                    "Must be one of: json, explode, skip"
                )
        else:
            # Keep primitives as-is
            items.append((new_key, value))
    
    return dict(items)


def unflatten_dict(data: dict[str, Any], sep: str = ".", options: OptionsConfig = None) -> dict[str, Any]:
    """Unflatten dictionary with dot notation back to nested structure.
    
    Args:
        data: Flattened dictionary with dot-notation keys
        sep: Separator used in keys (default: ".")
        options: OptionsConfig instance (uses defaults if None)
    
    Returns:
        Nested dictionary structure
    
    Example:
        >>> unflatten_dict({"user.name": "Alice", "user.age": "30"})
        {"user": {"name": "Alice", "age": "30"}}
        
        >>> opts = OptionsConfig(array_strategy="json")
        >>> unflatten_dict({"tags": '["a","b"]'}, options=opts)
        {"tags": ["a", "b"]}
        
        >>> opts = OptionsConfig(preserve_dots=True)
        >>> unflatten_dict({"user\\.name": "Alice"}, options=opts)
        {"user.name": "Alice"}
    """
    # Use default options if not provided
    options = options or OptionsConfig()
    
    result: dict[str, Any] = {}
    
    for key, value in data.items():
        # Split by separator, but handle escaped separators only if preserve_dots
        if options.preserve_dots:
            parts = key.replace(f"\\{sep}", "\x00").split(sep)
            parts = [p.replace("\x00", sep) for p in parts]
        else:
            # Simple split - no escaping
            parts = key.split(sep)
        
        # Parse arrays based on strategy
        if options.array_strategy == "json" and isinstance(value, str):
            try:
                # Try to parse as JSON (use orjson if available)
                if HAS_ORJSON:
                    parsed = orjson.loads(value)
                else:
                    import json
                    parsed = json.loads(value)
                # Only use if it's actually an array
                if isinstance(parsed, list):
                    value = parsed
            except Exception:
                # Not JSON or not an array, keep as string
                pass
        
        # Navigate/create nested structure
        current = result
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                # Conflict: key exists but isn't a dict
                # Override with dict to continue nesting
                current[part] = {}
            current = current[part]
        
        # Set the final value
        current[parts[-1]] = value
    
    return result


def explode_arrays(
    data: list[dict[str, Any]], 
    array_field: str | None = None
) -> list[dict[str, Any]]:
    """Explode array field into separate rows (database normalization).
    
    Converts each array element into a separate row, duplicating other fields.
    Useful for SQL-style CSV exports where arrays need to be normalized.
    
    Args:
        data: List of dictionaries
        array_field: Field to explode. If None, auto-detects first array field.
    
    Returns:
        Expanded list with one row per array element
    
    Example:
        >>> data = [{"user": "Alice", "tags": ["a", "b"]}]
        >>> explode_arrays(data, "tags")
        [
            {"user": "Alice", "tags": "a"},
            {"user": "Alice", "tags": "b"}
        ]
    
    Warning:
        - Multiple array fields create Cartesian product (exponential growth)
        - Changes data structure (not reversible)
        - Best for single array field
    """
    if not data:
        return data
    
    # Auto-detect array field if not specified
    if array_field is None:
        for record in data:
            for key, value in record.items():
                if isinstance(value, list) and value:
                    array_field = key
                    logger.info(f"Auto-detected array field for explosion: {array_field}")
                    break
            if array_field:
                break
    
    if not array_field:
        logger.warning("No array field found for explosion, returning data unchanged")
        return data
    
    exploded = []
    for record in data:
        array_value = record.get(array_field)
        
        if not isinstance(array_value, list) or not array_value:
            # Not an array or empty - keep row as-is
            exploded.append(record)
        else:
            # Create one row per array element
            for item in array_value:
                new_record = record.copy()
                new_record[array_field] = item  # Replace array with scalar
                exploded.append(new_record)
    
    return exploded


class FileFormat(Enum):
    """Supported file formats for data conversion."""

    JSON = "json"
    TOML = "toml"
    YAML = "yaml"
    XML = "xml"
    CSV = "csv"


class DataConverterIOError(Exception):
    """Base exception for I/O operations."""

    pass


class FileLoadError(DataConverterIOError):
    """Exception raised when file loading fails."""

    pass


class FileSaveError(DataConverterIOError):
    """Exception raised when file saving fails."""

    pass


class UnsupportedFormatError(DataConverterIOError):
    """Exception raised for unsupported file formats."""

    pass


def detect_format(path: Path) -> FileFormat:
    """Detect file format from file extension.

    Args:
        path: Path to the file

    Returns:
        Detected FileFormat enum value

    Raises:
        UnsupportedFormatError: If file extension is not supported

    Example:
        >>> detect_format(Path("data.json"))
        <FileFormat.JSON: 'json'>
    """
    extension = path.suffix.lower().lstrip(".")

    try:
        return FileFormat(extension)
    except ValueError:
        # Handle .yml as YAML
        if extension == "yml":
            return FileFormat.YAML
        raise UnsupportedFormatError(
            f"Unsupported file format: {extension}. "
            f"Supported formats: {', '.join(f.value for f in FileFormat)}, yml"
        )


def smart_load(path: Path) -> dict[str, Any]:
    """Load data from file with automatic format detection.

    Automatically detects the file format based on extension and uses the
    appropriate parser. All file operations use context managers for safety.

    Args:
        path: Path to the file to load

    Returns:
        Loaded data as a dictionary

    Raises:
        FileLoadError: If file cannot be loaded or parsed
        UnsupportedFormatError: If file format is not supported

    Example:
        >>> data = smart_load(Path("config.json"))
        >>> print(data['version'])
    """
    # Normalize path to default to 'files' directory for relative paths
    path = normalize_path(path)
    
    logger.debug(f"Loading file: {path}")

    if not path.exists():
        raise FileLoadError(f"File not found: {path}")

    file_format = detect_format(path)

    try:
        with open(path, encoding="utf-8") as file:
            if file_format == FileFormat.JSON:
                if HAS_ORJSON:
                    # orjson requires bytes
                    content = file.read()
                    data = orjson.loads(content)
                else:
                    data = json.load(file)
            elif file_format == FileFormat.TOML:
                if HAS_TOMLLIB:
                    # tomllib requires binary mode, re-open
                    with open(path, "rb") as binary_file:
                        data = tomllib.load(binary_file)
                else:
                    data = toml.load(file)
            elif file_format == FileFormat.YAML:
                data = yaml.load(file, Loader=YAMLLoader)
            elif file_format == FileFormat.XML:
                data = xmltodict.parse(file.read())
            elif file_format == FileFormat.CSV:
                # Load CSV as list of dicts
                reader = csv.DictReader(file)
                csv_data = list(reader)
                
                # Unflatten each row (convert dot notation to nested dicts)
                # Default to json strategy for array parsing
                data = [unflatten_dict(row, array_strategy="json") for row in csv_data]
            else:
                raise UnsupportedFormatError(f"Unsupported format: {file_format}")

        logger.info(f"Successfully loaded {file_format.value} file: {path}")
        return data  # type: ignore

    except UnsupportedFormatError:
        raise
    except Exception as e:
        logger.error(f"Failed to load file {path}: {e}")
        raise FileLoadError(f"Error loading file {path}: {e}") from e


def smart_save(
    data: dict[str, Any],
    path: Path,
    options: OptionsConfig = None,
) -> None:
    """Save data to file with automatic format detection.

    Supports atomic writes (write to temp file then rename) for data safety.
    Automatically detects the file format based on extension and uses the
    appropriate serializer.

    Args:
        data: Dictionary data to save
        path: Destination path
        options: OptionsConfig instance (uses defaults if None)

    Raises:
        FileSaveError: If file cannot be saved
        UnsupportedFormatError: If file format is not supported

    Example:
        >>> data = {'name': 'John', 'age': 30}
        >>> smart_save(data, Path("output.json"))
        
        >>> opts = OptionsConfig(atomic=False)
        >>> smart_save(data, Path("output.yaml"), opts)
        
        >>> # CSV with JSON-encoded arrays (default)
        >>> data = [{"user": "Alice", "tags": ["python", "rust"]}]
        >>> smart_save(data, Path("out.csv"))
        
        >>> # CSV with row explosion
        >>> opts = OptionsConfig(array_strategy="explode", array_field="tags")
        >>> smart_save(data, Path("out.csv"), opts)
    """
    # Use default options if not provided
    options = options or OptionsConfig()
    
    # Normalize path to default to 'files' directory for relative paths
    path = normalize_path(path)
    
    logger.debug(f"Saving file: {path} (atomic={options.atomic})")

    file_format = detect_format(path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Determine target path (temp file for atomic writes)
    if options.atomic:
        fd, temp_path_str = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )
        temp_path = Path(temp_path_str)
        os.close(fd)  # Close file descriptor, we'll open with context manager
        target_path = temp_path
    else:
        target_path = path

    try:
        with open(target_path, "w", encoding="utf-8") as file:
            if file_format == FileFormat.JSON:
                if HAS_ORJSON:
                    # orjson.dumps returns bytes, need to decode
                    # OPT_INDENT_2 for pretty printing
                    output = orjson.dumps(data, option=orjson.OPT_INDENT_2)
                    file.write(output.decode('utf-8'))
                else:
                    # Use indent from options (or fall back to 2)
                    json.dump(data, file, indent=options.indent)

            elif file_format == FileFormat.TOML:
                toml.dump(data, file)

            elif file_format == FileFormat.YAML:
                # Use allow_unicode from options
                yaml.dump(data, file, Dumper=YAMLDumper, allow_unicode=options.allow_unicode)

            elif file_format == FileFormat.XML:
                # Use pretty from options
                xml_string = xmltodict.unparse(data, pretty=options.pretty)
                file.write(xml_string)

            elif file_format == FileFormat.CSV:
                # CSV requires list of dictionaries
                if not isinstance(data, list):
                    raise FileSaveError(
                        "CSV format requires a list of dictionaries. "
                        f"Got {type(data).__name__} instead."
                    )
                
                if not data:
                    logger.warning("Saving empty CSV file")
                    # Create empty file - don't return, let file be created
                else:
                    # Handle "explode" strategy before flattening
                    if options.array_strategy == "explode":
                        data = explode_arrays(data, options.array_field)
                    
                    # Flatten with options
                    flattened_data = [
                        flatten_dict(row, options=options) 
                        for row in data
                    ]
                    
                    fieldnames: list[str] = []
                    seen = set()
                    for row in flattened_data:
                        for key in row.keys():
                            if key not in seen:
                                fieldnames.append(key)
                                seen.add(key)
                    
                    if not fieldnames:
                        raise FileSaveError(
                            "No fields to write to CSV. "
                            "All data may be nested (try ignore_nested=False)."
                        )
                    
                    # Write CSV with DictWriter
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(flattened_data)

            else:
                raise UnsupportedFormatError(f"Unsupported format: {file_format}")

        # Atomic write: rename temp file to final destination
        if options.atomic:
            temp_path.replace(path)
            logger.debug(f"Atomic write completed: {temp_path} -> {path}")

        logger.info(f"Successfully saved {file_format.value} file: {path}")

    except Exception as e:
        # Clean up temp file on error
        if options.atomic and temp_path.exists():
            temp_path.unlink()
            logger.debug(f"Cleaned up temp file: {temp_path}")

        logger.error(f"Failed to save file {path}: {e}")
        raise FileSaveError(f"Error saving file {path}: {e}") from e
