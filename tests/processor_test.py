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
from src.parser import AndExpr, Comparison


class TestApplyPath:
    """Tests for JSONPath extraction."""

    def test_apply_path_simple(self):
        """Test simple path extraction."""
        data = {"name": "John", "age": 30}
        result = apply_path(data, "$.name")

        assert result == "John"

    def test_apply_path_nested(self):
        """Test nested path extraction."""
        data = {"user": {"profile": {"name": "Alice"}}}
        result = apply_path(data, "$.user.profile.name")

        assert result == "Alice"

    def test_apply_path_array(self):
        """Test array path extraction."""
        data = {"users": [{"name": "John"}, {"name": "Jane"}]}
        result = apply_path(data, "$.users[*].name")

        assert result == ["John", "Jane"]

    def test_apply_path_wildcard(self):
        """Test wildcard path."""
        data = {"users": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]}
        result = apply_path(data, "$.users[*]")

        assert len(result) == 2
        assert result[0]["name"] == "John"

    def test_apply_path_no_match(self):
        """Test empty result when no matches."""
        data = {"users": []}
        result = apply_path(data, "$.nonexistent")

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
        condition = Comparison("age", ">", 26)

        result = apply_conditions(data, condition)

        assert len(result) == 1
        assert result[0]["name"] == "John"

    def test_multiple_conditions_and_logic(self):
        """Test AND logic with multiple conditions."""
        data = [
            {"name": "John", "age": 30, "active": True},
            {"name": "Jane", "age": 25, "active": True},
            {"name": "Bob", "age": 35, "active": False},
        ]
        condition = AndExpr([
            Comparison("age", ">=", 26),
            Comparison("active", "==", True),
        ])

        result = apply_conditions(data, condition)

        assert len(result) == 1
        assert result[0]["name"] == "John"

    def test_empty_conditions_list(self):
        """Test no filtering when conditions are None."""
        data = [{"name": "John"}, {"name": "Jane"}]
        result = apply_conditions(data, None)

        assert len(result) == 2
        assert result == data

    def test_all_filtered_out(self):
        """Test when no items match."""
        data = [{"age": 20}, {"age": 22}]
        condition = Comparison("age", ">", 100)

        result = apply_conditions(data, condition)

        assert result == []

    def test_non_list_input_dict(self):
        """Test handling single dict (wraps in list)."""
        data = {"name": "John", "age": 30}
        condition = Comparison("age", ">", 25)

        result = apply_conditions(data, condition)  # type: ignore

        assert len(result) == 1
        assert result[0]["name"] == "John"


class TestProcessData:
    """Tests for combined path extraction and filtering."""

    def test_process_with_path_only(self):
        """Test processing with path, no conditions."""
        data = {"users": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]}

        result = process_data(data, "$.users[*]", None)

        assert len(result) == 2

    def test_process_with_conditions_only(self):
        """Test processing with conditions, no path."""
        data = {"users": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]}
        condition = Comparison("age", ">", 26)

        # This will try to filter the dict directly, which wraps it
        result = process_data(data, None, condition)

        # The dict itself doesn't have 'age' field, so it won't match
        assert result == []

    def test_process_combined(self):
        """Test path extraction followed by filtering."""
        data = {"users": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]}
        condition = Comparison("age", ">", 26)

        result = process_data(data, "$.users[*]", condition)

        assert len(result) == 1
        assert result[0]["name"] == "John"

    def test_process_no_path_no_conditions(self):
        """Test no processing returns original data."""
        data = {"test": "data"}

        result = process_data(data, None, None)

        assert result == data


