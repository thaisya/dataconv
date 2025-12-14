"""Unit tests for src/processor.py module.

Tests cover:
- JSONPath extraction (apply_path)
- Condition evaluation (evaluate_condition)
- Data filtering (apply_conditions)
- Combined processing (process_data)
"""

import pytest

from src.processor import (
    ProcessorError,
    apply_conditions,
    apply_path,
    evaluate_condition,
    process_data,
)


class TestApplyPath:
    """Tests for JSONPath extraction."""

    def test_apply_path_simple(self):
        """Test simple path extraction."""
        data = {"name": "John", "age": 30}
        result = apply_path(data, "name")

        assert result == "John"

    def test_apply_path_nested(self):
        """Test nested path extraction."""
        data = {"user": {"profile": {"name": "Alice"}}}
        result = apply_path(data, "user.profile.name")

        assert result == "Alice"

    def test_apply_path_array(self):
        """Test array path extraction."""
        data = {"users": [{"name": "John"}, {"name": "Jane"}]}
        result = apply_path(data, "users[*].name")

        assert result == ["John", "Jane"]

    def test_apply_path_wildcard(self):
        """Test wildcard path."""
        data = {"users": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]}
        result = apply_path(data, "users.*")

        assert len(result) == 2
        assert result[0]["name"] == "John"

    def test_apply_path_no_match(self):
        """Test empty result when no matches."""
        data = {"users": []}
        result = apply_path(data, "nonexistent")

        assert result == []

    def test_apply_path_none(self):
        """Test None path returns original data."""
        data = {"test": "data"}
        result = apply_path(data, None)

        assert result == data

    def test_apply_path_empty_string(self):
        """Test empty string path returns original data."""
        data = {"test": "data"}
        result = apply_path(data, "")

        assert result == data

    def test_apply_path_invalid_syntax(self):
        """Test ProcessorError on invalid JSONPath."""
        data = {"test": "data"}

        with pytest.raises(ProcessorError) as exc_info:
            apply_path(data, "[[[invalid")

        assert "Invalid JSONPath" in str(exc_info.value)


class TestEvaluateCondition:
    """Tests for condition evaluation."""

    def test_equality_operator(self):
        """Test == operator."""
        assert evaluate_condition(30, "==", 30) is True
        assert evaluate_condition(30, "==", 25) is False
        assert evaluate_condition("John", "==", "John") is True
        assert evaluate_condition("John", "==", "Jane") is False

    def test_inequality_operator(self):
        """Test != operator."""
        assert evaluate_condition(30, "!=", 25) is True
        assert evaluate_condition(30, "!=", 30) is False

    def test_greater_than(self):
        """Test > operator."""
        assert evaluate_condition(30, ">", 25) is True
        assert evaluate_condition(25, ">", 30) is False
        assert evaluate_condition(30, ">", 30) is False

    def test_less_than(self):
        """Test < operator."""
        assert evaluate_condition(25, "<", 30) is True
        assert evaluate_condition(30, "<", 25) is False
        assert evaluate_condition(30, "<", 30) is False

    def test_greater_equal(self):
        """Test >= operator."""
        assert evaluate_condition(30, ">=", 30) is True
        assert evaluate_condition(30, ">=", 25) is True
        assert evaluate_condition(25, ">=", 30) is False

    def test_less_equal(self):
        """Test <= operator."""
        assert evaluate_condition(30, "<=", 30) is True
        assert evaluate_condition(25, "<=", 30) is True
        assert evaluate_condition(30, "<=", 25) is False

    def test_type_coercion(self):
        """Test int/float comparison with type coercion."""
        assert evaluate_condition(30, "==", 30.0) is True
        assert evaluate_condition(30.5, ">", 30) is True
        assert evaluate_condition(25, "<", 25.5) is True

    def test_null_comparison(self):
        """Test None/null handling."""
        assert evaluate_condition(None, "==", None) is True
        assert evaluate_condition(None, "!=", None) is False
        assert evaluate_condition(None, "==", 5) is False
        assert evaluate_condition(5, "==", None) is False
        assert evaluate_condition(None, ">", 5) is False

    def test_unsupported_operator(self):
        """Test error on unsupported operator."""
        with pytest.raises(ProcessorError) as exc_info:
            evaluate_condition(30, "~=", 30)

        assert "Unsupported operator" in str(exc_info.value)


class TestApplyConditions:
    """Tests for data filtering with conditions."""

    def test_single_condition(self):
        """Test filtering with one condition."""
        data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
        conditions = [{"field": "age", "op": ">", "value": 26}]

        result = apply_conditions(data, conditions)

        assert len(result) == 1
        assert result[0]["name"] == "John"

    def test_multiple_conditions_and_logic(self):
        """Test AND logic with multiple conditions."""
        data = [
            {"name": "John", "age": 30, "active": True},
            {"name": "Jane", "age": 25, "active": True},
            {"name": "Bob", "age": 35, "active": False},
        ]
        conditions = [
            {"field": "age", "op": ">=", "value": 26},
            {"field": "active", "op": "==", "value": True},
        ]

        result = apply_conditions(data, conditions)

        assert len(result) == 1
        assert result[0]["name"] == "John"

    def test_empty_conditions_list(self):
        """Test no filtering when conditions are empty."""
        data = [{"name": "John"}, {"name": "Jane"}]
        result = apply_conditions(data, [])

        assert len(result) == 2
        assert result == data

    def test_all_filtered_out(self):
        """Test when no items match."""
        data = [{"age": 20}, {"age": 22}]
        conditions = [{"field": "age", "op": ">", "value": 100}]

        result = apply_conditions(data, conditions)

        assert result == []

    def test_non_list_input_dict(self):
        """Test handling single dict (wraps in list)."""
        data = {"name": "John", "age": 30}
        conditions = [{"field": "age", "op": ">", "value": 25}]

        result = apply_conditions(data, conditions)  # type: ignore

        assert len(result) == 1
        assert result[0]["name"] == "John"


class TestProcessData:
    """Tests for combined path extraction and filtering."""

    def test_process_with_path_only(self):
        """Test processing with path, no conditions."""
        data = {"users": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]}

        result = process_data(data, "users.*", [])

        assert len(result) == 2

    def test_process_with_conditions_only(self):
        """Test processing with conditions, no path."""
        data = {"users": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]}
        conditions = [{"field": "age", "op": ">", "value": 26}]

        # This will try to filter the dict directly, which wraps it
        result = process_data(data, None, conditions)

        # The dict itself doesn't have 'age' field, so it won't match
        assert result == []

    def test_process_combined(self):
        """Test path extraction followed by filtering."""
        data = {"users": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]}
        conditions = [{"field": "age", "op": ">", "value": 26}]

        result = process_data(data, "users.*", conditions)

        assert len(result) == 1
        assert result[0]["name"] == "John"

    def test_process_no_path_no_conditions(self):
        """Test no processing returns original data."""
        data = {"test": "data"}

        result = process_data(data, None, [])

        assert result == data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
