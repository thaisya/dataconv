"""Unit tests for src/grammar.py module.

Tests cover:
- Grammar constant existence
- Grammar structure validation
- Basic parsing capability
"""

import pytest
from lark import Lark

from src.grammar import QUERY_GRAMMAR


class TestQueryGrammar:
    """Tests for QUERY_GRAMMAR constant."""

    def test_grammar_exists(self):
        """Test that QUERY_GRAMMAR constant exists."""
        assert QUERY_GRAMMAR is not None

    def test_grammar_is_string(self):
        """Test that QUERY_GRAMMAR is a string."""
        assert isinstance(QUERY_GRAMMAR, str)

    def test_grammar_not_empty(self):
        """Test that grammar is not empty."""
        assert len(QUERY_GRAMMAR) > 0

    def test_grammar_contains_start_rule(self):
        """Test that grammar contains start rule."""
        assert "query" in QUERY_GRAMMAR or "start" in QUERY_GRAMMAR

    def test_grammar_parseable_by_lark(self):
        """Test that Lark can parse the grammar definition."""
        try:
            parser = Lark(QUERY_GRAMMAR, parser="lalr")
            assert parser is not None
        except Exception as e:
            pytest.fail(f"Grammar is not valid Lark syntax: {e}")

    def test_grammar_parses_simple_query(self):
        """Test that grammar can parse a basic query."""
        parser = Lark(QUERY_GRAMMAR, parser="lalr")

        try:
            tree = parser.parse("from input.json to output.yaml")
            assert tree is not None
        except Exception as e:
            pytest.fail(f"Grammar failed to parse simple query: {e}")

    def test_grammar_parses_with_conditions(self):
        """Test that grammar can parse queries with WHERE clause."""
        parser = Lark(QUERY_GRAMMAR, parser="lalr")

        try:
            tree = parser.parse("from data.json to output.yaml where age > 25")
            assert tree is not None
        except Exception as e:
            pytest.fail(f"Grammar failed to parse query with conditions: {e}")

    def test_grammar_parses_with_path(self):
        """Test that grammar can parse queries with JSONPath."""
        parser = Lark(QUERY_GRAMMAR, parser="lalr")

        try:
            tree = parser.parse("from data.json[users.*] to output.yaml")
            assert tree is not None
        except Exception as e:
            pytest.fail(f"Grammar failed to parse query with path: {e}")

    def test_grammar_rejects_invalid_syntax(self):
        """Test that grammar rejects invalid queries."""
        parser = Lark(QUERY_GRAMMAR, parser="lalr")

        invalid_queries = [
            "invalid query",
            "from only",
            "to only",
            "where age > 25",  # Missing from/to
        ]

        for query in invalid_queries:
            with pytest.raises(Exception):  # Lark raises various parse exceptions
                parser.parse(query)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
