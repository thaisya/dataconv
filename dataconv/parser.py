"""Parser and transformer for the Data Converter query language.

This module provides parsing capabilities for the data conversion query syntax
using Lark parser. It transforms the parse tree into typed Python data structures.

Example:
    >>> from dataconv.parser import QueryParser
    >>> parser = QueryParser()
    >>> result = parser.parse('from input.json[users[*]] to output.yaml where age > 25')
    >>> print(result['source']['file'])
    'input.json'
"""

import logging
from dataclasses import dataclass
from typing import Any, TypedDict, Union

from lark import Lark, Token, Transformer

from dataconv.grammar import QUERY_GRAMMAR

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Exception raised when query parsing fails."""

    pass


@dataclass
class Comparison:
    """Single comparison condition.
    
    Example: age > 18
    """
    field: str
    op: str
    value: Any


@dataclass
class NotExpr:
    """NOT expression - negates inner expression.
    
    Example: !(status == "active")
    """
    expr: "BooleanExpr"


@dataclass
class AndExpr:
    """AND expression - all sub-expressions must be true.
    
    Example: age > 18 AND status == "active"
    """
    exprs: list["BooleanExpr"]


@dataclass
class OrExpr:
    """OR expression - at least one sub-expression must be true.
    
    Example: age < 18 OR role == "admin"
    """
    exprs: list["BooleanExpr"]


@dataclass
class XorExpr:
    """XOR expression - exactly one sub-expression must be true.
    
    Example: premium == true XOR trial == true
    """
    exprs: list["BooleanExpr"]


# Type alias for any boolean expression
BooleanExpr = Union[Comparison, NotExpr, AndExpr, OrExpr, XorExpr]


# Legacy compatibility - keep old Condition type
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
        dest: Destination file path specification (None for view-only queries)
        conditions: Boolean expression tree (can be Comparison, And, Or, Not, Xor)
    """

    source: PathSpec
    dest: PathSpec | None
    conditions: BooleanExpr | None


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

    def SINGLE_QUOTED_STRING(self, token: Token) -> str:
        """Transform SINGLE_QUOTED_STRING token to string (removes quotes)."""
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

    def field(self, children: list[Any]) -> str:
        """Transform field rule to field name string.
        
        Args:
            children: List containing [NAME]
            
        Returns:
            Field name as string
        """
        return str(children[0])
    
    def value(self, children: list[Any]) -> Any:
        """Transform value rule to actual value.
        
        Args:
            children: List containing one of [ESCAPED_STRING, SIGNED_NUMBER, TRUE, FALSE, NULL, NAME]
            
        Returns:
            The actual value (string, number, bool, None, or field name)
        """
        return children[0]

    def field_value(self, children: list[Any]) -> tuple[Any, bool]:
        """Transform field_value rule to actual value and negation flag.
        
        Args:
            children: List containing [Token("!"), value] or [value]
            
        Returns:
            Tuple of (actual value, is_negated flag)
        """
        if len(children) == 2:
            # First element is the "!" token, second is the transformed value
            return (children[1], True)
        else:
            # Just the transformed value, no negation
            return (children[0], False)

    def OP(self, token: Token) -> str:
        """Transform OP token to operator string."""
        return str(token.value)

    def field_check(self, children: list[Any]) -> Comparison:
        """Transform standalone field to truthiness comparison.
        
        Converts standalone field references to comparisons against True.
        This allows:
            - 'where status' → Comparison(status, ==, True)
            - 'where !status' → NotExpr(Comparison(status, ==, True))
        
        Args:
            children: List containing [field_name]
            
        Returns:
            Comparison object checking field == True
        """
        field_name = children[0]
        # Use tuple format (value, is_negated) for consistency
        return Comparison(field=field_name, op="==", value=(True, False))

    def comparison(self, children: list[Any]) -> Comparison:
        """Transform comparison rule to Comparison object.

        Args:
            children: List containing [field_name, op, value]

        Returns:
            Comparison object with field, op, and value
        """
        return Comparison(field=children[0], op=children[1], value=children[2])
    
    def atom(self, children: list[Any]) -> BooleanExpr:
        """Transform atom rule (parenthesized expression or comparison)."""
        return children[0]
    
    def not_expr(self, children: list[Any]) -> BooleanExpr:
        """Transform not_expr rule - just pass through.
        
        not_expr is either negation or atom, both handled by their own transformers.
        """
        return children[0]
    
    def negation(self, children: list[Any]) -> BooleanExpr:
        """Transform negation rule ("!" not_expr).
        
        The "!" token is consumed, children contains the negated expression.
        """
        return NotExpr(expr=children[0])
    
    def and_expr(self, children: list[Any]) -> BooleanExpr:
        """Transform and_expr rule.
        
        Single child: pass through
        Multiple children: wrap in AndExpr
        """
        if len(children) == 1:
            return children[0]
        return AndExpr(exprs=children)
    
    def or_expr(self, children: list[Any]) -> BooleanExpr:
        """Transform or_expr rule.
        
        Single child: pass through
        Multiple children: wrap in OrExpr
        """
        if len(children) == 1:
            return children[0]
        return OrExpr(exprs=children)
    
    def xor_expr(self, children: list[Any]) -> BooleanExpr:
        """Transform xor_expr rule.
        
        Single child: pass through
        Multiple children: wrap in XorExpr
        """
        if len(children) == 1:
            return children[0]
        return XorExpr(exprs=children)
    
    def condition_list(self, children: list[Any]) -> BooleanExpr:
        """Transform condition_list to boolean expression tree."""
        return children[0]

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

    def path_segment(self, children: list[Any]) -> str:
        """Extract non-bracket characters from path segment.
        
        Args:
            children: Token containing path segment text
            
        Returns:
            Path segment as string
        """
        return str(children[0])
    
    def quoted_string(self, children: list[Any]) -> str:
        """Preserve quoted strings with their quotes for JSONPath.
        
        Args:
            children: ESCAPED_STRING token
            
        Returns:
            Quoted string (e.g., '"name"')
        """
        return f'"{children[0]}"'
    
    def nested_bracket(self, children: list[Any]) -> str:
        """Wrap nested path content in brackets.
        
        Args:
            children: List containing the path_content
            
        Returns:
            Bracketed content (e.g., '[0]', '[*]')
        """
        return f"[{children[0]}]"
    
    def path_content(self, children: list[Any]) -> str:
        """Concatenate all path segments, brackets, and strings.
        
        Args:
            children: Mix of path_segment, nested_bracket, quoted_string
            
        Returns:
            Concatenated JSONPath content
        """
        return "".join(str(child) for child in children)
    
    def path_bracket(self, children: list[Any]) -> str:
        """Transform path_bracket to JSONPath expression.

        Args:
            children: List containing the path_content

        Returns:
            JSONPath expression without outer brackets
        """
        return str(children[0])

    def query(self, children: list[Any]) -> QueryResult:
        """Transform query rule to QueryResult.

        Args:
            children: List containing source path, optional dest path, and optional conditions
                     Possible structures:
                     - [source] - Just source (view-only)
                     - [source, dest] - Source and dest (no filter)
                     - [source, conditions] - Source with filter (view-only)
                     - [source, dest, conditions] - Full query

        Returns:
            QueryResult dictionary
        """
        source = children[0]
        
        # Determine what we have based on children count and types
        if len(children) == 1:
            # Just source: "from data.json"
            return {"source": source, "dest": None, "conditions": None}
        elif len(children) == 2:
            # Two items - could be:
            # 1. source + dest: "from data.json to output.yaml"
            # 2. source + conditions: "from data.json where age > 25"
            if isinstance(children[1], dict) and 'file' in children[1]:
                return {"source": source, "dest": children[1], "conditions": None}
            else:
                return {"source": source, "dest": None, "conditions": children[1]}
        else:
            # Three items: source + dest + conditions
            return {"source": source, "dest": children[1], "conditions": children[2]}


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

    _shared_parser: Lark | None = None

    def __init__(self) -> None:
        """Initialize the query parser with grammar and transformer."""
        if QueryParser._shared_parser is None:
            QueryParser._shared_parser = Lark(QUERY_GRAMMAR, parser="lalr")
        self._parser = QueryParser._shared_parser
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

    def _parse_conditions(self, conditions: str) -> BooleanExpr:
        """Parse standalone where clause without FROM...TO.
        
        Args:
            conditions: Boolean expression (e.g., "age > 25 AND status == 'active'")
        
        Returns:
            BooleanExpr object
        
        Example:
            >>> parser = QueryParser()
            >>> expr = parser._parse_conditions("age > 25")
            >>> # Returns: Comparison('age', '>', 25)
        """
        dummy_query = f"from _ to output.json where {conditions}"

        parsed = self.parse(dummy_query)
        return parsed["conditions"]
