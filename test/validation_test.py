"""Unit tests for src/validation.py module.

Tests cover:
- JSON validator
- TOML validator
- YAML validator
- XML validator
- Validation results and reporting
"""

import math
from datetime import date, datetime

import pytest

from src.io import FileFormat
from src.validation import (
    JSONValidator,
    TOMLValidator,
    ValidationError,
    ValidationResult,
    XMLValidator,
    YAMLValidator,
    format_validation_report,
    validate,
)


class TestJSONValidator:
    """Tests for JSON format validator."""

    def test_valid_json_data(self):
        """Test valid JSON data passes validation."""
        validator = JSONValidator()
        data = {"name": "John", "age": 30, "active": True, "tags": ["a", "b"]}

        result = validator.validate(data)

        assert result.is_valid()
        assert len(result.errors) == 0

    def test_non_string_key_error(self):
        """Test error on non-string dictionary keys."""
        validator = JSONValidator()
        data = {1: "value"}  # Integer key

        result = validator.validate(data)

        assert not result.is_valid()
        assert len(result.errors) == 1
        assert "non-string key" in result.errors[0].message

    def test_nan_value_error(self):
        """Test error on NaN values."""
        validator = JSONValidator()
        data = {"value": float("nan")}

        result = validator.validate(data)

        assert not result.is_valid()
        assert "non-finite float" in result.errors[0].message

    def test_infinity_value_error(self):
        """Test error on Infinity values."""
        validator = JSONValidator()
        data = {"value": float("inf")}

        result = validator.validate(data)

        assert not result.is_valid()
        assert "non-finite float" in result.errors[0].message

    def test_nested_structure(self):
        """Test validation of nested structures."""
        validator = JSONValidator()
        data = {"user": {"profile": {"name": "Alice", "settings": {"theme": "dark"}}}}

        result = validator.validate(data)

        assert result.is_valid()


class TestTOMLValidator:
    """Tests for TOML format validator."""

    def test_valid_toml_data(self):
        """Test valid TOML data passes."""
        validator = TOMLValidator()
        data = {"name": "John", "age": 30, "active": True}

        result = validator.validate(data)

        assert result.is_valid()

    def test_heterogeneous_array_warning(self):
        """Test warning on mixed-type arrays."""
        validator = TOMLValidator()
        data = {"mixed": [1, "string", True]}  # Mixed types

        result = validator.validate(data)

        # Should have warnings but still be valid (no errors)
        assert result.is_valid()
        assert len(result.warnings) > 0
        assert "same type" in result.warnings[0].message

    def test_datetime_support(self):
        """Test datetime type support."""
        validator = TOMLValidator()
        data = {"created": datetime(2024, 1, 1, 12, 0, 0), "date": date(2024, 1, 1)}

        result = validator.validate(data)

        assert result.is_valid()

    def test_homogeneous_array_valid(self):
        """Test homogeneous arrays are valid."""
        validator = TOMLValidator()
        data = {"numbers": [1, 2, 3], "strings": ["a", "b", "c"]}

        result = validator.validate(data)

        assert result.is_valid()
        assert len(result.warnings) == 0


class TestYAMLValidator:
    """Tests for YAML format validator."""

    def test_valid_yaml_data(self):
        """Test valid YAML data passes."""
        validator = YAMLValidator()
        data = {"name": "John", "age": 30, "tags": ["python", "testing"]}

        result = validator.validate(data)

        assert result.is_valid()

    def test_non_string_key_warning(self):
        """Test warning (not error) on non-string keys."""
        validator = YAMLValidator()
        data = {1: "value"}  # Integer key

        result = validator.validate(data)

        # YAML allows non-string keys but warns
        assert result.is_valid()  # No errors
        assert len(result.warnings) > 0
        assert "non-string key" in result.warnings[0].message

    def test_decimal_support(self):
        """Test Decimal type support."""
        from decimal import Decimal

        validator = YAMLValidator()
        data = {"price": Decimal("19.99")}

        result = validator.validate(data)

        assert result.is_valid()


