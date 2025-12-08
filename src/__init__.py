"""Data Converter - Professional data format converter with query support.

This package provides tools for converting between different data formats
(JSON, TOML, YAML, XML) with powerful querying and filtering capabilities.

Example:
    >>> from src.io import smart_load, smart_save
    >>> from src.parser import QueryParser
    >>>
    >>> # Load data
    >>> data = smart_load(Path("input.json"))
    >>>
    >>> # Parse query
    >>> parser = QueryParser()
    >>> query = parser.parse('from input.json to output.yaml')
"""

__version__ = "2.0.0"
__author__ = "Data Converter Team"

# Public API exports
from src.io import (
    DataConverterIOError,
    FileFormat,
    FileLoadError,
    FileSaveError,
    UnsupportedFormatError,
    detect_format,
    smart_load,
    smart_save,
)
from src.parser import (
    Condition,
    ParseError,
    PathSpec,
    QueryParser,
    QueryResult,
)
from src.processor import (
    ProcessorError,
    apply_conditions,
    apply_path,
    process_data,
)
from src.validation import (
    ValidationError,
    ValidationIssue,
    ValidationResult,
    format_validation_report,
    validate,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # I/O
    "smart_load",
    "smart_save",
    "detect_format",
    "FileFormat",
    "DataConverterIOError",
    "FileLoadError",
    "FileSaveError",
    "UnsupportedFormatError",
    # Parser
    "QueryParser",
    "QueryResult",
    "PathSpec",
    "Condition",
    "ParseError",
    # Processor
    "apply_path",
    "apply_conditions",
    "process_data",
    "ProcessorError",
    # Validation
    "validate",
    "ValidationResult",
    "ValidationIssue",
    "ValidationError",
    "format_validation_report",
]