class TestJSONPathGrammar:
    """Tests for advanced JSONPath parsing - Stage 3 implementation.
    
    These tests verify that the recursive grammar correctly handles:
    - Nested brackets at arbitrary depth
    - Quoted strings containing special characters
    - Filter expressions with nested brackets
    - Complex real-world JSONPath expressions
    """

    # Simple Cases
    def test_array_wildcard(self):
        """Test basic array wildcard."""
        data = {"users": [{"name": "John"}, {"name": "Jane"}]}
        result = apply_path(data, "$.users[*]")
        
        assert len(result) == 2
        assert result[0]["name"] == "John"
    
    def test_array_index(self):
        """Test array index access."""
        data = {"users": [{"name": "John"}, {"name": "Jane"}]}
        result = apply_path(data, "$.users[0]")
        
        assert result["name"] == "John"
    
    def test_negative_index(self):
        """Test negative array index."""
        data = {"users": [{"name": "John"}, {"name": "Jane"}]}
        result = apply_path(data, "$.users[-1]")
        
        assert result["name"] == "Jane"
    
    def test_array_slicing(self):
        """Test array slicing."""
        data = {"items": [1, 2, 3, 4, 5]}
        result = apply_path(data, "$.items[0:3]")
        
        assert result == [1, 2, 3]
    
    # Nested Brackets
    def test_single_nesting(self):
        """Test single level of bracket nesting."""
        data = {"users": [{"name": "John", "age": 30}]}
        result = apply_path(data, "$.users[0].name")
        
        assert result == "John"
    
    def test_double_nesting(self):
        """Test double nesting: data[0].items[1]"""
        data = {"data": [{"items": ["a", "b", "c"]}]}
        result = apply_path(data, "$.data[0].items[1]")
        
        assert result == "b"
    
    def test_triple_nesting(self):
        """Test triple nesting: users[0].addresses[1].codes[2]"""
        data = {
            "users": [
                {
                    "addresses": [
                        {"codes": []},
                        {"codes": ["x", "y", "z"]}
                    ]
                }
            ]
        }
        result = apply_path(data, "$.users[0].addresses[1].codes[2]")
        
        assert result == "z"
    
    def test_wildcard_with_nesting(self):
        """Test wildcard combined with nested access."""
        data = {
            "users": [
                {"items": ["a", "b"]},
                {"items": ["c", "d"]}
            ]
        }
        result = apply_path(data, "$.users[*].items[0]")
        
        assert result == ["a", "c"]
    
    # Quoted Strings
    def test_quoted_path(self):
        """Test simple quoted string in path."""
        data = {"users": {"name": "John"}}
        result = apply_path(data, '$.users["name"]')
        
        assert result == "John"
    
    def test_quoted_string_with_brackets(self):
        """Test quoted string containing brackets."""
        data = {"items": {"[test]": "value"}}
        result = apply_path(data, '$.items["[test]"]')
        
        assert result == "value"
    
    def test_recursive_descent(self):
        """Test recursive descent operator."""
        data = {
            "store": {
                "book": [
                    {"price": 10},
                    {"price": 20}
                ]
            }
        }
        result = apply_path(data, "$.store..price")
        
        assert result == [10, 20]


class TestBooleanFieldNegation:
    """Tests for boolean field negation in comparisons.
    
    Tests the new feature that supports:
    - Literal value negation: where status == !true
    - Field reference negation: where status == !active
    """
    
    def test_negated_literal_true(self):
        """Test negating literal 'true' in comparison."""
        from src.processor import evaluate_boolean_expr
        
        item = {"status": False}
        expr = Comparison("status", "==", (True, True))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_negated_literal_false(self):
        """Test negating literal 'false' in comparison."""
        from src.processor import evaluate_boolean_expr
        
        item = {"active": True}
        expr = Comparison("active", "==", (False, True))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_non_negated_literal(self):
        """Test non-negated literal value."""
        from src.processor import evaluate_boolean_expr
        
        item = {"enabled": True}
        expr = Comparison("enabled", "==", (True, False))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_field_reference_negation_match(self):
        """Test negating a field reference - matching case."""
        from src.processor import evaluate_boolean_expr
        
        item = {"status": True, "disabled": False}
        expr = Comparison("status", "==", ("disabled", True))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_field_reference_negation_no_match(self):
        """Test negating a field reference - non-matching case."""
        from src.processor import evaluate_boolean_expr
        
        item = {"status": False, "active": True}
        expr = Comparison("status", "==", ("active", True))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_field_reference_without_negation(self):
        """Test field reference without negation."""
        from src.processor import evaluate_boolean_expr
        
        item = {"enabled": True, "active": True}
        expr = Comparison("enabled", "==", ("active", False))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_nonexistent_field_reference(self):
        """Test negating a field that doesn't exist (treated as literal string)."""
        from src.processor import evaluate_boolean_expr
        
        item = {"name": "John"}
        expr = Comparison("name", "==", ("nonexistent", False))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is False
    
    def test_complex_and_with_negation(self):
        """Test AND expression with negated field reference."""
        from src.processor import evaluate_boolean_expr, AndExpr
        
        item = {"age": 30, "active": True, "locked": False}
        expr = AndExpr([
            Comparison("age", ">", 25),
            Comparison("active", "==", ("locked", True))
        ])
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_apply_conditions_with_field_negation(self):
        """Test filtering data with field reference negation."""
        data = [
            {"name": "Alice", "status": True, "disabled": False},
            {"name": "Bob", "status": False, "disabled": True},
            {"name": "Charlie", "status": True, "disabled": True},
        ]
        
        # Filter where status == !disabled
        expr = Comparison("status", "==", ("disabled", True))
        result = apply_conditions(data, expr)
        
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"
    
    def test_negation_with_inequality_operator(self):
        """Test negation with != operator."""
        from src.processor import evaluate_boolean_expr
        
        item = {"premium": True, "trial": True}
        expr = Comparison("premium", "!=", ("trial", True))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_field_reference_with_none_value(self):
        """Test field reference negation when field value is None."""
        from src.processor import evaluate_boolean_expr
        
        item = {"status": True, "disabled": None}
        expr = Comparison("status", "==", ("disabled", True))
        
        result = evaluate_boolean_expr(item, expr)
        # disabled is None, !None should be True (not of falsy value)
        assert result is True


