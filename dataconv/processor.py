"""Data processing with JSONPath extraction and conditional filtering.

This module provides functionality to extract data using JSONPath expressions
and filter results based on conditional expressions.

Example:
    >>> from dataconv.processor import apply_path, apply_conditions
    >>>
    >>> data = {'users': [{'name': 'John', 'age': 30}, {'name': 'Jane', 'age': 25}]}
    >>> result = apply_path(data, "users[*].name")
    >>> # result = [{'name': 'John', 'age': 30}, {'name': 'Jane', 'age': 25}]
    >>>
    >>> conditions = [{'field': 'age', 'op': '>', 'value': 26}]
    >>> filtered = apply_conditions(result, conditions)
    >>> # filtered = [{'name': 'John', 'age': 30}]
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError

from dataconv.parser import AndExpr, BooleanExpr, Comparison, NotExpr, OrExpr, XorExpr

logger = logging.getLogger(__name__)


class ProcessorError(Exception):
    """Exception raised when data processing fails."""

    pass


@lru_cache(maxsize=128)
def _get_jsonpath_expr(path: str):
    """Get or compile JSONPath expression with caching."""
    return parse(path)


def apply_path(data: dict[str, Any], path: str | None) -> Any:
    """Extract data using JSONPath expression.

    Args:
        data: Source data dictionary
        path: JSONPath expression (e.g., "users[*]", "users[0].name", "config.database.host")
              If None or empty, returns original data

    Returns:
        Extracted data. If path matches multiple items, returns list of values.
        If single match, returns the matched value.

    Raises:
        ProcessorError: If JSONPath expression is invalid

    Example:
        >>> data = {'users': [{'name': 'John'}, {'name': 'Jane'}]}
        >>> apply_path(data, "users[*].name")
        ['John', 'Jane']
    """
    if not path:
        logger.debug("No path specified, returning original data")
        return data

    try:
        logger.debug(f"Applying JSONPath: {path}")
        jsonpath_expr = _get_jsonpath_expr(path)
        matches = jsonpath_expr.find(data)

        if not matches:
            logger.warning(f"JSONPath expression '{path}' matched no results")
            return []

        results = [match.value for match in matches]

        if len(results) == 1:
            logger.info(f"JSONPath '{path}' matched 1 result")
            return results[0]
        else:
            logger.info(f"JSONPath '{path}' matched {len(results)} results")
            return results

    except JsonPathParserError as e:
        logger.error(f"Invalid JSONPath expression '{path}': {e}")
        raise ProcessorError(f"Invalid JSONPath expression '{path}': {e}") from e
    except Exception as e:
        logger.error(f"Error applying JSONPath '{path}': {e}")
        raise ProcessorError(f"Error applying path '{path}': {e}") from e


def evaluate_condition(value: Any, op: str, expected: Any) -> bool:
    """Evaluate a single condition.

    Performs type-safe comparison with basic type coercion for numbers.

    Args:
        value: The actual value to check
        op: Comparison operator (==, !=, >, <, >=, <=)
        expected: The expected value to compare against

    Returns:
        Boolean result of the comparison

    Raises:
        ProcessorError: If operator is not supported

    Example:
        >>> evaluate_condition(30, '>', 25)
        True
        >>> evaluate_condition('John', '==', 'John')
        True
    """
    if value is None or expected is None:
        if op in ("==", "!="):
            return (value == expected) if op == "==" else (value != expected)
        return False

    try:
        if isinstance(value, (int, float)) and isinstance(expected, (int, float)):
            value_num = float(value)
            expected_num = float(expected)
        else:
            value_num = value
            expected_num = expected

        if op == "==":
            return value_num == expected_num
        elif op == "!=":
            return value_num != expected_num
        elif op == ">":
            return value_num > expected_num
        elif op == "<":
            return value_num < expected_num
        elif op == ">=":
            return value_num >= expected_num
        elif op == "<=":
            return value_num <= expected_num
        else:
            raise ProcessorError(f"Unsupported operator: {op}")

    except TypeError as e:
        logger.warning(
            f"Type error in condition evaluation: {value} {op} {expected}: {e}"
        )
        return False


def evaluate_boolean_expr(item: dict[str, Any], expr: BooleanExpr) -> bool:
    """Recursively evaluate complex boolean expressions.
    
    Args:
        item: Data item to check
        expr: Boolean expression (Comparison, AndExpr, OrExpr, NotExpr, XorExpr)
    
    Returns:
        True if expression evaluates to true for this item
    
    Examples:
        >>> evaluate_boolean_expr({"age": 25}, Comparison("age", ">", 18))
        True
        
        >>> evaluate_boolean_expr(
        ...     {"age": 25, "status": "active"},
        ...     AndExpr([Comparison("age", ">", 18), 
        ...             Comparison("status", "==", "active")])
        ... )
        True
    """
    if isinstance(expr, Comparison):
        value = item.get(expr.field)
        expected = expr.value
        
        if isinstance(expected, tuple):
            expected_val, is_negated = expected
            
            if isinstance(expected_val, str):
                # Check if field exists in item (not if value is not None)
                if expected_val in item:
                    # It's a field reference - get the actual value
                    field_value = item[expected_val]
                    expected = not field_value if is_negated else field_value
                else:
                    # Treat as literal string value
                    expected = not expected_val if is_negated else expected_val
            else:
                expected = not expected_val if is_negated else expected_val
        
        return evaluate_condition(value, expr.op, expected)
    
    elif isinstance(expr, NotExpr):
        return not evaluate_boolean_expr(item, expr.expr)
    
    elif isinstance(expr, AndExpr):
        return all(evaluate_boolean_expr(item, e) for e in expr.exprs)
    
    elif isinstance(expr, OrExpr):
        return any(evaluate_boolean_expr(item, e) for e in expr.exprs)
    
    elif isinstance(expr, XorExpr):
        true_count = sum(1 for e in expr.exprs if evaluate_boolean_expr(item, e))
        return true_count == 1
    
    else:
        raise ProcessorError(f"Unknown expression type: {type(expr).__name__}")


def apply_conditions(
    data: list[dict[str, Any]], expr: BooleanExpr | None
) -> list[dict[str, Any]]:
    """Filter list of dictionaries using boolean expressions.

    Args:
        data: List of dictionaries to filter
        expr: Boolean expression tree (None means no filtering)

    Returns:
        Filtered list containing only items matching the expression

    Example:
        >>> data = [{'name': 'John', 'age': 30}, {'name': 'Jane', 'age': 25}]
        >>> expr = Comparison('age', '>=', 26)
        >>> apply_conditions(data, expr)
        [{'name': 'John', 'age': 30}]
    """
    if expr is None:
        logger.debug("No conditions specified, returning all data")
        return data

    if not isinstance(data, list):
        logger.warning(f"Expected list for filtering, got {type(data).__name__}")
        data = [data] if isinstance(data, dict) else []

    logger.debug(f"Applying boolean expression to {len(data)} items")

    filtered_results = [
        item for item in data
        if isinstance(item, dict) and evaluate_boolean_expr(item, expr)
    ]

    logger.info(
        f"Filtered {len(data)} items to {len(filtered_results)} "
        f"matching boolean expression"
    )

    return filtered_results


def process_data(
    data: dict[str, Any],
    path: str | None,
    conditions: BooleanExpr | None,
) -> Any:
    """Process data by applying path extraction and conditions.

    This is a convenience function that combines path extraction and filtering.

    Args:
        data: Source data dictionary
        path: Optional JSONPath expression
        conditions: Optional boolean expression for filtering

    Returns:
        Processed data (extracted and filtered)

    Example:
        >>> data = {'users': [{'name': 'John', 'age': 30}, {'name': 'Jane', 'age': 25}]}
        >>> expr = Comparison('age', '>', 26)
        >>> result = process_data(data, "users[*]", expr)
        >>> # result = [{'name': 'John', 'age': 30}]
    """
    logger.debug(
        f"Processing data with path='{path}' and conditions={'present' if conditions else 'none'}"
    )

    extracted = apply_path(data, path)

    if conditions:
        extracted = apply_conditions(extracted, conditions)

    return extracted