class TestXMLValidator:
    """Tests for XML format validator."""

    def test_valid_xml_data(self):
        """Test valid XML-compatible data."""
        validator = XMLValidator()
        data = {"root": {"user": {"name": "John", "age": "30"}}}

        result = validator.validate(data)

        assert result.is_valid()

    def test_non_string_key_error(self):
        """Test error on non-string keys."""
        validator = XMLValidator()
        data = {1: "value"}  # Integer key not allowed in XML

        result = validator.validate(data)

        assert not result.is_valid()
        assert "non-string key" in result.errors[0].message


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_is_valid_no_errors(self):
        """Test is_valid returns True when no errors."""
        result = ValidationResult()

        assert result.is_valid()

    def test_is_valid_with_warnings(self):
        """Test is_valid returns True with only warnings."""
        result = ValidationResult()
        result.add_warning("$.field", "This is a warning")

        assert result.is_valid()
        assert len(result.warnings) == 1

    def test_is_valid_with_errors(self):
        """Test is_valid returns False with errors."""
        result = ValidationResult()
        result.add_error("$.field", "This is an error")

        assert not result.is_valid()
        assert len(result.errors) == 1

    def test_add_error_method(self):
        """Test adding errors."""
        result = ValidationResult()
        result.add_error("$.users[0].age", "Age must be positive")

        assert len(result.errors) == 1
        assert result.errors[0].path == "$.users[0].age"
        assert result.errors[0].message == "Age must be positive"

    def test_add_warning_method(self):
        """Test adding warnings."""
        result = ValidationResult()
        result.add_warning("$.config", "Deprecated field")

        assert len(result.warnings) == 1
        assert result.warnings[0].path == "$.config"


class TestValidateFunctionFactory:
    """Tests for validate() factory function."""

    def test_validate_json_format(self):
        """Test validate dispatches to JSON validator."""
        data = {"name": "John", "age": 30}
        result = validate(data, FileFormat.JSON)

        assert isinstance(result, ValidationResult)
        assert result.is_valid()

    def test_validate_toml_format(self):
        """Test validate dispatches to TOML validator."""
        data = {"name": "John", "age": 30}
        result = validate(data, FileFormat.TOML)

        assert isinstance(result, ValidationResult)

    def test_validate_yaml_format(self):
        """Test validate dispatches to YAML validator."""
        data = {"name": "John"}
        result = validate(data, FileFormat.YAML)

        assert isinstance(result, ValidationResult)

    def test_validate_xml_format(self):
        """Test validate dispatches to XML validator."""
        data = {"root": {"name": "John"}}
        result = validate(data, FileFormat.XML)

        assert isinstance(result, ValidationResult)


class TestFormatValidationReport:
    """Tests for validation report formatting."""

    def test_report_with_no_issues(self):
        """Test report when validation passes."""
        result = ValidationResult()
        report = format_validation_report(result)

        assert "[+] Validation passed" in report

    def test_report_with_errors_only(self):
        """Test report with only errors."""
        result = ValidationResult()
        result.add_error("$.field1", "Error 1")
        result.add_error("$.field2", "Error 2")

        report = format_validation_report(result)

        assert "[X] Validation Errors:" in report
        assert "$.field1" in report
        assert "$.field2" in report

    def test_report_with_warnings_only(self):
        """Test report with only warnings."""
        result = ValidationResult()
        result.add_warning("$.field1", "Warning 1")

        report = format_validation_report(result)

        assert "[!] Validation Warnings:" in report
        assert "$.field1" in report

    def test_report_with_both(self):
        """Test report with both errors and warnings."""
        result = ValidationResult()
        result.add_error("$.error_field", "This is an error")
        result.add_warning("$.warning_field", "This is a warning")

        report = format_validation_report(result)

        assert "[X] Validation Errors:" in report
        assert "[!] Validation Warnings:" in report
        assert "error_field" in report
        assert "warning_field" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
