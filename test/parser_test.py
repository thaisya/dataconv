"""Unit tests for src/parser.py module.

Tests cover:
- Query parsing (QueryParser)
- Path specifications
- Conditions and operators
- Error handling
"""

import pytest

from src.parser import Condition, ParseError, PathSpec, QueryParser, QueryResult


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
        assert result["conditions"] == []

    def test_parse_with_source_path(self, parser):
        """Test query with JSONPath in source."""
        result = parser.parse("from data.json[users.*] to output.yaml")

        assert result["source"]["file"] == "data.json"
        assert result["source"]["path"] == "users.*"
        assert result["dest"]["file"] == "output.yaml"

    def test_parse_with_single_condition(self, parser):
        """Test WHERE clause with single condition."""
        result = parser.parse("from input.json to output.yaml where age > 25")

        assert len(result["conditions"]) == 1
        condition = result["conditions"][0]
        assert condition["field"] == "age"
        assert condition["op"] == ">"
        assert condition["value"] == 25.0

    def test_parse_with_multiple_conditions(self, parser):
        """Test WHERE with multiple AND conditions."""
        result = parser.parse(
            "from data.json to output.yaml where age >= 18 and status == \"active\""
        )

        assert len(result["conditions"]) == 2
        assert result["conditions"][0]["field"] == "age"
        assert result["conditions"][0]["op"] == ">="
        assert result["conditions"][0]["value"] == 18.0
        assert result["conditions"][1]["field"] == "status"
        assert result["conditions"][1]["op"] == "=="
        assert result["conditions"][1]["value"] == "active"

    def test_parse_equality_operator(self, parser):
        """Test == operator."""
        result = parser.parse("from data.json to out.yaml where name == \"John\"")
        assert result["conditions"][0]["op"] == "=="
        assert result["conditions"][0]["value"] == "John"

    def test_parse_inequality_operator(self, parser):
        """Test != operator."""
        result = parser.parse("from data.json to out.yaml where status != \"deleted\"")
        assert result["conditions"][0]["op"] == "!="

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
            assert result["conditions"][0]["op"] == expected_op

    def test_parse_string_value(self, parser):
        """Test string value parsing."""
        result = parser.parse("from data.json to out.yaml where name == \"Alice\"")
        assert result["conditions"][0]["value"] == "Alice"

    def test_parse_number_value(self, parser):
        """Test number value parsing."""
        result = parser.parse("from data.json to out.yaml where age == 30")
        assert result["conditions"][0]["value"] == 30.0

    def test_parse_boolean_true(self, parser):
        """Test boolean true value."""
        result = parser.parse("from data.json to out.yaml where active == true")
        assert result["conditions"][0]["value"] is True

    def test_parse_boolean_false(self, parser):
        """Test boolean false value."""
        result = parser.parse("from data.json to out.yaml where active == false")
        assert result["conditions"][0]["value"] is False

    def test_parse_null_value(self, parser):
        """Test null value."""
        result = parser.parse("from data.json to out.yaml where metadata == null")
        assert result["conditions"][0]["value"] is None

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
            "from input.json",  # Missing "to"
            "to output.yaml",  # Missing "from"
            "from input.json to",  # Missing destination
        ]

        for query in invalid_queries:
            with pytest.raises(ParseError):
                parser.parse(query)

    def test_parse_complex_query(self, parser):
        """Test complex query with all features."""
        result = parser.parse(
            "from data.json[users.*] to filtered.yaml "
            "where age >= 18 and status == \"active\" and score > 80"
        )

        assert result["source"]["file"] == "data.json"
        assert result["source"]["path"] == "users.*"
        assert result["dest"]["file"] == "filtered.yaml"
        assert len(result["conditions"]) == 3


class TestConditionTypedDict:
    """Test Condition TypedDict structure."""

    def test_condition_structure(self):
        """Test creating a Condition."""
        condition: Condition = {"field": "age", "op": ">", "value": 25}

        assert condition["field"] == "age"
        assert condition["op"] == ">"
        assert condition["value"] == 25


class TestPathSpecTypedDict:
    """Test PathSpec TypedDict structure."""

    def test_pathspec_with_path(self):
        """Test PathSpec with JSONPath."""
        path_spec: PathSpec = {"file": "data.json", "path": "users.*"}

        assert path_spec["file"] == "data.json"
        assert path_spec["path"] == "users.*"

    def test_pathspec_without_path(self):
        """Test PathSpec without JSONPath."""
        path_spec: PathSpec = {"file": "data.json", "path": None}

        assert path_spec["file"] == "data.json"
        assert path_spec["path"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
