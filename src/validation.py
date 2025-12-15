"""Data validation for different file formats.

This module provides comprehensive validation logic for JSON, TOML, YAML, and XML
formats. Each format has specific requirements and constraints that are checked.

Example:
    >>> from src.validation import validate, FileFormat
    >>> data = {'name': 'John', 'age': 30}
    >>> result = validate(data, FileFormat.JSON)
    >>> if result.errors:
    >>>     print("Validation failed:", result.errors)
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Protocol

from src.io import FileFormat

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"


class ValidationError(Exception):
    """Base exception for validation errors."""

    pass


@dataclass
class ValidationIssue:
    """Represents a single validation issue.

    Attributes:
        path: Path to the problematic data (e.g., "$.users[0].age")
        message: Description of the issue
        severity: Whether this is an error or warning
    """

    path: str
    message: str
    severity: Severity = Severity.ERROR


@dataclass
class ValidationResult:
    """Result of validation containing errors and warnings.

    Attributes:
        errors: List of validation errors
        warnings: List of validation warnings
    """

    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    def is_valid(self) -> bool:
        """Check if validation passed (no errors).

        Returns:
            True if there are no errors, False otherwise
        """
        return len(self.errors) == 0

    def add_error(self, path: str, message: str) -> None:
        """Add an error to the result.

        Args:
            path: Path to the problematic data
            message: Error message
        """
        self.errors.append(ValidationIssue(path, message, Severity.ERROR))

    def add_warning(self, path: str, message: str) -> None:
        """Add a warning to the result.

        Args:
            path: Path to the data
            message: Warning message
        """
        self.warnings.append(ValidationIssue(path, message, Severity.WARNING))


class Validator(Protocol):
    """Protocol defining the interface for format validators."""

    def validate(self, data: Any, path: str) -> ValidationResult:
        """Validate data and return validation result.

        Args:
            data: Data to validate
            path: Current path in the data structure

        Returns:
            ValidationResult with errors and warnings
        """
        ...


class FloatCheckMixin:
    """Mixin for validating float values are finite.
    
    Provides method to check for non-finite floats (NaN, Infinity).
    Used by JSON, TOML, and YAML validators.
    """

    def check_finite_float(
        self, value: Any, path: str, result: ValidationResult
    ) -> bool:
        """Check if value is a non-finite float and add error if so.

        Args:
            value: Value to check
            path: Current path in data structure
            result: ValidationResult to add error to

        Returns:
            True if value is a non-finite float, False otherwise
        """
        if isinstance(value, float) and not math.isfinite(value):
            result.add_error(path, f"non-finite float {value}")
            return True
        return False


class DictKeyCheckMixin:
    """Mixin for validating dictionary keys are strings.
    
    Provides strict (error) and soft (warning) validation modes.
    Used by all validators with different strictness levels.
    """

    def check_string_keys_strict(
        self, value: dict, path: str, result: ValidationResult
    ) -> None:
        """Add ERROR for non-string keys (strict mode).

        Args:
            value: Dictionary to check
            path: Current path in data structure
            result: ValidationResult to add errors to
        """
        for key in value.keys():
            if not isinstance(key, str):
                result.add_error(path, f"non-string key {key}")

    def check_string_keys_soft(
        self, value: dict, path: str, result: ValidationResult
    ) -> None:
        """Add WARNING for non-string keys (soft mode).

        Args:
            value: Dictionary to check
            path: Current path in data structure
            result: ValidationResult to add warnings to
        """
        for key in value.keys():
            if not isinstance(key, str):
                result.add_warning(path, f"non-string key {key}")


class RecursiveWalkMixin:
    """Mixin providing recursive traversal of dict/list structures.
    
    Provides helper methods for walking nested data structures.
    Used by all validators to eliminate iteration duplication.
    """

    def walk_dict(
        self,
        value: dict,
        path: str,
        result: ValidationResult,
        walker: Callable[[Any, str, ValidationResult], None],
    ) -> None:
        """Recursively walk dictionary items.

        Args:
            value: Dictionary to walk
            path: Current path in data structure
            result: ValidationResult to accumulate issues
            walker: Callback function to process each value
        """
        for key, subvalue in value.items():
            walker(subvalue, f"{path}.{key}", result)

    def walk_list(
        self,
        value: list,
        path: str,
        result: ValidationResult,
        walker: Callable[[Any, str, ValidationResult], None],
    ) -> None:
        """Recursively walk list items.

        Args:
            value: List to walk
            path: Current path in data structure
            result: ValidationResult to accumulate issues
            walker: Callback function to process each value
        """
        for i, subvalue in enumerate(value):
            walker(subvalue, f"{path}[{i}]", result)


class JSONValidator(FloatCheckMixin, DictKeyCheckMixin, RecursiveWalkMixin):
    """Validator for JSON format.

    JSON requirements:
    - Keys must be strings
    - Values must be: null, bool, number, string, array, or object
    - Numbers must be finite (no NaN or Infinity)
    """

    def validate(self, data: Any, path: str = "$") -> ValidationResult:
        """Validate data for JSON compatibility.

        Args:
            data: Data to validate
            path: Current path (default: "$")

        Returns:
            ValidationResult with any errors found
        """
        result = ValidationResult()
        self._walk(data, path, result)
        return result

    def _walk(self, value: Any, path: str, result: ValidationResult) -> None:
        """Recursively walk data structure and validate.

        Args:
            value: Current value to check
            path: Current path in data
            result: ValidationResult to accumulate issues
        """
        if value is None or isinstance(value, (int, str, bool)):
            return

        if self.check_finite_float(value, path, result):
            return

        if isinstance(value, dict):
            self.check_string_keys_strict(value, path, result)
            self.walk_dict(value, path, result, self._walk)
            return

        if isinstance(value, list):
            self.walk_list(value, path, result, self._walk)
            return

        result.add_error(
            path, f"{value} (type {type(value).__name__}) is not a valid JSON value"
        )


class TOMLValidator(FloatCheckMixin, DictKeyCheckMixin, RecursiveWalkMixin):
    """Validator for TOML format.

    TOML requirements:
    - Keys must be strings
    - Arrays must be homogeneous (all elements same type)
    - Supports datetime, date, and time types
    - Numbers must be finite
    """

    def validate(self, data: Any, path: str = "$") -> ValidationResult:
        """Validate data for TOML compatibility.

        Args:
            data: Data to validate
            path: Current path (default: "$")

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        self._walk(data, path, result)
        return result

    def _walk(self, value: Any, path: str, result: ValidationResult) -> None:
        """Recursively walk data structure and validate.

        Args:
            value: Current value to check
            path: Current path in data
            result: ValidationResult to accumulate issues
        """
        if value is None or isinstance(value, (int, str, bool, datetime, date, time)):
            return

        if self.check_finite_float(value, path, result):
            return

        if isinstance(value, dict):
            self.check_string_keys_strict(value, path, result)
            self.walk_dict(value, path, result, self._walk)
            return

        if isinstance(value, list):
            if value and len(value) > 1:
                first_type = type(value[0])
                if not all(isinstance(elem, first_type) for elem in value):
                    result.add_warning(
                        path,
                        "all elements in list must be of the same type (TOML requirement)",
                    )
            self.walk_list(value, path, result, self._walk)
            return

        result.add_error(
            path, f"{value} (type {type(value).__name__}) is not a valid TOML value"
        )


