"""File I/O operations with smart format detection and atomic writes.

This module provides smart loading and saving of data files in multiple formats
(JSON, TOML, YAML, XML) with automatic format detection and optional atomic writes.

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

import json
import logging
import os
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any

import toml
import xmltodict
import yaml

logger = logging.getLogger(__name__)


class FileFormat(Enum):
    """Supported file formats for data conversion."""

    JSON = "json"
    TOML = "toml"
    YAML = "yaml"
    XML = "xml"


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
    logger.debug(f"Loading file: {path}")

    if not path.exists():
        raise FileLoadError(f"File not found: {path}")

    file_format = detect_format(path)

    try:
        with open(path, encoding="utf-8") as file:
            if file_format == FileFormat.JSON:
                data = json.load(file)
            elif file_format == FileFormat.TOML:
                data = toml.load(file)
            elif file_format == FileFormat.YAML:
                data = yaml.safe_load(file)
            elif file_format == FileFormat.XML:
                data = xmltodict.parse(file.read())
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
    atomic: bool = True,
    **kwargs: Any,
) -> None:
    """Save data to file with automatic format detection.

    Supports atomic writes (write to temp file then rename) for data safety.
    Automatically detects the file format based on extension and uses the
    appropriate serializer.

    Args:
        data: Dictionary data to save
        path: Destination path
        atomic: If True, use atomic write (temp file + rename). Default: True
        **kwargs: Additional keyword arguments passed to the serializer
                  (e.g., indent for JSON, allow_unicode for YAML)

    Raises:
        FileSaveError: If file cannot be saved
        UnsupportedFormatError: If file format is not supported

    Example:
        >>> data = {'name': 'John', 'age': 30}
        >>> smart_save(data, Path("output.json"), indent=2)
        >>> smart_save(data, Path("output.yaml"), atomic=True, allow_unicode=True)
    """
    logger.debug(f"Saving file: {path} (atomic={atomic})")

    file_format = detect_format(path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Determine target path (temp file for atomic writes)
    if atomic:
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
                # Default to indent=2 for readable JSON
                json_kwargs = {"indent": 2, **kwargs}
                json.dump(data, file, **json_kwargs)

            elif file_format == FileFormat.TOML:
                toml.dump(data, file)

            elif file_format == FileFormat.YAML:
                # Default to allow_unicode for better YAML
                yaml_kwargs = {"allow_unicode": True, **kwargs}
                yaml.safe_dump(data, file, **yaml_kwargs)

            elif file_format == FileFormat.XML:
                xml_kwargs = {"pretty": True, **kwargs}
                xml_string = xmltodict.unparse(data, **xml_kwargs)
                file.write(xml_string)

            else:
                raise UnsupportedFormatError(f"Unsupported format: {file_format}")

        # Atomic write: rename temp file to final destination
        if atomic:
            temp_path.replace(path)
            logger.debug(f"Atomic write completed: {temp_path} -> {path}")

        logger.info(f"Successfully saved {file_format.value} file: {path}")

    except Exception as e:
        # Clean up temp file on error
        if atomic and temp_path.exists():
            temp_path.unlink()
            logger.debug(f"Cleaned up temp file: {temp_path}")

        logger.error(f"Failed to save file {path}: {e}")
        raise FileSaveError(f"Error saving file {path}: {e}") from e