class TestStandaloneFieldChecks:
    """Tests for standalone field boolean checks (where field, where !field)."""
    
    def test_truthy_field_check(self):
        """Test 'where field' syntax with truthy value."""
        from src.processor import evaluate_boolean_expr
        
        item = {"status": True}
        expr = Comparison("status", "==", (True, False))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_falsy_field_check_with_false(self):
        """Test 'where !field' syntax with False value."""
        from src.processor import evaluate_boolean_expr, NotExpr
        
        item = {"status": False}
        expr = NotExpr(Comparison("status", "==", (True, False)))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_truthy_field_check_fails_on_false(self):
        """Test 'where field' returns False when field is False."""
        from src.processor import evaluate_boolean_expr
        
        item = {"status": False}
        expr = Comparison("status", "==", (True, False))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is False
    
    def test_field_check_with_and(self):
        """Test field check in AND expression."""
        from src.processor import evaluate_boolean_expr, AndExpr
        
        item = {"active": True, "verified": True, "age": 25}
        expr = AndExpr([
            Comparison("active", "==", (True, False)),
            Comparison("verified", "==", (True, False)),
            Comparison("age", ">", (18, False))
        ])
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_field_check_with_or(self):
        """Test field check in OR expression."""
        from src.processor import evaluate_boolean_expr, OrExpr
        
        item = {"premium": False, "trial": True}
        expr = OrExpr([
            Comparison("premium", "==", (True, False)),
            Comparison("trial", "==", (True, False))
        ])
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_negated_field_with_true_value(self):
        """Test 'where !field' with field=True."""
        from src.processor import evaluate_boolean_expr, NotExpr
        
        item = {"locked": True}
        expr = NotExpr(Comparison("locked", "==", (True, False)))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is False
    
    def test_field_check_with_none_value(self):
        """Test field check treats None as falsy."""
        from src.processor import evaluate_boolean_expr
        
        item = {"status": None}
        expr = Comparison("status", "==", (True, False))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is False
    
    def test_field_check_with_nonexistent_field(self):
        """Test field check with non-existent field."""
        from src.processor import evaluate_boolean_expr
        
        item = {"other": True}
        expr = Comparison("status", "==", (True, False))
        
        result = evaluate_boolean_expr(item, expr)
        assert result is False
    
    def test_complex_nested_field_checks(self):
        """Test complex nesting: (active and !locked) or admin."""
        from src.processor import evaluate_boolean_expr, OrExpr, AndExpr, NotExpr
        
        item = {"active": True, "locked": False, "admin": False}
        expr = OrExpr([
            AndExpr([
                Comparison("active", "==", (True, False)),
                NotExpr(Comparison("locked", "==", (True, False)))
            ]),
            Comparison("admin", "==", (True, False))
        ])
        
        result = evaluate_boolean_expr(item, expr)
        assert result is True
    
    def test_apply_conditions_with_field_check(self):
        """Test filtering data using standalone field checks."""
        data = [
            {"name": "Alice", "active": True},
            {"name": "Bob", "active": False},
            {"name": "Charlie", "active": True},
        ]
        
        # Filter where active
        expr = Comparison("active", "==", (True, False))
        result = apply_conditions(data, expr)
        
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Charlie"
    
    def test_apply_conditions_with_negated_field_check(self):
        """Test filtering with negated field check."""
        from src.processor import NotExpr
        
        data = [
            {"name": "Alice", "disabled": False},
            {"name": "Bob", "disabled": True},
            {"name": "Charlie", "disabled": False},
        ]
        
        # Filter where !disabled
        expr = NotExpr(Comparison("disabled", "==", (True, False)))
        result = apply_conditions(data, expr)
        
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Charlie"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
