"""Unit tests for src/parser.py module.

Tests cover:
- Query parsing (QueryParser)
- Path specifications
- Conditions and operators
- Boolean expressions (AND, OR, NOT, XOR)
- Parentheses grouping
- Error handling
"""

import pytest

from src.parser import (
    AndExpr,
    Comparison,
    NotExpr,
    OrExpr,
    ParseError,
    PathSpec,
    QueryParser,
    XorExpr,
)


class TestQueryParser:
    """Tests for QueryParser class."""

    @pytest.fixture
    def parser(self):
        """Create a QueryParser instance."""
        return QueryParser()

    def test_parse_simple_query(self, parser):
        """Test basic 'from X to Y' query."""
        result = parser.parse("from input.json to output.yaml")

        assert result["source"]["file"] == "input.json"
        assert result["source"]["path"] is None
        assert result["dest"]["file"] == "output.yaml"
        assert result["dest"]["path"] is None
        assert result["conditions"] is None

    def test_parse_with_source_path(self, parser):
        """Test query with JSONPath in source."""
        result = parser.parse("from data.json[$.users[*]] to output.yaml")

        assert result["source"]["file"] == "data.json"
        assert result["source"]["path"] == "$.users[*]"
        assert result["dest"]["file"] == "output.yaml"

    def test_parse_with_single_condition(self, parser):
        """Test WHERE clause with single condition."""
        result = parser.parse("from input.json to output.yaml where age > 25")

        assert isinstance(result["conditions"], Comparison)
        assert result["conditions"].field == "age"
        assert result["conditions"].op == ">"
        assert result["conditions"].value == (25.0, False)

    def test_parse_with_and_conditions(self, parser):
        """Test WHERE with multiple AND conditions."""
        result = parser.parse(
            "from data.json to output.yaml where age >= 18 and status == \"active\""
        )

        assert isinstance(result["conditions"], AndExpr)
        assert len(result["conditions"].exprs) == 2
        assert isinstance(result["conditions"].exprs[0], Comparison)
        assert result["conditions"].exprs[0].field == "age"
        assert result["conditions"].exprs[1].field == "status"

    def test_parse_with_or_operator(self, parser):
        """Test OR operator."""
        result = parser.parse(
            "from data.json to output.yaml where age < 18 or premium == true"
        )

        assert isinstance(result["conditions"], OrExpr)
        assert len(result["conditions"].exprs) == 2

    def test_parse_with_not_operator(self, parser):
        """Test NOT (!) operator."""
        result = parser.parse(
            "from data.json to output.yaml where !(status == \"inactive\")"
        )

        assert isinstance(result["conditions"], NotExpr)
        assert isinstance(result["conditions"].expr, Comparison)
        assert result["conditions"].expr.field == "status"

    def test_parse_with_xor_operator(self, parser):
        """Test XOR operator."""
        result = parser.parse(
            "from data.json to output.yaml where premium == true xor trial == true"
        )

        assert isinstance(result["conditions"], XorExpr)
        assert len(result["conditions"].exprs) == 2

    def test_parse_with_parentheses(self, parser):
        """Test parentheses grouping."""
        result = parser.parse(
            "from data.json to output.yaml where (age > 18 and status == \"active\") or role == \"admin\""
        )

        assert isinstance(result["conditions"], OrExpr)
        assert isinstance(result["conditions"].exprs[0], AndExpr)

    def test_parse_complex_nested_expression(self, parser):
        """Test complex nested boolean expression."""
        result = parser.parse(
            "from data.json to output.yaml where "
            "(age >= 18 and !(status == \"inactive\")) or trial == true"
        )

        assert isinstance(result["conditions"], OrExpr)
        and_expr = result["conditions"].exprs[0]
        assert isinstance(and_expr, AndExpr)
        assert isinstance(and_expr.exprs[1], NotExpr)

    def test_operator_precedence(self, parser):
        """Test operator precedence: AND before OR."""
        result = parser.parse(
            "from data.json to output.yaml where age < 18 or age > 65 and retired == true"
        )

        assert isinstance(result["conditions"], OrExpr)
        assert isinstance(result["conditions"].exprs[0], Comparison)
        assert isinstance(result["conditions"].exprs[1], AndExpr)

    def test_parse_equality_operator(self, parser):
        """Test == operator."""
        result = parser.parse("from data.json to out.yaml where name == \"John\"")
        assert result["conditions"].op == "=="
        assert result["conditions"].value == ("John", False)

    def test_parse_inequality_operator(self, parser):
        """Test != operator."""
        result = parser.parse("from data.json to out.yaml where status != \"deleted\"")
        assert result["conditions"].op == "!="

    def test_parse_comparison_operators(self, parser):
        """Test >, <, >=, <= operators."""
        queries = [
            ("where age > 18", ">"),
            ("where age < 65", "<"),
            ("where score >= 90", ">="),
            ("where price <= 100", "<="),
        ]

        for where_clause, expected_op in queries:
            result = parser.parse(f"from data.json to out.yaml {where_clause}")
            assert result["conditions"].op == expected_op

    def test_parse_string_value(self, parser):
        """Test string value parsing."""
        result = parser.parse("from data.json to out.yaml where name == \"Alice\"")
        assert result["conditions"].value == ("Alice", False)

    def test_parse_number_value(self, parser):
        """Test number value parsing."""
        result = parser.parse("from data.json to out.yaml where age == 30")
        assert result["conditions"].value == (30.0, False)

    def test_parse_boolean_true(self, parser):
        """Test boolean true value."""
        result = parser.parse("from data.json to out.yaml where active == true")
        assert result["conditions"].value == (True, False)

    def test_parse_boolean_false(self, parser):
        """Test boolean false value."""
        result = parser.parse("from data.json to out.yaml where active == false")
        assert result["conditions"].value == (False, False)

    def test_parse_null_value(self, parser):
        """Test null value."""
        result = parser.parse("from data.json to out.yaml where metadata == null")
        assert result["conditions"].value == (None, False)

    def test_parse_nested_path(self, parser):
        """Test nested path expression."""
        result = parser.parse("from data.json[user.profile.email] to out.yaml")
        assert result["source"]["path"] == "user.profile.email"

    def test_parse_quoted_file_paths(self, parser):
        """Test quoted file paths with spaces."""
        result = parser.parse('from "my data.json" to "output file.yaml"')
        assert result["source"]["file"] == "my data.json"
        assert result["dest"]["file"] == "output file.yaml"

    def test_parse_invalid_syntax(self, parser):
        """Test ParseError on invalid query syntax."""
        invalid_queries = [
            "invalid query",
            "to output.yaml",
            "from input.json to",
        ]

        for query in invalid_queries:
            with pytest.raises(ParseError):
                parser.parse(query)

    def test_parse_complex_query_with_all_features(self, parser):
        """Test complex query with multiple operators."""
        result = parser.parse(
            "from data.json[$.users[*]] to filtered.yaml "
            "where (age >= 18 and status == \"active\") or premium == true"
        )

        assert result["source"]["file"] == "data.json"
        assert result["source"]["path"] == "$.users[*]"
        assert result["dest"]["file"] == "filtered.yaml"
        assert isinstance(result["conditions"], OrExpr)