class YAMLValidator(FloatCheckMixin, DictKeyCheckMixin, RecursiveWalkMixin):
    """Validator for YAML format.

    YAML requirements:
    - String keys are recommended (non-string keys generate warnings)
    - Supports a wide range of types including Decimal
    - Numbers must be finite
    """

    def validate(self, data: Any, path: str = "$") -> ValidationResult:
        """Validate data for YAML compatibility.

        Args:
            data: Data to validate
            path: Current path (default: "$")

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        self._walk(data, path, result)
        return result

    def _walk(self, value: Any, path: str, result: ValidationResult) -> None:
        """Recursively walk data structure and validate.

        Args:
            value: Current value to check
            path: Current path in data
            result: ValidationResult to accumulate issues
        """
        if value is None or isinstance(
            value, (int, str, bool, datetime, date, Decimal)
        ):
            return

        if self.check_finite_float(value, path, result):
            return

        if isinstance(value, dict):
            self.check_string_keys_soft(value, path, result)
            self.walk_dict(value, path, result, self._walk)
            return

        if isinstance(value, list):
            self.walk_list(value, path, result, self._walk)
            return

        result.add_error(
            path,
            f"{value!r} (type {type(value).__name__}) is not a valid YAML value",
        )


class XMLValidator(DictKeyCheckMixin, RecursiveWalkMixin):
    """Validator for XML format.

    XML requirements:
    - Keys must be strings (tag names and attributes)
    - Values must be convertible to strings
    """

    def validate(self, data: Any, path: str = "$") -> ValidationResult:
        """Validate data for XML compatibility.

        Args:
            data: Data to validate
            path: Current path (default: "$")

        Returns:
            ValidationResult with errors found
        """
        result = ValidationResult()
        self._walk(data, path, result)
        return result

    def _walk(self, value: Any, path: str, result: ValidationResult) -> None:
        """Recursively walk data structure and validate.

        Args:
            value: Current value to check
            path: Current path in data
            result: ValidationResult to accumulate issues
        """
        if isinstance(value, dict):
            self.check_string_keys_strict(value, path, result)
            self.walk_dict(value, path, result, self._walk)
            return

        if isinstance(value, list):
            self.walk_list(value, path, result, self._walk)
            return

        try:
            _ = str(value)
        except Exception as e:
            result.add_error(
                path,
                f"value {value!r} (type {type(value).__name__}) "
                f"is not convertible to string for XML: {e}",
            )


def validate(data: dict[str, Any], file_format: FileFormat) -> ValidationResult:
    """Validate data against format-specific requirements.

    Args:
        data: Data dictionary to validate
        file_format: Target file format

    Returns:
        ValidationResult with errors and warnings

    Raises:
        ValidationError: If format is not supported

    Example:
        >>> from src.io import FileFormat
        >>> data = {'name': 'John', 'age': 30}
        >>> result = validate(data, FileFormat.JSON)
        >>> assert result.is_valid()
    """
    logger.debug(f"Validating data for {file_format.value} format")

    validator: Validator
    if file_format == FileFormat.JSON:
        validator = JSONValidator()
    elif file_format == FileFormat.TOML:
        validator = TOMLValidator()
    elif file_format == FileFormat.YAML:
        validator = YAMLValidator()
    elif file_format == FileFormat.XML:
        validator = XMLValidator()
    else:
        raise ValidationError(f"Unsupported file format: {file_format}")

    result = validator.validate(data)

    if result.errors:
        logger.warning(
            f"Validation found {len(result.errors)} error(s) for {file_format.value}"
        )
    if result.warnings:
        logger.info(
            f"Validation found {len(result.warnings)} warning(s) for {file_format.value}"
        )

    return result


def format_validation_report(result: ValidationResult) -> str:
    """Format validation result into a human-readable report.

    Args:
        result: ValidationResult to format

    Returns:
        Formatted string with all errors and warnings

    Example:
        >>> result = ValidationResult()
        >>> result.add_error("$.users[0].age", "Invalid age value")
        >>> print(format_validation_report(result))
    """
    lines: list[str] = []

    if result.errors:
        lines.append("[X] Validation Errors:")
        for issue in result.errors:
            lines.append(f"  • [{issue.path}] {issue.message}")

    if result.warnings:
        if lines:
            lines.append("")
        lines.append("[!] Validation Warnings:")
        for issue in result.warnings:
            lines.append(f"  • [{issue.path}] {issue.message}")

    if not result.errors and not result.warnings:
        lines.append("[+] Validation passed - no issues found")

    return "\n".join(lines)
