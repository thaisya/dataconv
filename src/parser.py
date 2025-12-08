"""Parser and transformer for the Data Converter query language.

This module provides parsing capabilities for the data conversion query syntax
using Lark parser. It transforms the parse tree into typed Python data structures.

Example:
    >>> from src.parser import QueryParser
    >>> parser = QueryParser()
    >>> result = parser.parse('from input.json[users.*] to output.yaml where age > 25')
    >>> print(result['source']['file'])
    'input.json'
"""

import logging
from typing import Any, TypedDict

from lark import Lark, Token, Transformer

from src.grammar import QUERY_GRAMMAR

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Exception raised when query parsing fails."""

    pass


class Condition(TypedDict):
    """Represents a single filter condition.

    Attributes:
        field: The field name to filter on
        op: The comparison operator (==, !=, >, <, >=, <=)
        value: The value to compare against
    """

    field: str
    op: str
    value: Any


class PathSpec(TypedDict):
    """Represents a file path with optional JSONPath expression.

    Attributes:
        file: The file path/name
        path: Optional JSONPath expression for data extraction
    """

    file: str
    path: str | None


class QueryResult(TypedDict):
    """Result of parsing a query.

    Attributes:
        source: Source file path specification
        dest: Destination file path specification
        conditions: List of filter conditions (empty if no where clause)
    """

    source: PathSpec
    dest: PathSpec
    conditions: list[Condition]


class QueryTransformer(Transformer):
    """Transforms Lark parse tree into typed Python structures.

    This class inherits from Lark's Transformer and implements methods
    to convert each grammar rule into appropriate Python types.
    """

    def NAME(self, token: Token) -> str:
        """Transform NAME token to string."""
        return str(token.value)

    def ESCAPED_STRING(self, token: Token) -> str:
        """Transform ESCAPED_STRING token to string (removes quotes)."""
        return str(token.value[1:-1])

    def SIGNED_NUMBER(self, token: Token) -> float:
        """Transform SIGNED_NUMBER token to float."""
        return float(token.value)

    def TRUE(self, token: Token) -> bool:
        """Transform TRUE token to boolean True."""
        return True

    def FALSE(self, token: Token) -> bool:
        """Transform FALSE token to boolean False."""
        return False

    def NULL(self, token: Token) -> None:
        """Transform NULL token to None."""
        return None

    def OP(self, token: Token) -> str:
        """Transform OP token to operator string."""
        return str(token.value)

    def condition(self, children: list[Any]) -> Condition:
        """Transform condition rule to Condition TypedDict.

        Args:
            children: List containing [field, op, value]

        Returns:
            Condition dictionary with field, op, and value
        """
        return {"field": children[0], "op": children[1], "value": children[2]}

    def condition_list(self, children: list[Condition]) -> list[Condition]:
        """Transform condition_list to list of Conditions."""
        return children

    def file_path(self, children: list[Any]) -> PathSpec:
        """Transform file_path rule to PathSpec.

        Args:
            children: List containing [file] or [file, path]

        Returns:
            PathSpec dictionary with file and optional path
        """
        file = str(children[0])
        path = children[1] if len(children) > 1 else None
        return {"file": file, "path": path}

    def path_bracket(self, children: list[Any]) -> str:
        """Transform path_bracket to path expression string.

        Args:
            children: List containing the path expression

        Returns:
            Path expression string
        """
        return children[0]

    def path_expression(self, children: list[Any]) -> str:
        """Transform path_expression to dot-separated string.

        Args:
            children: List of name components and optional wildcard

        Returns:
            Dot-separated path string (e.g., "users.name" or "users.*")
        """
        parts = [str(c) for c in children if str(c) != "."]

        # Handle array wildcard
        if parts and parts[-1] == "*":
            parts[-2] += "*"
            parts.pop()

        return ".".join(parts)

    def query(self, children: list[Any]) -> QueryResult:
        """Transform query rule to QueryResult.

        Args:
            children: List containing source path, dest path, and optional conditions

        Returns:
            QueryResult dictionary
        """
        return {
            "source": children[0],
            "dest": children[1],
            "conditions": children[2] if len(children) > 2 else [],
        }


class QueryParser:
    """Parser for data conversion queries.

    This class encapsulates the Lark parser and transformer for parsing
    data conversion query strings.

    Example:
        >>> parser = QueryParser()
        >>> result = parser.parse('from input.json to output.yaml')
        >>> print(result['source']['file'])
        'input.json'
    """

    def __init__(self) -> None:
        """Initialize the query parser with grammar and transformer."""
        self._parser = Lark(QUERY_GRAMMAR, parser="lalr")
        self._transformer = QueryTransformer()
        logger.debug("QueryParser initialized")

    def parse(self, query: str) -> QueryResult:
        """Parse a query string into a QueryResult.

        Args:
            query: The query string to parse

        Returns:
            Parsed query result with source, dest, and conditions

        Raises:
            ParseError: If the query syntax is invalid

        Example:
            >>> parser = QueryParser()
            >>> result = parser.parse('from data.json to output.yaml where age > 25')
            >>> assert result['conditions'][0]['field'] == 'age'
        """
        try:
            logger.debug(f"Parsing query: {query}")
            tree = self._parser.parse(query)
            result = self._transformer.transform(tree)
            logger.info(f"Successfully parsed query: {query}")
            return result  # type: ignore
        except Exception as e:
            logger.error(f"Failed to parse query '{query}': {e}")
            raise ParseError(f"Invalid query syntax: {e}") from e