class TestBooleanExpressions:
    """Tests specifically for boolean expression structures."""

    @pytest.fixture
    def parser(self):
        return QueryParser()

    def test_triple_and(self, parser):
        """Test three conditions with AND."""
        result = parser.parse(
            "from data.json to out.yaml where a == 1 and b == 2 and c == 3"
        )
        assert isinstance(result["conditions"], AndExpr)
        assert len(result["conditions"].exprs) == 3

    def test_triple_or(self, parser):
        """Test three conditions with OR."""
        result = parser.parse(
            "from data.json to out.yaml where a == 1 or b == 2 or c == 3"
        )
        assert isinstance(result["conditions"], OrExpr)
        assert len(result["conditions"].exprs) == 3

    def test_double_negation(self, parser):
        """Test NOT of NOT."""
        result = parser.parse("from data.json to out.yaml where !!(status == \"active\")")
        assert isinstance(result["conditions"], NotExpr)
        assert isinstance(result["conditions"].expr, NotExpr)

    def test_complex_xor(self, parser):
        """Test XOR with complex expressions."""
        result = parser.parse(
            "from data.json to out.yaml where "
            "(premium == true and trial == false) xor (premium == false and trial == true)"
        )
        assert isinstance(result["conditions"], XorExpr)


class TestParseConditions:
    """Tests for _parse_conditions() method (Phase 2)."""

    @pytest.fixture
    def parser(self):
        """Create a QueryParser instance."""
        return QueryParser()

    def test_parse_simple_comparison(self, parser):
        """Test parsing simple comparison without full query."""
        expr = parser._parse_conditions("age > 25")
        
        assert isinstance(expr, Comparison)
        assert expr.field == "age"
        assert expr.op == ">"
        assert expr.value == (25.0, False)

    def test_parse_and_expression(self, parser):
        """Test parsing AND expression."""
        expr = parser._parse_conditions('age >= 18 and status == "active"')
        
        assert isinstance(expr, AndExpr)
        assert len(expr.exprs) == 2
        assert expr.exprs[0].field == "age"
        assert expr.exprs[1].field == "status"

    def test_parse_or_expression(self, parser):
        """Test parsing OR expression."""
        expr = parser._parse_conditions("age < 18 or premium == true")
        
        assert isinstance(expr, OrExpr)
        assert len(expr.exprs) == 2
        assert expr.exprs[0].field == "age"
        assert expr.exprs[1].field == "premium"

    def test_parse_not_expression(self, parser):
        """Test parsing NOT expression."""
        expr = parser._parse_conditions('!(status == "inactive")')
        
        assert isinstance(expr, NotExpr)
        assert isinstance(expr.expr, Comparison)
        assert expr.expr.field == "status"

    def test_parse_xor_expression(self, parser):
        """Test parsing XOR expression."""
        expr = parser._parse_conditions("premium == true xor trial == true")
        
        assert isinstance(expr, XorExpr)
        assert len(expr.exprs) == 2

    def test_parse_complex_nested(self, parser):
        """Test parsing complex nested expression."""
        expr = parser._parse_conditions(
            '(age >= 18 and !(status == "inactive")) or trial == true'
        )
        
        assert isinstance(expr, OrExpr)
        assert isinstance(expr.exprs[0], AndExpr)
        assert isinstance(expr.exprs[0].exprs[1], NotExpr)

    def test_parse_with_parentheses(self, parser):
        """Test parsing with parentheses grouping."""
        expr = parser._parse_conditions(
            '(age > 18 and status == "active") or role == "admin"'
        )
        
        assert isinstance(expr, OrExpr)
        assert isinstance(expr.exprs[0], AndExpr)
        assert isinstance(expr.exprs[1], Comparison)

    def test_parse_invalid_expression(self, parser):
        """Test that invalid expressions raise ParseError."""
        with pytest.raises(ParseError):
            parser._parse_conditions("age > ")
        
        with pytest.raises(ParseError):
            parser._parse_conditions("== 25")
        
        with pytest.raises(ParseError):
            parser._parse_conditions("age >< 25")


class TestPathSpecTypedDict:
    """Test PathSpec TypedDict structure."""

    def test_pathspec_with_path(self):
        """Test PathSpec with JSONPath."""
        path_spec: PathSpec = {"file": "data.json", "path": "$.users[*]"}

        assert path_spec["file"] == "data.json"
        assert path_spec["path"] == "$.users[*]"

    def test_pathspec_without_path(self):
        """Test PathSpec without JSONPath."""
        path_spec: PathSpec = {"file": "data.json", "path": None}

        assert path_spec["file"] == "data.json"
        assert path_spec["path"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
